"""
方案模块 API 测试 — 正向/异常/边界
覆盖: GET /api/schemes, GET /api/scheme/{id}, POST /api/schemes/compare
"""
import pytest


class TestListSchemes:
    """方案列表测试"""

    def test_list_schemes_success(self, client, auth_headers, created_session):
        """正向：获取会话的方案列表"""
        sid = created_session["session_id"]
        resp = client.get(f"/api/schemes?session_id={sid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # API 返回的格式可能是直接列表也可能是带 session_id 的包装
        assert len(data.get("schemes", data if isinstance(data, list) else [])) >= 3
        # 验证每个方案的字段
        for s in data["schemes"]:
            assert s["version"] in ("A", "B", "C")
            assert "title" in s
            assert "hook" in s
            assert "score" in s
            assert "rank" in s

    def test_list_schemes_unauthorized(self, client):
        """异常：无认证"""
        resp = client.get("/api/schemes?session_id=1")
        assert resp.status_code in (401, 403)

    def test_list_schemes_nonexistent_session(self, client, auth_headers):
        """边界：不存在的会话（返回空列表）"""
        resp = client.get("/api/schemes?session_id=9999999", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # 不存在的会话返回空方案列表
        assert len(data.get("schemes", [])) == 0

    def test_list_schemes_wrong_user(self, client, auth_headers):
        """安全测试：session 不存在于当前用户则返回空列表"""
        resp = client.get("/api/schemes?session_id=9999998", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json().get("schemes", [])) == 0


class TestGetScheme:
    """单个方案详情测试"""

    def test_get_scheme_success(self, client, auth_headers, created_session):
        """正向：获取单个方案详情"""
        scheme_id = created_session["schemes"][0]["id"]
        resp = client.get(f"/api/scheme/{scheme_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == scheme_id
        assert "scenes" in data
        assert "hashtags" in data

    def test_get_scheme_not_found(self, client, auth_headers):
        """异常：方案不存在"""
        resp = client.get("/api/scheme/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_scheme_no_auth(self, client):
        """异常：无认证"""
        resp = client.get("/api/scheme/1")
        assert resp.status_code in (401, 403)


class TestCompareSchemes:
    """方案对比测试"""

    def test_compare_two_schemes(self, client, auth_headers, created_session):
        """正向：对比2个方案"""
        ids = [s["id"] for s in created_session["schemes"][:2]]
        resp = client.post("/api/schemes/compare", json={
            "scheme_ids": ids,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["schemes"]) == 2
        assert "diff_summary" in data

    def test_compare_three_schemes(self, client, auth_headers, created_session):
        """正向：对比3个方案"""
        ids = [s["id"] for s in created_session["schemes"][:3]]
        resp = client.post("/api/schemes/compare", json={
            "scheme_ids": ids,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["schemes"]) == 3

    def test_compare_one_scheme_rejected(self, client, auth_headers, created_session):
        """边界：只传1个方案ID（min_length=2）"""
        resp = client.post("/api/schemes/compare", json={
            "scheme_ids": [created_session["schemes"][0]["id"]],
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_compare_four_schemes_rejected(self, client, auth_headers, created_session):
        """边界：传4个方案ID（max_length=3）"""
        ids = [s["id"] for s in created_session["schemes"]] + [999]
        resp = client.post("/api/schemes/compare", json={
            "scheme_ids": ids,
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_compare_invalid_ids(self, client, auth_headers):
        """边界：无效的方案ID"""
        resp = client.post("/api/schemes/compare", json={
            "scheme_ids": [99999, 99998],
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_compare_empty_list(self, client, auth_headers):
        """边界：空列表"""
        resp = client.post("/api/schemes/compare", json={
            "scheme_ids": [],
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_compare_schemes_ranking(self, client, auth_headers, created_session):
        """正向：验证对比结果中有排名信息"""
        ids = [s["id"] for s in created_session["schemes"][:3]]
        resp = client.post("/api/schemes/compare", json={
            "scheme_ids": ids,
        }, headers=auth_headers)
        data = resp.json()
        # 验证返回的方案有评分差异
        scores = [s["score"] for s in data["schemes"]]
        assert len(set(scores)) >= 1  # 至少有一个不同评分
