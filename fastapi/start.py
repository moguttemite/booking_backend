"""
开发环境启动脚本
用于快速启动 FastAPI 应用进行开发测试
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
