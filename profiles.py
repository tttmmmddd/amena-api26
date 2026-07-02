"""
/api/v1/profiles — إنشاء الملف الشخصي المتخصص حسب دور المستخدم
يجب استدعاء هذا بعد /auth/register مباشرة لإكمال إعداد الحساب
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.enums import UserRole
from app.models.profiles import FarmerProfile, TraderProfile, TransporterProfile, ExpertProfile
from app.models.user import User
from app.schemas.profile import (
    FarmerProfileCreateRequest, FarmerProfileOut,
    TraderProfileCreateRequest, TransporterProfileCreateRequest, ExpertProfileCreateRequest,
)

router = APIRouter(prefix="/profiles", tags=["الملفات الشخصية — Profiles"])


@router.post("/farmer", response_model=FarmerProfileOut, status_code=status.HTTP_201_CREATED)
def create_farmer_profile(
    payload: FarmerProfileCreateRequest,
    current_user: User = Depends(require_role(UserRole.farmer)),
    db: Session = Depends(get_db),
):
    if db.query(FarmerProfile).filter(FarmerProfile.user_id == current_user.id).first():
        raise HTTPException(status_code=409, detail="ملف المزارع موجود مسبقاً")

    profile = FarmerProfile(user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/trader", status_code=status.HTTP_201_CREATED)
def create_trader_profile(
    payload: TraderProfileCreateRequest,
    current_user: User = Depends(require_role(UserRole.trader)),
    db: Session = Depends(get_db),
):
    if db.query(TraderProfile).filter(TraderProfile.user_id == current_user.id).first():
        raise HTTPException(status_code=409, detail="ملف التاجر موجود مسبقاً")

    profile = TraderProfile(user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    return {"message": "تم إنشاء ملف التاجر بنجاح"}


@router.post("/transporter", status_code=status.HTTP_201_CREATED)
def create_transporter_profile(
    payload: TransporterProfileCreateRequest,
    current_user: User = Depends(require_role(UserRole.transporter)),
    db: Session = Depends(get_db),
):
    if db.query(TransporterProfile).filter(TransporterProfile.user_id == current_user.id).first():
        raise HTTPException(status_code=409, detail="ملف الناقل موجود مسبقاً")

    profile = TransporterProfile(user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    return {"message": "تم إنشاء ملف الناقل بنجاح"}


@router.post("/expert", status_code=status.HTTP_201_CREATED)
def create_expert_profile(
    payload: ExpertProfileCreateRequest,
    current_user: User = Depends(require_role(UserRole.expert)),
    db: Session = Depends(get_db),
):
    if db.query(ExpertProfile).filter(ExpertProfile.user_id == current_user.id).first():
        raise HTTPException(status_code=409, detail="ملف الخبير موجود مسبقاً")

    profile = ExpertProfile(user_id=current_user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    return {"message": "تم إنشاء ملف الخبير بنجاح"}
