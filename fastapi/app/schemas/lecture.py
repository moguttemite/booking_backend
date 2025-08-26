"""
講座関連の Pydantic モデル
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class LectureBase(BaseModel):
    """講座基礎モデル"""
    lecture_title: str
    lecture_description: Optional[str] = None


class LectureCreate(LectureBase):
    """講座作成モデル"""
    lecture_title: str
    lecture_description: Optional[str] = None
    teacher_id: Optional[int] = None  # 新增：指定讲座的主讲讲师ID
    is_multi_teacher: bool = False  # 新增：是否为多讲师讲座
    
    @field_validator('lecture_title')
    @classmethod
    def validate_lecture_title(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('講座タイトルは3文字以上である必要があります')
        if len(v) > 200:
            raise ValueError('講座タイトルは200文字以下である必要があります')
        return v.strip()
    
    @field_validator('lecture_description')
    @classmethod
    def validate_lecture_description(cls, v):
        if v is not None:
            if len(v) > 1000:
                raise ValueError('講座説明は1000文字以下である必要があります')
        return v
    
    @field_validator('teacher_id')
    @classmethod
    def validate_teacher_id(cls, v):
        if v is not None and v < 0:
            raise ValueError('講師IDは0以上の整数である必要があります')
        return v


class LectureUpdate(LectureBase):
    """講座更新モデル"""
    lecture_title: Optional[str] = None
    approval_status: Optional[str] = None
    is_multi_teacher: Optional[bool] = None  # 新增：是否为多讲师讲座


class LectureOut(LectureBase):
    """講座出力モデル"""
    id: int
    teacher_id: int  # 保持为必需字段，总是有主讲讲师
    approval_status: str
    is_multi_teacher: bool  # 新增：是否为多讲师讲座
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LectureListOut(BaseModel):
    """講座一覧出力モデル"""
    id: int
    lecture_title: str
    lecture_description: Optional[str] = None
    approval_status: str
    teacher_name: str
    is_multi_teacher: bool  # 新增：是否为多讲师讲座
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LectureDetailOut(LectureOut):
    """講座詳細出力モデル"""
    teacher_name: str
    teacher_email: str
    teacher_phone: Optional[str] = None
    teacher_bio: Optional[str] = None
    teacher_profile_image: Optional[str] = None

    class Config:
        from_attributes = True


class LectureScheduleBase(BaseModel):
    """講座スケジュール基礎モデル"""
    booking_date: datetime
    start_time: datetime
    end_time: datetime


class LectureScheduleCreate(LectureScheduleBase):
    """講座スケジュール作成モデル"""
    pass


class LectureScheduleOut(LectureScheduleBase):
    """講座スケジュール出力モデル"""
    id: int
    lecture_id: int
    created_at: datetime
    is_expired: bool

    class Config:
        from_attributes = True


class LectureBookingBase(BaseModel):
    """講座予約基礎モデル"""
    booking_date: datetime
    start_time: datetime
    end_time: datetime


class LectureBookingCreate(LectureBookingBase):
    """講座予約作成モデル"""
    pass


class LectureBookingOut(LectureBookingBase):
    """講座予約出力モデル"""
    id: int
    user_id: int
    lecture_id: int
    status: str
    created_at: datetime
    is_expired: bool

    class Config:
        from_attributes = True


class CarouselBase(BaseModel):
    """カルーセル基礎モデル"""
    display_order: int
    is_active: bool = True


class CarouselCreate(CarouselBase):
    """カルーセル作成モデル"""
    lecture_id: int


class CarouselOut(CarouselBase):
    """カルーセル出力モデル"""
    lecture_id: int

    class Config:
        from_attributes = True


class LectureCreateResponse(BaseModel):
    """講座作成レスポンス"""
    message: str = "講座の作成が完了しました"
    lecture_id: int
    lecture_title: str
    approval_status: str
    created_at: datetime


class LectureTeacherChange(BaseModel):
    """講座担当講師変更モデル"""
    new_teacher_id: int
    
    @field_validator('new_teacher_id')
    @classmethod
    def validate_new_teacher_id(cls, v):
        if v <= 0:
            raise ValueError('講師IDは正の整数である必要があります')
        return v


class LectureTeacherChangeResponse(BaseModel):
    """講座担当講師変更レスポンス"""
    message: str = "講座の担当講師の変更が完了しました"


# 多讲师講座関連スキーマ
class LectureTeacherBase(BaseModel):
    """講座講師基礎モデル"""
    teacher_id: int

class LectureTeacherOut(LectureTeacherBase):
    """講座講師出力モデル"""
    teacher_name: str

    class Config:
        from_attributes = True

class AddTeacherToLectureRequest(BaseModel):
    """講座に講師を追加するリクエスト"""
    teacher_id: int

class MultiTeacherLectureResponse(BaseModel):
    """多讲师講座操作レスポンス"""
    message: str
    lecture_id: int
    affected_teacher_id: Optional[int] = None
