import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{BASE_DIR}/jkxt.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============== 定义所有模型 ==============

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime)
    last_login = Column(DateTime)

    def verify_password(self, password):
        return self.hashed_password == password

    @staticmethod
    def hash_password(password):
        return password


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_name = Column(String(100), nullable=False)
    device_token = Column(String(64), unique=True, nullable=False)
    device_type = Column(String(50), default="ESP32-S3-EYE")
    registered_at = Column(DateTime)
    last_seen = Column(DateTime)
    is_active = Column(Boolean, default=True)


class FamilyMember(Base):
    __tablename__ = "family_members"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    avatar_image_path = Column(String(255))
    face_encoding = Column(Text, nullable=False)
    relationship = Column(String(50))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    notes = Column(Text)


class RecognitionLog(Base):
    __tablename__ = "recognition_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer)
    member_name = Column(String(100))
    confidence = Column(Float)
    matched = Column(Boolean, default=False)
    image_path = Column(String(255))
    timestamp = Column(DateTime)
    device_id = Column(String(50))
    recognition_type = Column(String(20), default="unknown")
    note = Column(Text)


class SystemConfig(Base):
    __tablename__ = "system_config"
    key = Column(String(100), primary_key=True)
    value = Column(Text)
    description = Column(String(255))
    updated_at = Column(DateTime)


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(Integer)
    notification_type = Column(String(50))
    content = Column(Text)
    status = Column(String(20), default="pending")
    sent_at = Column(DateTime)
    error_message = Column(Text)


# ============== 数据库操作函数 ==============

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，创建所有表和默认数据"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 创建默认管理员
        admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        if not admin:
            admin = AdminUser(
                username="admin",
                hashed_password=AdminUser.hash_password("admin123"),
                is_super_admin=True
            )
            db.add(admin)

        # 创建默认配置
        default_configs = [
            ("face_threshold", "0.6", "人脸识别相似度阈值"),
            ("detection_interval", "10", "检测间隔(秒)"),
            ("notification_enabled", "true", "是否启用通知"),
            ("notification_ways", '["wecom"]', "通知方式"),
            ("stranger_alert", "true", "陌生人是否报警"),
        ]

        for key, value, desc in default_configs:
            config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if not config:
                config = SystemConfig(key=key, value=value, description=desc)
                db.add(config)

        db.commit()
        print("数据库初始化成功!")
    except Exception as e:
        db.rollback()
        print(f"初始化数据库出错: {e}")
        raise
    finally:
        db.close()
