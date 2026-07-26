"""
P4 → P3 对接入口
提供 create_content() 函数，直接对接 P3 的 CreationRequest 格式。
P3 在 _run_mock_workflow 中调用此函数替换 Mock 逻辑。
"""

from __future__ import annotations

from typing import Any

from agents import run_agent, run_agent_pipeline
from parser import parse_pipeline_result
from workflow.scoring import rank_schemes


def create_content(
    topic: str,
    target_audience: str,
    platform: str,
    duration: str,
    style: str = "通用",
    *,
    provider: str = "mock",
    enable_trend: bool = True,
    enable_review: bool = True,
    enable_strategy: bool = True,
    image_url: str = "",       # P3 多模态：图片路径/URL
    video_path: str = "",      # P3 多模态：视频路径
    audio_path: str = "",      # P3 多模态：音频路径
) -> dict[str, Any]:
    """
    核心创作入口，接收 P3 CreationRequest 字段，返回可直接入库的结构。

    Args:
        topic:          创作主题
        target_audience: 目标受众
        platform:       平台 (douyin / xiaohongshu / bilibili)
        duration:       视频时长 (30s / 60s / 3min)
        style:          风格偏好
        provider:       后端选择 (mock / deepseek / coze / dify)
        enable_trend:   是否启用热点分析
        enable_review:  是否启用合规审查
        enable_strategy:是否启用发布策略
        image_url:      多模态 — 图片文件路径
        video_path:     多模态 — 视频文件路径
        audio_path:     多模态 — 音频文件路径

    Returns:
        {
            "ok": bool,
            "error": str | None,
            "pipeline_id": str,
            "provider": str,
            "agent_logs": [...],      # → agent_logs 表
            "schemes": [...],          # → schemes 表 (已评分+排名)
            "recommendation": {...},
            "raw_markdown": str,       # 脚本 Markdown 原文，供前端渲染
            "multimodal": {...},       # 多模态分析结果（如有素材输入）
        }
    """
    user_input = (
        f"主题：{topic} | 平台：{platform} | "
        f"受众：{target_audience} | 时长：{duration} | 风格：{style}"
    )

    # ▸ 多模态预处理：图片/视频/音频 → 文本分析注入 Prompt
    multimodal_result = None
    if image_url or video_path or audio_path:
        try:
            from multimodal import image_to_script, analyze_video, transcribe_audio

            if image_url:
                multimodal_result = image_to_script(image_url, platform, style)
            elif video_path:
                multimodal_result = analyze_video(video_path)
            elif audio_path:
                multimodal_result = transcribe_audio(audio_path)

            if multimodal_result and multimodal_result.get("success"):
                analysis = multimodal_result.get("image_analysis") or multimodal_result.get("content", "")
                user_input += f"\n\n【素材分析结果】\n{analysis[:2000]}"
        except ImportError:
            pass  # multimodal 模块不可用时静默跳过
        except Exception as exc:
            multimodal_result = {"success": False, "error": str(exc)}
    # ▸ 多模态预处理结束

    try:
        # 执行完整流水线
        pipeline_result = run_agent_pipeline(
            user_input,
            provider=provider,
            enable_trend=enable_trend,
            enable_review=enable_review,
            enable_strategy=enable_strategy,
        )

        # 解析脚本输出
        parsed = parse_pipeline_result(pipeline_result)
        schemes = parsed["schemes"]

        # 评分 + 排名
        if schemes:
            schemes = rank_schemes(schemes)

        return {
            "ok": True,
            "error": None,
            "pipeline_id": parsed["pipeline_id"],
            "provider": parsed["provider"],
            "agent_logs": parsed["agent_logs"],
            "schemes": schemes,
            "recommendation": parsed["recommendation"],
            "raw_markdown": parsed["raw_markdown"],
            "multimodal": multimodal_result,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "pipeline_id": "",
            "provider": provider,
            "agent_logs": [],
            "schemes": [],
            "recommendation": {},
            "raw_markdown": "",
            "multimodal": None,
        }


# ---------------------------------------------------------------------------
# P3 集成代码模板（供 P3 参考，复制到 backend/app/routers/creation.py）
# ---------------------------------------------------------------------------
P3_INTEGRATION_TEMPLATE = '''
# ===== 替换 _run_mock_workflow 中的 Mock 逻辑 =====

# 方式一：直接调用（同步，适合快速验证）
from agents import create_content

result = create_content(
    topic="秋季护肤",
    target_audience="25-35岁职场女性",
    platform="douyin",
    duration="60s",
    style="干货+轻娱乐",
    provider="mock",  # 联调时改为 "deepseek"
)

if result["ok"]:
    for log in result["agent_logs"]:
        db.add(AgentLog(session_id=session_id, **log))
    for scheme_data in result["schemes"]:
        db.add(Scheme(session_id=session_id, **scheme_data))
    db.commit()
else:
    _task_store[task_id]["status"] = "failed"
    _task_store[task_id]["result"] = {"error": "agent_error", "detail": result["error"]}


# 方式二：分步调用（需要更细粒度控制时）
from agents import run_agent, run_agent_pipeline
from parser import parse_script_output
from workflow.scoring import rank_schemes

pipeline_result = run_agent_pipeline(user_input, provider="deepseek")
parsed = parse_pipeline_result(pipeline_result)
schemes = rank_schemes(parsed["schemes"])
'''
