"""
/api/v1/products — إدارة المنتجات عبر الأعمدة الأربعة للسوق، مع فلترة حسب الفئة والولاية
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.enums import ProductCategory, UserRole
from app.models.product import Product
from app.models.profiles import FarmerProfile
from app.models.user import User
from app.models.wilaya import Wilaya
from app.schemas.product import (
    ProductCreateRequest, ProductUpdateRequest, ProductOut, ProductListResponse,
)

router = APIRouter(prefix="/products", tags=["المنتجات — Products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    db: Session = Depends(get_db),
    category: Optional[ProductCategory] = None,
    wilaya_id: Optional[int] = Query(None, ge=1, le=69),
    is_for_rent: Optional[bool] = None,
    search: Optional[str] = Query(None, min_length=2, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Product).filter(Product.is_active == True)  # noqa: E712

    if category:
        query = query.filter(Product.category == category)
    if wilaya_id:
        query = query.filter(Product.wilaya_id == wilaya_id)
    if is_for_rent is not None:
        query = query.filter(Product.is_for_rent == is_for_rent)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    total = query.count()
    items = (
        query.order_by(Product.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ProductListResponse(total=total, items=items)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    product.views_count += 1
    db.commit()
    db.refresh(product)
    return product


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateRequest,
    current_user: User = Depends(require_role(UserRole.farmer)),
    db: Session = Depends(get_db),
):
    if not db.query(Wilaya).filter(Wilaya.id == payload.wilaya_id).first():
        raise HTTPException(status_code=400, detail="رقم الولاية غير صحيح")

    farmer_profile = db.query(FarmerProfile).filter(
        FarmerProfile.user_id == current_user.id
    ).first()
    if not farmer_profile:
        raise HTTPException(
            status_code=400,
            detail="يجب إكمال ملف المزارع الشخصي (farmer profile) قبل إضافة منتجات"
        )

    product = Product(farmer_id=current_user.id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdateRequest,
    current_user: User = Depends(require_role(UserRole.farmer)),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    if product.farmer_id != current_user.id:
        raise HTTPException(status_code=403, detail="لا يمكنك تعديل منتج لا يخصّك")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.farmer)),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="المنتج غير موجود")
    if product.farmer_id != current_user.id:
        raise HTTPException(status_code=403, detail="لا يمكنك حذف منتج لا يخصّك")

    db.delete(product)
    db.commit()
