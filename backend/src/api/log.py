import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import desc

from models.database import get_db, RecognitionLog
from schemas import LogListResponse

router = APIRouter(prefix="/api/log", tags=["日志接口"])


@router.get("/list", response_model=LogListResponse)
async def get_log_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    member_id: Optional[int] = None,
    device_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    recognition_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(RecognitionLog)

    if member_id:
        query = query.filter(RecognitionLog.member_id == member_id)
    if device_id:
        query = query.filter(RecognitionLog.device_id == device_id)
    if recognition_type:
        query = query.filter(RecognitionLog.recognition_type == recognition_type)
    if start_date:
        query = query.filter(RecognitionLog.timestamp >= start_date)
    if end_date:
        query = query.filter(RecognitionLog.timestamp <= end_date)

    total = query.count()
    offset = (page - 1) * page_size
    logs = query.order_by(desc(RecognitionLog.timestamp)).offset(offset).limit(page_size).all()

    return LogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[log_to_dict(log) for log in logs]
    )


@router.get("/recent")
async def get_recent_logs(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    logs = db.query(RecognitionLog).order_by(desc(RecognitionLog.timestamp)).limit(limit).all()
    return [log_to_dict(log) for log in logs]


def log_to_dict(log):
    return {
        "id": log.id,
        "member_id": log.member_id,
        "member_name": log.member_name,
        "confidence": log.confidence,
        "matched": log.matched,
        "image_path": log.image_path,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        "device_id": log.device_id,
        "recognition_type": log.recognition_type,
        "note": log.note
    }
