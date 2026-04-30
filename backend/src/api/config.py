import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import get_db, SystemConfig
from schemas import ConfigUpdateRequest, ConfigResponse

router = APIRouter(prefix="/api/config", tags=["配置接口"])


@router.get("/get", response_model=ConfigResponse)
async def get_config(db: Session = Depends(get_db)):
    configs = db.query(SystemConfig).all()
    config_dict = {c.key: c.value for c in configs}

    return ConfigResponse(
        face_threshold=float(config_dict.get("face_threshold", "0.6")),
        detection_interval=int(config_dict.get("detection_interval", "10")),
        notification_enabled=config_dict.get("notification_enabled", "true").lower() == "true",
        stranger_alert=config_dict.get("stranger_alert", "true").lower() == "true"
    )


@router.get("/all")
async def get_all_configs(db: Session = Depends(get_db)):
    configs = db.query(SystemConfig).all()
    return {c.key: c.value for c in configs}


@router.put("/update")
async def update_config(request: ConfigUpdateRequest, db: Session = Depends(get_db)):
    config = db.query(SystemConfig).filter(SystemConfig.key == request.key).first()

    if config:
        config.value = request.value
    else:
        config = SystemConfig(key=request.key, value=request.value)
        db.add(config)

    db.commit()
    return {"success": True, "message": "配置已更新"}
