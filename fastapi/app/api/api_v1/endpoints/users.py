"""
用户相关 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserOut
from app.models.user import User
from app.core.security import get_password_hash
from app.db.database import get_db

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册 API"""
    print("用户注册请求...")
    
    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role
    )
    
    # 保存到数据库
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    print(f"用户 {user_data.email} 注册成功")
    
    return UserOut.model_validate(db_user)
    
