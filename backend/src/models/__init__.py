import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models.database import Base, engine, get_db, init_db
from models.database import AdminUser, Device, FamilyMember, RecognitionLog, SystemConfig, NotificationLog

__all__ = [
    "Base",
    "engine",
    "get_db",
    "init_db",
    "AdminUser",
    "Device",
    "FamilyMember",
    "RecognitionLog",
    "SystemConfig",
    "NotificationLog"
]
