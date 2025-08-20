# FastAPI 预约系统后端

## 启动方式

### 方式一：使用 uvicorn 直接启动（推荐）
```bash
# 开发环境（带自动重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产环境
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 方式二：使用开发脚本启动
```bash
python start.py
```

### 方式三：使用 uvicorn 配置文件
```bash
uvicorn main:app --config uvicorn.conf
```

## 访问地址

- **API 文档**: http://localhost:8000/docs
- **ReDoc 文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **API 根路径**: http://localhost:8000/

## 项目结构

```
fastapi/
├── main.py              # FastAPI 应用入口
├── start.py             # 开发启动脚本
├── requirements.txt     # 依赖包
└── app/
    ├── api/             # API 路由
    ├── core/            # 核心配置
    ├── db/              # 数据库
    ├── models/          # 数据模型
    ├── schemas/         # Pydantic 模型
    └── services/        # 业务逻辑
```

## 为什么推荐使用 uvicorn 直接启动？

1. **更灵活**: 可以轻松配置端口、主机、重载等参数
2. **生产标准**: 生产环境的标准做法
3. **更好性能**: 更好的性能和配置选项
4. **易于部署**: 便于容器化部署和进程管理
