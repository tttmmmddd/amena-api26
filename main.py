"""
نقطة الدخول الرئيسية لـ AMENA API
تشغيل محلي: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
import app.models  # noqa: F401 — يضمن تسجيل كل النماذج قبل create_all

from app.routers.auth import router as auth_router
from app.routers.profiles import router as profiles_router
from app.routers.products import router as products_router
from app.routers.orders import orders_router, escrow_router

# في الإنتاج استخدم Alembic للترحيلات (migrations) بدل create_all
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="واجهة برمجية لمنصة آمنة — السوق الزراعي الرقمي الجزائري",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # قيّد هذا في الإنتاج لنطاقات محددة فقط
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(profiles_router, prefix=settings.API_V1_PREFIX)
app.include_router(products_router, prefix=settings.API_V1_PREFIX)
app.include_router(orders_router, prefix=settings.API_V1_PREFIX)
app.include_router(escrow_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "message": "مرحباً بك في AMENA API 🌾",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
