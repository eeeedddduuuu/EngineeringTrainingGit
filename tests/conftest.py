"""pytest 全局 fixtures"""
import pytest
import os
import sys

# 将 backend 加入 sys.path，以便导入 app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture(scope="session")
def base_url() -> str:
    """后端 API 基地址"""
    return os.getenv("API_BASE_URL", "http://localhost:8000")
