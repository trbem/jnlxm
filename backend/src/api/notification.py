import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.database import get_db
from services.notification_service import notification_service

router = APIRouter(prefix="/api/notification", tags=["通知接口"])


class TestNotificationRequest(BaseModel):
    content: str
    way: str = "wecom"


@router.post("/test")
async def test_notification(request: TestNotificationRequest, db: Session = Depends(get_db)):
    if request.way == "wecom":
        success = await notification_service.send_wecom_notification(request.content)
    elif request.way == "dingtalk":
        success = await notification_service.send_dingtalk_notification(request.content)
    elif request.way == "email":
        success = notification_service.send_email_notification("测试通知", request.content)
    else:
        raise HTTPException(status_code=400, detail="不支持的通知方式")

    if success:
        return {"success": True, "message": "通知发送成功"}
    else:
        return {"success": False, "message": "通知发送失败，请检查配置"}


@router.get("/test/connection")
async def test_connection():
    from config import settings
    return {
        "wecom_configured": bool(settings.WECOM_WEBHOOK_URL),
        "dingtalk_configured": bool(settings.DINGTALK_WEBHOOK_URL),
        "email_configured": bool(settings.EMAIL_HOST and settings.EMAIL_USER)
    }
