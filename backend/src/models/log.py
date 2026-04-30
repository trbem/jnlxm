import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float
from sqlalchemy.sql import func
from models.database import Base


class RecognitionLog(Base):
    """识别日志模型"""
    __tablename__ = "recognition_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True)
    member_name = Column(String(100))
    confidence = Column(Float)
    matched = Column(Boolean, default=False)
    image_path = Column(String(255))
    timestamp = Column(DateTime, server_default=func.now())
    device_id = Column(String(50))
    recognition_type = Column(String(20), default="unknown")
    note = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "member_id": self.member_id,
            "member_name": self.member_name,
            "confidence": self.confidence,
            "matched": self.matched,
            "image_path": self.image_path,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "device_id": self.device_id,
            "recognition_type": self.recognition_type,
            "note": self.note
        }
