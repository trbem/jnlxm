import os
import sys
import json

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime
import logging

from models.database import get_db, Device, SystemConfig, RecognitionLog, FamilyMember
from schemas import (
    DeviceRegisterRequest, DeviceRegisterResponse,
    DeviceConfigResponse, RecognitionResult
)
from services.face_service import face_service
from services.member_service import member_service
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/device", tags=["设备端接口"])


async def send_notification(db: Session, log):
    """发送识别通知"""
    from services.notification_service import notification_service

    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == "notification_enabled").first()
        if config and config.value.lower() != "true":
            return

        notification_ways_config = db.query(SystemConfig).filter(
            SystemConfig.key == "notification_ways"
        ).first()
        if notification_ways_config:
            try:
                ways = json.loads(notification_ways_config.value)
            except:
                ways = [notification_ways_config.value]
        else:
            ways = ["wecom"]

        stranger_alert_config = db.query(SystemConfig).filter(
            SystemConfig.key == "stranger_alert"
        ).first()
        stranger_alert_enabled = stranger_alert_config.value.lower() == "true" if stranger_alert_config else True

        if log.recognition_type == "unknown" and not stranger_alert_enabled:
            return

        if log.recognition_type == "known":
            return

        await notification_service.send_recognition_notification(db, log, ways)
        logger.info("通知发送完成")
    except Exception as e:
        logger.error(f"发送通知失败: {e}")


def generate_device_token():
    import secrets
    return secrets.token_hex(32)


@router.post("/register", response_model=DeviceRegisterResponse)
async def register_device(request: DeviceRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Device).filter(Device.device_name == request.device_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="设备名已存在")

    device_token = generate_device_token()

    device = Device(
        device_name=request.device_name,
        device_token=device_token,
        device_type=request.device_type,
        is_active=True
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return DeviceRegisterResponse(
        device_id=device.id,
        device_name=device.device_name,
        device_token=device.device_token,
        success=True
    )


@router.post("/heartbeat")
async def device_heartbeat(device_token: str = Form(...), db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_token == device_token).first()
    if not device:
        raise HTTPException(status_code=401, detail="无效的设备令牌")

    device.last_seen = datetime.now()
    db.commit()

    return {"success": True, "message": "心跳成功"}


@router.post("/upload", response_model=RecognitionResult)
async def upload_face_data(
    device_token: str = Form(...),
    image: UploadFile = File(...),
    face_encoding: Optional[str] = Form(None),
    timestamp: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.device_token == device_token).first()
    if not device:
        raise HTTPException(status_code=401, detail="无效的设备令牌")

    device.last_seen = datetime.now()

    file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    content = await image.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # 1. 提取人脸特征
        current_encoding = face_service.encode_image(content)

        # 2. 获取所有家庭成员的特征向量
        all_encodings = member_service.get_all_active_encodings(db)

        if not all_encodings:
            # 没有家庭成员，返回陌生人
            log = RecognitionLog(
                member_id=None,
                member_name=None,
                confidence=0.0,
                matched=False,
                image_path=unique_filename,
                device_id=device.device_name,
                recognition_type="unknown",
                note="没有注册的家庭成员"
            )
            db.add(log)
            db.commit()
            db.refresh(log)

            # 发送陌生人通知
            await send_notification(db, log)

            return RecognitionResult(
                matched=False,
                member_id=None,
                member_name=None,
                confidence=0.0,
                recognition_type="unknown"
            )

        # 3. 比对所有人脸
        matched, member_id, member_name, confidence = face_service.compare_faces(
            current_encoding, all_encodings
        )

        # 4. 确定识别类型
        recognition_type = face_service.get_recognition_type(confidence)

        # 5. 记录识别日志
        log = RecognitionLog(
            member_id=member_id,
            member_name=member_name,
            confidence=round(confidence, 4),
            matched=matched,
            image_path=unique_filename,
            device_id=device.device_name,
            recognition_type=recognition_type,
            note=f"识别类型: {recognition_type}"
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        logger.info(f"人脸识别结果: {member_name}, 置信度: {confidence:.4f}, 类型: {recognition_type}")

        # 6. 发送通知
        await send_notification(db, log)

        return RecognitionResult(
            matched=matched,
            member_id=member_id,
            member_name=member_name,
            confidence=round(confidence, 4),
            recognition_type=recognition_type
        )

    except ValueError as e:
        # 未检测到人脸
        logger.warning(f"图片中未检测到人脸: {e}")
        log = RecognitionLog(
            member_id=None,
            member_name=None,
            confidence=0.0,
            matched=False,
            image_path=unique_filename,
            device_id=device.device_name,
            recognition_type="no_face",
            note=f"未检测到人脸: {str(e)}"
        )
        db.add(log)
        db.commit()

        return RecognitionResult(
            matched=False,
            member_id=None,
            member_name=None,
            confidence=0.0,
            recognition_type="no_face"
        )

    except Exception as e:
        logger.error(f"人脸识别出错: {e}")
        return RecognitionResult(
            matched=False,
            member_id=None,
            member_name=None,
            confidence=0.0,
            recognition_type="error"
        )


@router.get("/config", response_model=DeviceConfigResponse)
async def get_device_config(db: Session = Depends(get_db)):
    configs = db.query(SystemConfig).all()
    config_dict = {c.key: c.value for c in configs}

    return DeviceConfigResponse(
        face_threshold=float(config_dict.get("face_threshold", "0.6")),
        detection_interval=int(config_dict.get("detection_interval", "10")),
        notification_enabled=config_dict.get("notification_enabled", "true").lower() == "true"
    )


@router.get("/list")
async def get_device_list(db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    devices = db.query(Device).all()
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())

    result = []
    for device in devices:
        today_logs = db.query(RecognitionLog).filter(
            RecognitionLog.device_id == device.device_name,
            RecognitionLog.timestamp >= today_start
        ).count()

        stranger_count = db.query(RecognitionLog).filter(
            RecognitionLog.device_id == device.device_name,
            RecognitionLog.recognition_type == "unknown",
            RecognitionLog.timestamp >= today_start
        ).count()

        result.append({
            "id": device.id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "is_active": device.is_active,
            "is_online": device.last_seen and (datetime.now() - device.last_seen).seconds < 120 if device.last_seen else False,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "today_recognitions": today_logs,
            "today_strangers": stranger_count
        })

    return result
