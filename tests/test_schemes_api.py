"""
方案浏览 API 测试（需 JWT 认证 + 已有创作数据）
"""
import httpx
import time


def _setup_user_and_create(base_url: str) -> tuple:
    """注册登录并创建一个已完成任务，返回 (token, session_id, scheme_ids)"""
    import random, string
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    user = {"username": f"sc_test_{suffix}", "password": "test123"}
    httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10)
    r = httpx.post(f"{base_url}/api/auth/login", json=user, timeout=10)
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    r = httpx.post(f"{base_url}/api/creation/start", json={
        "topic": "测试方案查询", "target_audience": "测试",
        "platform": "douyin", "duration": "60s", "style": "测试",
    }, headers=h, timeout=10)
    task_id = r.json()["task_id"]

    for _ in range(15):
        time.sleep(2)
        r = httpx.get(f"{base_url}/api/task/{task_id}/status", headers=h, timeout=10)
        s = r.json()
        if s["status"] == "completed":
            session_id = s["result"]["session_id"]
            scheme_ids = [sc["id"] for sc in s["result"]["schemes"]]
            return token, session_id, scheme_ids
    return token, None, []


class TestSchemesList:
    """GET /api/schemes — 获取会话方案列表"""

    def test_get_schemes_by_session(self, base_url):
        """正向：通过 session_id 获取所有方案"""
        token, session_id, _ = _setup_user_and_create(base_url)
        assert session_id is not None, "创作未完成"
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(
            f"{base_url}/api/schemes", params={"session_id": session_id},
            headers=h, timeout=10,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "schemes" in data
        assert len(data["schemes"]) >= 1

    def test_without_token_rejected(self, base_url):
        """异常：无 Token 被拒"""
        resp = httpx.get(f"{base_url}/api/schemes", params={"session_id": 1}, timeout=10)
        assert resp.status_code == 401


class TestSchemeDetail:
    """GET /api/scheme/{id} — 获取单个方案详情"""

    def test_get_scheme_detail(self, base_url):
        """正向：获取单个方案的完整信息"""
        token, _, scheme_ids = _setup_user_and_create(base_url)
        assert len(scheme_ids) > 0, "未生成方案"
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{base_url}/api/scheme/{scheme_ids[0]}", headers=h, timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        for key in ["id", "version", "title", "hook", "score", "rank"]:
            assert key in data, f"缺少字段: {key}"

    def test_nonexistent_scheme(self, base_url):
        """异常：查询不存在的方案"""
        token, _, _ = _setup_user_and_create(base_url)
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{base_url}/api/scheme/99999", headers=h, timeout=10)
        assert resp.status_code in (404, 200)


class TestSchemeCompare:
    """POST /api/schemes/compare — 方案对比"""

    def test_compare_two_schemes(self, base_url):
        """正向：对比两个方案"""
        token, _, scheme_ids = _setup_user_and_create(base_url)
        assert len(scheme_ids) >= 2, "至少需要 2 个方案"
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(f"{base_url}/api/schemes/compare", json={
            "scheme_ids": scheme_ids[:2],
        }, headers=h, timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert "schemes" in data
        assert len(data["schemes"]) == 2
