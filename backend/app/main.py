from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, knowledge, stats

app = FastAPI(title="AI 数字媒体创作助手", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(stats.router)


@app.on_event("startup")
def startup():
    """应用启动时自动创建数据库表"""
    # 确保所有模型已导入
    from app.models import user, business  # noqa: F401
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "AI 数字媒体创作助手 API", "version": "0.1.0"}
