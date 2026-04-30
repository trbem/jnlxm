import os
import sys
import json
import logging

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import FamilyMember


class MemberService:
    """家庭成员服务"""

    @staticmethod
    def get_all_members(db: Session, include_inactive: bool = False) -> List[FamilyMember]:
        query = db.query(FamilyMember)
        if not include_inactive:
            query = query.filter(FamilyMember.is_active == True)
        return query.order_by(FamilyMember.created_at.desc()).all()

    @staticmethod
    def get_member_by_id(db: Session, member_id: int) -> Optional[FamilyMember]:
        return db.query(FamilyMember).filter(FamilyMember.id == member_id).first()

    @staticmethod
    def create_member(db: Session, name: str, face_encoding: List[float],
                     avatar_path: str = None, relationship: str = None,
                     notes: str = None) -> FamilyMember:
        member = FamilyMember(
            name=name,
            avatar_image_path=avatar_path,
            face_encoding=json.dumps(face_encoding),
            relationship=relationship,
            notes=notes
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def update_member(db: Session, member_id: int, **kwargs) -> Optional[FamilyMember]:
        member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
        if not member:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(member, key):
                setattr(member, key, value)

        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def delete_member(db: Session, member_id: int) -> bool:
        member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
        if not member:
            return False

        member.is_active = False
        db.commit()
        return True

    @staticmethod
    def get_all_active_encodings(db: Session) -> List[tuple]:
        members = db.query(FamilyMember).filter(FamilyMember.is_active == True).all()
        result = []
        for member in members:
            encoding = json.loads(member.face_encoding)
            result.append((member.id, member.name, encoding))
        return result

    @staticmethod
    def count_members(db: Session) -> int:
        return db.query(FamilyMember).filter(FamilyMember.is_active == True).count()


member_service = MemberService()
