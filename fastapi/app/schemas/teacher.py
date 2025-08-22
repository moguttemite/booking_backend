"""
教师関連の Pydantic モデル
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TeacherProfileBase(BaseModel):
    """教师档案基础模型"""
    phone: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None


class TeacherProfileCreate(TeacherProfileBase):
    """创建教师档案模型"""
    pass


class TeacherProfileUpdate(TeacherProfileBase):
    """更新教师档案模型"""
    phone: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None


class TeacherProfileOut(TeacherProfileBase):
    """教师档案输出模型"""
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
