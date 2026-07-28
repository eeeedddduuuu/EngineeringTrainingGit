"""统一 Agent 对话接口 — EXAgent 终极助手

把 EXAgent 目录下的 orchestrator（DeepSeek function calling 编排器）接入后端。
用户用自然语言对话，Agent 自动判断调用哪些后端工具（创作/生图/生视频/配音/搜索/合规等）。
支持多模态文件上传，Agent 可分析用户上传的图片/视频/音频。
"""
import sys
import uuid
from pathlib import Path

# 确保能 import EXAgent 目录下的 orchestrator
# 本文件: EXAgent/backend/app/routers/agent.py → parent x4 = EXAgent/
_EXDIR = Path(__file__).resolve().parent.parent.parent.parent
if str(_EXDIR) not in sys.path:
    sys.path.insert(0, str(_EXDIR))

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/agent", tags=["AI助手"])

# 上传目录
_AGENT_UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads" / "agent_uploads"
_AGENT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="用户自然语言输入")
    session_id: str | None = Field(None, description="会话ID，为空则新建会话")
    files: list[dict] | None = Field(None, description="上传的素材文件列表 [{file_path, file_type, file_url}]")


def _build_user_message(message: str, files: list[dict] | None) -> str:
    """将用户消息和上传文件信息拼接为完整 prompt"""
    if not files:
        return message
    lines = ["[用户上传了以下素材文件，你可以用 analyze_material / concat_video 等工具处理它们:]"]
    for i, f in enumerate(files, 1):
        ftype = f.get("file_type", "file")
        fpath = f.get("file_path", "")
        emoji = {"image": "🖼️", "video": "🎬", "audio": "🎵"}.get(ftype, "📎")
        lines.append(f"{i}. {emoji} {ftype}: {fpath}")
    lines.append(f"\n用户消息: {message}")
    return "\n".join(lines)


@router.post("/upload")
async def agent_upload(file: UploadFile = File(...)):
    """上传素材文件供 Agent 分析/处理。返回 file_path 供工具调用。"""
    # 读取文件
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    # 推断类型
    ext = (file.filename or "file").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
        file_type = "image"
    elif ext in ("mp4", "mov", "avi", "mkv", "webm", "flv"):
        file_type = "video"
    elif ext in ("mp3", "wav", "ogg", "aac", "flac", "m4a"):
        file_type = "audio"
    else:
        file_type = "file"

    # 保存
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}" if ext else f"{uuid.uuid4().hex[:12]}"
    save_path = _AGENT_UPLOAD_DIR / unique_name
    save_path.write_bytes(content)

    file_path = f"/uploads/agent_uploads/{unique_name}"
    file_url = f"http://127.0.0.1:8000{file_path}"

    return {
        "ok": True,
        "file_path": str(save_path),   # 绝对路径，供 tool 调用
        "file_type": file_type,
        "file_url": file_url,           # HTTP URL，供前端预览/下载
        "filename": file.filename,
        "size": len(content),
    }


@router.post("/chat")
def agent_chat(req: ChatRequest):
    """一次对话轮次 — 自动 function calling 编排后端工具。

    返回: {reply, tool_calls_made, session_id, usage}
    """
    from orchestrator import get_orchestrator
    orch = get_orchestrator()
    msg = _build_user_message(req.message, req.files)
    try:
        return orch.chat(message=msg, session_id=req.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 处理失败: {e}")


@router.get("/sessions")
def list_sessions():
    """列出活跃会话（内存中，最多 20 条）"""
    from orchestrator import get_orchestrator
    return {"sessions": get_orchestrator().get_sessions()}


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """获取指定会话的消息历史（不含 system prompt）"""
    from orchestrator import get_orchestrator
    msgs = get_orchestrator().get_session(session_id)
    if msgs is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session_id": session_id, "messages": msgs}


@router.get("/tools")
def list_tools():
    """列出 Agent 可调用的全部工具（用于前端展示能力清单）"""
    from orchestrator import ORCHESTRATOR_TOOLS
    return {
        "count": len(ORCHESTRATOR_TOOLS),
        "tools": [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
            }
            for t in ORCHESTRATOR_TOOLS
        ],
    }


@router.post("/chat/stream")
def agent_chat_stream(req: ChatRequest):
    """流式对话 — SSE 实时输出。事件类型: text / tool_call / tool_result / done"""
    from orchestrator import get_orchestrator

    msg = _build_user_message(req.message, req.files)

    def generate():
        orch = get_orchestrator()
        try:
            for event in orch.chat_stream(message=msg, session_id=req.session_id):
                yield event
        except Exception as e:
            import json
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
