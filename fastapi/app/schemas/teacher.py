"""
教師関連の Pydantic モデル
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TeacherProfileBase(BaseModel):
    """教師プロフィール基礎モデル"""
    phone: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None


class TeacherProfileCreate(TeacherProfileBase):
    """教師プロフィール作成モデル"""
    pass


class TeacherProfileUpdate(TeacherProfileBase):
    """教師プロフィール更新モデル"""
    name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None


class TeacherProfileOut(TeacherProfileBase):
    """教師プロフィール出力モデル"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeacherListOut(BaseModel):
    """講師一覧出力モデル"""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None

    class Config:
        from_attributes = True


class TeacherProfileUpdateResponse(BaseModel):
    """教師プロフィール更新レスポンス"""
    message: str = "教師プロフィールの更新が完了しました"
