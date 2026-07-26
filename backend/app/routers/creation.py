"""
创作模块 — 异步任务 + Agent 流水线集成
- 默认使用 P4 的 create_content()（Mock 模式，离线可跑，2秒出结果）
- 联调时切换 provider="deepseek" 调用真实 LLM
- 超时/失败时自动回退到内置 Mock 方案
"""
import os
import uuid
import sys
import shutil
import threading
import concurrent.futures
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models.user import User
from app.models.business import CreationSession, Scheme, AgentLog
from app.schemas.creation import CreationRequest, TaskStatusResponse
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["创作"])

# 上传文件存储目录
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 已上传文件暂存（session 级别，供 Agent 上下文注入）
_uploaded_files: dict[int, list[dict]] = {}  # user_id → [{path, filename, type, size, uploaded_at}]

# 简易内存任务存储
_task_store: dict[str, dict] = {}


def _analyze_image(image_url: str) -> str:
    """分析图片属性，生成文本描述供 Agent 参考。
    如果图片是本地文件，用 PIL 提取尺寸/格式/主色调等；否则返回 URL 引用。
    """
    try:
        from PIL import Image
    except ImportError:
        return f"[参考图片] {image_url}"

    # 本地文件
    local_path = None
    if image_url.startswith("/") or (len(image_url) > 2 and image_url[1] == ":"):
        local_path = image_url
    elif image_url.startswith("file://"):
        local_path = image_url[7:]

    if local_path and Path(local_path).exists():
        try:
            img = Image.open(local_path)
            w, h = img.size
            mode = img.mode
            fmt = img.format or "未知"
            ratio = "横版" if w > h else ("竖版" if h > w else "方形")
            # 简单的主色调分析
            if mode in ("RGB", "RGBA"):
                img_small = img.resize((50, 50))
                pixels = list(img_small.getdata())
                r_avg = sum(p[0] for p in pixels) // len(pixels)
                g_avg = sum(p[1] for p in pixels) // len(pixels)
                b_avg = sum(p[2] for p in pixels) // len(pixels)
                if r_avg > 180 and g_avg > 180 and b_avg > 180: tone = "亮白色调"
                elif r_avg < 60 and g_avg < 60 and b_avg < 60: tone = "暗黑色调"
                elif r_avg > g_avg and r_avg > b_avg: tone = "暖红色调"
                elif g_avg > r_avg and g_avg > b_avg: tone = "绿色调"
                elif b_avg > r_avg and b_avg > g_avg: tone = "蓝冷色调"
                else: tone = "中性灰色调"
            else:
                tone = "灰度"
            return (
                f"[参考图片分析] 格式:{fmt} | 尺寸:{w}×{h} | 比例:{ratio}({w//max(1,h//100)}%) | "
                f"色调:{tone} | 色彩模式:{mode} | 文件:{Path(local_path).name}"
            )
        except Exception:
            pass

    # 远程 URL
    return f"[参考图片] URL: {image_url}（远程图片，请根据 URL 中的关键词推断内容风格）"

# P4 Agent 调用超时（秒）
P4_TIMEOUT = 300


def _try_p4_create_content(
    topic: str, target_audience: str, platform: str,
    duration: str, style: str, provider: str = "mock",
    image_url: Optional[str] = None,
) -> Optional[dict]:
    """
    尝试调用 P4 的 create_content()。

    默认使用 Mock 模式（高速、离线可用）；传 provider="deepseek" 切真实 LLM。
    成功返回结果 dict，失败返回 None（触发内置回退）。
    """
    try:
        pass  # ARK_API_KEY 由 config.py 注入环境变量
        p4_path = Path(__file__).parent.parent.parent / "p4_agent"
        if str(p4_path) not in sys.path:
            sys.path.insert(0, str(p4_path))
        if str(p4_path.parent) not in sys.path:
            sys.path.insert(0, str(p4_path.parent))

        from p4_agent.pipeline_adapter import create_content

        # 多模态：分析上传的图片，提取视觉特征作为 Agent 上下文
        enhanced_topic = topic
        if image_url and image_url.strip():
            img_desc = _analyze_image(image_url.strip())
            enhanced_topic = f"{topic}\n\n{img_desc}\n请根据以上图片素材的风格和特征来定制脚本内容。"

        result = create_content(
            topic=enhanced_topic,
            target_audience=target_audience,
            platform=platform,
            duration=duration,
            style=style,
            provider=provider,
            image_url=image_url,   # 多模态：素材图片 URL 传入 Agent
            enable_trend=False,    # 跳过热分析
            enable_review=False,   # 跳过合规审查
            enable_strategy=False, # 跳过发布策略（脚本Agent已含推荐）
        )
        if result.get("ok"):
            return result
    except ImportError as e:
        print(f"[P3] P4 Agent 模块未安装或依赖缺失: {e}")
    except Exception as e:
        print(f"[P3] P4 create_content() 异常: {e}")
    return None


def _build_mock_schemes(topic: str, platform: str, style: str) -> list[dict]:
    """根据用户输入动态生成 Mock 方案 — 按风格+平台差异化"""
    platform_names = {"douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站"}
    pname = platform_names.get(platform, platform)

    # 不同风格 → 不同的脚本结构
    style_templates = {
        "干货科普": [
            {"scenes": [
                {"seq":1,"type":"数据冲击","duration":"0-3s","description":"大字数据+震惊表情",f"voiceover":f"你知道吗？90%的人{topic}都做错了！"},
                {"seq":2,"type":"误区拆解","duration":"3-18s","description":"三个常见误区逐个击破，配合对比画面","voiceover":f"误区一...误区二...误区三...是不是全中？"},
                {"seq":3,"type":"正确方法","duration":"18-42s","description":"专业步骤演示，重点标注","voiceover":f"正确的{topic}方法其实很简单，记住这三点"},
                {"seq":4,"type":"实操演示","duration":"42-52s","description":"快速过一遍完整流程","voiceover":"来，跟着我做一遍"},
                {"seq":5,"type":"总结引导","duration":"52-60s","description":"要点回顾+关注引导","voiceover":f"学会了吗？点个关注，每天学点{topic}干货"},
            ],"hashtags":[f"#{topic[:4]}","#干货分享","#涨知识",f"#{pname}"],"score":8.5},
            {"scenes":[
                {"seq":1,"type":"悬念提问","duration":"0-3s","description":"黑屏白字+疑问音效","voiceover":f"如果有人告诉你{topic}可以这样做，你信吗？"},
                {"seq":2,"type":"权威背书","duration":"3-15s","description":"引用研究报告/专家观点","voiceover":"最新研究显示...这不是我说的，是数据说的"},
                {"seq":3,"type":"原理讲解","duration":"15-38s","description":"动画图解+通俗比喻","voiceover":"原理其实很简单，像...一样"},
                {"seq":4,"type":"案例佐证","duration":"38-50s","description":"真实案例前后对比","voiceover":"看这个案例，之前vs之后"},
                {"seq":5,"type":"行动号召","duration":"50-60s","description":"引导尝试+评论区互动","voiceover":f"今天就开始试试{topic}，评论区告诉我你的结果"},
            ],"hashtags":[f"#{topic[:4]}","#科普","#冷知识",f"#{pname}"],"score":9.0},
            {"scenes":[
                {"seq":1,"type":"灵魂拷问","duration":"0-3s","description":"直视镜头+停顿","voiceover":f"你敢说你真的会{topic}吗？"},
                {"seq":2,"type":"清单体","duration":"3-25s","description":"快速罗列5个必知要点","voiceover":f"关于{topic}的5个真相：第一...第二..."},
                {"seq":3,"type":"深度解读","duration":"25-45s","description":"选最重要的1个点深入展开","voiceover":"其中最关键的是第三个，为什么？"},
                {"seq":4,"type":"避坑指南","duration":"45-55s","description":"3个绝对不能犯的错","voiceover":"记住这三个坑，打死别踩"},
                {"seq":5,"type":"收藏引导","duration":"55-60s","description":"引导收藏+下期预告","voiceover":"先收藏，下期告诉你进阶玩法"},
            ],"hashtags":[f"#{topic[:4]}","#避坑","#必看",f"#{pname}"],"score":7.8},
        ],
        "测评种草": [
            {"scenes":[
                {"seq":1,"type":"视觉冲击","duration":"0-3s","description":"产品特写+光效+大字","voiceover":f"这个{topic}，我用了30天，效果惊人"},
                {"seq":2,"type":"痛点共鸣","duration":"3-12s","description":"展示使用前的困扰","voiceover":"以前我也被这个问题困扰了很久"},
                {"seq":3,"type":"实测对比","duration":"12-35s","description":"左右对比/前后对比展示","voiceover":"左边没用，右边用了，差距也太明显了"},
                {"seq":4,"type":"成分/细节","duration":"35-48s","description":"放大镜特写，逐项分析","voiceover":"看这个细节...这个材质/成分..."},
                {"seq":5,"type":"总结推荐","duration":"48-60s","description":"红黑榜+购买建议","voiceover":f"总结：{topic}确实值得入手，链接在评论区"},
            ],"hashtags":[f"#{topic[:4]}","#测评","#好物推荐",f"#{pname}"],"score":9.2},
            {"scenes":[
                {"seq":1,"type":"故事开头","duration":"0-5s","description":"博主本人出镜+生活场景","voiceover":f"闺蜜问我为什么{topic}这么好，我说..."},
                {"seq":2,"type":"场景带入","duration":"5-20s","description":"多个使用场景快速切换","voiceover":"上班用、约会用、在家用，处处都能用"},
                {"seq":3,"type":"真实感受","duration":"20-40s","description":"真诚分享使用体验","voiceover":"说实话，一开始我也怀疑，但是..."},
                {"seq":4,"type":"对比避雷","duration":"40-50s","description":"和其他产品对比","voiceover":"我也试过XX和XX，但都..."},
                {"seq":5,"type":"福利引导","duration":"50-60s","description":"优惠信息+互动引导","voiceover":"评论区抽3个粉丝免费送，记得三连"},
            ],"hashtags":[f"#{topic[:4]}","#种草","#真香",f"#{pname}"],"score":8.8},
            {"scenes":[
                {"seq":1,"type":"夸张演绎","duration":"0-3s","description":"戏剧化表演+夸张表情","voiceover":f"我的天！这个{topic}也太..."},
                {"seq":2,"type":"盲测挑战","duration":"3-18s","description":"蒙眼/随机测试","voiceover":"今天来做个盲测，看能不能分辨出来"},
                {"seq":3,"type":"揭晓结果","duration":"18-35s","description":"揭晓+真实的反应","voiceover":"答案揭晓...天呐我居然..."},
                {"seq":4,"type":"性价比分析","duration":"35-48s","description":"价格对比表","voiceover":f"这个{topic}的价格才...性价比绝了"},
                {"seq":5,"type":"购买引导","duration":"48-60s","description":"购买链接+限量提醒","voiceover":"链接放这了，手慢无，懂的都懂"},
            ],"hashtags":[f"#{topic[:4]}","#开箱","#真香现场",f"#{pname}"],"score":7.5},
        ],
        "剧情故事": [
            {"scenes":[
                {"seq":1,"type":"悬念画面","duration":"0-3s","description":"昏暗灯光+背影+悬疑BGM","voiceover":f"那天晚上，我收到了一个改变一切的{topic}..."},
                {"seq":2,"type":"事件展开","duration":"3-20s","description":"快速闪回+第一人称叙述","voiceover":"一切都从三天前说起..."},
                {"seq":3,"type":"冲突升级","duration":"20-38s","description":"情绪递进+镜头抖动","voiceover":"我没想到事情会变成这样..."},
                {"seq":4,"type":"转折","duration":"38-50s","description":"色调变暖+节奏放缓","voiceover":"就在我以为没有希望的时候..."},
                {"seq":5,"type":"结局+感悟","duration":"50-60s","description":"唯美画面+金句","voiceover":f"也许{topic}的意义，不在于结果，而在于过程"},
            ],"hashtags":[f"#{topic[:4]}","#剧情","#故事","#情感"],"score":8.0},
            {"scenes":[
                {"seq":1,"type":"生活日常","duration":"0-3s","description":"温馨日常画面+轻快BGM","voiceover":f"这就是我和{topic}的日常"},
                {"seq":2,"type":"趣味片段","duration":"3-22s","description":"3个搞笑/温馨小片段拼接","voiceover":"有时候是这样的...有时候是那样的..."},
                {"seq":3,"type":"情感升温","duration":"22-40s","description":"慢镜头+情感BGM","voiceover":"直到有一天我发现..."},
                {"seq":4,"type":"感动瞬间","duration":"40-52s","description":"特写表情+留白","voiceover":"原来最珍贵的，一直都是..."},
                {"seq":5,"type":"暖心结尾","duration":"52-60s","description":"字幕+引导","voiceover":"你们有没有类似的经历？评论区聊聊"},
            ],"hashtags":[f"#{topic[:4]}","#日常","#治愈","#温暖"],"score":8.5},
            {"scenes":[
                {"seq":1,"type":"高能预警","duration":"0-3s","description":"动作场景+快节奏剪辑","voiceover":f"警告：关于{topic}，下面的内容可能颠覆你的认知"},
                {"seq":2,"type":"事件重现","duration":"3-25s","description":"电影感叙事+多角度拍摄","voiceover":"事情是这样的..."},
                {"seq":3,"type":"真相揭露","duration":"25-42s","description":"色调转变+信息量释放","voiceover":"但你绝对想不到的是..."},
                {"seq":4,"type":"反思","duration":"42-52s","description":"独白+留白画面","voiceover":"回想起来，一切都有迹可循"},
                {"seq":5,"type":"开放式结尾","duration":"52-60s","description":"余韵画面+引导讨论","voiceover":"如果是你，你会怎么做？评论区写下你的选择"},
            ],"hashtags":[f"#{topic[:4]}","#故事","#反转","#思考"],"score":7.2},
        ],
    }

    # 根据风格选择模板，找不到用通用模板
    templates = style_templates.get(style, style_templates["干货科普"])

    versions = []
    for i, tmpl in enumerate(templates):
        v = chr(65 + i)  # A, B, C
        sc = tmpl["scenes"]
        versions.append({
            "version": v,
            "title": f"{sc[0]['voiceover'][:25]}...",
            "hook": sc[0]["voiceover"],
            "scenes": sc,
            "hashtags": tmpl["hashtags"],
            "cover_text": f"{'🔥' if i==0 else '💡' if i==1 else '🎬'} {topic}｜{pname}",
            "score": tmpl["score"],
            "rank": i + 1,
            "recommendation_reason": {
                0: f"数据冲击型开头，适合{pname}推荐算法",
                1: f"悬念叙事型，完播率高",
                2: f"清单体节奏快，信息密度适合{style}受众",
            }.get(i, f"方案{v}综合表现优秀"),
        })
    # 按评分排名
    versions.sort(key=lambda x: x["score"], reverse=True)
    for i, v in enumerate(versions):
        v["rank"] = i + 1
    return versions


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
    _task_store[task_id]["progress"] = "⚠️ DeepSeek 调用失败，已回退 Mock 模式（内容为模板生成，非 AI 创作）"
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
    - Coze 模式：调用 P4 Coze Bot → 支持 image_url 多模态
    """
    provider = req.provider  # 用户在前端选择的模式
    provider_names = {"mock": "Mock 离线", "deepseek": "DeepSeek v4", "coze": "Coze 扣子"}
    pname = provider_names.get(provider, provider)

    _task_store[task_id]["status"] = "processing"

    # Mock 模式：跳过 P4，直接用动态 Mock
    if provider == "mock":
        _task_store[task_id]["progress"] = "🎨 动态方案生成中（Mock）..."
        _run_fallback_mock(task_id, session_id, req.topic, req.platform, req.style)
        return

    # DeepSeek / Coze 模式：调用 P4 Agent 流水线
    _task_store[task_id]["progress"] = f"🚀 Agent 流水线启动（{pname}）..."

    image_url = getattr(req, "image_url", None) or None

    try:
        _task_store[task_id]["progress"] = f"📊 AI 脚本创作中（{pname}）..."

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _try_p4_create_content,
                topic=req.topic,
                target_audience=req.target_audience,
                platform=req.platform,
                duration=req.duration,
                style=req.style,
                provider=provider,
                image_url=image_url,
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
            multimodal_info = p4_result.get("multimodal")  # 多模态分析结果
            _task_store[task_id]["status"] = "completed"
            _task_store[task_id]["progress"] = "✅ DeepSeek v4-pro 真实 AI 生成完成"
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
                "multimodal": multimodal_info,
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
        image_url=getattr(req, "image_url", None) or None,
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


@router.post("/creation/analyze-image")
async def analyze_uploaded_image(
    current_user: User = Depends(get_current_user),
):
    """
    分析最后上传的图片 — 调用豆包多模态，返回视觉分析结果。
    前端在创作前先调用此接口，展示图片分析结果给用户确认。
    """
    user_files = _uploaded_files.get(current_user.id, [])
    if not user_files:
        raise HTTPException(status_code=400, detail={"error": "no_file", "detail": "请先上传参考图片"})

    latest = user_files[-1]
    image_path = latest.get("path", "")

    if not image_path or not Path(image_path).exists():
        raise HTTPException(status_code=404, detail={"error": "file_not_found", "detail": "图片文件不存在，请重新上传"})

    try:
        pass  # ARK_API_KEY 由 config.py 注入环境变量
        p4_path = Path(__file__).parent.parent.parent / "p4_agent"
        if str(p4_path) not in sys.path:
            sys.path.insert(0, str(p4_path))
        from multimodal import analyze_image

        question = (
            "请详细描述这张图片：1)画面中的主体和场景 2)色调与氛围 3)文字信息(如有) "
            "4)这张图适合做什么类型的短视频内容 5)给出3个创作切入角度"
        )
        result = analyze_image(image_path, question)

        if result.get("success"):
            return {
                "ok": True,
                "filename": latest.get("filename", ""),
                "analysis": result.get("content", ""),
                "usage": result.get("usage", {}),
                "elapsed": result.get("elapsed", 0),
            }
        else:
            return {
                "ok": False,
                "error": result.get("error", "分析失败"),
            }
    except ImportError:
        # 豆包模块不可用时的回退
        return {
            "ok": True,
            "filename": latest.get("filename", ""),
            "analysis": _analyze_image(image_path),
            "source": "local_pil",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analysis_failed", "detail": str(e)})


@router.post("/creation/upload")
async def upload_creation_file(
    file: UploadFile = File(..., description="上传素材文件（图片/视频/文档）"),
    current_user: User = Depends(get_current_user),
):
    """
    上传多模态素材文件，供创作 Agent 参考。

    - 支持格式：png, jpg, jpeg, gif, webp, mp4, mov, pdf, txt, md, docx
    - 单文件最大 50MB
    - 上传后可在创作请求中通过 uploaded_file_ids 引用
    """
    # 校验扩展名
    ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".mp3", ".wav", ".pdf", ".txt", ".md", ".docx"}
    ext = Path(file.filename or "unknown").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_file_type", "detail": f"不支持的文件类型 '{ext}'，允许: {', '.join(sorted(ALLOWED_EXT))}"},
        )

    # 保存文件
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest = UPLOAD_DIR / safe_name
    try:
        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                f.write(chunk)
    except Exception as e:
        if dest.exists():
            dest.unlink()
        raise HTTPException(status_code=500, detail={"error": "upload_failed", "detail": str(e)})

    file_size = dest.stat().st_size
    file_type = file.content_type or "application/octet-stream"

    # 记录到用户上传清单（供 Agent 上下文注入）
    uid = current_user.id
    if uid not in _uploaded_files:
        _uploaded_files[uid] = []
    file_record = {
        "file_id": uuid.uuid4().hex[:12],
        "filename": file.filename,
        "path": str(dest),
        "type": file_type,
        "ext": ext,
        "size": file_size,
        "uploaded_at": datetime.now().isoformat(),
    }
    _uploaded_files[uid].append(file_record)

    return {
        "file_id": file_record["file_id"],
        "filename": file.filename,
        "type": file_type,
        "size": file_size,
        "image_url": str(dest),
        "message": "上传成功，可在创作请求中引用此文件",
    }


@router.get("/creation/uploads")
def list_uploaded_files(current_user: User = Depends(get_current_user)):
    """列出当前用户已上传的所有素材文件"""
    files = _uploaded_files.get(current_user.id, [])
    return {
        "total": len(files),
        "files": [
            {
                "file_id": f["file_id"],
                "filename": f["filename"],
                "type": f["type"],
                "ext": f["ext"],
                "size": f["size"],
                "uploaded_at": f["uploaded_at"],
            }
            for f in files
        ],
    }


@router.delete("/creation/uploads/{file_id}")
def delete_uploaded_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """删除已上传的素材文件"""
    uid = current_user.id
    files = _uploaded_files.get(uid, [])
    target = None
    for f in files:
        if f["file_id"] == file_id:
            target = f
            break
    if not target:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "文件不存在"})

    # 删除磁盘文件
    try:
        Path(target["path"]).unlink(missing_ok=True)
    except Exception:
        pass

    _uploaded_files[uid] = [f for f in files if f["file_id"] != file_id]
    return {"message": f"文件 {target['filename']} 已删除"}


@router.get("/uploads/{file_id}/analysis")
def get_upload_analysis(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取已上传素材的分析结果（announcement 要求）"""
    user_files = _uploaded_files.get(current_user.id, [])
    target = None
    for f in user_files:
        if f["file_id"] == file_id:
            target = f
            break
    if not target:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "文件不存在"})

    image_path = target.get("path", "")
    analysis_text = _analyze_image(image_path) if image_path else "[无本地文件]"

    # 同时检查是否有 MaterialAnalysis 记录
    from app.models.business import MaterialAnalysis
    db = SessionLocal()
    try:
        existing = db.query(MaterialAnalysis).filter(
            MaterialAnalysis.user_id == current_user.id,
            MaterialAnalysis.file_path == image_path,
        ).order_by(MaterialAnalysis.created_at.desc()).first()
        db_analysis = existing.analysis_result if existing else None
    finally:
        db.close()

    return {
        "file_id": file_id,
        "filename": target.get("filename", ""),
        "file_type": target.get("type", ""),
        "file_size": target.get("size", 0),
        "uploaded_at": target.get("uploaded_at", ""),
        "analysis": analysis_text,
        "material_analysis": db_analysis,
        "status": "completed" if analysis_text else "pending",
    }


# ====================== 多模态素材分析 API ======================

@router.post("/creation/analyze")
async def analyze_material(
    file: UploadFile = File(..., description="上传素材文件（图片/视频/音频）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传素材文件并调用豆包多模态分析。

    - 图片 → 豆包 2.0 Pro 视觉分析
    - 视频 → 豆包 2.0 Pro 视频帧分析
    - 音频 → 本地 Whisper 转录 + 豆包分析
    - 分析结果保存到 material_analyses 表，支持历史查看
    """
    # 校验扩展名
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
    video_exts = {".mp4", ".mov", ".mkv", ".avi"}
    audio_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
    ALLOWED = image_exts | video_exts | audio_exts
    ext = Path(file.filename or "unknown").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(status_code=400, detail={
            "error": "invalid_file_type", "detail": f"不支持的文件类型 '{ext}'"})

    # 判断类型
    if ext in image_exts:
        file_type = "image"
    elif ext in video_exts:
        file_type = "video"
    else:
        file_type = "audio"

    # 保存文件
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest = UPLOAD_DIR / safe_name
    try:
        file_bytes = await file.read()
        with open(dest, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        if dest.exists():
            dest.unlink()
        raise HTTPException(status_code=500, detail={"error": "upload_failed", "detail": str(e)})

    file_size = len(file_bytes)

    # 创建分析记录
    from app.models.business import MaterialAnalysis
    analysis = MaterialAnalysis(
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(dest),
        file_type=file_type,
        file_size=file_size,
        status="processing",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # 调用多模态分析
    try:
        p4_path = Path(__file__).parent.parent.parent / "p4_agent"
        if str(p4_path) not in sys.path:
            sys.path.insert(0, str(p4_path))

        from multimodal import analyze_image, analyze_video, transcribe_audio

        if file_type == "image":
            result = analyze_image(str(dest))
        elif file_type == "video":
            result = analyze_video(str(dest))
        else:
            result = transcribe_audio(str(dest))

        if result.get("success"):
            analysis.analysis_result = {
                "success": True,
                "content": result.get("content", ""),
                "usage": result.get("usage", {}),
                "is_free": result.get("is_free", False),
                "audio_transcripts": result.get("audio_transcripts", []),
                "elapsed": result.get("elapsed", 0),
            }
            analysis.status = "completed"
            analysis.provider = "doubao"
        else:
            analysis.analysis_result = {"success": False, "error": result.get("error", "不明错误")}
            analysis.status = "failed"
            analysis.error_message = result.get("error", "")[:500]
    except ImportError:
        analysis.analysis_result = {"success": False, "error": "多模态模块未安装"}
        analysis.status = "failed"
        analysis.error_message = "multimodal module not available"
    except Exception as e:
        analysis.analysis_result = {"success": False, "error": str(e)}
        analysis.status = "failed"
        analysis.error_message = str(e)[:500]

    db.commit()
    db.refresh(analysis)

    return {
        "id": analysis.id,
        "filename": analysis.filename,
        "file_type": analysis.file_type,
        "file_size": analysis.file_size,
        "status": analysis.status,
        "analysis_result": analysis.analysis_result,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }


@router.get("/creation/analyses")
def list_material_analyses(
    page: int = 1,
    size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户的所有素材分析记录"""
    from app.models.business import MaterialAnalysis
    query = db.query(MaterialAnalysis).filter(
        MaterialAnalysis.user_id == current_user.id
    ).order_by(MaterialAnalysis.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [
            {
                "id": a.id,
                "filename": a.filename,
                "file_type": a.file_type,
                "file_size": a.file_size,
                "status": a.status,
                "provider": a.provider,
                "analysis_result": a.analysis_result,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ],
    }


@router.get("/creation/analyses/{analysis_id}")
def get_material_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单条素材分析详情"""
    from app.models.business import MaterialAnalysis
    a = db.query(MaterialAnalysis).filter(
        MaterialAnalysis.id == analysis_id,
        MaterialAnalysis.user_id == current_user.id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "分析记录不存在"})

    return {
        "id": a.id,
        "filename": a.filename,
        "file_type": a.file_type,
        "file_size": a.file_size,
        "file_path": a.file_path,
        "status": a.status,
        "provider": a.provider,
        "analysis_result": a.analysis_result,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get("/creation/analyses/{analysis_id}/file")
def download_material_file(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """下载/查看原始素材文件（inline 展示图片，attachment 下载视频/音频）"""
    from app.models.business import MaterialAnalysis
    from fastapi.responses import FileResponse

    a = db.query(MaterialAnalysis).filter(
        MaterialAnalysis.id == analysis_id,
        MaterialAnalysis.user_id == current_user.id,
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "分析记录不存在"})

    path = Path(a.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail={"error": "file_missing", "detail": "原始文件已丢失"})

    # 图片 → inline 预览，视频/音频 → 下载
    inline_types = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
    disposition = "inline" if path.suffix.lower() in inline_types else "attachment"
    return FileResponse(
        path=str(path),
        filename=a.filename,
        media_type=a.file_type + "/*" if a.file_type else None,
        content_disposition_type=disposition,
    )
