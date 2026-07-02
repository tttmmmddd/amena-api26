#!/bin/bash
set -e
BASE="http://127.0.0.1:8000/api/v1"

echo "=========================================="
echo "1. تسجيل مزارع جديد"
echo "=========================================="
FARMER_REG=$(curl -s -X POST "$BASE/auth/register" -H "Content-Type: application/json" -d '{
  "full_name": "مزرعة بن علي",
  "phone": "+213551111111",
  "email": "farmer@amena.dz",
  "password": "SecurePass123",
  "primary_role": "farmer",
  "wilaya_id": 7
}')
echo "$FARMER_REG" | python3 -m json.tool

echo ""
echo "=========================================="
echo "2. تسجيل دخول المزارع"
echo "=========================================="
FARMER_LOGIN=$(curl -s -X POST "$BASE/auth/login" -H "Content-Type: application/json" -d '{
  "phone": "+213551111111",
  "password": "SecurePass123"
}')
echo "$FARMER_LOGIN" | python3 -m json.tool
FARMER_TOKEN=$(echo "$FARMER_LOGIN" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "FARMER_TOKEN obtained: ${FARMER_TOKEN:0:20}..."

echo ""
echo "=========================================="
echo "3. إنشاء ملف المزارع الشخصي"
echo "=========================================="
curl -s -X POST "$BASE/profiles/farmer" -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER_TOKEN" -d '{
  "farm_name": "مزرعة بن علي للتمور",
  "farm_description": "مزرعة عائلية في بسكرة منذ 1985",
  "established_year": 1985
}' | python3 -m json.tool

echo ""
echo "=========================================="
echo "4. إضافة منتج (تمور دقلة نور)"
echo "=========================================="
PRODUCT=$(curl -s -X POST "$BASE/products" -H "Content-Type: application/json" -H "Authorization: Bearer $FARMER_TOKEN" -d '{
  "category": "dates",
  "name": "تمور دقلة نور",
  "description": "تمور فاخرة من بسكرة",
  "price": 450,
  "unit": "kg",
  "quantity_available": 3000,
  "min_order_quantity": 1,
  "wilaya_id": 7,
  "qr_tracked": true
}')
echo "$PRODUCT" | python3 -m json.tool
PRODUCT_ID=$(echo "$PRODUCT" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "PRODUCT_ID: $PRODUCT_ID"

echo ""
echo "=========================================="
echo "5. تسجيل مستهلك جديد"
echo "=========================================="
curl -s -X POST "$BASE/auth/register" -H "Content-Type: application/json" -d '{
  "full_name": "محمد عبد الرحمن",
  "phone": "+213552222222",
  "password": "ConsumerPass123",
  "primary_role": "consumer",
  "wilaya_id": 16
}' | python3 -m json.tool

echo ""
echo "=========================================="
echo "6. تسجيل دخول المستهلك"
echo "=========================================="
CONSUMER_LOGIN=$(curl -s -X POST "$BASE/auth/login" -H "Content-Type: application/json" -d '{
  "phone": "+213552222222",
  "password": "ConsumerPass123"
}')
CONSUMER_TOKEN=$(echo "$CONSUMER_LOGIN" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo "CONSUMER_TOKEN obtained: ${CONSUMER_TOKEN:0:20}..."

echo ""
echo "=========================================="
echo "7. تصفح المنتجات (فلترة حسب الفئة والولاية)"
echo "=========================================="
curl -s "$BASE/products?category=dates&wilaya_id=7" | python3 -m json.tool

echo ""
echo "=========================================="
echo "8. إنشاء طلب شراء"
echo "=========================================="
ORDER=$(curl -s -X POST "$BASE/orders" -H "Content-Type: application/json" -H "Authorization: Bearer $CONSUMER_TOKEN" -d "{
  \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 5}],
  \"delivery_wilaya_id\": 16,
  \"delivery_address\": \"حي بئر مراد رايس، الجزائر العاصمة\"
}")
echo "$ORDER" | python3 -m json.tool
ORDER_ID=$(echo "$ORDER" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "ORDER_ID: $ORDER_ID"

echo ""
echo "=========================================="
echo "9. الدفع عبر Escrow (تجميد المبلغ)"
echo "=========================================="
curl -s -X POST "$BASE/escrow/orders/$ORDER_ID/pay" -H "Content-Type: application/json" -H "Authorization: Bearer $CONSUMER_TOKEN" -d '{
  "payment_method": "baridimob"
}' | python3 -m json.tool

echo ""
echo "=========================================="
echo "10. التحقق من حالة الطلب بعد الدفع (يجب أن تكون paid_escrow)"
echo "=========================================="
curl -s "$BASE/orders/$ORDER_ID" -H "Authorization: Bearer $CONSUMER_TOKEN" | python3 -m json.tool

echo ""
echo "=========================================="
echo "11. تحرير Escrow (المستهلك يؤكد الاستلام)"
echo "=========================================="
curl -s -X POST "$BASE/escrow/orders/$ORDER_ID/release" -H "Content-Type: application/json" -H "Authorization: Bearer $CONSUMER_TOKEN" -d '{
  "confirm": true
}' | python3 -m json.tool

echo ""
echo "=========================================="
echo "12. التحقق من نفاد كمية المنتج بعد الطلب (يجب أن تنقص 5 كغ)"
echo "=========================================="
curl -s "$BASE/products/$PRODUCT_ID" | python3 -m json.tool

echo ""
echo "=========================================="
echo "13. اختبار: محاولة شراء كمية أكبر من المتاح (يجب أن يفشل)"
echo "=========================================="
curl -s -X POST "$BASE/orders" -H "Content-Type: application/json" -H "Authorization: Bearer $CONSUMER_TOKEN" -d "{
  \"items\": [{\"product_id\": \"$PRODUCT_ID\", \"quantity\": 999999}],
  \"delivery_wilaya_id\": 16
}"

echo ""
echo ""
echo "=========================================="
echo "14. اختبار: الدخول برقم ولاية غير صحيح (يجب أن يفشل - >69)"
echo "=========================================="
curl -s -X POST "$BASE/auth/register" -H "Content-Type: application/json" -d '{
  "full_name": "اختبار خاطئ",
  "phone": "+213553333333",
  "password": "TestPass123",
  "primary_role": "consumer",
  "wilaya_id": 70
}'

echo ""
echo ""
echo "=========================================="
echo "15. اختبار: تفعيل المصادقة الثنائية للمزارع"
echo "=========================================="
TFA_ENABLE=$(curl -s -X POST "$BASE/auth/2fa/enable" -H "Authorization: Bearer $FARMER_TOKEN")
echo "$TFA_ENABLE" | python3 -m json.tool

echo ""
echo "=========================================="
echo "✅ اكتملت جميع الاختبارات"
echo "=========================================="
