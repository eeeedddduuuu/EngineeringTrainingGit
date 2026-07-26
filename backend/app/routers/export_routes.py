import io
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.business import Scheme
from app.utils.deps import get_current_user

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    from docx.oxml.ns import qn
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

router = APIRouter(prefix="/api", tags=["导出"])


def _safe_filename(version: str, title: str, ext: str = "md") -> str:
    """生成安全的下载文件名（URL 编码非 ASCII 字符）"""
    raw = f"方案{version}_{title or '导出'}.{ext}"
    # ASCII 字符保持不变，非 ASCII 字符百分号编码
    try:
        encoded = quote(raw, safe="")
        return f"filename*=UTF-8''{encoded}"
    except Exception:
        # 极端回退：纯 ASCII 文件名
        safe = f"scheme_{version}.{ext}"
        return f"filename*=UTF-8''{safe}"


def _scheme_to_markdown(scheme: Scheme) -> str:
    """将方案序列化为 Markdown"""
    lines = [
        f"# {scheme.title or '未命名方案'}",
        "",
        f"**版本：** {scheme.version}  |  **评分：** {scheme.score}  |  **排名：** #{scheme.rank}",
        "",
        "---",
        "",
        "## 开头钩子",
        "",
        scheme.hook or "（无）",
        "",
        "## 分镜脚本",
        "",
    ]
    scenes = scheme.scenes or []
    if not isinstance(scenes, list):
        scenes = []
    for s in scenes:
        lines.append(f"### 第{s.get('seq', '?')}镜 — {s.get('type', '')} ({s.get('duration', '')})")
        lines.append(f"- **画面：** {s.get('description', '')}")
        lines.append(f"- **配音：** {s.get('voiceover', '')}")
        lines.append("")

    if scheme.hashtags:
        hashtags = scheme.hashtags
        if isinstance(hashtags, list):
            lines.append("## 推荐标签")
            lines.append(" ".join(hashtags))
            lines.append("")

    if scheme.cover_text:
        lines.append("## 封面文案")
        lines.append(scheme.cover_text)
        lines.append("")

    if scheme.recommendation_reason:
        lines.append("## 推荐理由")
        lines.append(scheme.recommendation_reason)
        lines.append("")

    # 如果解析出的分镜为空，但 storyboard_json 中有完整 raw_markdown，则直接输出原始内容
    raw_md = (scheme.storyboard_json or {}).get("raw_markdown", "")
    if not scenes and raw_md:
        lines.append("---")
        lines.append("")
        lines.append("## 完整脚本内容（AI 原始输出）")
        lines.append("")
        lines.append(raw_md)

    return "\n".join(lines)


def _scheme_to_docx(scheme: Scheme) -> io.BytesIO:
    """将方案序列化为真正的 .docx 文件"""
    if not DOCX_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail={"error": "dependency_missing", "detail": "python-docx 未安装，请运行: pip install python-docx"}
        )

    doc = Document()

    # --- 页面设置 ---
    section = doc.sections[0]
    section.page_width = Inches(8.27)   # A4
    section.page_height = Inches(11.69)

    # --- 标题 ---
    title_text = scheme.title or "未命名方案"
    heading = doc.add_heading(title_text, level=1)
    heading.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    # --- 元信息 ---
    meta = doc.add_paragraph()
    meta.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    meta_run = meta.add_run(f"版本：{scheme.version}  |  评分：{scheme.score}  |  排名：#{scheme.rank}")
    meta_run.font.size = Pt(10)
    meta_run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph()  # 空行

    # --- 开头钩子 ---
    doc.add_heading("开头钩子", level=2)
    hook_text = scheme.hook or "（无）"
    doc.add_paragraph(hook_text)

    # --- 分镜脚本 ---
    doc.add_heading("分镜脚本", level=2)
    scenes = scheme.scenes or []
    if not isinstance(scenes, list):
        scenes = []

    if scenes:
        for i, s in enumerate(scenes, 1):
            seq = s.get("seq", i)
            stype = s.get("type", "")
            duration = s.get("duration", "")
            desc = s.get("description", "")
            vo = s.get("voiceover", "")

            # 每镜标题
            doc.add_heading(f"第{seq}镜 — {stype} ({duration})", level=3)

            # 画面描述
            if desc:
                p = doc.add_paragraph()
                run_bold = p.add_run("画面：")
                run_bold.bold = True
                p.add_run(desc)

            # 配音
            if vo:
                p = doc.add_paragraph()
                run_bold = p.add_run("配音：")
                run_bold.bold = True
                p.add_run(vo)

            if i < len(scenes):
                doc.add_paragraph()  # 镜头间空行
    else:
        # 无结构化分镜时，尝试输出 storyboard_json 中的 raw_markdown
        raw_md = (scheme.storyboard_json or {}).get("raw_markdown", "")
        if raw_md:
            doc.add_paragraph(raw_md)
        else:
            doc.add_paragraph("（无分镜数据）")

    # --- 推荐标签 ---
    hashtags = scheme.hashtags
    if isinstance(hashtags, list) and hashtags:
        doc.add_heading("推荐标签", level=2)
        doc.add_paragraph(" ".join(hashtags))

    # --- 封面文案 ---
    if scheme.cover_text:
        doc.add_heading("封面文案", level=2)
        doc.add_paragraph(scheme.cover_text)

    # --- 推荐理由 ---
    if scheme.recommendation_reason:
        doc.add_heading("推荐理由", level=2)
        doc.add_paragraph(scheme.recommendation_reason)

    # --- 写入 BytesIO ---
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


@router.get("/export/{scheme_id}")
def export_scheme(
    scheme_id: int,
    format: str = Query("md", pattern=r"^(md|docx)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """导出方案为 Markdown 或 Word"""
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "方案不存在"})

    md_content = _scheme_to_markdown(scheme)

    if format == "md":
        content_disposition = _safe_filename(scheme.version, scheme.title, "md")
        return StreamingResponse(
            io.BytesIO(md_content.encode("utf-8")),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": content_disposition},
        )

    elif format == "docx":
        if not DOCX_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail={"error": "dependency_missing", "detail": "python-docx 未安装，请运行: pip install python-docx"}
            )
        docx_buffer = _scheme_to_docx(scheme)
        content_disposition = _safe_filename(scheme.version, scheme.title, "docx")
        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": content_disposition},
        )
