-- ============================================================================
-- AMENA (آمنة) — السوق الزراعي الرقمي الجزائري
-- مخطط قاعدة البيانات الكامل — PostgreSQL 15+
-- يغطي: المستخدمون (6 أدوار)، المنتجات، الطلبات، Escrow، الشحنات،
--       شهادات الجودة، البث المباشر والمزادات، الولايات الـ69
-- ============================================================================

-- ============================================================================
-- 0. EXTENSIONS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. ENUM TYPES
-- ============================================================================
CREATE TYPE user_role AS ENUM ('consumer', 'farmer', 'trader', 'transporter', 'expert', 'admin');

CREATE TYPE product_category AS ENUM (
    'dates', 'vegetables_fruits', 'strategic_crops', 'olive_oil',          -- المحاصيل الطازجة
    'seeds_seedlings', 'fertilizers', 'pesticides', 'soil_treatment',      -- مستلزمات الإنتاج
    'tractors_harvesters', 'irrigation', 'packaging', 'solar_energy',      -- العتاد والآلات
    'cold_transport', 'soil_water_analysis', 'labor', 'weather_reports'    -- الخدمات واللوجستيات
);

CREATE TYPE product_unit AS ENUM ('kg', 'ton', 'liter', 'unit', 'box', 'day', 'hour', 'service');

CREATE TYPE order_status AS ENUM (
    'pending_payment', 'paid_escrow', 'preparing', 'ready_for_pickup',
    'in_transit', 'delivered', 'completed', 'disputed', 'cancelled', 'refunded'
);

CREATE TYPE escrow_status AS ENUM ('held', 'released', 'refunded', 'disputed');

CREATE TYPE payment_method AS ENUM ('cib', 'baridimob', 'ccp', 'cash_on_delivery');

CREATE TYPE shipment_status AS ENUM (
    'awaiting_transporter', 'accepted', 'picked_up', 'in_transit', 'delivered', 'failed'
);

CREATE TYPE certificate_grade AS ENUM ('a_plus', 'a', 'b_plus', 'b', 'c', 'rejected');

CREATE TYPE certificate_status AS ENUM ('pending_review', 'approved', 'expired', 'revoked');

CREATE TYPE auction_status AS ENUM ('scheduled', 'live', 'ended', 'cancelled');

CREATE TYPE kyc_status AS ENUM ('unverified', 'pending', 'verified', 'rejected');

CREATE TYPE contract_status AS ENUM ('active', 'pending_renewal', 'expired', 'cancelled');

CREATE TYPE notification_type AS ENUM (
    'order_update', 'escrow_release', 'new_message', 'auction_bid',
    'certificate_ready', 'security_alert', 'system'
);

-- ============================================================================
-- 2. WILAYAS — الولايات الـ69 (وفق القانون 06-26، أفريل 2026)
-- ============================================================================
CREATE TABLE wilayas (
    id              SMALLINT PRIMARY KEY,
    name_ar         VARCHAR(50) NOT NULL,
    name_fr         VARCHAR(50),
    is_new_2026     BOOLEAN NOT NULL DEFAULT FALSE,  -- ولاية مستحدثة بالقانون 06-26
    parent_wilaya_id SMALLINT REFERENCES wilayas(id), -- الولاية الأم التي اقتُطعت منها (للولايات الجديدة)
    region          VARCHAR(30),                      -- شمال / هضاب عليا / جنوب
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE wilayas IS 'الولايات الجزائرية الـ69 — 58 أصلية + 11 مستحدثة بالقانون 06-26';
COMMENT ON COLUMN wilayas.is_new_2026 IS 'TRUE للولايات الـ11 المستحدثة (أرقام 59-69)';

-- ============================================================================
-- 3. USERS — جدول المستخدمين الموحّد (كل الأدوار)
-- ============================================================================
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name           VARCHAR(150) NOT NULL,
    phone               VARCHAR(20) NOT NULL UNIQUE,
    email               VARCHAR(150) UNIQUE,
    password_hash       TEXT NOT NULL,
    primary_role        user_role NOT NULL,
    wilaya_id           SMALLINT NOT NULL REFERENCES wilayas(id),
    address_detail      TEXT,
    avatar_url          TEXT,

    -- الأمان
    kyc_status          kyc_status NOT NULL DEFAULT 'unverified',
    kyc_document_url    TEXT,
    two_fa_enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    two_fa_secret       TEXT,

    -- حالة الحساب
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_suspended        BOOLEAN NOT NULL DEFAULT FALSE,
    suspension_reason   TEXT,

    -- نظام الولاء (للمستهلكين بشكل أساسي)
    loyalty_points      INTEGER NOT NULL DEFAULT 0,
    loyalty_tier        VARCHAR(20) DEFAULT 'bronze',

    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_loyalty_points_positive CHECK (loyalty_points >= 0)
);

CREATE INDEX idx_users_role ON users(primary_role);
CREATE INDEX idx_users_wilaya ON users(wilaya_id);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_kyc_status ON users(kyc_status);

-- ============================================================================
-- 3.1 ROLE-SPECIFIC PROFILES — ملفات تفصيلية لكل دور (علاقة 1-إلى-1 مع users)
--      يسمح هذا التصميم لاحقاً بأن يحمل نفس المستخدم أكثر من دور عبر
--      جدول user_roles الإضافي (انظر القسم 3.2) إن احتاج المشروع لذلك مستقبلاً
-- ============================================================================

CREATE TABLE farmer_profiles (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    farm_name           VARCHAR(150) NOT NULL,
    farm_description    TEXT,
    established_year    SMALLINT,
    total_area_hectares DECIMAL(10,2),
    verified_badge       BOOLEAN NOT NULL DEFAULT FALSE,
    rating               DECIMAL(2,1) DEFAULT 0.0 CHECK (rating BETWEEN 0 AND 5),
    rating_count         INTEGER NOT NULL DEFAULT 0,
    bank_account_iban    VARCHAR(34),
    withdrawal_method    payment_method DEFAULT 'ccp'
);

CREATE TABLE trader_profiles (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    business_name        VARCHAR(150) NOT NULL,
    trade_register_no    VARCHAR(50) UNIQUE,
    tax_id                VARCHAR(50),
    business_type         VARCHAR(50),       -- سوبرماركت، مطعم، مصدّر، إلخ
    monthly_volume_estimate DECIMAL(12,2)
);

CREATE TABLE transporter_profiles (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    vehicle_type         VARCHAR(50) NOT NULL,    -- شاحنة مبردة، صغيرة، إلخ
    plate_number          VARCHAR(20) NOT NULL,
    vehicle_year           SMALLINT,
    capacity_kg             DECIMAL(10,2),
    insurance_valid_until    DATE,
    transport_license_url    TEXT,
    rating                    DECIMAL(2,1) DEFAULT 0.0 CHECK (rating BETWEEN 0 AND 5),
    rating_count              INTEGER NOT NULL DEFAULT 0,
    is_available              BOOLEAN NOT NULL DEFAULT TRUE,
    current_wilaya_id          SMALLINT REFERENCES wilayas(id)
);

CREATE TABLE expert_profiles (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    specialty            VARCHAR(150) NOT NULL,
    years_experience      SMALLINT,
    academic_credentials   TEXT,
    license_number          VARCHAR(50),
    rating                   DECIMAL(2,1) DEFAULT 0.0 CHECK (rating BETWEEN 0 AND 5),
    rating_count              INTEGER NOT NULL DEFAULT 0,
    consultation_fee          DECIMAL(10,2),
    inspection_fee             DECIMAL(10,2)
);

-- ============================================================================
-- 3.2 USER_ROLES (اختياري للمستقبل) — يدعم تعدد الأدوار لنفس المستخدم
--      مثال: مزارع يشتري أيضاً كمستهلك. غير مُفعَّل افتراضياً في منطق التطبيق
--      الحالي (الذي يعتمد على primary_role)، لكنه موجود لتوسعة لاحقة سهلة.
-- ============================================================================
CREATE TABLE user_roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        user_role NOT NULL,
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, role)
);

-- ============================================================================
-- 4. PRODUCTS — المنتجات (الأعمدة الأربعة للسوق)
-- ============================================================================
CREATE TABLE products (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farmer_id           UUID NOT NULL REFERENCES farmer_profiles(user_id) ON DELETE CASCADE,
    category            product_category NOT NULL,
    name                VARCHAR(200) NOT NULL,
    description         TEXT,
    price               DECIMAL(12,2) NOT NULL CHECK (price >= 0),
    unit                product_unit NOT NULL,
    quantity_available  DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (quantity_available >= 0),
    min_order_quantity  DECIMAL(12,2) DEFAULT 1,

    wilaya_id           SMALLINT NOT NULL REFERENCES wilayas(id),
    pickup_address      TEXT,

    qr_tracked          BOOLEAN NOT NULL DEFAULT FALSE,
    qr_code_value       TEXT UNIQUE,

    is_for_rent         BOOLEAN NOT NULL DEFAULT FALSE,  -- للعتاد/الآلات
    is_wholesale_only    BOOLEAN NOT NULL DEFAULT FALSE,  -- جملة فقط (للتجار)

    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    views_count           INTEGER NOT NULL DEFAULT 0,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_products_farmer ON products(farmer_id);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_wilaya ON products(wilaya_id);
CREATE INDEX idx_products_active ON products(is_active) WHERE is_active = TRUE;

CREATE TABLE product_images (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id  UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url   TEXT NOT NULL,
    sort_order  SMALLINT NOT NULL DEFAULT 0
);

-- تتبع QR من الحقل إلى المستهلك: كل حدث في رحلة المنتج
CREATE TABLE product_traceability_events (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id  UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    event_type  VARCHAR(50) NOT NULL,   -- harvested, quality_checked, packaged, shipped, delivered
    event_note  TEXT,
    wilaya_id   SMALLINT REFERENCES wilayas(id),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 5. QUALITY CERTIFICATES — شهادات الجودة الصادرة عن الخبراء
-- ============================================================================
CREATE TABLE quality_certificates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    expert_id       UUID NOT NULL REFERENCES expert_profiles(user_id),
    grade           certificate_grade NOT NULL,
    status          certificate_status NOT NULL DEFAULT 'pending_review',
    report_notes    TEXT,
    report_file_url TEXT,
    inspection_fee_paid DECIMAL(10,2),
    issued_at       TIMESTAMPTZ,
    valid_until     DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_valid_until_future CHECK (valid_until IS NULL OR valid_until > created_at::date)
);

CREATE INDEX idx_certificates_product ON quality_certificates(product_id);
CREATE INDEX idx_certificates_expert ON quality_certificates(expert_id);
CREATE INDEX idx_certificates_status ON quality_certificates(status);

-- ============================================================================
-- 6. ORDERS — الطلبات (مستهلك أو تاجر يشتري)
-- ============================================================================
CREATE TABLE orders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number        VARCHAR(20) NOT NULL UNIQUE,   -- AM-3321 مثلاً
    buyer_id            UUID NOT NULL REFERENCES users(id),
    status              order_status NOT NULL DEFAULT 'pending_payment',

    subtotal_amount     DECIMAL(12,2) NOT NULL CHECK (subtotal_amount >= 0),
    shipping_fee        DECIMAL(12,2) NOT NULL DEFAULT 0,
    platform_commission DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_amount        DECIMAL(12,2) NOT NULL CHECK (total_amount >= 0),

    delivery_wilaya_id  SMALLINT NOT NULL REFERENCES wilayas(id),
    delivery_address    TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at         TIMESTAMPTZ
);

CREATE INDEX idx_orders_buyer ON orders(buyer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

CREATE TABLE order_items (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id    UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  UUID NOT NULL REFERENCES products(id),
    quantity    DECIMAL(12,2) NOT NULL CHECK (quantity > 0),
    unit_price  DECIMAL(12,2) NOT NULL CHECK (unit_price >= 0),
    line_total  DECIMAL(12,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

CREATE INDEX idx_order_items_order ON order_items(order_id);

-- ============================================================================
-- 7. ESCROW TRANSACTIONS — الدفع الآمن
-- ============================================================================
CREATE TABLE escrow_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id        UUID NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    amount          DECIMAL(12,2) NOT NULL CHECK (amount >= 0),
    payment_method  payment_method NOT NULL,
    status          escrow_status NOT NULL DEFAULT 'held',

    held_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at     TIMESTAMPTZ,
    refunded_at     TIMESTAMPTZ,
    auto_release_at TIMESTAMPTZ,            -- تحرير تلقائي بعد مهلة (افتراضي 48 ساعة من التسليم)

    dispute_reason   TEXT,
    dispute_opened_at TIMESTAMPTZ,
    dispute_resolved_by UUID REFERENCES users(id),  -- مشرف admin يحل النزاع

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_escrow_status ON escrow_transactions(status);
CREATE INDEX idx_escrow_order ON escrow_transactions(order_id);

-- سجل كل حركة مالية (دفتر أستاذ بسيط) لكل مستخدم
CREATE TABLE wallet_ledger_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id),
    entry_type      VARCHAR(30) NOT NULL,   -- escrow_release, commission, withdrawal, refund
    amount          DECIMAL(12,2) NOT NULL,  -- موجب = دخول، سالب = خروج
    related_order_id UUID REFERENCES orders(id),
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_wallet_user ON wallet_ledger_entries(user_id, created_at DESC);

-- ============================================================================
-- 8. SHIPMENTS — الشحنات والنقل
-- ============================================================================
CREATE TABLE shipments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_number      VARCHAR(20) NOT NULL UNIQUE,   -- SH-1021 مثلاً
    order_id             UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    transporter_id        UUID REFERENCES transporter_profiles(user_id),

    origin_wilaya_id       SMALLINT NOT NULL REFERENCES wilayas(id),
    destination_wilaya_id   SMALLINT NOT NULL REFERENCES wilayas(id),
    distance_km              DECIMAL(8,2),
    transport_fee             DECIMAL(10,2),

    status                    shipment_status NOT NULL DEFAULT 'awaiting_transporter',

    accepted_at                TIMESTAMPTZ,
    picked_up_at                 TIMESTAMPTZ,
    delivered_at                  TIMESTAMPTZ,
    estimated_arrival              TIMESTAMPTZ,

    current_lat                     DECIMAL(9,6),       -- لتتبع GPS حي
    current_lng                      DECIMAL(9,6),
    last_location_update              TIMESTAMPTZ,

    created_at                         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_shipments_transporter ON shipments(transporter_id);
CREATE INDEX idx_shipments_status ON shipments(status);
CREATE INDEX idx_shipments_order ON shipments(order_id);

-- ============================================================================
-- 9. LIVE STREAMING & AUCTIONS — البث المباشر والمزادات
-- ============================================================================
CREATE TABLE live_auctions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farmer_id            UUID NOT NULL REFERENCES farmer_profiles(user_id),
    product_id            UUID NOT NULL REFERENCES products(id),
    title                  VARCHAR(200) NOT NULL,
    stream_url               TEXT,
    starting_price             DECIMAL(12,2) NOT NULL,
    current_price                DECIMAL(12,2) NOT NULL,
    status                        auction_status NOT NULL DEFAULT 'scheduled',
    viewer_count                   INTEGER NOT NULL DEFAULT 0,
    scheduled_start                 TIMESTAMPTZ,
    started_at                       TIMESTAMPTZ,
    ended_at                          TIMESTAMPTZ,
    winning_bid_id                     UUID,            -- FK مضافة لاحقاً بعد إنشاء auction_bids

    created_at                          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE auction_bids (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auction_id  UUID NOT NULL REFERENCES live_auctions(id) ON DELETE CASCADE,
    bidder_id   UUID NOT NULL REFERENCES users(id),
    amount      DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    placed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE live_auctions
    ADD CONSTRAINT fk_winning_bid FOREIGN KEY (winning_bid_id) REFERENCES auction_bids(id);

CREATE INDEX idx_auctions_farmer ON live_auctions(farmer_id);
CREATE INDEX idx_auctions_status ON live_auctions(status);
CREATE INDEX idx_bids_auction ON auction_bids(auction_id, amount DESC);

CREATE TABLE auction_chat_messages (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auction_id  UUID NOT NULL REFERENCES live_auctions(id) ON DELETE CASCADE,
    sender_id   UUID NOT NULL REFERENCES users(id),
    message     TEXT NOT NULL,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 10. TRADER CONTRACTS — عقود الجملة بين التاجر والمزارع
-- ============================================================================
CREATE TABLE wholesale_contracts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trader_id            UUID NOT NULL REFERENCES trader_profiles(user_id),
    farmer_id             UUID NOT NULL REFERENCES farmer_profiles(user_id),
    product_category       product_category NOT NULL,
    product_description     VARCHAR(200),
    quantity_per_period       DECIMAL(12,2) NOT NULL,
    period_unit                 VARCHAR(20) NOT NULL,   -- weekly, monthly
    unit_price                    DECIMAL(12,2) NOT NULL,
    status                         contract_status NOT NULL DEFAULT 'active',
    starts_at                       DATE NOT NULL,
    ends_at                           DATE NOT NULL,
    created_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_contract_dates CHECK (ends_at > starts_at)
);

CREATE INDEX idx_contracts_trader ON wholesale_contracts(trader_id);
CREATE INDEX idx_contracts_farmer ON wholesale_contracts(farmer_id);

-- طلبات عروض الأسعار (RFQ) التي يرسلها التاجر
CREATE TABLE rfq_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trader_id       UUID NOT NULL REFERENCES trader_profiles(user_id),
    product_category product_category NOT NULL,
    product_name     VARCHAR(200),
    quantity          DECIMAL(12,2) NOT NULL,
    max_price          DECIMAL(12,2),
    preferred_wilaya_id SMALLINT REFERENCES wilayas(id),
    needed_by_date       DATE,
    status                 VARCHAR(20) NOT NULL DEFAULT 'open',  -- open, fulfilled, expired
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rfq_responses (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rfq_id      UUID NOT NULL REFERENCES rfq_requests(id) ON DELETE CASCADE,
    farmer_id   UUID NOT NULL REFERENCES farmer_profiles(user_id),
    offered_price DECIMAL(12,2) NOT NULL,
    message      TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 11. EXPERT CONSULTATIONS — الاستشارات المدفوعة
-- ============================================================================
CREATE TABLE consultations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    expert_id       UUID NOT NULL REFERENCES expert_profiles(user_id),
    requester_id    UUID NOT NULL REFERENCES users(id),
    topic           VARCHAR(200),
    fee             DECIMAL(10,2) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, answered, closed
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE consultation_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    consultation_id UUID NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
    sender_id       UUID NOT NULL REFERENCES users(id),
    message         TEXT NOT NULL,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 12. REVIEWS & RATINGS — التقييمات (عام لكل الأدوار)
-- ============================================================================
CREATE TABLE reviews (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reviewer_id     UUID NOT NULL REFERENCES users(id),
    reviewee_id     UUID NOT NULL REFERENCES users(id),
    order_id        UUID REFERENCES orders(id),
    rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_no_self_review CHECK (reviewer_id != reviewee_id)
);

CREATE INDEX idx_reviews_reviewee ON reviews(reviewee_id);

-- ============================================================================
-- 13. NOTIFICATIONS — الإشعارات
-- ============================================================================
CREATE TABLE notifications (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        notification_type NOT NULL,
    title       VARCHAR(200) NOT NULL,
    body        TEXT,
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    related_entity_id UUID,    -- order_id أو auction_id أو غيره، بدون FK صارم لمرونة الأنواع
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;

-- ============================================================================
-- 14. AI ASSISTANT LOG — سجل تفاعلات المساعد الذكي (لتحسين التوصيات لاحقاً)
-- ============================================================================
CREATE TABLE ai_assistant_queries (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id),
    query_text  TEXT NOT NULL,
    response_text TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 15. ADMIN / SECURITY AUDIT LOG — سجل الأمان للوحة الإدارة
-- ============================================================================
CREATE TABLE security_audit_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id),
    event_type  VARCHAR(50) NOT NULL,   -- login_success, login_failed, role_change, ip_blocked, account_suspended
    ip_address  INET,
    user_agent  TEXT,
    details     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_user ON security_audit_log(user_id, created_at DESC);
CREATE INDEX idx_audit_log_event_type ON security_audit_log(event_type);

CREATE TABLE blocked_ips (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip_address  INET NOT NULL UNIQUE,
    reason      TEXT,
    blocked_by  UUID REFERENCES users(id),
    blocked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- 16. PLATFORM SETTINGS — إعدادات المنصة القابلة للتعديل من لوحة الإدارة
-- ============================================================================
CREATE TABLE platform_settings (
    key         VARCHAR(100) PRIMARY KEY,
    value       JSONB NOT NULL,
    updated_by  UUID REFERENCES users(id),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- قيم افتراضية أساسية
INSERT INTO platform_settings (key, value) VALUES
    ('commission_rate_percent', '2'),
    ('minimum_withdrawal_amount', '1000'),
    ('default_escrow_hold_hours', '48'),
    ('maintenance_mode', 'false');

-- ============================================================================
-- 17. AUTO-UPDATE TRIGGER FOR updated_at COLUMNS
-- ============================================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_users BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
CREATE TRIGGER set_updated_at_products BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
CREATE TRIGGER set_updated_at_orders BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================================
-- END OF SCHEMA — 17 جدولاً أساسياً + 3 جداول إعدادات/سجلات
-- ============================================================================
