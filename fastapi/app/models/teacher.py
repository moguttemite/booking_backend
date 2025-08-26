"""
教師 SQLAlchemy ORM モデル
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class TeacherProfile(Base):
    """教師プロフィールモデル"""
    __tablename__ = "teacher_profiles"

    id = Column(Integer, ForeignKey("user_infos.id"), primary_key=True)
    phone = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    profile_image = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # リレーションシップ
    user = relationship("User", back_populates="teacher_profile")
    lectures = relationship("Lecture", back_populates="teacher")
