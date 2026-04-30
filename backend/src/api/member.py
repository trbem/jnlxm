import os
import sys
import json
import logging

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime

from models.database import get_db, Device, SystemConfig, RecognitionLog, FamilyMember
from schemas import (
    MemberCreateRequest, MemberUpdateRequest, MemberResponse
)
from services.face_service import face_service
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/member", tags=["成员管理接口"])


@router.get("/list")
async def get_member_list(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(FamilyMember)
    if not include_inactive:
        query = query.filter(FamilyMember.is_active == True)
    members = query.order_by(FamilyMember.created_at.desc()).all()
    return [member_to_dict(m) for m in members]


@router.get("/{member_id}")
async def get_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    return member_to_dict(member)


@router.post("/add")
async def add_member(request: MemberCreateRequest, db: Session = Depends(get_db)):
    member = FamilyMember(
        name=request.name,
        face_encoding=json.dumps([0.0] * 128),
        relationship=request.relationship,
        notes=request.notes,
        is_active=True
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member_to_dict(member)


@router.post("/enroll")
async def enroll_member(
    name: str = Form(...),
    relationship: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    content = await image.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # 使用 face_recognition 提取真实人脸特征
        encoding = face_service.encode_image(content)
        logger.info(f"为人脸 {name} 提取特征成功，维度: {len(encoding)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"人脸特征提取失败: {str(e)}")

    member = FamilyMember(
        name=name,
        avatar_image_path=unique_filename,
        face_encoding=json.dumps(encoding),
        relationship=relationship,
        notes=notes,
        is_active=True
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    return member_to_dict(member)


@router.put("/update/{member_id}")
async def update_member(member_id: int, request: MemberUpdateRequest, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    if request.name is not None:
        member.name = request.name
    if request.relationship is not None:
        member.relationship = request.relationship
    if request.notes is not None:
        member.notes = request.notes
    if request.is_active is not None:
        member.is_active = request.is_active

    db.commit()
    db.refresh(member)
    return member_to_dict(member)


@router.put("/update-face/{member_id}")
async def update_member_face(
    member_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    # 保存新图片
    file_ext = os.path.splitext(image.filename)[1] if image.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    content = await image.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # 提取新人脸特征
        encoding = face_service.encode_image(content)
        member.avatar_image_path = unique_filename
        member.face_encoding = json.dumps(encoding)
        db.commit()
        db.refresh(member)
        logger.info(f"更新成员 {member.name} 的人脸特征成功")
        return member_to_dict(member)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"人脸特征提取失败: {str(e)}")


@router.delete("/delete/{member_id}")
async def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    member.is_active = False
    db.commit()
    return {"success": True, "message": "成员已删除"}


@router.get("/count/total")
async def get_member_count(db: Session = Depends(get_db)):
    count = db.query(FamilyMember).filter(FamilyMember.is_active == True).count()
    return {"total": count}


@router.get("/list/all")
async def get_all_members(db: Session = Depends(get_db)):
    members = db.query(FamilyMember).filter(FamilyMember.is_active == True).all()
    return [member_to_dict(m) for m in members]


def member_to_dict(member):
    return {
        "id": member.id,
        "name": member.name,
        "avatar_image_path": member.avatar_image_path,
        "relationship": member.relationship,
        "created_at": member.created_at.isoformat() if member.created_at else None,
        "updated_at": member.updated_at.isoformat() if member.updated_at else None,
        "is_active": member.is_active,
        "notes": member.notes
    }
