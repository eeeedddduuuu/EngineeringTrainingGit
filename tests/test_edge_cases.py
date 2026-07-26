"""
边界与异常场景测试 — 覆盖极端输入、特殊字符、并发等
"""
import httpx
import concurrent.futures


def _get_token(base_url: str) -> str:
    import random, string
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    user = {"username": f"edge_{suffix}", "password": "test123"}
    httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10)
    r = httpx.post(f"{base_url}/api/auth/login", json=user, timeout=10)
    return r.json()["access_token"]


class TestKnowledgeEdgeCases:
    """知识库检索边界测试"""

    def test_very_long_query(self, base_url):
        """边界：超长查询字符串"""
        token = _get_token(base_url)
        h = {"Authorization": f"Bearer {token}"}
        long_query = "短视频创作脚本分镜拍摄" * 20  # ~200 chars
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": long_query, "top_k": 3},
            headers=h, timeout=30,
        )
        assert resp.status_code == 200, f"超长查询应正常返回, got {resp.status_code}"

    def test_special_characters(self, base_url):
        """边界：查询含特殊符号"""
        token = _get_token(base_url)
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": "游戏策划 #角色 @设计 2024 & AI", "top_k": 3},
            headers=h, timeout=30,
        )
        assert resp.status_code == 200

    def test_single_character_query(self, base_url):
        """边界：单个字符查询"""
        token = _get_token(base_url)
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": "策", "top_k": 5},
            headers=h, timeout=30,
        )
        assert resp.status_code == 200

    def test_top_k_out_of_range(self, base_url):
        """边界：top_k 超出范围"""
        token = _get_token(base_url)
        h = {"Authorization": f"Bearer {token}"}
        for k in [0, 50, 100]:
            resp = httpx.get(
                f"{base_url}/api/knowledge/search",
                params={"q": "测试", "top_k": k},
                headers=h, timeout=10,
            )
            assert resp.status_code in (200, 422), f"top_k={k} 返回 {resp.status_code}"


class TestAuthEdgeCases:
    """认证边界测试"""

    def test_very_long_username(self, base_url):
        """边界：超长用户名注册"""
        long_name = "a" * 100
        resp = httpx.post(f"{base_url}/api/auth/register", json={
            "username": long_name, "password": "test123",
        }, timeout=10)
        assert resp.status_code in (200, 422)

    def test_very_short_password(self, base_url):
        """边界：过短密码"""
        resp = httpx.post(f"{base_url}/api/auth/register", json={
            "username": "validuser", "password": "ab",
        }, timeout=10)
        assert resp.status_code == 422

    def test_username_with_special_chars(self, base_url):
        """边界：用户名含特殊字符"""
        resp = httpx.post(f"{base_url}/api/auth/register", json={
            "username": "user@#$%", "password": "test1234",
        }, timeout=10)
        assert resp.status_code == 422


class TestConcurrency:
    """并发测试"""

    def test_concurrent_registrations(self, base_url):
        """并发：5 个用户同时注册不冲突"""
        def register(i):
            import random, string
            suffix = "".join(random.choices(string.ascii_lowercase, k=6))
            user = {"username": f"conc_{suffix}_{i}", "password": "test123"}
            r = httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10)
            return r.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(register, range(5)))
        assert all(s == 200 for s in results), f"并发注册失败: {results}"

    def test_concurrent_knowledge_queries(self, base_url):
        """并发：10 个知识库查询同时请求"""
        token = _get_token(base_url)
        h = {"Authorization": f"Bearer {token}"}
        queries = ["游戏策划", "短视频", "宣传片", "社交媒体", "护肤",
                    "美食", "数码", "旅行", "穿搭", "AI"]

        def search(q):
            r = httpx.get(
                f"{base_url}/api/knowledge/search",
                params={"q": q, "top_k": 3},
                headers=h, timeout=30,
            )
            return r.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(search, queries))
        assert all(s == 200 for s in results), f"并发查询失败: {results}"
