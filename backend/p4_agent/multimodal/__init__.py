"""
P4 Agent — 多模态统一接口
基于 AISkills 的 doubao-multimodal + doubao-tts
为 P4 流水线提供：图片分析、视频抽帧分析、音频转录、TTS 语音合成
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# 确保能 import 同目录下的 multimodal.py 和 doubao_tts.py
_SKILL_DIR = Path(__file__).resolve().parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))


def analyze_image(image_path: str, question: str = "") -> dict[str, Any]:
    """
    图片多模态分析 — 用豆包 2.0 Pro 分析图片内容。

    Args:
        image_path: 图片文件路径 (png/jpg/webp/gif/bmp)
        question: 分析问题，默认自动生成

    Returns:
        {"success": True, "content": "分析结果...", "usage": {...}, "elapsed": 3.2}
    """
    from .multimodal import call_multimodal

    if not question:
        question = (
            "请详细描述这张图片的内容，包括：1)画面主体 2)色调与氛围 3)文字信息(如有) "
            "4)这张图适合做什么类型的短视频内容 5)如果是宣传海报/产品图/场景图，给出3个创作切入角度"
        )
    return call_multimodal(images=[image_path], question=question, timeout=180)


def analyze_images(image_paths: list[str], question: str = "") -> dict[str, Any]:
    """多图对比分析。"""
    from .multimodal import call_multimodal

    if not question:
        question = f"请分别描述这{len(image_paths)}张图片的内容，并指出它们的异同。"
    return call_multimodal(images=image_paths, question=question, timeout=180)


def analyze_video(video_path: str, question: str = "") -> dict[str, Any]:
    """
    视频多模态分析 — 分析视频画面帧（不含音轨）。

    Args:
        video_path: 视频文件路径 (mp4/mkv/avi/mov)
        question: 分析问题
    """
    from .multimodal import call_multimodal

    if not question:
        question = (
            "请分析这个视频的内容：1)画面中的主要场景和动作 2)视频风格和节奏 "
            "3)适合的平台和受众 4)给出3个基于此视频风格的创作选题建议"
        )
    return call_multimodal(videos=[video_path], question=question, timeout=300)


def transcribe_audio(audio_path: str, question: str = "") -> dict[str, Any]:
    """
    音频转录 + 分析 — Whisper 本地转录后送豆包分析。

    Args:
        audio_path: 音频文件路径 (mp3/wav/flac/ogg/m4a)
        question: 分析问题
    """
    from .multimodal import call_multimodal

    if not question:
        question = "请分析这段音频的转录文本：总结主要内容、情感基调、关键信息点。"
    return call_multimodal(audios=[audio_path], question=question, timeout=300)


def generate_tts(
    text: str,
    speaker: str = "zh_female_qingxin",
    audio_format: str = "mp3",
    sample_rate: int = 24000,
    speed: int = 0,
    volume: int = 0,
    pitch: int = 0,
) -> dict[str, Any]:
    """
    TTS 语音合成 — 将脚本文本转为配音音频。

    Args:
        text: 待合成文本 (最大3000字符)
        speaker: 音色ID，可选 zh_female_tianmei/zh_female_qingxin/zh_female_zhixing/zh_female_wenrou
        audio_format: mp3/wav/ogg_opus/pcm
        sample_rate: 采样率，默认 24000
        speed: 语速 [-50, 100]，默认0
        volume: 音量 [-50, 100]，默认0
        pitch: 音调 [-12, 12]，默认0

    Returns:
        {"success": True, "audio_base64": "...", "duration": 4.1, "url": "..."}
    """
    from .doubao_tts import generate_tts as _tts

    return _tts(
        text=text,
        model="seed-audio-1.0-multilingual",
        speaker=speaker,
        audio_format=audio_format,
        sample_rate=sample_rate,
        speed=speed,
        volume=volume,
        pitch=pitch,
    )


def image_to_script(image_path: str, platform: str = "抖音", style: str = "通用") -> dict[str, Any]:
    """
    图片 → 脚本流水线：分析图片内容 → 生成匹配的短视频脚本方案。

    Args:
        image_path: 图片路径
        platform: 目标平台
        style: 风格偏好

    Returns:
        {"success": True, "image_analysis": "...", "raw_script": "..."}
    """
    # Step 1: 豆包多模态分析图片
    img_result = analyze_image(
        image_path,
        question=(
            f"这张图将用于{platform}平台的短视频创作，风格偏好为{style}。"
            "请分析：1)画面的核心元素和视觉亮点 2)目标受众画像 "
            "3)可以延伸的故事情节 4)适合的标题/封面方向"
        ),
    )

    if not img_result.get("success"):
        return {"success": False, "error": f"图片分析失败: {img_result.get('error')}", "image_analysis": img_result}

    return {
        "success": True,
        "image_analysis": img_result.get("content", ""),
        "usage": img_result.get("usage", {}),
        "is_free": img_result.get("is_free", False),
    }
