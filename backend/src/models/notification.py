import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from models.database import Base


class NotificationLog(Base):
    """通知日志模型"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(Integer, ForeignKey("recognition_logs.id"))
    notification_type = Column(String(50))
    content = Column(Text)
    status = Column(String(20), default="pending")
    sent_at = Column(DateTime)
    error_message = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "log_id": self.log_id,
            "notification_type": self.notification_type,
            "content": self.content,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "error_message": self.error_message
        }
