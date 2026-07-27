"""
知识库 API 测试 — 正向/异常/边界
覆盖: GET /api/knowledge/search
"""
import pytest


class TestKnowledgeSearch:
    """知识库检索接口测试"""

    def test_search_success(self, client, auth_headers):
        """正向：正常搜索"""
        resp = client.get("/api/knowledge/search?q=护肤&top_k=5", headers=auth_headers)
        # 如果 Chroma 不可用可能返回 503
        if resp.status_code == 503:
            pytest.skip("知识库服务暂不可用（Chroma 未安装或无数据）")
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "护肤"
        assert "results" in data
        for r in data["results"]:
            assert "id" in r
            assert "title" in r
            assert "similarity" in r
            assert 0 <= r["similarity"] <= 1

    def test_search_chinese_query(self, client, auth_headers):
        """正向：中文关键词搜索"""
        resp = client.get("/api/knowledge/search?q=秋季护肤好物推荐&top_k=5", headers=auth_headers)
        if resp.status_code == 503:
            pytest.skip("知识库服务暂不可用")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) >= 0

    def test_search_single_result(self, client, auth_headers):
        """边界：top_k=1"""
        resp = client.get("/api/knowledge/search?q=护肤&top_k=1", headers=auth_headers)
        if resp.status_code == 503:
            pytest.skip("知识库服务暂不可用")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) <= 1

    def test_search_top_k_20(self, client, auth_headers):
        """边界：top_k=20（最大值）"""
        resp = client.get("/api/knowledge/search?q=护肤&top_k=20", headers=auth_headers)
        if resp.status_code == 503:
            pytest.skip("知识库服务暂不可用")
        assert resp.status_code == 200

    def test_search_top_k_exceeded(self, client, auth_headers):
        """边界：top_k超过上限"""
        resp = client.get("/api/knowledge/search?q=测试&top_k=50", headers=auth_headers)
        assert resp.status_code == 422

    def test_search_empty_query(self, client, auth_headers):
        """边界：空查询"""
        resp = client.get("/api/knowledge/search?q=&top_k=5", headers=auth_headers)
        assert resp.status_code == 422

    def test_search_no_auth(self, client):
        """异常：无认证"""
        resp = client.get("/api/knowledge/search?q=护肤")
        assert resp.status_code in (401, 403)

    def test_search_similarity_descending(self, client, auth_headers):
        """正向：验证结果按相似度降序排列"""
        resp = client.get("/api/knowledge/search?q=美食&top_k=5", headers=auth_headers)
        if resp.status_code == 503:
            pytest.skip("知识库服务暂不可用")
        data = resp.json()
        similarities = [r["similarity"] for r in data["results"]]
        assert similarities == sorted(similarities, reverse=True), (
            f"结果未按相似度降序: {similarities}"
        )

    def test_search_different_queries(self, client, auth_headers):
        """正向：同一数据集不同查询返回不同结果"""
        resp1 = client.get("/api/knowledge/search?q=护肤&top_k=3", headers=auth_headers)
        resp2 = client.get("/api/knowledge/search?q=游戏&top_k=3", headers=auth_headers)
        if resp1.status_code == 503 or resp2.status_code == 503:
            pytest.skip("知识库服务暂不可用")

        titles1 = [r["title"] for r in resp1.json()["results"]]
        titles2 = [r["title"] for r in resp2.json()["results"]]
        # 不同查询应有不同结果（或至少不完全相同）
        if titles1 and titles2:
            assert titles1 != titles2, (
                f"不同查询返回了完全相同的结果: {titles1}"
            )
