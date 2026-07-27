"""
统计模块 API 测试 — 正向/异常/边界
覆盖: GET /api/stats/samples, GET /api/statistics/summary, GET /api/stats/wordclouds
"""
import pytest


class TestStatsSamples:
    """样例统计测试"""

    def test_stats_samples_success(self, client, auth_headers):
        """正向：获取样例统计数据"""
        resp = client.get("/api/stats/samples", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_samples" in data
        assert "topic_distribution" in data
        assert "platform_distribution" in data
        assert "monthly_trends" in data

    def test_stats_samples_topic_distribution(self, client, auth_headers):
        """正向：验证主题分布数据格式"""
        resp = client.get("/api/stats/samples", headers=auth_headers)
        data = resp.json()
        for item in data["topic_distribution"]:
            assert "name" in item
            assert "count" in item
            assert isinstance(item["count"], int)

    def test_stats_samples_platform_distribution(self, client, auth_headers):
        """正向：验证平台分布数据格式"""
        resp = client.get("/api/stats/samples", headers=auth_headers)
        data = resp.json()
        for item in data["platform_distribution"]:
            assert "platform" in item
            assert "count" in item
            assert isinstance(item["count"], int)

    def test_stats_samples_monthly_trends(self, client, auth_headers):
        """正向：验证月度趋势数据格式"""
        resp = client.get("/api/stats/samples", headers=auth_headers)
        data = resp.json()
        for item in data["monthly_trends"]:
            assert "month" in item
            assert "count" in item
            assert isinstance(item["count"], int)

    def test_stats_samples_no_auth(self, client):
        """异常：无认证"""
        resp = client.get("/api/stats/samples")
        assert resp.status_code in (401, 403)


class TestDashboardSummary:
    """看板汇总测试"""

    def test_summary_success(self, client, auth_headers):
        """正向：获取看板汇总"""
        resp = client.get("/api/statistics/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data
        assert "in_progress" in data
        assert "pending_review" in data
        assert "completed_this_week" in data
        assert "total_schemes" in data
        assert "total_users" in data
        # 验证都是非负整数
        for key in data:
            assert isinstance(data[key], int)
            assert data[key] >= 0

    def test_summary_no_auth(self, client):
        """异常：无认证"""
        resp = client.get("/api/statistics/summary")
        assert resp.status_code in (401, 403)


class TestWordClouds:
    """词云接口测试"""

    def test_wordclouds_success(self, client, auth_headers):
        """正向：获取词云"""
        resp = client.get("/api/stats/wordclouds", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "wordclouds" in data
        for wc in data["wordclouds"]:
            assert "label" in wc
            assert "base64" in wc
            assert len(wc["base64"]) > 0  # 应有 base64 数据

    def test_wordclouds_no_auth(self, client):
        """异常：无认证"""
        resp = client.get("/api/stats/wordclouds")
        assert resp.status_code in (401, 403)
