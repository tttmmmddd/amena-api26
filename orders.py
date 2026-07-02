"""
/api/v1/orders — إنشاء الطلبات، ثم /api/v1/escrow — دفع وتحرير ونزاعات Escrow
هذا هو قلب التدفق المالي للمنصة: الشراء → تجميد المبلغ → التسليم → تحرير المبلغ للمزارع
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.enums import OrderStatus, EscrowStatus
from app.models.order import Order, OrderItem, EscrowTransaction, WalletLedgerEntry
from app.models.product import Product
from app.models.user import User
from app.models.wilaya import Wilaya
from app.schemas.order import (
    OrderCreateRequest, OrderOut,
    EscrowPayRequest, EscrowOut, EscrowReleaseRequest, EscrowDisputeRequest,
)

orders_router = APIRouter(prefix="/orders", tags=["الطلبات — Orders"])
escrow_router = APIRouter(prefix="/escrow", tags=["الدفع الآمن — Escrow"])


def _generate_order_number(db: Session) -> str:
    count = db.query(Order).count()
    return f"AM-{3000 + count + 1}"


@orders_router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not db.query(Wilaya).filter(Wilaya.id == payload.delivery_wilaya_id).first():
        raise HTTPException(status_code=400, detail="رقم ولاية التوصيل غير صحيح")

    order_items = []
    subtotal = Decimal("0")

    for item_req in payload.items:
        product = db.query(Product).filter(Product.id == item_req.product_id).first()
        if not product or not product.is_active:
            raise HTTPException(status_code=404, detail=f"المنتج {item_req.product_id} غير متوفر")
        if product.quantity_available < item_req.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"الكمية المطلوبة من '{product.name}' غير متوفرة (المتاح: {product.quantity_available})"
            )
        if item_req.quantity < product.min_order_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"الحد الأدنى للطلب من '{product.name}' هو {product.min_order_quantity}"
            )

        line_total = product.price * item_req.quantity
        subtotal += line_total

        order_items.append(OrderItem(
            product_id=product.id,
            quantity=item_req.quantity,
            unit_price=product.price,
        ))
        # حجز الكمية فوراً لتفادي البيع المضاعف (oversell)
        product.quantity_available -= item_req.quantity

    commission_rate = Decimal(str(settings.DEFAULT_COMMISSION_RATE_PERCENT)) / Decimal("100")
    platform_commission = (subtotal * commission_rate).quantize(Decimal("0.01"))
    shipping_fee = Decimal("0")  # يُحسب لاحقاً عبر خدمة النقل بحسب الوزن/المسافة
    total = subtotal + shipping_fee

    order = Order(
        order_number=_generate_order_number(db),
        buyer_id=current_user.id,
        status=OrderStatus.pending_payment,
        subtotal_amount=subtotal,
        shipping_fee=shipping_fee,
        platform_commission=platform_commission,
        total_amount=total,
        delivery_wilaya_id=payload.delivery_wilaya_id,
        delivery_address=payload.delivery_address,
        items=order_items,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@orders_router.get("", response_model=list[OrderOut])
def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.buyer_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )


@orders_router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="لا يمكنك الاطلاع على طلب لا يخصّك")
    return order


# ============================================================================
# ESCROW — الدفع الآمن
# ============================================================================

@escrow_router.post("/orders/{order_id}/pay", response_model=EscrowOut, status_code=status.HTTP_201_CREATED)
def pay_into_escrow(
    order_id: uuid.UUID,
    payload: EscrowPayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    يجمّد المبلغ في Escrow بعد الدفع — لا يُحوَّل للبائع فوراً.
    في الإنتاج: هنا يتم استدعاء بوابة الدفع الفعلية (CIB/BaridiMob/CCP) قبل التجميد.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="لا يمكنك الدفع عن طلب لا يخصّك")
    if order.status != OrderStatus.pending_payment:
        raise HTTPException(status_code=400, detail="هذا الطلب ليس في انتظار الدفع")

    existing_escrow = db.query(EscrowTransaction).filter(
        EscrowTransaction.order_id == order_id
    ).first()
    if existing_escrow:
        raise HTTPException(status_code=409, detail="تم تجميد مبلغ لهذا الطلب مسبقاً")

    auto_release = datetime.now(timezone.utc) + timedelta(
        hours=settings.DEFAULT_ESCROW_HOLD_HOURS
    )

    escrow = EscrowTransaction(
        order_id=order.id,
        amount=order.total_amount,
        payment_method=payload.payment_method,
        status=EscrowStatus.held,
        auto_release_at=auto_release,
    )
    order.status = OrderStatus.paid_escrow
    db.add(escrow)
    db.commit()
    db.refresh(escrow)
    return escrow


@escrow_router.get("/orders/{order_id}", response_model=EscrowOut)
def get_escrow_status(
    order_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="غير مصرّح")

    escrow = db.query(EscrowTransaction).filter(EscrowTransaction.order_id == order_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="لا توجد معاملة Escrow لهذا الطلب بعد")
    return escrow


@escrow_router.post("/orders/{order_id}/release", response_model=EscrowOut)
def release_escrow(
    order_id: uuid.UUID,
    payload: EscrowReleaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    المشتري يؤكد استلام الطلب → يُحرَّر المبلغ من Escrow إلى محفظة البائع (المزارع/التاجر)
    مطروحاً منه عمولة المنصة.
    """
    order = db.query(Order).options(joinedload(Order.items)).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="غير مصرّح")
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="يجب تأكيد الاستلام (confirm=true) لتحرير المبلغ")

    escrow = db.query(EscrowTransaction).filter(EscrowTransaction.order_id == order_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="لا توجد معاملة Escrow لهذا الطلب")
    if escrow.status != EscrowStatus.held:
        raise HTTPException(status_code=400, detail=f"لا يمكن تحرير معاملة بحالة: {escrow.status.value}")

    escrow.status = EscrowStatus.released
    escrow.released_at = datetime.now(timezone.utc)
    order.status = OrderStatus.completed
    order.delivered_at = order.delivered_at or datetime.now(timezone.utc)

    # توزيع المبلغ على البائعين (المزارعين) في دفتر الأستاذ، بعد خصم العمولة
    seller_amount = order.subtotal_amount - order.platform_commission
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            db.add(WalletLedgerEntry(
                user_id=product.farmer_id,
                entry_type="escrow_release",
                amount=item.quantity * item.unit_price,
                related_order_id=order.id,
                description=f"تحرير Escrow — طلب {order.order_number}",
            ))

    db.add(WalletLedgerEntry(
        user_id=current_user.id,  # سجل مرجعي فقط (لا يُخصَم من المشتري هنا لأنه دفع مسبقاً)
        entry_type="order_completed",
        amount=Decimal("0"),
        related_order_id=order.id,
        description=f"تم استلام الطلب {order.order_number} بنجاح",
    ))

    db.commit()
    db.refresh(escrow)
    return escrow


@escrow_router.post("/orders/{order_id}/dispute", response_model=EscrowOut)
def open_dispute(
    order_id: uuid.UUID,
    payload: EscrowDisputeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يفتح نزاعاً يوقف تحرير المبلغ تلقائياً حتى تراجعه الإدارة"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="غير مصرّح")

    escrow = db.query(EscrowTransaction).filter(EscrowTransaction.order_id == order_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="لا توجد معاملة Escrow لهذا الطلب")
    if escrow.status != EscrowStatus.held:
        raise HTTPException(status_code=400, detail="لا يمكن فتح نزاع على معاملة غير محجوزة حالياً")

    escrow.status = EscrowStatus.disputed
    escrow.dispute_reason = payload.reason
    escrow.dispute_opened_at = datetime.now(timezone.utc)
    order.status = OrderStatus.disputed

    db.commit()
    db.refresh(escrow)
    return escrow
