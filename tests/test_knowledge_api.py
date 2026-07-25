"""
知识库检索 API 测试（需 JWT 认证）
"""
import httpx


def _get_token(base_url: str) -> str:
    """注册测试用户并返回 JWT Token"""
    import random, string
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    user = {"username": f"kbtest_{suffix}", "password": "test123"}
    httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10)
    r = httpx.post(f"{base_url}/api/auth/login", json=user, timeout=10)
    return r.json()["access_token"]


class TestKnowledgeSearch:
    """知识库检索接口测试（P3 已添加 JWT 认证）"""

    def test_search_returns_results(self, base_url):
        """正向：正常查询应返回相关结果"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": "短视频脚本", "top_k": 5},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0, "知识库应有数据，检索应返回结果"
        r = data["results"][0]
        for key in ["id", "title", "content_snippet", "platform", "tags", "source", "similarity"]:
            assert key in r, f"结果中缺少字段: {key}"

    def test_search_similarity_descending(self, base_url):
        """正向：结果应按相似度降序排列"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": "游戏策划角色设计", "top_k": 5},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        if len(results) >= 2:
            sims = [r["similarity"] for r in results]
            assert sims == sorted(sims, reverse=True), "相似度应降序排列"

    def test_search_top_k_limit(self, base_url):
        """边界：top_k 应限制返回数量"""
        token = _get_token(base_url)
        for k in [1, 3, 5]:
            resp = httpx.get(
                f"{base_url}/api/knowledge/search",
                params={"q": "短视频", "top_k": k},
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )
            assert resp.status_code == 200
            assert len(resp.json()["results"]) <= k

    def test_search_empty_query_rejected(self, base_url):
        """异常：空查询应被拒绝"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": "", "top_k": 5},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        assert resp.status_code == 422

    def test_search_missing_query_rejected(self, base_url):
        """异常：缺少 q 参数应被拒绝"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"top_k": 5},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        assert resp.status_code == 422

    def test_search_different_topics(self, base_url):
        """验证：不同主题查询应返回不同结果"""
        token = _get_token(base_url)
        queries = ["游戏策划", "短视频创作", "社交媒体运营"]
        top_titles = []
        for q in queries:
            resp = httpx.get(
                f"{base_url}/api/knowledge/search",
                params={"q": q, "top_k": 1},
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )
            assert resp.status_code == 200
            results = resp.json()["results"]
            if results:
                top_titles.append(results[0]["title"])
        assert len(set(top_titles)) == len(top_titles), "不同主题的 top1 结果应各不相同"
