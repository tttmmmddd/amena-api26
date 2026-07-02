"""
Pydantic schemas للطلبات والدفع الآمن (Escrow)
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator

from app.models.enums import OrderStatus, EscrowStatus, PaymentMethod


class OrderItemCreateRequest(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)


class OrderCreateRequest(BaseModel):
    items: List[OrderItemCreateRequest] = Field(..., min_length=1)
    delivery_wilaya_id: int = Field(..., ge=1, le=69)
    delivery_address: Optional[str] = None

    @model_validator(mode="after")
    def check_unique_products(self):
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("لا يمكن تكرار نفس المنتج في عناصر منفصلة بنفس الطلب")
        return self


class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    buyer_id: uuid.UUID
    status: OrderStatus
    subtotal_amount: Decimal
    shipping_fee: Decimal
    platform_commission: Decimal
    total_amount: Decimal
    delivery_wilaya_id: int
    created_at: datetime
    items: List[OrderItemOut] = []

    model_config = {"from_attributes": True}


class EscrowPayRequest(BaseModel):
    payment_method: PaymentMethod


class EscrowOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    payment_method: PaymentMethod
    status: EscrowStatus
    held_at: datetime
    released_at: Optional[datetime] = None
    auto_release_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EscrowReleaseRequest(BaseModel):
    confirm: bool = Field(..., description="تأكيد استلام الطلب من طرف المشتري")


class EscrowDisputeRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1000)
