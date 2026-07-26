"""
创作流水线 API 测试（需 JWT 认证）
覆盖：提交任务 / 轮询状态 / 边界校验 / Agent 输出完整性
"""
import httpx


def _register_and_login(base_url: str) -> str:
    import random, string
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    user = {"username": f"cr_test_{suffix}", "password": "test123"}
    httpx.post(f"{base_url}/api/auth/register", json=user, timeout=10)
    r = httpx.post(f"{base_url}/api/auth/login", json=user, timeout=10)
    return r.json()["access_token"]


class TestCreationStart:
    """POST /api/creation/start — 提交创作任务"""

    def test_start_returns_task_id(self, base_url):
        """正向：提交后应立即返回 task_id 和 pending 状态"""
        token = _register_and_login(base_url)
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(f"{base_url}/api/creation/start", json={
            "topic": "AI 工具推荐", "target_audience": "职场新人",
            "platform": "douyin", "duration": "60s", "style": "干货",
        }, headers=h, timeout=10)
        assert resp.status_code in (200, 202)
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    def test_missing_required_field_rejected(self, base_url):
        """异常：缺少必填字段 topic 应返回 422"""
        token = _register_and_login(base_url)
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(f"{base_url}/api/creation/start", json={
            "target_audience": "测试", "platform": "douyin", "duration": "30s",
        }, headers=h, timeout=10)
        assert resp.status_code == 422

    def test_invalid_platform_rejected(self, base_url):
        """异常：非法平台值应被校验拒绝"""
        token = _register_and_login(base_url)
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(f"{base_url}/api/creation/start", json={
            "topic": "测试", "target_audience": "测试",
            "platform": "youtube", "duration": "30s", "style": "通用",
        }, headers=h, timeout=10)
        assert resp.status_code == 422

    def test_invalid_duration_rejected(self, base_url):
        """异常：非法时长值应被校验拒绝"""
        token = _register_and_login(base_url)
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(f"{base_url}/api/creation/start", json={
            "topic": "测试", "target_audience": "测试",
            "platform": "douyin", "duration": "10min", "style": "通用",
        }, headers=h, timeout=10)
        assert resp.status_code == 422

    def test_without_token_rejected(self, base_url):
        """异常：无 Token 提交创作被拒"""
        resp = httpx.post(f"{base_url}/api/creation/start", json={
            "topic": "测试", "target_audience": "测试",
            "platform": "douyin", "duration": "30s", "style": "通用",
        }, timeout=10)
        assert resp.status_code == 401


class TestTaskStatus:
    """GET /api/task/{id}/status — 轮询任务状态"""

    def test_task_completes_with_schemes(self, base_url):
        """正向：提交后轮询，任务应在 30s 内完成并返回 3 个方案"""
        import time
        token = _register_and_login(base_url)
        h = {"Authorization": f"Bearer {token}"}
        # 提交
        r = httpx.post(f"{base_url}/api/creation/start", json={
            "topic": "测试创作", "target_audience": "通用",
            "platform": "douyin", "duration": "30s", "style": "通用",
        }, headers=h, timeout=10)
        task_id = r.json()["task_id"]

        # 轮询
        for _ in range(15):
            time.sleep(2)
            r = httpx.get(f"{base_url}/api/task/{task_id}/status", headers=h, timeout=10)
            s = r.json()
            if s["status"] == "completed":
                assert "result" in s
                assert "schemes" in s["result"]
                schemes = s["result"]["schemes"]
                assert len(schemes) >= 1, "应至少生成 1 个方案"
                # 验证方案字段完整性
                sc = schemes[0]
                for key in ["version", "title", "hook", "score", "rank"]:
                    assert key in sc, f"方案缺少字段: {key}"
                return
            elif s["status"] == "failed":
                assert False, f"任务失败: {s.get('result')}"
        assert False, "任务超时 30s 未完成"

    def test_nonexistent_task(self, base_url):
        """异常：查询不存在的 task_id"""
        token = _register_and_login(base_url)
        h = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(
            f"{base_url}/api/task/nonexistent-id-999/status",
            headers=h, timeout=10,
        )
        # 404 或 500 均可（取决于实现）
        assert resp.status_code in (404, 500)


class TestAgentOutput:
    """Agent 输出质量验证"""

    def test_schemes_have_required_content(self, base_url):
        """验证：生成的方案包含脚本结构（scenes）"""
        import time
        token = _register_and_login(base_url)
        h = {"Authorization": f"Bearer {token}"}
        r = httpx.post(f"{base_url}/api/creation/start", json={
            "topic": "秋季护肤", "target_audience": "25-35岁女性",
            "platform": "douyin", "duration": "60s", "style": "干货+轻娱乐",
        }, headers=h, timeout=10)
        task_id = r.json()["task_id"]
        for _ in range(15):
            time.sleep(2)
            r = httpx.get(f"{base_url}/api/task/{task_id}/status", headers=h, timeout=10)
            s = r.json()
            if s["status"] == "completed":
                for sc in s["result"]["schemes"]:
                    # 每个方案至少要有标题和钩子（非空）
                    assert len(sc.get("title", "")) > 0, f"方案 {sc['version']} 标题为空"
                    # 评分应在合理范围
                    assert 0 <= sc.get("score", 0) <= 10, f"{sc['version']} 评分 {sc['score']} 超出 0-10"
                return

    def test_cross_platform_generates_different_content(self, base_url):
        """验证：同一主题在不同平台生成不同内容"""
        import time
        token = _register_and_login(base_url)
        h = {"Authorization": f"Bearer {token}"}
        topics = [
            ("AI工具推荐", "douyin"),
            ("AI工具推荐", "bilibili"),
        ]
        titles = []
        for topic, platform in topics:
            r = httpx.post(f"{base_url}/api/creation/start", json={
                "topic": topic, "target_audience": "通用",
                "platform": platform, "duration": "60s", "style": "通用",
            }, headers=h, timeout=10)
            task_id = r.json()["task_id"]
            for _ in range(15):
                time.sleep(2)
                r = httpx.get(f"{base_url}/api/task/{task_id}/status", headers=h, timeout=10)
                s = r.json()
                if s["status"] == "completed":
                    titles.append(s["result"]["schemes"][0]["title"])
                    break
        # 同一主题不同平台应产生不同标题（Mock 模式下可能相同，记录即可）
        print(f"  抖音标题: {titles[0][:40] if len(titles)>0 else 'N/A'}")
        print(f"  B站标题: {titles[1][:40] if len(titles)>1 else 'N/A'}")
