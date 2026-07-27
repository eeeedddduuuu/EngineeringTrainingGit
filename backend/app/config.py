import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "你的DeepSeek_API_Key")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# ── 火山引擎 ARK Keys（不同服务用不同 Key） ──
# 请通过环境变量设置，或在此填入默认值
ARK_API_KEY = os.getenv("ARK_API_KEY", "")           # Seedream 图片生成
ARK_VIDEO_KEY = os.getenv("ARK_VIDEO_KEY", "")       # Seedance 视频生成
ARK_VISION_KEY = os.getenv("ARK_VISION_KEY", "")     # 豆包多模态识别
TTS_API_KEY = os.getenv("TTS_API_KEY", "")           # 豆包语音合成

# 注入环境变量（供下游模块 os.environ.get() 读取）
for _key in ("ARK_API_KEY", "ARK_VIDEO_KEY", "ARK_VISION_KEY", "TTS_API_KEY"):
    _val = locals().get(_key, "")
    if _val:
        os.environ[_key] = _val

# ── 模型端点（支持环境变量覆盖） ──
SEEDREAM_MODEL = os.getenv("SEEDREAM_MODEL", "doubao-seedream-4-0-250828")
SEEDANCE_MODEL = os.getenv("SEEDANCE_MODEL", "doubao-seedance-1-0-pro-250528")

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(
    __import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "chroma_db"
))
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
