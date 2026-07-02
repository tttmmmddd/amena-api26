"""
أدوات الأمان: تشفير كلمات المرور، إصدار وفحص JWT، توليد ورموز OTP لـ 2FA
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import pyotp
from jose import jwt, JWTError

from app.core.config import settings


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))


def create_access_token(subject: str, role: str, expires_minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


# ===== 2FA (TOTP) =====

def generate_totp_secret() -> str:
    """يولّد سراً جديداً للمصادقة الثنائية (يُخزَّن مشفّراً مع المستخدم)"""
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, user_phone: str) -> str:
    """رابط QR لإضافة الحساب في تطبيق Google Authenticator أو ما شابه"""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_phone, issuer_name=settings.OTP_ISSUER_NAME
    )


def verify_totp_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
