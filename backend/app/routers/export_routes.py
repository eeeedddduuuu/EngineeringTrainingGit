import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.business import Scheme
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["导出"])


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
    for s in scenes:
        lines.append(f"### 第{s.get('seq', '?')}镜 — {s.get('type', '')} ({s.get('duration', '')})")
        lines.append(f"- **画面：** {s.get('description', '')}")
        lines.append(f"- **配音：** {s.get('voiceover', '')}")
        lines.append("")

    if scheme.hashtags:
        lines.append("## 推荐标签")
        lines.append(" ".join(scheme.hashtags))
        lines.append("")

    if scheme.cover_text:
        lines.append("## 封面文案")
        lines.append(scheme.cover_text)
        lines.append("")

    if scheme.recommendation_reason:
        lines.append("## 推荐理由")
        lines.append(scheme.recommendation_reason)
        lines.append("")

    return "\n".join(lines)


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

    if format == "md":
        md_content = _scheme_to_markdown(scheme)
        filename = f"方案{scheme.version}_{scheme.title or '导出'}.md"
        return StreamingResponse(
            io.BytesIO(md_content.encode("utf-8")),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )

    elif format == "docx":
        # 简易 Word 导出（纯文本版，进阶可换 python-docx）
        md_content = _scheme_to_markdown(scheme)
        filename = f"方案{scheme.version}_{scheme.title or '导出'}.docx"
        return StreamingResponse(
            io.BytesIO(md_content.encode("utf-8")),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )
