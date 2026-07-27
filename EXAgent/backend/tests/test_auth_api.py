"""
认证模块 API 测试 — 正向/异常/边界
覆盖: POST /api/auth/register, POST /api/auth/login, GET /api/auth/me
"""
import pytest


class TestRegister:
    """注册接口测试"""

    def test_register_success(self, client):
        """正向：正常注册"""
        resp = client.post("/api/auth/register", json={
            "username": "newuser123",
            "password": "Test123456",
            "email": "new@test.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "newuser123"
        assert "id" in data
        assert data["message"] == "注册成功"

    def test_register_duplicate_username(self, client, auth_headers):
        """异常：重复用户名注册"""
        resp = client.post("/api/auth/register", json={
            "username": auth_headers["username"],
            "password": "Test123456",
        })
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["error"] == "user_exists"

    def test_register_short_username(self, client):
        """边界：用户名过短（<3字符）"""
        resp = client.post("/api/auth/register", json={
            "username": "ab",
            "password": "Test123456",
        })
        assert resp.status_code == 422  # Pydantic validation error

    def test_register_long_username(self, client):
        """边界：用户名过长（>20字符）"""
        resp = client.post("/api/auth/register", json={
            "username": "a" * 21,
            "password": "Test123456",
        })
        assert resp.status_code == 422

    def test_register_invalid_username_chars(self, client):
        """边界：用户名含非法字符（中文）"""
        resp = client.post("/api/auth/register", json={
            "username": "用户测试",
            "password": "Test123456",
        })
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        """边界：密码过短（<6字符）"""
        resp = client.post("/api/auth/register", json={
            "username": "validuser",
            "password": "12345",
        })
        assert resp.status_code == 422

    def test_register_missing_fields(self, client):
        """异常：缺少必填字段"""
        resp = client.post("/api/auth/register", json={})
        assert resp.status_code == 422

    def test_register_without_email(self, client):
        """正向：不提供邮箱也能注册"""
        resp = client.post("/api/auth/register", json={
            "username": "noemail_user",
            "password": "Test123456",
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == "noemail_user"


class TestLogin:
    """登录接口测试"""

    def test_login_success(self, client, auth_headers):
        """正向：正常登录"""
        resp = client.post("/api/auth/login", json={
            "username": auth_headers["username"],
            "password": "Test123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, auth_headers):
        """异常：密码错误"""
        resp = client.post("/api/auth/login", json={
            "username": auth_headers["username"],
            "password": "WrongPassword",
        })
        assert resp.status_code == 401
        detail = resp.json()["detail"]
        assert detail["error"] == "invalid_credentials"

    def test_login_nonexistent_user(self, client):
        """异常：用户不存在"""
        resp = client.post("/api/auth/login", json={
            "username": "nonexistent_user_999",
            "password": "Test123456",
        })
        assert resp.status_code == 401

    def test_login_empty_fields(self, client):
        """边界：空用户名密码（LoginRequest无min_length限制，走认证逻辑返回401）"""
        resp = client.post("/api/auth/login", json={
            "username": "",
            "password": "",
        })
        assert resp.status_code in (401, 422)

    def test_login_missing_password(self, client):
        """边界：缺少密码字段"""
        resp = client.post("/api/auth/login", json={
            "username": "someone",
        })
        assert resp.status_code == 422


class TestGetMe:
    """获取当前用户信息测试"""

    def test_get_me_success(self, client, auth_headers):
        """正向：有效 Token 获取用户信息"""
        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == auth_headers["username"]
        assert "id" in data
        assert "created_at" in data

    def test_get_me_no_token(self, client):
        """异常：无 Token（FastAPI HTTPBearer 返回 401）"""
        resp = client.get("/api/auth/me")
        assert resp.status_code in (401, 403)

    def test_get_me_invalid_token(self, client):
        """异常：无效 Token"""
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid_token_here",
        })
        assert resp.status_code == 401

    def test_get_me_expired_token(self, client):
        """边界：过期 Token（伪造的过期 JWT）"""
        # 使用一个已过期的 JWT
        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6InRlc3QiLCJleHAiOjE3MDAwMDAwMDB9."
            "invalid_signature"
        )
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {expired_token}",
        })
        assert resp.status_code == 401

    def test_get_me_malformed_token(self, client):
        """边界：格式错误的 Token"""
        resp = client.get("/api/auth/me", headers={
            "Authorization": "NotBearer just_some_string",
        })
        assert resp.status_code in (401, 403)
