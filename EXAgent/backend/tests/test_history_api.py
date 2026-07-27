"""
历史记录 API 测试 — 正向/异常/边界
覆盖: GET /api/history
"""
import pytest


class TestHistory:
    """历史记录接口测试"""

    def test_get_history_empty(self, client, auth_headers):
        """正向：新用户无历史"""
        resp = client.get("/api/history?page=1&size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_get_history_with_data(self, client, auth_headers, created_session):
        """正向：有创作记录后查询"""
        resp = client.get("/api/history?page=1&size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert item["topic"] == "秋季护肤好物推荐"
        assert item["platform"] == "douyin"
        assert item["scheme_count"] >= 3

    def test_history_pagination(self, client, auth_headers):
        """正向：分页测试"""
        # 创建多个会话
        for i in range(3):
            client.post("/api/creation/start", json={
                "topic": f"测试主题{i}",
                "target_audience": "测试受众",
                "platform": "douyin",
                "duration": "60s",
                "style": "干货科普",
                "provider": "mock",
            }, headers=auth_headers)

        # 第1页，每页2条
        resp = client.get("/api/history?page=1&size=2", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) <= 2

    def test_history_no_auth(self, client):
        """异常：无认证"""
        resp = client.get("/api/history")
        assert resp.status_code in (401, 403)

    def test_history_invalid_page(self, client, auth_headers):
        """边界：无效页码（<1）"""
        resp = client.get("/api/history?page=0&size=10", headers=auth_headers)
        assert resp.status_code == 422

    def test_history_large_size(self, client, auth_headers):
        """边界：超出限制的size（>50）"""
        resp = client.get("/api/history?page=1&size=100", headers=auth_headers)
        assert resp.status_code == 422

    def test_history_reverse_chronological(self, client, auth_headers):
        """正向：验证按时间倒序"""
        # 创建两个会话
        client.post("/api/creation/start", json={
            "topic": "先创建",
            "target_audience": "测试",
            "platform": "douyin",
            "duration": "60s",
            "style": "干货科普",
            "provider": "mock",
        }, headers=auth_headers)

        import time
        time.sleep(0.2)  # 确保时间戳不同

        client.post("/api/creation/start", json={
            "topic": "后创建",
            "target_audience": "测试",
            "platform": "xiaohongshu",
            "duration": "60s",
            "style": "测评种草",
            "provider": "mock",
        }, headers=auth_headers)

        resp = client.get("/api/history?page=1&size=10", headers=auth_headers)
        data = resp.json()
        if len(data["items"]) >= 2:
            # 最新的应该在前面
            assert data["items"][0]["topic"] == "后创建"
