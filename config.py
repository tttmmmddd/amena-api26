"""
إعدادات التطبيق العامة — قراءة متغيرات البيئة وتوفير قيم افتراضية للتطوير
"""
import os


class Settings:
    PROJECT_NAME: str = "AMENA API — منصة آمنة"
    API_V1_PREFIX: str = "/api/v1"

    # قاعدة البيانات — في الإنتاج استخدم PostgreSQL، الافتراضي هنا SQLite للتطوير المحلي السريع
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./amena_dev.db"
    )

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_ENV_VAR")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 ساعة
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Escrow
    DEFAULT_ESCROW_HOLD_HOURS: int = 48
    DEFAULT_COMMISSION_RATE_PERCENT: float = 2.0

    # 2FA
    OTP_ISSUER_NAME: str = "AMENA"


settings = Settings()
