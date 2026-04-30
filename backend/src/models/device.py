import os
import sys

# 添加 backend 目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from models.database import Base


class Device(Base):
    """设备模型"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_name = Column(String(100), nullable=False)
    device_token = Column(String(64), unique=True, nullable=False)
    device_type = Column(String(50), default="ESP32-S3-EYE")
    registered_at = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, onupdate=func.now())
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_active": self.is_active
        }
