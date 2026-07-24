import uuid
import threading
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.business import CreationSession, AgentLog
from app.schemas.creation import CreationRequest, TaskStatusResponse
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["创作"])

# 简易内存任务存储（生产环境应使用 Redis）
_task_store: dict[str, dict] = {}


def _run_mock_workflow(task_id: str, session_id: int, db_url: str):
    """Mock Agent 工作流 —— 在后台线程中模拟 4 个 Agent 依次执行"""
    agents = [
        ("trend", "热点分析"),
        ("script", "脚本创作"),
        ("review", "合规审查"),
        ("strategy", "发布策略"),
    ]
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        for i, (agent_name, agent_label) in enumerate(agents):
            _task_store[task_id]["progress"] = f"{agent_label}Agent 正在执行..."
            _task_store[task_id]["status"] = "processing"
            time.sleep(0.5)  # 模拟 Agent 耗时

            # 记录 Agent 日志
            log = AgentLog(
                session_id=session_id,
                agent_name=agent_name,
                input_json={"session_id": session_id},
                output_json={"status": "ok", "mock": True},
                tools_called=["搜索API" if agent_name == "trend" else "知识库RAG" if agent_name == "script" else "敏感词过滤" if agent_name == "review" else "平台模板,A/B生成"],
                latency_ms=int(500 + i * 200),
                tokens_used=1200 + i * 300,
                status="success",
            )
            db.add(log)
            db.commit()

        # 生成 3 个 Mock 方案
        from app.models.business import Scheme
        mock_schemes = [
            {"version": "A", "title": "秋季护肤3步走，皮肤科医生都在用", "hook": "你还在用夏天的护肤品吗？99%的人秋天都踩坑了！",
             "scenes": [{"seq":1,"type":"口播","duration":"5s","description":"博主正面镜头","voiceover":"你还在用夏天的护肤品吗？..."}],
             "hashtags": ["#秋季护肤","#护肤干货","#好物推荐"], "cover_text": "秋季护肤3步走", "score": 8.5, "rank": 2,
             "recommendation_reason": "结构完整，干货风格匹配"},
            {"version": "B", "title": "秋天不护肤=慢性毁容？三步拯救干燥肌", "hook": "秋天到了，你的皮肤却亮了红灯？",
             "scenes": [{"seq":1,"type":"口播","duration":"3s","description":"悬念开场","voiceover":"秋天到了，你的皮肤却亮了红灯？"}],
             "hashtags": ["#秋季护肤","#皮肤管理","#护肤科普"], "cover_text": "秋季护肤急救指南", "score": 9.2, "rank": 1,
             "recommendation_reason": "悬念式开头吸引力强，适合抖音算法"},
            {"version": "C", "title": "护肤博主教你：60秒搞定秋季护肤全流程", "hook": "早上起不来？60秒护肤全流程来了！",
             "scenes": [{"seq":1,"type":"口播+文字","duration":"5s","description":"快节奏开场","voiceover":"早上起不来？60秒护肤全流程来了！"}],
             "hashtags": ["#护肤流程","#懒人护肤","#秋季好物"], "cover_text": "60秒极速护肤", "score": 7.8, "rank": 3,
             "recommendation_reason": "实用性强但开头冲击力稍弱"},
        ]
        for s in mock_schemes:
            scheme = Scheme(session_id=session_id, **s)
            db.add(scheme)
        db.commit()

        # 更新 session 状态
        session = db.query(CreationSession).filter(CreationSession.id == session_id).first()
        if session:
            session.status = "completed"
            db.commit()

        _task_store[task_id]["status"] = "completed"
        _task_store[task_id]["progress"] = "全部完成"
        _task_store[task_id]["result"] = {
            "session_id": session_id,
            "schemes": [
                {"id": sid, "version": s["version"], "title": s["title"], "hook": s["hook"],
                 "scenes": s["scenes"], "hashtags": s["hashtags"], "cover_text": s["cover_text"],
                 "score": s["score"], "rank": s["rank"]}
                for sid, s in zip(range(session_id * 100 + 1, session_id * 100 + 4), mock_schemes)
            ],
            "recommendation": {"best_version": "B", "reason": "B方案开局悬念最强，预估前3秒留存率最高"}
        }
    except Exception as e:
        _task_store[task_id]["status"] = "failed"
        _task_store[task_id]["result"] = {"error": "agent_error", "detail": str(e)}


@router.post("/creation/start")
def start_creation(req: CreationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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

    # 启动后台线程模拟 Agent 工作流
    t = threading.Thread(target=_run_mock_workflow, args=(task_id, session.id, ""), daemon=True)
    t.start()

    return {"task_id": task_id, "status": "pending", "message": "创作任务已提交，请轮询状态接口获取结果"}


@router.get("/task/{task_id}/status", response_model=TaskStatusResponse)
def get_task_status(task_id: str, current_user: User = Depends(get_current_user)):
    """轮询任务进度"""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"error": "task_not_found", "detail": "任务不存在"})
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task.get("progress"),
        result=task.get("result"),
    )
