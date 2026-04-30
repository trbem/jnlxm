import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ==================== 设备相关 ====================

class DeviceRegisterRequest(BaseModel):
    device_name: str
    device_type: str = "ESP32-S3-EYE"


class DeviceRegisterResponse(BaseModel):
    device_id: int
    device_name: str
    device_token: str
    success: bool


class DeviceHeartbeatRequest(BaseModel):
    device_token: str


class DeviceUploadRequest(BaseModel):
    device_token: str
    timestamp: Optional[str] = None


class DeviceConfigResponse(BaseModel):
    face_threshold: float
    detection_interval: int
    notification_enabled: bool


# ==================== 成员相关 ====================

class MemberCreateRequest(BaseModel):
    name: str
    relationship: Optional[str] = None
    notes: Optional[str] = None


class MemberUpdateRequest(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class MemberResponse(BaseModel):
    id: int
    name: str
    avatar_image_path: Optional[str]
    relationship: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    is_active: bool
    notes: Optional[str]


# ==================== 日志相关 ====================

class RecognitionLogResponse(BaseModel):
    id: int
    member_id: Optional[int]
    member_name: Optional[str]
    confidence: Optional[float]
    matched: bool
    image_path: Optional[str]
    timestamp: Optional[datetime]
    device_id: Optional[str]
    recognition_type: str
    note: Optional[str]


class LogListQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    member_id: Optional[int] = None
    device_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    recognition_type: Optional[str] = None


class LogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[RecognitionLogResponse]


# ==================== 统计数据 ====================

class StatsOverview(BaseModel):
    total_members: int
    total_logs: int
    today_logs: int
    stranger_alerts: int
    recognition_rate: float
    recent_logs: List[RecognitionLogResponse]


# ==================== 配置相关 ====================

class ConfigUpdateRequest(BaseModel):
    key: str
    value: str


class ConfigResponse(BaseModel):
    face_threshold: float
    detection_interval: int
    notification_enabled: bool
    stranger_alert: bool


# ==================== 识别结果 ====================

class RecognitionResult(BaseModel):
    matched: bool
    member_id: Optional[int] = None
    member_name: Optional[str] = None
    confidence: float
    recognition_type: str


# ==================== 认证相关 ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
