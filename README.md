# مخطط قاعدة بيانات آمنة (AMENA) — دليل التنفيذ

## الملفات
1. **schema.sql** — المخطط الكامل: 30 جدولاً، 13 نوع ENUM، فهارس، قيود (constraints)، triggers
2. **seed_wilayas.sql** — بيانات الولايات الـ69 (يُنفَّذ بعد schema.sql لأنه يعتمد على جدول wilayas)

## طريقة التنفيذ (محلياً أو على سيرفر)

```bash
# 1. إنشاء قاعدة البيانات
createdb amena_db

# 2. تنفيذ المخطط
psql -d amena_db -f schema.sql

# 3. تعبئة بيانات الولايات
psql -d amena_db -f seed_wilayas.sql
```

أو عبر سطر واحد:
```bash
createdb amena_db && psql -d amena_db -f schema.sql && psql -d amena_db -f seed_wilayas.sql
```

## بنية المخطط (ملخص)

| المجموعة | الجداول |
|---|---|
| **المستخدمون** | users, farmer_profiles, trader_profiles, transporter_profiles, expert_profiles, user_roles |
| **الجغرافيا** | wilayas (69 ولاية) |
| **المنتجات** | products, product_images, product_traceability_events |
| **الجودة** | quality_certificates |
| **الطلبات والدفع** | orders, order_items, escrow_transactions, wallet_ledger_entries |
| **النقل** | shipments |
| **البث والمزادات** | live_auctions, auction_bids, auction_chat_messages |
| **التجارة بالجملة** | wholesale_contracts, rfq_requests, rfq_responses |
| **الاستشارات** | consultations, consultation_messages |
| **التقييمات والإشعارات** | reviews, notifications |
| **الذكاء الاصطناعي** | ai_assistant_queries |
| **الإدارة والأمان** | security_audit_log, blocked_ips, platform_settings |

## قرارات تصميم رئيسية

- **جدول `users` موحّد** بدور أساسي (`primary_role`)، مع جدول `user_roles` احتياطي يسمح لاحقاً بتعدد الأدوار (مثلاً مزارع يشتري أيضاً كمستهلك) دون تعديل هيكلي كبير.
- **فصل `escrow_transactions` عن `orders`** لتتبع دقيق لحالة الأموال المجمّدة بشكل مستقل ومُدقَّق، مع `auto_release_at` لدعم التحرير التلقائي بعد مهلة.
- **`wallet_ledger_entries`** كدفتر أستاذ بسيط (append-only) لكل حركة مالية — أساس ضروري لأي نظام مالي موثوق.
- **`product_traceability_events`** يدعم ميزة "تتبع QR من الحقل إلى المستهلك" بسجل أحداث زمني.
- **`live_auctions` + `auction_bids`** منفصلان عن نظام الشراء العادي لأن منطق "أعلى سعر يفوز خلال نافذة زمنية" يختلف جوهرياً.
- **`wilayas.is_new_2026`** يفرّق بين الولايات الأصلية والمستحدثة بالقانون 06-26 — مفيد لإحصائيات وتقارير لوحة الإدارة لاحقاً.
- جميع المبالغ المالية `DECIMAL(12,2)` (وليس FLOAT) لتفادي أخطاء التقريب.
- استُخدم `UUID` كمفتاح أساسي لكل الجداول (عدا wilayas التي تستخدم SMALLINT لأنها قائمة مرجعية ثابتة) لتفادي تعارضات لاحقة عند التوزيع أو الدمج.

## الخطوة التالية المقترحة
بعد تنفيذ هذا المخطط، الخطوة المنطقية هي بناء طبقة FastAPI (نماذج SQLAlchemy + Pydantic schemas + endpoints REST) فوق هذه الجداول، تبدأ بـ:
1. `/auth` — تسجيل/دخول/2FA
2. `/products` — CRUD + فلترة حسب الفئة والولاية
3. `/orders` + `/escrow` — تدفق الشراء الكامل
