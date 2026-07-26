"""
创作模块 — 异步任务 + Agent 流水线集成
- 默认使用 P4 的 create_content()（Mock 模式，离线可跑，2秒出结果）
- 联调时切换 provider="deepseek" 调用真实 LLM
- 超时/失败时自动回退到内置 Mock 方案
"""
import uuid
import sys
import threading
import concurrent.futures
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

# P4 Agent 调用超时（秒）
P4_TIMEOUT = 30


def _try_p4_create_content(
    topic: str, target_audience: str, platform: str,
    duration: str, style: str, provider: str = "mock",
) -> Optional[dict]:
    """
    尝试调用 P4 的 create_content()。

    默认使用 Mock 模式（高速、离线可用）；传 provider="deepseek" 切真实 LLM。
    成功返回结果 dict，失败返回 None（触发内置回退）。
    """
    try:
        # 确保 p4_agent 模块可导入
        p4_path = Path(__file__).parent.parent.parent / "p4_agent"
        if str(p4_path) not in sys.path:
            sys.path.insert(0, str(p4_path))
        if str(p4_path.parent) not in sys.path:
            sys.path.insert(0, str(p4_path.parent))

        from p4_agent.pipeline_adapter import create_content

        result = create_content(
            topic=topic,
            target_audience=target_audience,
            platform=platform,
            duration=duration,
            style=style,
            provider=provider,
        )
        if result.get("ok"):
            return result
    except ImportError as e:
        print(f"[P3] P4 Agent 模块未安装或依赖缺失: {e}")
    except Exception as e:
        print(f"[P3] P4 create_content() 异常: {e}")
    return None


def _build_mock_schemes(topic: str, platform: str, style: str) -> list[dict]:
    """根据用户输入动态生成 Mock 方案（不再硬编码护肤场景）"""
    platform_names = {
        "douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站",
    }
    pname = platform_names.get(platform, platform)

    return [
        {
            "version": "A",
            "title": f"【{style}】{topic}｜{pname}爆款脚本",
            "hook": f"关于{topic}，你可能一直都理解错了！",
            "scenes": [
                {"seq": 1, "type": "钩子开场", "duration": "0-3s",
                 "description": f"冲击力画面+大字标题「{topic}」", "voiceover": f"关于{topic}，你可能一直都理解错了！"},
                {"seq": 2, "type": "痛点引入", "duration": "3-15s",
                 "description": "展示常见误区或问题", "voiceover": f"很多人在{topic}上踩过的坑，今天一次说清楚"},
                {"seq": 3, "type": "干货输出", "duration": "15-45s",
                 "description": "3个核心要点逐一讲解", "voiceover": f"第一点...第二点...第三点...记住这些就够了"},
                {"seq": 4, "type": "总结引导", "duration": "45-55s",
                 "description": "金句总结+引导互动", "voiceover": "觉得有用的话，点赞收藏，下期见！"},
            ],
            "hashtags": [f"#{topic[:4]}", f"#{pname}", "#干货分享"],
            "cover_text": f"🔥 {topic}｜新手必看",
            "score": 8.5,
            "rank": 2,
            "recommendation_reason": f"干货结构完整，适合{pname}平台{style}风格",
        },
        {
            "version": "B",
            "title": f"颠覆认知！{topic}的全新打开方式",
            "hook": f"你还在用传统方式做{topic}吗？",
            "scenes": [
                {"seq": 1, "type": "悬念开场", "duration": "0-5s",
                 "description": "对比画面+疑问文字", "voiceover": f"你还在用传统方式做{topic}吗？"},
                {"seq": 2, "type": "故事展开", "duration": "5-25s",
                 "description": "新旧方法对比展示", "voiceover": f"我以前也这样做{topic}，直到我发现了这个方法..."},
                {"seq": 3, "type": "核心揭秘", "duration": "25-50s",
                 "description": "新方法的详细讲解", "voiceover": f"核心秘密就在于..."},
                {"seq": 4, "type": "金句收尾", "duration": "50-55s",
                 "description": "表情特写+金句字幕", "voiceover": f"做{topic}，方法比努力更重要"},
            ],
            "hashtags": [f"#{topic[:4]}", "#颠覆认知", "#效率翻倍"],
            "cover_text": f"💡 {topic}新思路｜效率翻倍",
            "score": 9.2,
            "rank": 1,
            "recommendation_reason": f"悬念式开头吸引力强，颠覆性角度适合{pname}算法推荐",
        },
        {
            "version": "C",
            "title": f"沉浸式体验｜{topic}全过程记录",
            "hook": f"第一次做{topic}是什么样的体验？",
            "scenes": [
                {"seq": 1, "type": "沉浸开场", "duration": "0-5s",
                 "description": "第一视角+环境音", "voiceover": f"第一次做{topic}是什么样的体验？"},
                {"seq": 2, "type": "过程记录", "duration": "5-30s",
                 "description": "关键步骤展示", "voiceover": "准备好材料，我们开始吧..."},
                {"seq": 3, "type": "结果揭晓", "duration": "30-45s",
                 "description": "成果展示+对比", "voiceover": "来看看最终效果！"},
                {"seq": 4, "type": "互动引导", "duration": "45-55s",
                 "description": "评论区引导", "voiceover": "你也试试{topic}？评论区交作业！"},
            ],
            "hashtags": [f"#{topic[:4]}", "#沉浸式体验", "#记录生活"],
            "cover_text": f"🎬 {topic}全过程｜沉浸式",
            "score": 7.8,
            "rank": 3,
            "recommendation_reason": "沉浸式体验感强但开头冲击力稍弱",
        },
    ]


def _run_fallback_mock(task_id: str, session_id: int, topic: str, platform: str, style: str):
    """内置回退 — 根据用户输入动态生成 Mock 方案"""
    _task_store[task_id]["progress"] = "Mock 方案生成中..."

    mock_schemes = _build_mock_schemes(topic, platform, style)

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
    _task_store[task_id]["progress"] = "全部完成（Mock 模式）"
    _task_store[task_id]["result"] = {
        "session_id": session_id,
        "schemes": [
            {"id": sid, "version": m["version"], "title": m["title"], "hook": m["hook"],
             "scenes": m["scenes"], "hashtags": m["hashtags"], "cover_text": m["cover_text"],
             "score": m["score"], "rank": m["rank"],
             "recommendation_reason": m.get("recommendation_reason", "")}
            for sid, m in zip(scheme_ids, mock_schemes)
        ],
        "recommendation": {
            "best_version": "B",
            "reason": "B方案悬念式开头吸引力最强，预估前3秒留存率最高",
        },
    }


def _run_agent_workflow(task_id: str, session_id: int, req: CreationRequest):
    """
    后台线程执行 Agent 流水线：
    - Mock 模式：直接用内置动态 Mock（秒出结果，内容匹配用户主题）
    - DeepSeek 模式：调用 P4 Agent → 超时/失败回退动态 Mock
    """
    PROVIDER = "mock"  # 改为 "deepseek" 以使用真实 LLM

    _task_store[task_id]["status"] = "processing"

    # Mock 模式：跳过 P4，直接用动态 Mock（更快、内容更匹配）
    if PROVIDER == "mock":
        _task_store[task_id]["progress"] = "🎨 动态方案生成中..."
        _run_fallback_mock(task_id, session_id, req.topic, req.platform, req.style)
        return

    # DeepSeek 模式：调用 P4 Agent 流水线
    _task_store[task_id]["progress"] = "🚀 Agent 流水线启动..."

    try:
        _task_store[task_id]["progress"] = "📊 热点分析 + 脚本创作中..."

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _try_p4_create_content,
                topic=req.topic,
                target_audience=req.target_audience,
                platform=req.platform,
                duration=req.duration,
                style=req.style,
                provider=PROVIDER,
            )
            try:
                p4_result = future.result(timeout=P4_TIMEOUT)
            except concurrent.futures.TimeoutError:
                print(f"[P3] P4 Agent 超时（>{P4_TIMEOUT}s），回退到内置 Mock")
                p4_result = None

        if p4_result:
            _task_store[task_id]["progress"] = "💾 写入数据库 + 评分排名..."
            raw_md = p4_result.get("raw_markdown", "")
            schemes_data = p4_result.get("schemes") or []

            # === 解析失败时的回退：从 raw_markdown 提取方案 ===
            if not schemes_data and raw_md:
                import re
                parts = re.split(r'\n(?=##\s*版本\s*)', raw_md)
                for idx, part in enumerate(parts):
                    if not part.strip():
                        continue
                    title_match = re.search(r'\*\*标题\*\*:\s*(.+)', part)
                    hook_match = re.search(r'\*\*开头钩子[^)]*\)?\*\*:\s*(.+)', part)
                    hashtag_match = re.findall(r'#(\S+)', part)
                    cover_match = re.search(r'\*\*封面文案\*\*:\s*(.+)', part)
                    schemes_data.append({
                        "version": chr(65 + idx),
                        "title": title_match.group(1).strip() if title_match else f"AI创作方案{chr(65+idx)}",
                        "hook": hook_match.group(1).strip()[:200] if hook_match else "",
                        "scenes": [],
                        "hashtags": [f"#{t}" for t in hashtag_match[:5]] if hashtag_match else [],
                        "cover_text": cover_match.group(1).strip()[:200] if cover_match else "",
                        "total_score": 7.0,
                        "rank": idx + 1,
                        "recommendation_reason": "AI 生成（Markdown解析）",
                    })

            if not schemes_data:
                _run_fallback_mock(task_id, session_id, req.topic, req.platform, req.style)
                return

            # === P4 Agent 成功 → 写入数据库 ===
            db = SessionLocal()

            # 写入 agent_logs
            for log_data in p4_result.get("agent_logs", []):
                db.add(AgentLog(session_id=session_id, **log_data))
            db.commit()

            # 写入 schemes
            scheme_ids = []
            for scheme_data in schemes_data:
                storyboard = scheme_data.get("storyboard_json") or {}
                if raw_md and not storyboard.get("raw_markdown"):
                    storyboard["raw_markdown"] = raw_md

                scheme = Scheme(
                    session_id=session_id,
                    version=scheme_data.get("version") or "?",
                    title=scheme_data.get("title") or "",
                    hook=scheme_data.get("hook") or "",
                    scenes=scheme_data.get("scenes") or [],
                    storyboard_json=storyboard or {},
                    hashtags=scheme_data.get("hashtags") or [],
                    cover_text=scheme_data.get("cover_text") or "",
                    score=scheme_data.get("total_score") or scheme_data.get("score") or 0,
                    rank=scheme_data.get("rank") or 0,
                    recommendation_reason=scheme_data.get("recommendation_reason") or "",
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
            _task_store[task_id]["progress"] = "✅ 全部完成（P4 Agent 流水线）"
            _task_store[task_id]["result"] = {
                "session_id": session_id,
                "provider": p4_result.get("provider", "mock"),
                "schemes": [
                    {"id": sid, "version": s.get("version"), "title": s.get("title"),
                     "hook": s.get("hook"), "scenes": s.get("scenes"),
                     "hashtags": s.get("hashtags"), "cover_text": s.get("cover_text"),
                     "score": s.get("total_score") or s.get("score") or 7.0,
                     "rank": s.get("rank", 0),
                     "recommendation_reason": s.get("recommendation_reason", ""),
                     "raw_markdown": raw_md}
                    for sid, s in zip(scheme_ids, schemes_data)
                ],
                "recommendation": recommendation,
                "raw_markdown": raw_md,
            }
        else:
            # P4 调用失败/超时 → 回退内置 Mock
            _run_fallback_mock(task_id, session_id, req.topic, req.platform, req.style)

    except Exception as e:
        import traceback as _tb
        from datetime import datetime as _dt
        with open("creation_errors.log", "a", encoding="utf-8") as _f:
            _f.write(f"\n[{_dt.now()}] task={task_id} session={session_id}\n")
            _f.write(f"Error: {e}\n")
            _tb.print_exc(file=_f)
        # 即使异常也尝试回退 Mock
        try:
            _run_fallback_mock(task_id, session_id, req.topic, req.platform, req.style)
        except Exception:
            _task_store[task_id]["status"] = "failed"
            _task_store[task_id]["progress"] = "❌ 创作失败"
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
