"""
Pydantic schemas لإنشاء الملفات الشخصية المتخصصة بعد التسجيل (مزارع، تاجر، ناقل، خبير)
"""
import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod


class FarmerProfileCreateRequest(BaseModel):
    farm_name: str = Field(..., min_length=2, max_length=150)
    farm_description: Optional[str] = None
    established_year: Optional[int] = Field(None, ge=1900, le=2026)
    total_area_hectares: Optional[Decimal] = Field(None, ge=0)
    bank_account_iban: Optional[str] = None
    withdrawal_method: PaymentMethod = PaymentMethod.ccp


class FarmerProfileOut(BaseModel):
    user_id: uuid.UUID
    farm_name: str
    farm_description: Optional[str] = None
    verified_badge: bool
    rating: Optional[Decimal] = None
    rating_count: int

    model_config = {"from_attributes": True}


class TraderProfileCreateRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=150)
    trade_register_no: Optional[str] = None
    tax_id: Optional[str] = None
    business_type: Optional[str] = None


class TransporterProfileCreateRequest(BaseModel):
    vehicle_type: str = Field(..., min_length=2, max_length=50)
    plate_number: str = Field(..., min_length=2, max_length=20)
    vehicle_year: Optional[int] = Field(None, ge=1980, le=2026)
    capacity_kg: Optional[Decimal] = Field(None, ge=0)


class ExpertProfileCreateRequest(BaseModel):
    specialty: str = Field(..., min_length=2, max_length=150)
    years_experience: Optional[int] = Field(None, ge=0, le=60)
    academic_credentials: Optional[str] = None
    consultation_fee: Optional[Decimal] = Field(None, ge=0)
    inspection_fee: Optional[Decimal] = Field(None, ge=0)
