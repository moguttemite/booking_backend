"""
API v1 主路由配置
"""
from fastapi import APIRouter

# 创建主路由
api_router = APIRouter()

# 基本测试端点
@api_router.get("/test")
async def test_endpoint():
    """测试端点"""
    return {"message": "API v1 is working!", "status": "success"}

# 导入用户路由
from .endpoints import users

# 注册用户路由
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 这里将来会添加更多路由
# from .endpoints import auth, lectures, bookings
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(lectures.router, prefix="/lectures", tags=["lectures"])
# api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
