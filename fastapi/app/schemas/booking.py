"""
講座予約関連の Pydantic モデル
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


# ==================== 講座スケジュール関連スキーマ ====================

class ScheduleBase(BaseModel):
    """講座スケジュール基礎モデル"""
    schedule_date: datetime
    duration_minutes: int = 60
    max_participants: int = 20
    location: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('duration_minutes')
    @classmethod
    def validate_duration_minutes(cls, v):
        if v < 15 or v > 480:  # 15分〜8時間
            raise ValueError('講座時間は15分以上8時間以下である必要があります')
        return v

    @field_validator('max_participants')
    @classmethod
    def validate_max_participants(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('最大参加者数は1人以上1000人以下である必要があります')
        return v


class ScheduleCreate(ScheduleBase):
    """講座スケジュール作成モデル"""
    lecture_id: int

    @field_validator('lecture_id')
    @classmethod
    def validate_lecture_id(cls, v):
        if v <= 0:
            raise ValueError('講座IDは正の整数である必要があります')
        return v


class ScheduleUpdate(BaseModel):
    """講座スケジュール更新モデル"""
    schedule_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    max_participants: Optional[int] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

    @field_validator('duration_minutes')
    @classmethod
    def validate_duration_minutes(cls, v):
        if v is not None and (v < 15 or v > 480):
            raise ValueError('講座時間は15分以上8時間以下である必要があります')
        return v

    @field_validator('max_participants')
    @classmethod
    def validate_max_participants(cls, v):
        if v is not None and (v < 1 or v > 1000):
            raise ValueError('最大参加者数は1人以上1000人以下である必要があります')
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ['active', 'cancelled', 'completed']:
            raise ValueError('ステータスは active、cancelled、completed のいずれかである必要があります')
        return v


class ScheduleOut(ScheduleBase):
    """講座スケジュール出力モデル"""
    id: int
    lecture_id: int
    current_participants: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScheduleListOut(BaseModel):
    """講座スケジュール一覧出力モデル"""
    id: int
    lecture_id: int
    lecture_title: str
    schedule_date: datetime
    duration_minutes: int
    max_participants: int
    current_participants: int
    status: str
    location: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 講座予約関連スキーマ ====================

class BookingBase(BaseModel):
    """講座予約基礎モデル"""
    notes: Optional[str] = None


class BookingCreate(BookingBase):
    """講座予約作成モデル"""
    schedule_id: int

    @field_validator('schedule_id')
    @classmethod
    def validate_schedule_id(cls, v):
        if v <= 0:
            raise ValueError('スケジュールIDは正の整数である必要があります')
        return v


class BookingUpdate(BaseModel):
    """講座予約更新モデル"""
    status: Optional[str] = None
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ['confirmed', 'cancelled', 'attended', 'no_show']:
            raise ValueError('ステータスは confirmed、cancelled、attended、no_show のいずれかである必要があります')
        return v


class BookingOut(BookingBase):
    """講座予約出力モデル"""
    id: int
    user_id: int
    schedule_id: int
    status: str
    booking_date: datetime
    cancellation_date: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    attendance_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BookingListOut(BaseModel):
    """講座予約一覧出力モデル"""
    id: int
    user_id: int
    user_name: str
    schedule_id: int
    lecture_title: str
    schedule_date: datetime
    status: str
    booking_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class BookingDetailOut(BaseModel):
    """講座予約詳細出力モデル"""
    id: int
    user_id: int
    user_name: str
    user_email: str
    schedule_id: int
    lecture_title: str
    lecture_description: Optional[str] = None
    schedule_date: datetime
    duration_minutes: int
    location: Optional[str] = None
    status: str
    booking_date: datetime
    cancellation_date: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    attendance_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== 待機リスト関連スキーマ ====================

class WaitlistBase(BaseModel):
    """待機リスト基礎モデル"""
    priority: int = 1

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v < 1 or v > 100:
            raise ValueError('優先度は1以上100以下である必要があります')
        return v


class WaitlistCreate(WaitlistBase):
    """待機リスト登録モデル"""
    schedule_id: int

    @field_validator('schedule_id')
    @classmethod
    def validate_schedule_id(cls, v):
        if v <= 0:
            raise ValueError('スケジュールIDは正の整数である必要があります')
        return v


class WaitlistUpdate(BaseModel):
    """待機リスト更新モデル"""
    status: Optional[str] = None
    priority: Optional[int] = None
    offer_expires_at: Optional[datetime] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ['waiting', 'offered', 'accepted', 'declined', 'expired']:
            raise ValueError('ステータスは waiting、offered、accepted、declined、expired のいずれかである必要があります')
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('優先度は1以上100以下である必要があります')
        return v


class WaitlistOut(WaitlistBase):
    """待機リスト出力モデル"""
    id: int
    user_id: int
    schedule_id: int
    status: str
    waitlist_date: datetime
    offer_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WaitlistListOut(BaseModel):
    """待機リスト一覧出力モデル"""
    id: int
    user_id: int
    user_name: str
    schedule_id: int
    lecture_title: str
    schedule_date: datetime
    priority: int
    status: str
    waitlist_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== レスポンススキーマ ====================

class ScheduleCreateResponse(BaseModel):
    """講座スケジュール作成レスポンス"""
    message: str = "講座スケジュールの作成が完了しました"
    schedule_id: int


class ScheduleUpdateResponse(BaseModel):
    """講座スケジュール更新レスポンス"""
    message: str = "講座スケジュールの更新が完了しました"


class ScheduleDeleteResponse(BaseModel):
    """講座スケジュール削除レスポンス"""
    message: str = "講座スケジュールの削除が完了しました"
    schedule_id: int


class BookingCreateResponse(BaseModel):
    """講座予約作成レスポンス"""
    message: str = "講座予約が完了しました"
    booking_id: int


class BookingUpdateResponse(BaseModel):
    """講座予約更新レスポンス"""
    message: str = "講座予約の更新が完了しました"


class BookingCancelResponse(BaseModel):
    """講座予約キャンセルレスポンス"""
    message: str = "講座予約のキャンセルが完了しました"
    booking_id: int


class WaitlistCreateResponse(BaseModel):
    """待機リスト登録レスポンス"""
    message: str = "待機リストへの登録が完了しました"
    waitlist_id: int


class WaitlistUpdateResponse(BaseModel):
    """待機リスト更新レスポンス"""
    message: str = "待機リストの更新が完了しました"


# ==================== 統計・レポート関連スキーマ ====================

class ScheduleStatsOut(BaseModel):
    """講座スケジュール統計出力モデル"""
    total_schedules: int
    active_schedules: int
    cancelled_schedules: int
    completed_schedules: int
    total_bookings: int
    total_waitlist: int


class UserBookingStatsOut(BaseModel):
    """ユーザー予約統計出力モデル"""
    total_bookings: int
    confirmed_bookings: int
    cancelled_bookings: int
    attended_bookings: int
    no_show_bookings: int
    current_waitlist: int
