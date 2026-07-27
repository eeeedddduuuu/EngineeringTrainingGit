"""
Pytest 配置 & 共享 Fixtures
用于所有 API 接口测试、Agent 稳定性测试、知识库检索测试、跨平台测试
"""
import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 确保 backend 目录在 sys.path 中
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 使用独立测试数据库（每次 pytest 会话重建）
TEST_DB_PATH = BACKEND_DIR / "test_app.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["CHROMA_DB_PATH"] = str(BACKEND_DIR / "data" / "test_chroma_db")


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """会话级：创建测试数据库表，测试结束后清理"""
    # 清理旧数据库
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    from app.database import Base, engine
    from app.models import user, business  # noqa: F401
    Base.metadata.create_all(bind=engine)

    yield

    # teardown: 清理测试数据库
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(scope="session")
def app():
    """创建 FastAPI 应用实例（会话级复用）"""
    from app.main import app as _app
    return _app


@pytest.fixture(scope="session")
def client(app):
    """FastAPI TestClient（会话级复用）"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def auth_headers(client):
    """每个测试独立注册+登录，返回带 Authorization 的 headers"""
    username = f"testuser_{int(time.time() * 1000000) % 1000000}"
    resp = client.post("/api/auth/register", json={
        "username": username,
        "password": "Test123456",
        "email": f"{username}@test.com",
    })
    assert resp.status_code == 200, f"注册失败: {resp.json()}"

    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": "Test123456",
    })
    assert resp.status_code == 200, f"登录失败: {resp.json()}"
    token = resp.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
        "username": username,
    }


@pytest.fixture(scope="function")
def created_session(client, auth_headers):
    """创建一个创作会话（mock模式），返回 session_id + task_id + schemes"""
    resp = client.post("/api/creation/start", json={
        "topic": "秋季护肤好物推荐",
        "target_audience": "25-35岁职场女性",
        "platform": "douyin",
        "duration": "60s",
        "style": "干货科普",
        "provider": "mock",
    }, headers=auth_headers)
    assert resp.status_code == 200, f"创建会话失败: {resp.json()}"
    task_id = resp.json()["task_id"]

    # 轮询直到完成
    for _ in range(30):
        status_resp = client.get(f"/api/task/{task_id}/status", headers=auth_headers)
        if status_resp.status_code == 200:
            data = status_resp.json()
            if data["status"] in ("completed", "failed"):
                return {
                    "task_id": task_id,
                    "session_id": data["result"]["session_id"],
                    "schemes": data["result"].get("schemes", []),
                }
        time.sleep(0.3)

    pytest.fail("创作任务未在预期时间内完成")


# ─── 内置 Mock 创作函数（不依赖 HTTP，直接测试 Agent 逻辑） ───

def run_mock_creation(topic: str, target_audience: str, platform: str,
                      duration: str, style: str) -> dict:
    """
    直接调用 P4 pipeline_adapter.create_content() 进行 Mock 创作。
    返回结果字典，供 Agent 稳定性测试和跨平台测试使用。
    """
    from p4_agent.pipeline_adapter import create_content
    return create_content(
        topic=topic,
        target_audience=target_audience,
        platform=platform,
        duration=duration,
        style=style,
        provider="mock",
        enable_trend=False,
        enable_review=False,
        enable_strategy=False,
    )


# ─── 15 条基本要求清单 ───

BASIC_REQUIREMENTS = [
    {"id": 1, "name": "明确Agent角色/用户/能力边界/输出格式",
     "check_method": "检查 agents/__init__.py 中 Agent 定义 + prompts/*.yaml 文件"},
    {"id": 2, "name": "支持输入主题/受众/平台/时长/风格",
     "check_method": "检查 CreationRequest Pydantic schema 和前端表单"},
    {"id": 3, "name": "导入不少于30条场景相关样例",
     "check_method": "检查 data/collected_samples.xlsx 行数 + Chroma 知识库条目数"},
    {"id": 4, "name": "接入不少于3个工具或插件",
     "check_method": "检查 tools/__init__.py 中的 TOOL_DEFINITIONS"},
    {"id": 5, "name": "生成不少于3个候选方案+推荐理由",
     "check_method": "检查创作结果中 schemes 数量 ≥ 3 + recommendation 字段"},
    {"id": 6, "name": "输出脚本/分镜表/拍摄清单/提示词/发布文案",
     "check_method": "检查 Scheme 表中的 scenes/storyboard_json/hashtags/cover_text 字段"},
    {"id": 7, "name": "保存会话/用户偏好/不同版本结果",
     "check_method": "检查 sessions/schemes 表 + User.preferences JSON 字段"},
    {"id": 8, "name": "提供Agent配置截图和工作流YAML/JSON导出",
     "check_method": "检查 p4_agent/prompts/ 目录下的 YAML 文件"},
    {"id": 9, "name": "采集不少于30条样例+标题/标签/平台/时间/来源",
     "check_method": "检查 samples.xlsx 列和知识库 metadata"},
    {"id": 10, "name": "使用图表展示主题分布/平台分布/时间趋势",
     "check_method": "检查 /api/stats/samples 响应 + 前端 ECharts"},
    {"id": 11, "name": "增加热点分析/脚本创作/合规审查/发布策略多个Agent",
     "check_method": "检查 agents/__init__.py 中 run_agent_pipeline()"},
    {"id": 12, "name": "针对抖音/小红书/B站生成不同版本",
     "check_method": "同一主题不同 platform 参数 → 检查输出差异"},
    {"id": 13, "name": "支持标题/封面文案/开头钩子A/B比较",
     "check_method": "检查 /api/schemes/compare 接口 + CompareResponse"},
    {"id": 14, "name": "导出Markdown/Word/素材清单",
     "check_method": "检查 /api/export/{scheme_id}?format=md|docx 接口"},
    {"id": 15, "name": "根据历史数据计算候选方案评分+迭代建议",
     "check_method": "检查 workflow/scoring.py 的 rank_schemes() + scoring_report()"},
]
