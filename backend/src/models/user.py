import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from models.database import Base

pwd_context = None
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except:
    pass


class AdminUser(Base):
    """管理员用户模型"""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime)

    def verify_password(self, password: str) -> bool:
        if pwd_context:
            return pwd_context.verify(password, self.hashed_password)
        else:
            return self.hashed_password == password

    @staticmethod
    def hash_password(password: str) -> str:
        if pwd_context:
            return pwd_context.hash(password)
        else:
            return password

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "is_super_admin": self.is_super_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
