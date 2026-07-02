"""
/api/v1/auth — التسجيل، تسجيل الدخول، تجديد الرمز، والمصادقة الثنائية (2FA)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    generate_totp_secret, get_totp_provisioning_uri, verify_totp_code,
)
from app.models.user import User
from app.models.wilaya import Wilaya
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, TokenResponse, RefreshTokenRequest,
    Enable2FAResponse, Confirm2FARequest, UserOut,
)

router = APIRouter(prefix="/auth", tags=["المصادقة — Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    if not db.query(Wilaya).filter(Wilaya.id == payload.wilaya_id).first():
        raise HTTPException(status_code=400, detail="رقم الولاية غير صحيح")

    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(status_code=409, detail="رقم الهاتف مسجَّل مسبقاً")

    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="البريد الإلكتروني مسجَّل مسبقاً")

    user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        password_hash=hash_password(payload.password),
        primary_role=payload.primary_role,
        wilaya_id=payload.wilaya_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == payload.phone).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="رقم الهاتف أو كلمة المرور غير صحيحة")

    if not user.is_active or user.is_suspended:
        raise HTTPException(status_code=403, detail="هذا الحساب معطّل أو معلّق")

    if user.two_fa_enabled:
        if not payload.totp_code:
            return TokenResponse(access_token="", refresh_token="", requires_2fa=True)
        if not verify_totp_code(user.two_fa_secret, payload.totp_code):
            raise HTTPException(status_code=401, detail="رمز المصادقة الثنائية غير صحيح")

    access_token = create_access_token(subject=str(user.id), role=user.primary_role.value)
    refresh_token = create_refresh_token(subject=str(user.id))

    from datetime import datetime, timezone
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="رمز التجديد غير صالح")

    import uuid as uuid_mod
    user = db.query(User).filter(User.id == uuid_mod.UUID(decoded["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود أو معطّل")

    new_access = create_access_token(subject=str(user.id), role=user.primary_role.value)
    new_refresh = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/2fa/enable", response_model=Enable2FAResponse)
def enable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.two_fa_enabled:
        raise HTTPException(status_code=400, detail="المصادقة الثنائية مفعّلة مسبقاً")

    secret = generate_totp_secret()
    current_user.two_fa_secret = secret
    db.commit()

    uri = get_totp_provisioning_uri(secret, current_user.phone)
    return Enable2FAResponse(secret=secret, provisioning_uri=uri)


@router.post("/2fa/confirm", status_code=status.HTTP_200_OK)
def confirm_2fa(
    payload: Confirm2FARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.two_fa_secret:
        raise HTTPException(status_code=400, detail="يجب استدعاء /2fa/enable أولاً")

    if not verify_totp_code(current_user.two_fa_secret, payload.totp_code):
        raise HTTPException(status_code=401, detail="رمز التحقق غير صحيح")

    current_user.two_fa_enabled = True
    db.commit()
    return {"message": "تم تفعيل المصادقة الثنائية بنجاح"}


@router.post("/2fa/disable", status_code=status.HTTP_200_OK)
def disable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.two_fa_enabled = False
    current_user.two_fa_secret = None
    db.commit()
    return {"message": "تم إلغاء تفعيل المصادقة الثنائية"}
