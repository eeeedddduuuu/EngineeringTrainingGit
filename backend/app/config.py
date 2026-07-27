import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "你的DeepSeek_API_Key")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# ── 火山引擎 ARK Keys（不同服务用不同 Key） ──
# 参考: docs/工程实训_API_Keys清单_20260727.md
ARK_API_KEY = os.getenv(
    "ARK_API_KEY",
    "ark-0dbaf69f-9869-4182-b514-d91697aeff37-fa841",  # Seedream 图片生成
)
ARK_VIDEO_KEY = os.getenv(
    "ARK_VIDEO_KEY",
    "ark-3474411b-9a58-48fb-a1a6-6ed0b80eb820-75c3e",  # Seedance 视频生成
)
ARK_VISION_KEY = os.getenv(
    "ARK_VISION_KEY",
    "ark-342cf4b2-f72b-4267-a670-310451f37236-6372d",  # 豆包多模态识别
)
TTS_API_KEY = os.getenv(
    "TTS_API_KEY",
    "769b27b4-b1f7-4eee-b44d-c67c1269c0b7",  # 豆包语音合成
)

# 注入环境变量（供下游模块 os.environ.get() 读取）
os.environ["ARK_API_KEY"] = ARK_API_KEY
os.environ["ARK_VIDEO_KEY"] = ARK_VIDEO_KEY
os.environ["ARK_VISION_KEY"] = ARK_VISION_KEY
os.environ["TTS_API_KEY"] = TTS_API_KEY

# ── 模型端点（支持环境变量覆盖） ──
SEEDREAM_MODEL = os.getenv("SEEDREAM_MODEL", "doubao-seedream-4-0-250828")
SEEDANCE_MODEL = os.getenv("SEEDANCE_MODEL", "doubao-seedance-1-0-pro-250528")

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
