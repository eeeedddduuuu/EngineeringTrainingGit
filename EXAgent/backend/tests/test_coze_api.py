"""
Coze 绑定 API 测试 — 正向/异常/边界
覆盖: POST /api/coze/bind, GET /api/coze/status, DELETE /api/coze/unbind
"""
import pytest


class TestCozeBind:
    """Coze 绑定接口测试"""

    def test_bind_success(self, client, auth_headers):
        """正向：绑定 Coze API Key"""
        resp = client.post("/api/coze/bind", json={
            "api_key": "pat_test_coze_api_key_12345",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["bound"] is True
        assert data["platform"] == "扣子"

    def test_bind_no_auth(self, client):
        """异常：无认证"""
        resp = client.post("/api/coze/bind", json={
            "api_key": "pat_test",
        })
        assert resp.status_code in (401, 403)

    def test_bind_missing_key(self, client, auth_headers):
        """边界：不传 api_key"""
        resp = client.post("/api/coze/bind", json={}, headers=auth_headers)
        assert resp.status_code == 422


class TestCozeStatus:
    """Coze 状态查询测试"""

    def test_status_unbound(self, client, auth_headers):
        """正向：未绑定时的状态"""
        resp = client.get("/api/coze/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["bound"] is False

    def test_status_bound(self, client, auth_headers):
        """正向：绑定后的状态"""
        # 先绑定
        client.post("/api/coze/bind", json={
            "api_key": "pat_test_key_for_status",
        }, headers=auth_headers)

        resp = client.get("/api/coze/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["bound"] is True

    def test_status_no_auth(self, client):
        """异常：无认证"""
        resp = client.get("/api/coze/status")
        assert resp.status_code in (401, 403)


class TestCozeUnbind:
    """Coze 解绑测试"""

    def test_unbind_success(self, client, auth_headers):
        """正向：解绑"""
        # 先绑定
        client.post("/api/coze/bind", json={
            "api_key": "pat_test_to_unbind",
        }, headers=auth_headers)

        # 解绑
        resp = client.delete("/api/coze/unbind", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["bound"] is False
        assert data["message"] == "Coze 账号已解绑"

        # 验证已解绑
        status_resp = client.get("/api/coze/status", headers=auth_headers)
        assert status_resp.json()["bound"] is False

    def test_unbind_no_auth(self, client):
        """异常：无认证"""
        resp = client.delete("/api/coze/unbind")
        assert resp.status_code in (401, 403)

    def test_unbind_when_not_bound(self, client, auth_headers):
        """边界：未绑定时解绑（返回 400）"""
        resp = client.delete("/api/coze/unbind", headers=auth_headers)
        # API 要求已绑定才能解绑
        assert resp.status_code == 400
