"""
创作模块 — 异步任务 + Agent 流水线集成
- 默认使用 P4 的 create_content()（Mock 模式，离线可跑）
- 联调时切换 provider="deepseek" 调用真实 LLM
- 失败时自动回退到内置 Mock 方案
"""
import uuid
import sys
import threading
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models.user import User
from app.models.business import CreationSession, Scheme, AgentLog
from app.schemas.creation import CreationRequest, TaskStatusResponse
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["创作"])

# 简易内存任务存储
_task_store: dict[str, dict] = {}


def _try_p4_create_content(topic: str, target_audience: str, platform: str, duration: str, style: str) -> Optional[dict]:
    """
    尝试调用 P4 的 create_content()（Mock 模式）。
    成功返回结果 dict，失败返回 None（触发内置回退）。
    """
    try:
        # 确保 p4_agent 模块可导入
        p4_path = Path(__file__).parent.parent.parent / "p4_agent"
        if str(p4_path) not in sys.path:
            sys.path.insert(0, str(p4_path.parent))  # backend/

        from p4_agent.pipeline_adapter import create_content

        result = create_content(
            topic=topic,
            target_audience=target_audience,
            platform=platform,
            duration=duration,
            style=style,
            provider="mock",  # Day 1-2 用 Mock，联调时切 "deepseek"
        )
        if result.get("ok"):
            return result
    except ImportError as e:
        print(f"[P3] P4 Agent 模块未安装或依赖缺失: {e}")
    except Exception as e:
        print(f"[P3] P4 create_content() 异常: {e}")
    return None


def _run_fallback_mock(task_id: str, session_id: int):
    """内置回退 — 纯 Mock 方案（不依赖 P4 模块）"""
    mock_schemes = [
        {"version": "A", "title": "秋季护肤3步走，皮肤科医生都在用",
         "hook": "你还在用夏天的护肤品吗？99%的人秋天都踩坑了！",
         "scenes": [{"seq": 1, "type": "口播", "duration": "5s", "description": "博主正面镜头", "voiceover": "你还在用夏天的护肤品吗？..."}],
         "hashtags": ["#秋季护肤", "#护肤干货", "#好物推荐"], "cover_text": "秋季护肤3步走", "score": 8.5, "rank": 2,
         "recommendation_reason": "结构完整，干货风格匹配"},
        {"version": "B", "title": "秋天不护肤=慢性毁容？三步拯救干燥肌",
         "hook": "秋天到了，你的皮肤却亮了红灯？",
         "scenes": [{"seq": 1, "type": "口播", "duration": "3s", "description": "悬念开场", "voiceover": "秋天到了，你的皮肤却亮了红灯？"}],
         "hashtags": ["#秋季护肤", "#皮肤管理", "#护肤科普"], "cover_text": "秋季护肤急救指南", "score": 9.2, "rank": 1,
         "recommendation_reason": "悬念式开头吸引力强，适合抖音算法"},
        {"version": "C", "title": "护肤博主教你：60秒搞定秋季护肤全流程",
         "hook": "早上起不来？60秒护肤全流程来了！",
         "scenes": [{"seq": 1, "type": "口播+文字", "duration": "5s", "description": "快节奏开场", "voiceover": "早上起不来？60秒护肤全流程来了！"}],
         "hashtags": ["#护肤流程", "#懒人护肤", "#秋季好物"], "cover_text": "60秒极速护肤", "score": 7.8, "rank": 3,
         "recommendation_reason": "实用性强但开头冲击力稍弱"},
    ]
    db = SessionLocal()
    scheme_ids = []
    for s in mock_schemes:
        scheme = Scheme(session_id=session_id, **s)
        db.add(scheme)
        db.commit()
        db.refresh(scheme)
        scheme_ids.append(scheme.id)

    session = db.query(CreationSession).filter(CreationSession.id == session_id).first()
    if session:
        session.status = "completed"
        db.commit()
    db.close()

    _task_store[task_id]["status"] = "completed"
    _task_store[task_id]["progress"] = "全部完成（内置Mock）"
    _task_store[task_id]["result"] = {
        "session_id": session_id,
        "schemes": [
            {"id": sid, "version": m["version"], "title": m["title"], "hook": m["hook"],
             "scenes": m["scenes"], "hashtags": m["hashtags"], "cover_text": m["cover_text"],
             "score": m["score"], "rank": m["rank"]}
            for sid, m in zip(scheme_ids, mock_schemes)
        ],
        "recommendation": {"best_version": "B", "reason": "B方案开局悬念最强，预估前3秒留存率最高"}
    }


def _run_agent_workflow(task_id: str, session_id: int, req: CreationRequest):
    """
    后台线程执行 Agent 流水线：
    1. 优先调用 P4 的 create_content()（当前 Mock 模式）
    2. 失败时回退到内置 Mock 方案
    """
    _task_store[task_id]["status"] = "processing"
    _task_store[task_id]["progress"] = "Agent 流水线启动中..."

    try:
        p4_result = _try_p4_create_content(
            topic=req.topic,
            target_audience=req.target_audience,
            platform=req.platform,
            duration=req.duration,
            style=req.style,
        )

        if p4_result:
            # === P4 Agent 成功 → 写入数据库 ===
            db = SessionLocal()

            # 写入 agent_logs
            for log_data in p4_result.get("agent_logs", []):
                db.add(AgentLog(session_id=session_id, **log_data))
            db.commit()

            # 写入 schemes（P4 已经评分+排名）
            scheme_ids = []
            for scheme_data in p4_result.get("schemes", []):
                # P4 的 scheme_data 可能含 scoring 字段，映射到 Scheme 模型
                scheme = Scheme(
                    session_id=session_id,
                    version=scheme_data.get("version", "?"),
                    title=scheme_data.get("title", ""),
                    hook=scheme_data.get("hook", ""),
                    scenes=scheme_data.get("scenes", []),
                    storyboard_json=scheme_data.get("storyboard_json"),
                    hashtags=scheme_data.get("hashtags", []),
                    cover_text=scheme_data.get("cover_text", ""),
                    score=scheme_data.get("total_score", scheme_data.get("score", 0)),
                    rank=scheme_data.get("rank", 0),
                    recommendation_reason=scheme_data.get("recommendation_reason", ""),
                )
                db.add(scheme)
                db.commit()
                db.refresh(scheme)
                scheme_ids.append(scheme.id)

            # 更新 session 状态
            session = db.query(CreationSession).filter(CreationSession.id == session_id).first()
            if session:
                session.status = "completed"
                db.commit()
            db.close()

            recommendation = p4_result.get("recommendation", {})
            _task_store[task_id]["status"] = "completed"
            _task_store[task_id]["progress"] = "全部完成（P4 Agent 流水线）"
            _task_store[task_id]["result"] = {
                "session_id": session_id,
                "provider": p4_result.get("provider", "mock"),
                "schemes": [
                    {"id": sid, "version": s.get("version"), "title": s.get("title"),
                     "hook": s.get("hook"), "scenes": s.get("scenes"),
                     "hashtags": s.get("hashtags"), "cover_text": s.get("cover_text"),
                     "score": s.get("total_score", s.get("score", 0)), "rank": s.get("rank", 0)}
                    for sid, s in zip(scheme_ids, p4_result.get("schemes", []))
                ],
                "recommendation": recommendation,
                "raw_markdown": p4_result.get("raw_markdown", ""),
            }
        else:
            # P4 调用失败 → 回退内置 Mock
            _run_fallback_mock(task_id, session_id)

    except Exception as e:
        _task_store[task_id]["status"] = "failed"
        _task_store[task_id]["result"] = {"error": "agent_error", "detail": str(e)}


@router.post("/creation/start")
def start_creation(
    req: CreationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交创作任务 → 返回 task_id，后台异步执行 Agent 流水线"""
    session = CreationSession(
        user_id=current_user.id,
        topic=req.topic,
        target_audience=req.target_audience,
        platform=req.platform,
        duration=req.duration,
        style=req.style,
        status="pending",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    task_id = str(uuid.uuid4())
    _task_store[task_id] = {"status": "pending", "progress": "任务已排队，等待处理...", "result": None}

    # 后台线程执行 Agent 流水线
    t = threading.Thread(target=_run_agent_workflow, args=(task_id, session.id, req), daemon=True)
    t.start()

    return {"task_id": task_id, "status": "pending", "message": "创作任务已提交，请轮询状态接口获取结果"}


@router.get("/task/{task_id}/status", response_model=TaskStatusResponse)
def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    """轮询任务进度/结果"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"error": "task_not_found", "detail": "任务不存在"})
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task.get("progress"),
        result=task.get("result"),
    )
