import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from api.device import router as device_router
from api.member import router as member_router
from api.log import router as log_router
from api.stats import router as stats_router
from api.config import router as config_router
from api.auth import router as auth_router
from api.notification import router as notification_router

__all__ = [
    "device_router",
    "member_router",
    "log_router",
    "stats_router",
    "config_router",
    "auth_router",
    "notification_router"
]
