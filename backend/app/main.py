from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import user as _user_model
from app.models import business as _business_model
from app.routers import auth, creation, schemes, history, export_routes, stats, knowledge, review

# 创建所有表
Base.metadata.create_all(bind=engine)

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
app.include_router(stats.router)
app.include_router(knowledge.router)
app.include_router(review.router)


@app.get("/")
def root():
    return {"message": "AI 数字媒体创作助手 API", "version": "0.1.0"}
