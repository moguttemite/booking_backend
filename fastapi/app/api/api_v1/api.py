"""
API v1 主路由設定
"""
from fastapi import APIRouter

# メインルーターを作成
api_router = APIRouter()

# ユーザールーターをインポート
from .endpoints import users

# 講師ルーターをインポート
from .endpoints import teachers

# 講座ルーターをインポート
from .endpoints import lectures

# ユーザールーターを登録
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 講師ルーターを登録
api_router.include_router(teachers.router, prefix="/teachers", tags=["teachers"])

# 講座ルーターを登録
api_router.include_router(lectures.router, prefix="/lectures", tags=["lectures"])
