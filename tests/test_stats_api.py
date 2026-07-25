"""
统计看板 API 测试（需 JWT 认证）
"""
import httpx


def _get_token(base_url: str) -> str:
    import random, string
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    user = {"username": f"sttest_{suffix}", "password": "test123"}
    httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10)
    r = httpx.post(f"{base_url}/api/auth/login", json=user, timeout=10)
    return r.json()["access_token"]


class TestStatsSamples:
    """统计接口测试（P3 已添加 JWT 认证）"""

    def test_stats_returns_200(self, base_url):
        """正向：应正常返回统计数据"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/stats/samples",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_samples" in data
        assert "topic_distribution" in data
        assert "platform_distribution" in data
        assert "monthly_trends" in data

    def test_total_samples_positive(self, base_url):
        """应有正数样本"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/stats/samples",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        data = resp.json()
        assert data["total_samples"] > 0, "样例数据应 > 0"

    def test_topic_distribution_format(self, base_url):
        """主题分布格式校验"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/stats/samples",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        topics = resp.json()["topic_distribution"]
        assert len(topics) > 0
        for t in topics:
            assert "name" in t and "count" in t

    def test_platform_distribution_format(self, base_url):
        """平台分布格式校验"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/stats/samples",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        platforms = resp.json()["platform_distribution"]
        assert len(platforms) > 0
        for p in platforms:
            assert "platform" in p and "count" in p

    def test_monthly_trends_format(self, base_url):
        """月度趋势格式校验"""
        token = _get_token(base_url)
        resp = httpx.get(
            f"{base_url}/api/stats/samples",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        trends = resp.json()["monthly_trends"]
        for t in trends:
            assert "month" in t and "count" in t
            assert len(t["month"]) == 7 and "-" in t["month"]
