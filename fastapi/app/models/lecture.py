"""
講座 SQLAlchemy ORM モデル
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Lecture(Base):
    """講座モデル"""
    __tablename__ = "lectures"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teacher_profiles.id"), nullable=False)  # 主讲讲师ID（必須）
    lecture_title = Column(Text, nullable=False)
    lecture_description = Column(Text, nullable=True)
    approval_status = Column(String(20), nullable=False, default="pending")
    is_multi_teacher = Column(Boolean, default=False)  # 多讲师講座フラグ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # リレーションシップ
    teacher = relationship("TeacherProfile", back_populates="lectures")
    lecture_teachers = relationship("LectureTeacher", back_populates="lecture", cascade="all, delete-orphan")
    carousel = relationship("Carousel", back_populates="lecture", uselist=False, cascade="all, delete-orphan")
    schedules = relationship("LectureSchedule", back_populates="lecture", cascade="all, delete-orphan")





class LectureTeacher(Base):
    """講座-講師関連モデル（多讲师講座用）"""
    __tablename__ = "lecture_teachers"

    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teacher_profiles.id"), nullable=False, primary_key=True)

    # リレーションシップ
    lecture = relationship("Lecture", back_populates="lecture_teachers")
    teacher = relationship("TeacherProfile")


class Carousel(Base):
    """カルーセル（トップページ掲載）モデル"""
    __tablename__ = "carousel"

    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False, primary_key=True)
    display_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)

    # リレーションシップ
    lecture = relationship("Lecture", back_populates="carousel")
