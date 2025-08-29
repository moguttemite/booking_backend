"""
講座予約 SQLAlchemy ORM モデル
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Date, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class LectureSchedule(Base):
    """講座スケジュールモデル"""
    __tablename__ = "lecture_schedules"

    id = Column(Integer, primary_key=True, index=True)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)
    booking_date = Column(Date, nullable=False)  # 予約可能日期
    start_time = Column(Time, nullable=False)  # 開始時間
    end_time = Column(Time, nullable=False)  # 終了時間
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    is_expired = Column(Boolean, default=False)  # 是否过期

    # リレーションシップ
    lecture = relationship("Lecture", back_populates="schedules")


class LectureBooking(Base):
    """講座予約モデル"""
    __tablename__ = "lecture_bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_infos.id"), nullable=False)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)  # 直接关联讲座ID
    status = Column(String(20), nullable=False, default="pending")  # ステータス: pending, confirmed, cancelled
    booking_date = Column(Date, nullable=False)  # 予約日期
    start_time = Column(Time, nullable=False)  # 开始时间
    end_time = Column(Time, nullable=False)  # 结束时间
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    is_expired = Column(Boolean, default=False)

    # リレーションシップ
    user = relationship("User", back_populates="bookings")
    lecture = relationship("Lecture")





class BookingWaitlist(Base):
    """予約待機リストモデル"""
    __tablename__ = "booking_waitlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_infos.id"), nullable=False)
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False)  # 直接关联讲座ID
    waitlist_date = Column(DateTime, nullable=False, server_default=func.now())  # 待機リスト登録日時
    priority = Column(Integer, nullable=False, default=1)  # 優先度（1が最高）
    status = Column(String(20), nullable=False, default="waiting")  # ステータス: waiting, offered, accepted, declined, expired
    offer_expires_at = Column(DateTime(timezone=True), nullable=True)  # オファー有効期限
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # リレーションシップ
    user = relationship("User", back_populates="waitlist_entries")
    lecture = relationship("Lecture")
