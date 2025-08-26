"""
ユーザー関連の Pydantic モデル
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import re
import uuid


class UserBase(BaseModel):
    """ユーザー基礎モデル"""
    name: str
    email: EmailStr
    role: str = "student"


def generate_random_username() -> str:
    """ランダムなユーザー名を生成"""
    return f"user_{uuid.uuid4().hex[:8]}"


class UserCreate(BaseModel):
    """ユーザー作成モデル"""
    """
    ユーザー登録時に必要なパラメータ
    """
    email: EmailStr
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('パスワードは8文字以上である必要があります')
        if not re.search(r'[A-Z]', v):
            raise ValueError('パスワードには大文字が含まれている必要があります')
        if not re.search(r'[a-z]', v):
            raise ValueError('パスワードには小文字が含まれている必要があります')
        if not re.search(r'\d', v):
            raise ValueError('パスワードには数字が含まれている必要があります')
        return v


class UserOut(BaseModel):
    """ユーザー出力モデル（API レスポンス）"""
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    """データベース内のユーザーモデル"""
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserRegisterResponse(BaseModel):
    """ユーザー登録レスポンス"""
    message: str = "ユーザー登録が完了しました"


class UserLogin(BaseModel):
    """ユーザーログインモデル"""
    email: EmailStr
    password: str


class UserLoginResponse(BaseModel):
    """ユーザーログインレスポンス"""
    name: str
    role: str
    token: str


class UserUpdate(BaseModel):
    """ユーザー更新モデル"""
    name: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if not v or len(v.strip()) < 2:
                raise ValueError('名前は2文字以上である必要があります')
            if len(v) > 50:
                raise ValueError('名前は50文字以下である必要があります')
            return v.strip()
        return v


class UserRoleUpdate(BaseModel):
    """ユーザー役割更新モデル（管理者のみ）"""
    role: str
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ['student', 'teacher', 'admin']:
            raise ValueError('役割は student、teacher、admin のいずれかである必要があります')
        return v


class UserRoleUpdateResponse(BaseModel):
    """ユーザー役割更新レスポンス"""
    message: str = "ユーザー役割の更新が完了しました"
    user_id: int
    new_role: str
    teacher_profile_created: Optional[bool] = None


class PasswordChange(BaseModel):
    """パスワード変更モデル（本人のみ）"""
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('パスワードは8文字以上である必要があります')
        if not re.search(r'[A-Z]', v):
            raise ValueError('パスワードには大文字が含まれている必要があります')
        if not re.search(r'[a-z]', v):
            raise ValueError('パスワードには小文字が含まれている必要があります')
        if not re.search(r'\d', v):
            raise ValueError('パスワードには数字が含まれている必要があります')
        return v


class PasswordChangeResponse(BaseModel):
    """パスワード変更レスポンス"""
    message: str = "パスワードの変更が完了しました"


class UserDeleteResponse(BaseModel):
    """ユーザー削除レスポンス"""
    message: str = "ユーザーの削除が完了しました"
    deleted_user_email: str
