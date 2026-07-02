"""
أنواع Enum المستخدمة في كل النماذج — تطابق التعريفات في schema.sql
"""
import enum


class UserRole(str, enum.Enum):
    consumer = "consumer"
    farmer = "farmer"
    trader = "trader"
    transporter = "transporter"
    expert = "expert"
    admin = "admin"


class KycStatus(str, enum.Enum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class ProductCategory(str, enum.Enum):
    dates = "dates"
    vegetables_fruits = "vegetables_fruits"
    strategic_crops = "strategic_crops"
    olive_oil = "olive_oil"
    seeds_seedlings = "seeds_seedlings"
    fertilizers = "fertilizers"
    pesticides = "pesticides"
    soil_treatment = "soil_treatment"
    tractors_harvesters = "tractors_harvesters"
    irrigation = "irrigation"
    packaging = "packaging"
    solar_energy = "solar_energy"
    cold_transport = "cold_transport"
    soil_water_analysis = "soil_water_analysis"
    labor = "labor"
    weather_reports = "weather_reports"


class ProductUnit(str, enum.Enum):
    kg = "kg"
    ton = "ton"
    liter = "liter"
    unit = "unit"
    box = "box"
    day = "day"
    hour = "hour"
    service = "service"


class OrderStatus(str, enum.Enum):
    pending_payment = "pending_payment"
    paid_escrow = "paid_escrow"
    preparing = "preparing"
    ready_for_pickup = "ready_for_pickup"
    in_transit = "in_transit"
    delivered = "delivered"
    completed = "completed"
    disputed = "disputed"
    cancelled = "cancelled"
    refunded = "refunded"


class EscrowStatus(str, enum.Enum):
    held = "held"
    released = "released"
    refunded = "refunded"
    disputed = "disputed"


class PaymentMethod(str, enum.Enum):
    cib = "cib"
    baridimob = "baridimob"
    ccp = "ccp"
    cash_on_delivery = "cash_on_delivery"


class ShipmentStatus(str, enum.Enum):
    awaiting_transporter = "awaiting_transporter"
    accepted = "accepted"
    picked_up = "picked_up"
    in_transit = "in_transit"
    delivered = "delivered"
    failed = "failed"


class CertificateGrade(str, enum.Enum):
    a_plus = "a_plus"
    a = "a"
    b_plus = "b_plus"
    b = "b"
    c = "c"
    rejected = "rejected"


class CertificateStatus(str, enum.Enum):
    pending_review = "pending_review"
    approved = "approved"
    expired = "expired"
    revoked = "revoked"
