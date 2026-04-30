import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.database import RecognitionLog


class LogService:
    """识别日志服务"""

    @staticmethod
    def create_log(db: Session, member_id: int = None, member_name: str = None,
                   confidence: float = 0.0, matched: bool = False,
                   image_path: str = None, device_id: str = None,
                   recognition_type: str = "unknown", note: str = None) -> RecognitionLog:
        log = RecognitionLog(
            member_id=member_id,
            member_name=member_name,
            confidence=confidence,
            matched=matched,
            image_path=image_path,
            device_id=device_id,
            recognition_type=recognition_type,
            note=note
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def get_logs(db: Session, page: int = 1, page_size: int = 20,
                 member_id: int = None, device_id: str = None,
                 start_date: str = None, end_date: str = None,
                 recognition_type: str = None) -> tuple:
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

        return total, logs

    @staticmethod
    def get_recent_logs(db: Session, limit: int = 10) -> List[RecognitionLog]:
        return db.query(RecognitionLog).order_by(desc(RecognitionLog.timestamp)).limit(limit).all()

    @staticmethod
    def count_today_logs(db: Session) -> int:
        today = datetime.now().date()
        return db.query(RecognitionLog).filter(
            RecognitionLog.timestamp >= today
        ).count()

    @staticmethod
    def count_stranger_alerts(db: Session) -> int:
        return db.query(RecognitionLog).filter(
            RecognitionLog.recognition_type == "unknown"
        ).count()

    @staticmethod
    def get_recognition_rate(db: Session) -> float:
        total = db.query(RecognitionLog).count()
        if total == 0:
            return 0.0
        known = db.query(RecognitionLog).filter(
            RecognitionLog.recognition_type == "known"
        ).count()
        return round(known / total * 100, 2)


log_service = LogService()
