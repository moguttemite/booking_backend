"""
開発環境起動スクリプト
FastAPI アプリケーションを開発テスト用に素早く起動するためのスクリプト
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
