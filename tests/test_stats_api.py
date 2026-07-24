"""
统计看板 API 测试
"""
import pytest
import httpx


class TestStatsSamples:
    """统计接口测试"""

    def test_stats_returns_200(self, base_url):
        """正向：应正常返回统计数据"""
        resp = httpx.get(f"{base_url}/api/stats/samples", timeout=30.0)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_samples" in data
        assert "topic_distribution" in data
        assert "platform_distribution" in data
        assert "monthly_trends" in data

    def test_total_samples_positive(self, base_url):
        """应有正数样本"""
        resp = httpx.get(f"{base_url}/api/stats/samples", timeout=30.0)
        data = resp.json()
        assert data["total_samples"] > 0, "样例数据应 > 0"

    def test_topic_distribution_format(self, base_url):
        """主题分布格式校验"""
        resp = httpx.get(f"{base_url}/api/stats/samples", timeout=30.0)
        topics = resp.json()["topic_distribution"]
        assert len(topics) > 0
        for t in topics:
            assert "name" in t
            assert "count" in t
            assert isinstance(t["count"], int)

    def test_platform_distribution_format(self, base_url):
        """平台分布格式校验"""
        resp = httpx.get(f"{base_url}/api/stats/samples", timeout=30.0)
        platforms = resp.json()["platform_distribution"]
        assert len(platforms) > 0
        for p in platforms:
            assert "platform" in p
            assert "count" in p

    def test_monthly_trends_format(self, base_url):
        """月度趋势格式校验"""
        resp = httpx.get(f"{base_url}/api/stats/samples", timeout=30.0)
        trends = resp.json()["monthly_trends"]
        for t in trends:
            assert "month" in t
            assert "count" in t
            # 月份格式：YYYY-MM
            assert len(t["month"]) == 7
            assert "-" in t["month"]
