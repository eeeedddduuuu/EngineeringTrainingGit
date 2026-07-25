"""
用户认证 API 测试
- 注册/登录 正向流程
- 异常流程：重复注册、错误密码、无效 Token
"""
import pytest
import httpx
import random
import string


def _random_user():
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    return {
        "username": f"testuser_{suffix}",
        "password": "test123456",
        "email": f"test_{suffix}@example.com",
    }


class TestAuth:
    """认证接口测试"""

    def test_register_success(self, base_url):
        """正向：注册成功"""
        user = _random_user()
        resp = httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10.0)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == user["username"]
        assert "id" in data

    def test_register_duplicate_rejected(self, base_url):
        """异常：重复注册应被拒绝"""
        user = _random_user()
        # 第一次
        r1 = httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10.0)
        assert r1.status_code == 200
        # 第二次
        r2 = httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10.0)
        assert r2.status_code == 400

    def test_login_success_returns_token(self, base_url):
        """正向：登录成功返回 Token"""
        user = _random_user()
        httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10.0)
        resp = httpx.post(f"{base_url}/api/auth/login", json={
            "username": user["username"],
            "password": user["password"],
        }, timeout=10.0)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == user["username"]

    def test_login_wrong_password_rejected(self, base_url):
        """异常：错误密码应被拒绝（401）"""
        user = _random_user()
        httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10.0)
        resp = httpx.post(f"{base_url}/api/auth/login", json={
            "username": user["username"],
            "password": "wrongpassword",
        }, timeout=10.0)
        assert resp.status_code == 401

    def test_login_nonexistent_user_rejected(self, base_url):
        """异常：不存在用户应被拒绝"""
        resp = httpx.post(f"{base_url}/api/auth/login", json={
            "username": "nonexistent_user_xyz",
            "password": "whatever",
        }, timeout=10.0)
        assert resp.status_code == 401

    def test_me_with_valid_token(self, base_url):
        """正向：有效 Token 获取用户信息"""
        user = _random_user()
        httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10.0)
        login_resp = httpx.post(f"{base_url}/api/auth/login", json={
            "username": user["username"],
            "password": user["password"],
        }, timeout=10.0)
        token = login_resp.json()["access_token"]

        resp = httpx.get(
            f"{base_url}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == user["username"]

    def test_me_without_token_rejected(self, base_url):
        """异常：无 Token 应被拒绝"""
        resp = httpx.get(f"{base_url}/api/auth/me", timeout=10.0)
        # 当前实现可能 401 或 422（取决于参数校验方式）
        assert resp.status_code in (401, 422, 403)

    def test_me_with_invalid_token_rejected(self, base_url):
        """异常：无效 Token 应被拒绝"""
        resp = httpx.get(
            f"{base_url}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
            timeout=10.0,
        )
        assert resp.status_code in (401, 403)
