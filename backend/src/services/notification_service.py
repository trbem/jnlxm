import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from sqlalchemy.orm import Session

from config import settings
from models.database import NotificationLog, RecognitionLog


class NotificationService:
    """通知服务"""

    @staticmethod
    async def send_wecom_notification(content: str, webhook_url: str = None) -> bool:
        if not webhook_url:
            webhook_url = settings.WECOM_WEBHOOK_URL
        if not webhook_url:
            return False
        try:
            async with httpx.AsyncClient() as client:
                payload = {"msgtype": "text", "text": {"content": content}}
                response = await client.post(webhook_url, json=payload, timeout=10)
                return response.status_code == 200
        except Exception as e:
            print(f"企业微信通知发送失败: {e}")
            return False

    @staticmethod
    async def send_dingtalk_notification(content: str, webhook_url: str = None) -> bool:
        if not webhook_url:
            webhook_url = settings.DINGTALK_WEBHOOK_URL
        if not webhook_url:
            return False
        try:
            async with httpx.AsyncClient() as client:
                payload = {"msgtype": "text", "text": {"content": content}}
                response = await client.post(webhook_url, json=payload, timeout=10)
                return response.status_code == 200
        except Exception as e:
            print(f"钉钉通知发送失败: {e}")
            return False

    @staticmethod
    def send_email_notification(subject: str, content: str) -> bool:
        if not settings.EMAIL_HOST or not settings.EMAIL_USER:
            return False
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_FROM or settings.EMAIL_USER
            msg['To'] = settings.EMAIL_USER
            msg['Subject'] = subject
            msg.attach(MIMEText(content, 'html', 'utf-8'))
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                server.starttls()
                server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"邮件通知发送失败: {e}")
            return False

    @staticmethod
    def create_notification_log(db: Session, log_id: int, notification_type: str,
                                content: str, status: str, error_message: str = None) -> NotificationLog:
        notification_log = NotificationLog(
            log_id=log_id,
            notification_type=notification_type,
            content=content,
            status=status,
            sent_at=datetime.now() if status == "sent" else None,
            error_message=error_message
        )
        db.add(notification_log)
        db.commit()
        db.refresh(notification_log)
        return notification_log

    @staticmethod
    async def send_recognition_notification(db: Session, recognition_log: RecognitionLog,
                                          notification_ways: list = None) -> None:
        if recognition_log.recognition_type == "known":
            title = "家庭成员识别"
            content = f"家庭成员 {recognition_log.member_name} 已回家 ({recognition_log.confidence:.2%})"
        elif recognition_log.recognition_type == "unknown":
            title = "陌生人告警"
            content = f"检测到陌生人闯入 ({recognition_log.confidence:.2%})"
        else:
            title = "待审核识别"
            content = f"识别置信度较低 ({recognition_log.confidence:.2%})，请人工审核"

        content += f"\n时间: {recognition_log.timestamp.strftime('%Y-%m-%d %H:%M:%S') if recognition_log.timestamp else '未知'}"
        content += f"\n设备: {recognition_log.device_id or '未知'}"

        if notification_ways is None:
            notification_ways = ["wecom"]

        for way in notification_ways:
            try:
                if way == "wecom":
                    success = await NotificationService.send_wecom_notification(content)
                elif way == "dingtalk":
                    success = await NotificationService.send_dingtalk_notification(content)
                elif way == "email":
                    success = NotificationService.send_email_notification(title, content)
                else:
                    continue

                NotificationService.create_notification_log(
                    db=db,
                    log_id=recognition_log.id,
                    notification_type=way,
                    content=content,
                    status="sent" if success else "failed",
                    error_message=None if success else "发送失败"
                )
            except Exception as e:
                NotificationService.create_notification_log(
                    db=db,
                    log_id=recognition_log.id,
                    notification_type=way,
                    content=content,
                    status="failed",
                    error_message=str(e)
                )


notification_service = NotificationService()
