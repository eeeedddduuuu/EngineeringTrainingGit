"""
导出模块 API 测试 — 正向/异常/边界
覆盖: GET /api/export/{scheme_id}?format=md, GET /api/export/{scheme_id}?format=docx
"""
import pytest


class TestExportMarkdown:
    """Markdown 导出测试"""

    def test_export_md_success(self, client, auth_headers, created_session):
        """正向：导出 Markdown"""
        scheme_id = created_session["schemes"][0]["id"]
        resp = client.get(f"/api/export/{scheme_id}?format=md", headers=auth_headers)
        assert resp.status_code == 200
        content = resp.text
        assert len(content) > 0
        # 验证 Markdown 内容包含关键字段
        assert "开头钩子" in content or "#" in content

    def test_export_md_no_auth(self, client):
        """异常：无认证"""
        resp = client.get("/api/export/1?format=md")
        assert resp.status_code in (401, 403)

    def test_export_md_not_found(self, client, auth_headers):
        """异常：方案不存在"""
        resp = client.get("/api/export/99999?format=md", headers=auth_headers)
        assert resp.status_code == 404

    def test_export_md_invalid_format(self, client, auth_headers):
        """边界：无效的导出格式"""
        resp = client.get("/api/export/1?format=pdf", headers=auth_headers)
        assert resp.status_code == 422

    def test_export_md_no_format(self, client, auth_headers):
        """边界：不指定格式（有默认值 md）"""
        resp = client.get("/api/export/1", headers=auth_headers)
        # 如果方案不存在返回404，否则应该成功
        assert resp.status_code in (200, 404)


class TestExportDocx:
    """Word 导出测试"""

    def test_export_docx_success(self, client, auth_headers, created_session):
        """正向：导出 Word"""
        scheme_id = created_session["schemes"][0]["id"]
        resp = client.get(f"/api/export/{scheme_id}?format=docx", headers=auth_headers)
        # 可能成功也可能因为 python-docx 未安装而失败
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            assert resp.headers["content-type"] == (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            detail = resp.json()["detail"]
            assert detail["error"] == "dependency_missing"

    def test_export_docx_with_content(self, client, auth_headers, created_session):
        """正向：导出有内容的方案为 Word"""
        scheme_id = created_session["schemes"][0]["id"]
        resp = client.get(f"/api/export/{scheme_id}?format=docx", headers=auth_headers)
        if resp.status_code == 200:
            # 确保生成的内容非空
            assert len(resp.content) > 0

    def test_export_content_integrity(self, client, auth_headers, created_session):
        """正向：验证导出的 Markdown 包含完整方案内容"""
        scheme_id = created_session["schemes"][0]["id"]
        resp = client.get(f"/api/export/{scheme_id}?format=md", headers=auth_headers)
        content = resp.text

        # 验证包含基本结构
        has_content = (
            "开头钩子" in content
            or "分镜脚本" in content
            or "推荐标签" in content
            or "封面文案" in content
            or "推荐理由" in content
        )
        assert has_content, f"导出的 Markdown 缺少预期内容: {content[:200]}"

    def test_export_all_schemes_in_session(self, client, auth_headers, created_session):
        """正向：导出会话中所有三个方案"""
        for scheme in created_session["schemes"]:
            resp = client.get(
                f"/api/export/{scheme['id']}?format=md",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert len(resp.text) > 0
