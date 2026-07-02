"""
Pydantic schemas للمنتجات (الأعمدة الأربعة للسوق)
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.enums import ProductCategory, ProductUnit


class ProductCreateRequest(BaseModel):
    category: ProductCategory
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    price: Decimal = Field(..., ge=0)
    unit: ProductUnit
    quantity_available: Decimal = Field(..., ge=0)
    min_order_quantity: Decimal = Field(default=Decimal("1"), gt=0)
    wilaya_id: int = Field(..., ge=1, le=69)
    pickup_address: Optional[str] = None
    qr_tracked: bool = False
    is_for_rent: bool = False
    is_wholesale_only: bool = False


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    quantity_available: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    category: ProductCategory
    name: str
    description: Optional[str] = None
    price: Decimal
    unit: ProductUnit
    quantity_available: Decimal
    wilaya_id: int
    qr_tracked: bool
    is_for_rent: bool
    is_wholesale_only: bool
    is_active: bool
    views_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    total: int
    items: List[ProductOut]
