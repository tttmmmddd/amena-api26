from sqlalchemy import (
    Column, String, Boolean, Integer, SmallInteger, Text, DateTime, ForeignKey, Enum as SAEnum
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.types import GUID, new_uuid
from app.models.enums import UserRole, KycStatus


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=new_uuid)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(150), unique=True, nullable=True)
    password_hash = Column(Text, nullable=False)
    primary_role = Column(SAEnum(UserRole), nullable=False, index=True)
    wilaya_id = Column(SmallInteger, ForeignKey("wilayas.id"), nullable=False, index=True)
    address_detail = Column(Text)
    avatar_url = Column(Text)

    kyc_status = Column(SAEnum(KycStatus), nullable=False, default=KycStatus.unverified, index=True)
    kyc_document_url = Column(Text)
    two_fa_enabled = Column(Boolean, nullable=False, default=False)
    two_fa_secret = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    is_suspended = Column(Boolean, nullable=False, default=False)
    suspension_reason = Column(Text)

    loyalty_points = Column(Integer, nullable=False, default=0)
    loyalty_tier = Column(String(20), default="bronze")

    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    wilaya = relationship("Wilaya", back_populates="users")
    farmer_profile = relationship("FarmerProfile", back_populates="user", uselist=False)
    trader_profile = relationship("TraderProfile", back_populates="user", uselist=False)
    transporter_profile = relationship("TransporterProfile", back_populates="user", uselist=False)
    expert_profile = relationship("ExpertProfile", back_populates="user", uselist=False)
