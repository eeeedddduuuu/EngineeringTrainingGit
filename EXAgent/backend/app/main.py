import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pathlib import Path
from app.database import engine, Base
from app.routers import auth, creation, schemes, history, export_routes, stats, knowledge, review, coze, agent

app = FastAPI(title="AI 数字媒体创作助手", version="0.1.0")

# 确保所有 ARK Key 在导入路由前注入环境变量
from app.config import ARK_API_KEY, ARK_VIDEO_KEY, ARK_VISION_KEY, TTS_API_KEY  # noqa: E402
ARK_API_KEY = ARK_API_KEY; ARK_VIDEO_KEY = ARK_VIDEO_KEY; ARK_VISION_KEY = ARK_VISION_KEY; TTS_API_KEY = TTS_API_KEY

# 挂载 uploads 目录为静态文件服务
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "ai_images").mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "ai_videos").mkdir(parents=True, exist_ok=True)

@app.get("/download/{filename:path}")
def download_file(filename: str):
    """下载代理 — 强制 Content-Disposition: attachment"""
    from urllib.parse import unquote
    file_path = UPLOADS_DIR / unquote(filename)
    if not file_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path), filename=file_path.name, media_type="application/octet-stream")

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

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
app.include_router(coze.router)
app.include_router(agent.router)       # EXAgent: 统一 AI 助手（DeepSeek function calling 编排）


@app.on_event("startup")
def startup():
    """应用启动时自动创建数据库表 + 注入 ARK Keys"""
    from app.models import user, business  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 提前导入 orchestrator，触发 os.environ.setdefault() 注入 ARK Keys
    # 否则懒加载导致生图/视频/素材分析等功能在首次 AI 对话前 Key 为空
    try:
        _ex_root = Path(__file__).resolve().parent.parent.parent
        if str(_ex_root) not in sys.path:
            sys.path.insert(0, str(_ex_root))
        import orchestrator  # noqa: F401
    except Exception:
        pass


@app.get("/")
def root():
    return {"message": "AI 数字媒体创作助手 API", "version": "0.1.0"}
