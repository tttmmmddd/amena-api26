from sqlalchemy import Column, SmallInteger, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Wilaya(Base):
    __tablename__ = "wilayas"

    id = Column(SmallInteger, primary_key=True)
    name_ar = Column(String(50), nullable=False)
    name_fr = Column(String(50))
    is_new_2026 = Column(Boolean, nullable=False, default=False)
    parent_wilaya_id = Column(SmallInteger, ForeignKey("wilayas.id"), nullable=True)
    region = Column(String(30))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="wilaya")
