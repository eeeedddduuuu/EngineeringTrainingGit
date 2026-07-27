"""统一 Agent 对话接口 — EXAgent 终极助手

把 EXAgent 目录下的 orchestrator（DeepSeek function calling 编排器）接入后端。
用户用自然语言对话，Agent 自动判断调用哪些后端工具（创作/生图/生视频/配音/搜索/合规等）。
"""
import sys
from pathlib import Path

# 确保能 import EXAgent 目录下的 orchestrator
# 本文件: EXAgent/backend/app/routers/agent.py → parent x4 = EXAgent/
_EXDIR = Path(__file__).resolve().parent.parent.parent.parent
if str(_EXDIR) not in sys.path:
    sys.path.insert(0, str(_EXDIR))

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/agent", tags=["AI助手"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="用户自然语言输入")
    session_id: str | None = Field(None, description="会话ID，为空则新建会话")


@router.post("/chat")
def agent_chat(req: ChatRequest):
    """一次对话轮次 — 自动 function calling 编排后端工具。

    返回: {reply, tool_calls_made, session_id, usage}
    """
    from orchestrator import get_orchestrator
    orch = get_orchestrator()
    try:
        return orch.chat(message=req.message, session_id=req.session_id)
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

    def generate():
        orch = get_orchestrator()
        try:
            for event in orch.chat_stream(message=req.message, session_id=req.session_id):
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
