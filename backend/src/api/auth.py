import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from models.database import get_db, AdminUser
from schemas import LoginRequest, TokenResponse
from config import settings

router = APIRouter(prefix="/api/auth", tags=["认证接口"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == request.username).first()
    if not user or not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    user.last_login = datetime.now()
    db.commit()

    return TokenResponse(
        access_token="token_" + user.username,
        token_type="bearer",
        user={"id": user.id, "username": user.username, "is_super_admin": user.is_super_admin}
    )


@router.post("/logout")
async def logout():
    return {"success": True, "message": "已登出"}
