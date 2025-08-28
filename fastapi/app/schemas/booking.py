"""
講座予約関連の Pydantic モデル
"""
from pydantic import BaseModel, field_validator
from datetime import datetime


# ==================== 予約一覧取得API用スキーマ ====================

class BookingListResponse(BaseModel):
    """予約一覧取得API用レスポンスモデル"""
    user_name: str
    lecture_name: str
    teacher_name: str
    status: str
    reserved_date: str
    start_time: str
    end_time: str

    class Config:
        from_attributes = True


# ==================== 予約登録API用スキーマ ====================

class BookingItemCreate(BaseModel):
    """单个预约项目创建模型"""
    user_id: int
    lecture_id: int
    teacher_id: int
    reserved_date: str  # 格式: "YYYY-MM-DD"
    start_time: str     # 格式: "HH:MM"
    end_time: str       # 格式: "HH:MM"
    
    @field_validator('reserved_date')
    @classmethod
    def validate_reserved_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError('予約日付は YYYY-MM-DD 形式である必要があります')
    
    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            raise ValueError('開始時間は HH:MM 形式である必要があります')
    
    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            raise ValueError('終了時間は HH:MM 形式である必要があります')
    
    @field_validator('user_id', 'lecture_id', 'teacher_id')
    @classmethod
    def validate_ids(cls, v):
        if v <= 0:
            raise ValueError('IDは正の整数である必要があります')
        return v


class BookingCreateResponse(BaseModel):
    """预约创建响应模型"""
    message: str = "予約登録が完了しました"


class BookingCancelResponse(BaseModel):
    """预约取消响应模型"""
    message: str = "予約キャンセルが完了しました"
