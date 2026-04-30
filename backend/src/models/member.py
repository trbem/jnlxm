import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from models.database import Base


class FamilyMember(Base):
    """家庭成员模型"""
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    avatar_image_path = Column(String(255))
    face_encoding = Column(Text, nullable=False)
    relationship = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    notes = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "avatar_image_path": self.avatar_image_path,
            "relationship": self.relationship,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "notes": self.notes
        }
