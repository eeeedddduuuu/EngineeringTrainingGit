from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, creation, schemes, history, export_routes, stats, knowledge, review

app = FastAPI(title="AI 数字媒体创作助手", version="0.1.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(creation.router)
app.include_router(schemes.router)
app.include_router(history.router)
app.include_router(export_routes.router)
app.include_router(stats.router)       # P5: 真实统计数据（samples.xlsx）
app.include_router(knowledge.router)    # P5: Chroma向量检索（bge-small-zh-v1.5）
app.include_router(review.router)


@app.on_event("startup")
def startup():
    """应用启动时自动创建数据库表"""
    from app.models import user, business  # noqa: F401
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "AI 数字媒体创作助手 API", "version": "0.1.0"}
