import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.face_service import face_service
from services.member_service import member_service
from services.log_service import log_service
from services.notification_service import notification_service
from services.auth_service import (
    create_access_token,
    verify_token,
    authenticate_user,
    generate_device_token,
    verify_device_token
)

__all__ = [
    "face_service",
    "member_service",
    "log_service",
    "notification_service",
    "create_access_token",
    "verify_token",
    "authenticate_user",
    "generate_device_token",
    "verify_device_token"
]
