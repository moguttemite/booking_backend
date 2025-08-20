"""
应用配置设置
"""
from typing import List, Optional
import os


class Settings:
    """应用设置"""
    
    # 项目基本信息
    PROJECT_NAME: str = "Booking System API"
    API_V1_STR: str = "/api/v1"
    
    # 数据库配置
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "127.0.0.1")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5433")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "lecture_admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgresroot")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "lecture_booking")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # CORS 设置
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # React 默认端口
        "http://localhost:8080",  # Vue 默认端口
        "http://localhost:5173",  # Vite 默认端口
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
    ]
    
    # JWT 安全设置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 其他设置
    FIRST_SUPERUSER: str = os.getenv("FIRST_SUPERUSER", "admin@example.com")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "admin123")


# 创建设置实例
settings = Settings()
