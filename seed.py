"""
سكريبت تعبئة الولايات الـ69 لقاعدة بيانات التطوير — يقرأ من نفس البيانات المستخدمة
في seed_wilayas.sql لضمان التطابق. شغّله بـ: python -m app.seed
"""
from app.core.database import SessionLocal, Base, engine
from app.models.wilaya import Wilaya
import app.models  # noqa: F401

WILAYAS_DATA = [
    (1, "أدرار", "Adrar", False, "الجنوب"),
    (2, "الشلف", "Chlef", False, "الشمال"),
    (3, "الأغواط", "Laghouat", False, "الهضاب العليا"),
    (4, "أم البواقي", "Oum El Bouaghi", False, "الهضاب العليا"),
    (5, "باتنة", "Batna", False, "الهضاب العليا"),
    (6, "بجاية", "Béjaïa", False, "الشمال"),
    (7, "بسكرة", "Biskra", False, "الهضاب العليا"),
    (8, "بشار", "Béchar", False, "الجنوب"),
    (9, "البليدة", "Blida", False, "الشمال"),
    (10, "البويرة", "Bouira", False, "الشمال"),
    (11, "تمنراست", "Tamanrasset", False, "الجنوب"),
    (12, "تبسة", "Tébessa", False, "الهضاب العليا"),
    (13, "تلمسان", "Tlemcen", False, "الشمال"),
    (14, "تيارت", "Tiaret", False, "الهضاب العليا"),
    (15, "تيزي وزو", "Tizi Ouzou", False, "الشمال"),
    (16, "الجزائر العاصمة", "Alger", False, "الشمال"),
    (17, "الجلفة", "Djelfa", False, "الهضاب العليا"),
    (18, "جيجل", "Jijel", False, "الشمال"),
    (19, "سطيف", "Sétif", False, "الهضاب العليا"),
    (20, "سعيدة", "Saïda", False, "الهضاب العليا"),
    (21, "سكيكدة", "Skikda", False, "الشمال"),
    (22, "سيدي بلعباس", "Sidi Bel Abbès", False, "الشمال"),
    (23, "عنابة", "Annaba", False, "الشمال"),
    (24, "قالمة", "Guelma", False, "الشمال"),
    (25, "قسنطينة", "Constantine", False, "الشمال"),
    (26, "المدية", "Médéa", False, "الشمال"),
    (27, "مستغانم", "Mostaganem", False, "الشمال"),
    (28, "المسيلة", "M'Sila", False, "الهضاب العليا"),
    (29, "معسكر", "Mascara", False, "الشمال"),
    (30, "ورقلة", "Ouargla", False, "الجنوب"),
    (31, "وهران", "Oran", False, "الشمال"),
    (32, "البيض", "El Bayadh", False, "الهضاب العليا"),
    (33, "إليزي", "Illizi", False, "الجنوب"),
    (34, "برج بوعريريج", "Bordj Bou Arréridj", False, "الهضاب العليا"),
    (35, "بومرداس", "Boumerdès", False, "الشمال"),
    (36, "الطارف", "El Tarf", False, "الشمال"),
    (37, "تندوف", "Tindouf", False, "الجنوب"),
    (38, "تيسمسيلت", "Tissemsilt", False, "الهضاب العليا"),
    (39, "الوادي", "El Oued", False, "الجنوب"),
    (40, "خنشلة", "Khenchela", False, "الهضاب العليا"),
    (41, "سوق أهراس", "Souk Ahras", False, "الشمال"),
    (42, "تيبازة", "Tipaza", False, "الشمال"),
    (43, "ميلة", "Mila", False, "الشمال"),
    (44, "عين الدفلى", "Aïn Defla", False, "الشمال"),
    (45, "النعامة", "Naâma", False, "الهضاب العليا"),
    (46, "عين تموشنت", "Aïn Témouchent", False, "الشمال"),
    (47, "غرداية", "Ghardaïa", False, "الجنوب"),
    (48, "غليزان", "Relizane", False, "الشمال"),
    (49, "تيميمون", "Timimoun", False, "الجنوب"),
    (50, "برج باجي مختار", "Bordj Badji Mokhtar", False, "الجنوب"),
    (51, "أولاد جلال", "Ouled Djellal", False, "الجنوب"),
    (52, "بني عباس", "Béni Abbès", False, "الجنوب"),
    (53, "عين صالح", "In Salah", False, "الجنوب"),
    (54, "عين قزام", "In Guezzam", False, "الجنوب"),
    (55, "تقرت", "Touggourt", False, "الجنوب"),
    (56, "جانت", "Djanet", False, "الجنوب"),
    (57, "المغير", "El M'Ghair", False, "الجنوب"),
    (58, "المنيعة", "El Meniaa", False, "الجنوب"),
    (59, "أفلو", "Aflou", True, "الهضاب العليا"),
    (60, "بريكة", "Barika", True, "الهضاب العليا"),
    (61, "القنطرة", "El Kantara", True, "الهضاب العليا"),
    (62, "بئر العاتر", "Bir El Ater", True, "الهضاب العليا"),
    (63, "العريشة", "El Aricha", True, "الشمال"),
    (64, "قصر الشلالة", "Ksar Chellala", True, "الهضاب العليا"),
    (65, "عين وسارة", "Aïn Oussera", True, "الهضاب العليا"),
    (66, "مسعد", "Messaad", True, "الهضاب العليا"),
    (67, "قصر البخاري", "Ksar El Boukhari", True, "الشمال"),
    (68, "بوسعادة", "Bou Saâda", True, "الهضاب العليا"),
    (69, "الأبيض سيدي الشيخ", "Aïn Sefra Sud", True, "الهضاب العليا"),
]


def seed_wilayas():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Wilaya).count() > 0:
            print("الولايات معبّأة مسبقاً — تخطّي.")
            return
        for id_, name_ar, name_fr, is_new, region in WILAYAS_DATA:
            db.add(Wilaya(id=id_, name_ar=name_ar, name_fr=name_fr, is_new_2026=is_new, region=region))
        db.commit()
        print(f"تمت تعبئة {len(WILAYAS_DATA)} ولاية بنجاح.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_wilayas()
