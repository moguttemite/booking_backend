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

# 予約ルーターをインポート
from .endpoints import bookings

# スケジュールルーターをインポート
from .endpoints import schedules

# ユーザールーターを登録
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 講師ルーターを登録
api_router.include_router(teachers.router, prefix="/teachers", tags=["teachers"])

# 講座ルーターを登録
api_router.include_router(lectures.router, prefix="/lectures", tags=["lectures"])

# 予約ルーターを登録
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])

# スケジュールルーターを登録
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
