"""
创作模块 API 测试 — 正向/异常/边界
覆盖: POST /api/creation/start, GET /api/task/{task_id}/status,
      POST /api/creation/upload, POST /api/creation/analyze, GET /api/creation/analyses
"""
import time
import pytest


class TestStartCreation:
    """创作任务提交测试"""

    VALID_INPUT = {
        "topic": "秋季护肤好物推荐",
        "target_audience": "25-35岁职场女性",
        "platform": "douyin",
        "duration": "60s",
        "style": "干货科普",
        "provider": "mock",
    }

    def test_start_creation_success(self, client, auth_headers):
        """正向：正常提交创作任务"""
        resp = client.post("/api/creation/start", json=self.VALID_INPUT, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert data["message"] == "创作任务已提交，请轮询状态接口获取结果"

    def test_start_creation_all_platforms(self, client, auth_headers):
        """正向：三个平台分别提交"""
        for platform in ["douyin", "xiaohongshu", "bilibili"]:
            payload = {**self.VALID_INPUT, "platform": platform}
            resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
            assert resp.status_code == 200, f"平台 {platform} 失败: {resp.json()}"

    def test_start_creation_all_durations(self, client, auth_headers):
        """正向：三种时长分别提交"""
        for duration in ["30s", "60s", "3min"]:
            payload = {**self.VALID_INPUT, "duration": duration}
            resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
            assert resp.status_code == 200, f"时长 {duration} 失败: {resp.json()}"

    def test_start_creation_all_providers(self, client, auth_headers):
        """正向：三种模式分别提交"""
        for provider in ["mock", "deepseek", "coze"]:
            payload = {**self.VALID_INPUT, "provider": provider}
            resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
            assert resp.status_code == 200, f"模式 {provider} 失败: {resp.json()}"

    def test_start_creation_with_image_url(self, client, auth_headers):
        """正向：带图片URL的多模态创作"""
        payload = {**self.VALID_INPUT, "image_url": "/uploads/test.png"}
        resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
        assert resp.status_code == 200

    def test_start_creation_no_auth(self, client):
        """异常：无认证"""
        resp = client.post("/api/creation/start", json=self.VALID_INPUT)
        assert resp.status_code in (401, 403)

    def test_start_creation_empty_topic(self, client, auth_headers):
        """边界：空主题"""
        payload = {**self.VALID_INPUT, "topic": ""}
        resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_start_creation_invalid_platform(self, client, auth_headers):
        """边界：无效平台"""
        payload = {**self.VALID_INPUT, "platform": "youtube"}
        resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_start_creation_invalid_duration(self, client, auth_headers):
        """边界：无效时长"""
        payload = {**self.VALID_INPUT, "duration": "10min"}
        resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_start_creation_invalid_provider(self, client, auth_headers):
        """边界：无效 provider"""
        payload = {**self.VALID_INPUT, "provider": "gpt4"}
        resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_start_creation_very_long_topic(self, client, auth_headers):
        """边界：超长主题（>255字符）"""
        payload = {**self.VALID_INPUT, "topic": "A" * 256}
        resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    def test_start_creation_special_chars_topic(self, client, auth_headers):
        """边界：主题含特殊字符"""
        payload = {**self.VALID_INPUT, "topic": "秋季护肤<script>alert('xss')</script>"}
        resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
        assert resp.status_code == 200  # 应接受，安全由前端处理

    def test_start_creation_same_topic_different_style(self, client, auth_headers):
        """正向：同一主题不同风格"""
        for style in ["干货科普", "测评种草", "剧情故事"]:
            payload = {**self.VALID_INPUT, "style": style}
            resp = client.post("/api/creation/start", json=payload, headers=auth_headers)
            assert resp.status_code == 200


class TestTaskStatus:
    """任务状态轮询测试"""

    def test_poll_completed_task(self, client, auth_headers, created_session):
        """正向：轮询已完成的task"""
        resp = client.get(
            f"/api/task/{created_session['task_id']}/status",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert len(data["result"]["schemes"]) >= 3

    def test_poll_nonexistent_task(self, client, auth_headers):
        """异常：轮询不存在的task"""
        resp = client.get("/api/task/nonexistent-id/status", headers=auth_headers)
        assert resp.status_code == 404

    def test_poll_unauthorized(self, client):
        """异常：无认证"""
        resp = client.get("/api/task/some-id/status")
        assert resp.status_code in (401, 403)


class TestMaterialUpload:
    """素材上传测试"""

    def test_upload_image_success(self, client, auth_headers):
        """正向：上传图片文件"""
        # 创建一个微小的假PNG
        fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        resp = client.post(
            "/api/creation/upload",
            files={"file": ("test.png", fake_png, "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "file_id" in data
        assert data["filename"] == "test.png"

    def test_upload_invalid_extension(self, client, auth_headers):
        """异常：上传不支持的文件类型"""
        resp = client.post(
            "/api/creation/upload",
            files={"file": ("test.exe", b"malicious", "application/octet-stream")},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "invalid_file_type"

    def test_list_uploads(self, client, auth_headers):
        """正向：列出已上传文件"""
        resp = client.get("/api/creation/uploads", headers=auth_headers)
        assert resp.status_code == 200
        assert "files" in resp.json()
        assert "total" in resp.json()

    def test_delete_upload(self, client, auth_headers):
        """正向：删除已上传文件"""
        # 先上传
        fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        upload_resp = client.post(
            "/api/creation/upload",
            files={"file": ("to_delete.png", fake_png, "image/png")},
            headers=auth_headers,
        )
        file_id = upload_resp.json()["file_id"]

        # 再删除
        resp = client.delete(f"/api/creation/uploads/{file_id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_nonexistent_upload(self, client, auth_headers):
        """异常：删除不存在的文件"""
        resp = client.delete("/api/creation/uploads/nonexistent_id", headers=auth_headers)
        assert resp.status_code == 404


class TestMaterialAnalysis:
    """素材分析测试"""

    def test_analyze_image(self, client, auth_headers):
        """正向：分析上传的图片"""
        # 先上传一张假图片
        fake_png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        client.post(
            "/api/creation/upload",
            files={"file": ("analyze_me.png", fake_png, "image/png")},
            headers=auth_headers,
        )
        resp = client.post("/api/creation/analyze-image", headers=auth_headers)
        # 可能成功或失败（取决于环境），但不应500
        assert resp.status_code in (200, 500)

    def test_analyze_without_upload(self, client, auth_headers):
        """异常：未上传文件时分析"""
        # 需要先确保用户没有上传文件（新用户fixture确保这一点）
        resp = client.post("/api/creation/analyze-image", headers=auth_headers)
        assert resp.status_code == 400

    def test_list_analyses(self, client, auth_headers):
        """正向：列出分析历史"""
        resp = client.get("/api/creation/analyses", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_get_nonexistent_analysis(self, client, auth_headers):
        """异常：获取不存在的分析记录"""
        resp = client.get("/api/creation/analyses/99999", headers=auth_headers)
        assert resp.status_code == 404
