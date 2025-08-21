"""
FastAPI 主应用入口
講義予約システム バックエンド API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1.api import api_router

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="講義予約システム バックエンド API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 设置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# 根路径健康检查
@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "Booking System API", 
        "status": "running",
        "version": "1.0.0"
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


