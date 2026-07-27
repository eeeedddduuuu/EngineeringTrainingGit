"""
审核模块 API 测试 — 正向/异常/边界
覆盖: GET /api/reviews, POST /api/review, PUT /api/review/{id}
"""
import pytest


class TestReviewCreate:
    """审核提交测试"""

    def test_create_review_approved(self, client, auth_headers, created_session):
        """正向：审核通过"""
        scheme_id = created_session["schemes"][0]["id"]
        resp = client.post("/api/review", json={
            "scheme_id": scheme_id,
            "status": "approved",
            "comment": "方案质量优秀，同意发布",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["scheme_id"] == scheme_id
        assert data["status"] == "approved"
        assert data["comment"] == "方案质量优秀，同意发布"

    def test_create_review_rejected(self, client, auth_headers, created_session):
        """正向：审核拒绝"""
        scheme_id = created_session["schemes"][1]["id"]
        resp = client.post("/api/review", json={
            "scheme_id": scheme_id,
            "status": "rejected",
            "comment": "钩子不够吸引人，需要重写",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

    def test_create_review_no_auth(self, client):
        """异常：无认证"""
        resp = client.post("/api/review", json={
            "scheme_id": 1,
            "status": "approved",
            "comment": "test",
        })
        assert resp.status_code in (401, 403)

    def test_create_review_nonexistent_scheme(self, client, auth_headers):
        """异常：方案不存在"""
        resp = client.post("/api/review", json={
            "scheme_id": 99999,
            "status": "approved",
            "comment": "test",
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_create_review_invalid_status(self, client, auth_headers):
        """边界：无效的审核状态"""
        resp = client.post("/api/review", json={
            "scheme_id": 1,
            "status": "pending",  # 只允许 approved/rejected
            "comment": "test",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_review_no_comment(self, client, auth_headers, created_session):
        """正向：不填评论也能提交"""
        scheme_id = created_session["schemes"][0]["id"]
        resp = client.post("/api/review", json={
            "scheme_id": scheme_id,
            "status": "approved",
        }, headers=auth_headers)
        assert resp.status_code == 200

    def test_create_review_long_comment(self, client, auth_headers, created_session):
        """边界：超长评论（>1000字符）"""
        scheme_id = created_session["schemes"][0]["id"]
        resp = client.post("/api/review", json={
            "scheme_id": scheme_id,
            "status": "approved",
            "comment": "长" * 1001,
        }, headers=auth_headers)
        assert resp.status_code == 422


class TestReviewList:
    """审核列表测试"""

    def test_list_reviews(self, client, auth_headers):
        """正向：列出审核记录"""
        resp = client.get("/api/reviews", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_reviews_with_status_filter(self, client, auth_headers, created_session):
        """正向：按状态筛选"""
        # 先创建一条审核
        client.post("/api/review", json={
            "scheme_id": created_session["schemes"][0]["id"],
            "status": "approved",
            "comment": "test",
        }, headers=auth_headers)

        resp = client.get("/api/reviews?status=approved", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "approved"

    def test_list_reviews_invalid_status(self, client, auth_headers):
        """边界：无效的状态筛选"""
        resp = client.get("/api/reviews?status=invalid", headers=auth_headers)
        assert resp.status_code == 422

    def test_list_reviews_pagination(self, client, auth_headers):
        """正向：分页测试"""
        resp = client.get("/api/reviews?page=1&size=5", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 5


class TestReviewUpdate:
    """审核修改测试"""

    def test_update_review(self, client, auth_headers, created_session):
        """正向：修改审核意见"""
        # 先创建
        scheme_id = created_session["schemes"][0]["id"]
        create_resp = client.post("/api/review", json={
            "scheme_id": scheme_id,
            "status": "approved",
            "comment": "原始评论",
        }, headers=auth_headers)
        review_id = create_resp.json()["id"]

        # 再修改
        resp = client.put(f"/api/review/{review_id}", json={
            "scheme_id": scheme_id,
            "status": "rejected",
            "comment": "修改后的评论",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["comment"] == "修改后的评论"

    def test_update_nonexistent_review(self, client, auth_headers):
        """异常：修改不存在的审核"""
        resp = client.put("/api/review/99999", json={
            "scheme_id": 1,
            "status": "approved",
            "comment": "test",
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_update_wrong_user_review(self, client, auth_headers):
        """
        安全测试：尝试修改其他用户的审核
        由于每个测试用户独立，review_id=1 不属于当前用户，应返回404
        """
        resp = client.put("/api/review/1", json={
            "scheme_id": 1,
            "status": "approved",
            "comment": "test",
        }, headers=auth_headers)
        assert resp.status_code == 404
