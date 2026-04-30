import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from models.database import get_db, FamilyMember, RecognitionLog
from schemas import StatsOverview

router = APIRouter(prefix="/api/stats", tags=["统计接口"])


@router.get("/overview", response_model=StatsOverview)
async def get_stats_overview(db: Session = Depends(get_db)):
    total_members = db.query(FamilyMember).filter(FamilyMember.is_active == True).count()
    total_logs = db.query(RecognitionLog).count()

    today = datetime.now().date()
    today_logs = db.query(RecognitionLog).filter(RecognitionLog.timestamp >= today).count()

    stranger_alerts = db.query(RecognitionLog).filter(RecognitionLog.recognition_type == "unknown").count()

    if total_logs > 0:
        known = db.query(RecognitionLog).filter(RecognitionLog.recognition_type == "known").count()
        recognition_rate = round(known / total_logs * 100, 2)
    else:
        recognition_rate = 0.0

    recent_logs = db.query(RecognitionLog).order_by(desc(RecognitionLog.timestamp)).limit(10).all()

    return StatsOverview(
        total_members=total_members,
        total_logs=total_logs,
        today_logs=today_logs,
        stranger_alerts=stranger_alerts,
        recognition_rate=recognition_rate,
        recent_logs=[log_to_dict(log) for log in recent_logs]
    )


@router.get("/trend")
async def get_recognition_trend(db: Session = Depends(get_db)):
    days = 7
    trend_data = []
    today = datetime.now().date()

    for i in range(days - 1, -1, -1):
        target_date = today - timedelta(days=i)
        date_start = datetime.combine(target_date, datetime.min.time())
        date_end = datetime.combine(target_date, datetime.max.time())

        known_count = db.query(RecognitionLog).filter(
            RecognitionLog.timestamp >= date_start,
            RecognitionLog.timestamp <= date_end,
            RecognitionLog.recognition_type == "known"
        ).count()

        unknown_count = db.query(RecognitionLog).filter(
            RecognitionLog.timestamp >= date_start,
            RecognitionLog.timestamp <= date_end,
            RecognitionLog.recognition_type == "unknown"
        ).count()

        trend_data.append({
            "date": target_date.strftime("%m-%d"),
            "known": known_count,
            "unknown": unknown_count,
            "total": known_count + unknown_count
        })

    return trend_data


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
