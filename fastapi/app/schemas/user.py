"""
用户相关的 Pydantic 模型
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模型"""
    name: str
    email: EmailStr
    role: str = "student"


class UserCreate(BaseModel):
    """用户创建模型"""
    """
    用户注册时需要输入的参数
    """
    email: EmailStr
    password1: str
    password2: str


class UserOut(UserBase):
    """用户输出模型（API 响应）"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool = False

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    """数据库中的用户模型"""
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
