"""
知识库检索 API 测试
- 正向测试：正常查询返回结果
- 异常测试：空查询、缺失参数
- 边界测试：top_k 极值
"""
import pytest
import httpx


class TestKnowledgeSearch:
    """知识库检索接口测试"""

    def test_search_returns_results(self, base_url):
        """正向：正常查询应返回相关结果"""
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": "短视频脚本", "top_k": 5},
            timeout=30.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert data["query"] == "短视频脚本"
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0, "知识库应有数据，检索应返回结果"
        # 验证单条结果结构
        r = data["results"][0]
        for key in ["id", "title", "content_snippet", "platform", "tags", "source", "published_at", "similarity"]:
            assert key in r, f"结果中缺少字段: {key}"

    def test_search_similarity_descending(self, base_url):
        """正向：结果应按相似度降序排列"""
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": "游戏策划角色设计", "top_k": 5},
            timeout=30.0,
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        if len(results) >= 2:
            sims = [r["similarity"] for r in results]
            assert sims == sorted(sims, reverse=True), "相似度应降序排列"

    def test_search_top_k_limit(self, base_url):
        """边界：top_k 应限制返回数量"""
        for k in [1, 3, 5]:
            resp = httpx.get(
                f"{base_url}/api/knowledge/search",
                params={"q": "短视频", "top_k": k},
                timeout=30.0,
            )
            assert resp.status_code == 200
            assert len(resp.json()["results"]) <= k

    def test_search_empty_query_rejected(self, base_url):
        """异常：空查询应被拒绝（422 校验失败）"""
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"q": "", "top_k": 5},
            timeout=30.0,
        )
        assert resp.status_code == 422

    def test_search_missing_query_rejected(self, base_url):
        """异常：缺少 q 参数应被拒绝"""
        resp = httpx.get(
            f"{base_url}/api/knowledge/search",
            params={"top_k": 5},
            timeout=30.0,
        )
        assert resp.status_code == 422

    def test_search_different_topics(self, base_url):
        """验证：不同主题查询应返回不同结果"""
        queries = ["游戏策划", "短视频创作", "社交媒体运营"]
        top_titles = []
        for q in queries:
            resp = httpx.get(
                f"{base_url}/api/knowledge/search",
                params={"q": q, "top_k": 1},
                timeout=30.0,
            )
            assert resp.status_code == 200
            results = resp.json()["results"]
            if results:
                top_titles.append(results[0]["title"])
        # 不同查询应有不同的 top1 结果
        assert len(set(top_titles)) == len(top_titles), "不同主题的 top1 结果应各不相同"
