import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "你的DeepSeek_API_Key")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
HF_ENDPOINT = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

# 豆包/火山方舟 多模态 API
ARK_API_KEY = os.getenv("ARK_API_KEY", "你的火山方舟_API_Key")
os.environ.setdefault("ARK_API_KEY", ARK_API_KEY)
