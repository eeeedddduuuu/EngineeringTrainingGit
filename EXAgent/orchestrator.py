"""
EXAgent — 统一 Agent 编排器
DeepSeek function calling 驱动，10+ 工具全覆盖，多轮对话。
独立实验模块，不依赖主项目 HTTP 调用。
"""

import json
import uuid
import sys
import os
import shutil
import time
import urllib.request as _ur
from pathlib import Path
from typing import Any, Iterator, Generator

import requests

# ── P4 Agent 路径 ──
# orchestrator.py 位于 EXAgent/ 下，指向 EXAgent 自己的 backend（实验副本，与主项目隔离）
_P4_PATH = Path(__file__).resolve().parent / "backend" / "p4_agent"
if str(_P4_PATH) not in sys.path:
    sys.path.insert(0, str(_P4_PATH))

# ── DeepSeek 配置 ──
DS_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_BASE_URL = "https://api.deepseek.com/v1"
DS_MODEL = "deepseek-v4-pro"

# ── ARK/火山方舟 Keys ──
# 从环境变量读取，本地开发请在终端设置或使用 .env 文件
_ARK_IMAGE_KEY = os.environ.get("ARK_API_KEY", "")
_ARK_VIDEO_KEY_RAW = os.environ.get("ARK_VIDEO_KEY", "")
_ARK_VISION_KEY_RAW = os.environ.get("ARK_VISION_KEY", "")
_TTS_KEY_RAW = os.environ.get("TTS_API_KEY", "")

# 注入 os.environ（供 doubao_tts.py 等模块读取）
if _ARK_IMAGE_KEY:
    os.environ.setdefault("ARK_API_KEY", _ARK_IMAGE_KEY)
if _ARK_VIDEO_KEY_RAW:
    os.environ.setdefault("ARK_VIDEO_KEY", _ARK_VIDEO_KEY_RAW)
if _ARK_VISION_KEY_RAW:
    os.environ.setdefault("ARK_VISION_KEY", _ARK_VISION_KEY_RAW)
if _TTS_KEY_RAW:
    os.environ.setdefault("TTS_API_KEY", _TTS_KEY_RAW)

ARK_API_KEY = _ARK_IMAGE_KEY
ARK_VIDEO_KEY = _ARK_VIDEO_KEY_RAW
TTS_API_KEY = _TTS_KEY_RAW

# DeepSeek Key
DS_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ── 图片输出目录 ──（EXAgent 自己的 uploads，与主项目隔离）
_IMG_DIR = Path(__file__).resolve().parent / "backend" / "uploads" / "ai_images"
_IMG_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════
# System Prompt
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是 AI 数字媒体创作助手，专精于短视频创作全流程。

## 你的能力
- 📝 **创作短视频方案**: 根据主题/受众/平台/时长/风格，自动串联热点分析→脚本创作→合规审查→发布策略，生成3套差异化方案并评分排名
- 🎨 **AI 生图**: Seedream 文生图，支持多种模型(pro/lite/4.5/4.0)、尺寸(1K-4K)、比例(1:1/16:9/9:16等)
- 🎬 **AI 生视频**: Seedance 文生视频/图生视频，支持分辨率/时长/比例配置。生成后等待30-60秒即可获得视频链接。如果只返回了 task_id，用 query_video_status 查询进度。
- 🔊 **AI 配音**: 豆包 TTS 文字转语音，4种女声音色可选。生成后在回复中给出可直接点击的音频下载链接（audio_url 格式为 /uploads/tts/xxx.mp3，完整地址为 http://127.0.0.1:8000/uploads/tts/xxx.mp3）
- 🔍 **素材分析**: 豆包多模态识别图片/视频/音频内容，提取风格特征和创作角度
- 🌐 **网络搜索**: 搜索最新热点趋势、竞品分析数据
- 📚 **知识库检索**: 查找平台创作规范、脚本模板、分镜格式
- 🛡️ **合规审查**: 检查文本中的敏感词和违规内容

## 输出格式规范（必须遵守）
**所有回复必须使用 Markdown 排版**，确保内容结构清晰、易读美观：

1. **标题层级**：用 `##` 表示大段落，`###` 表示子段落
2. **列表**：并列项用 `- ` 无序列表，步骤用 `1. ` 有序列表
3. **强调**：关键词用 `**加粗**`，术语用 `` `代码` ``
4. **表格**：对比/方案/参数等数据一律用 Markdown 表格呈现
5. **分隔**：不同主题间用 `---` 分隔线
6. **引用**：重要提示/注意事项用 `>` 引用块
7. **代码块**：脚本、分镜表、JSON 等用 ` ``` ` 包裹

**格式示例**：
```
## 方案名称
> 一句话总结

### 核心亮点
- **亮点1**：说明
- **亮点2**：说明

### 详细参数
| 参数 | 值 |
|------|-----|
| 平台 | 抖音 |
| 时长 | 60秒 |

---
（下个主题）
```

## 行为规则
1. 用户提需求时，判断需要调用哪些工具，**把所有需要的工具一并调用**
2. 创作方案时**必须调用 create_content**，不要自己编造方案内容
3. 如果用户需求不完整（缺平台/时长/风格），主动问清楚再调用工具
4. 工具返回结果用**自然语言总结**，不要直接 dump JSON
5. 友好、专业、中文回复
6. 方案对比用**表格**呈现
7. **永远使用 Markdown 格式输出**，让回复美观易读

## 素材文件处理
用户上传的图片/视频/音频文件会自动保存到 uploads 目录，文件路径会以 `file_path` 形式注入到对话中。
- **图片**: 用 `analyze_material(file_path="/uploads/agent_uploads/xxx.png", file_type="image")` 分析内容/风格/色彩
- **视频**: 用 `analyze_material(file_path="/uploads/agent_uploads/xxx.mp4", file_type="video")` 分析场景/运镜/色调
- **音频**: 用 `analyze_material(file_path="/uploads/agent_uploads/xxx.mp3", file_type="audio")` 转写/分析
- **拼接视频**: 用 `concat_video(video_paths=["path1", "path2"])` 合并多个视频
- **处理视频**(裁剪/转码/去音): 用 `video_tool` 工具
- **图生视频**: 用 `generate_video(prompt="描述", image_url="文件URL")` 基于上传图片生成视频"""


# ══════════════════════════════════════════════════════════════
# Tool Definitions (OpenAI Function Calling 格式)
# ══════════════════════════════════════════════════════════════

ORCHESTRATOR_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "create_content",
            "description": "创作短视频方案（核心工具）。自动运行 热点分析→脚本创作→合规审查→发布策略 四步流水线，生成3套差异化方案并评分排名。",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "创作主题，如「秋季护肤」「美食探店」「AI工具测评」"},
                    "platform": {"type": "string", "enum": ["douyin", "xiaohongshu", "bilibili"], "description": "目标平台: douyin=抖音, xiaohongshu=小红书, bilibili=B站"},
                    "duration": {"type": "string", "description": "视频时长: 30s / 60s / 3min"},
                    "target_audience": {"type": "string", "description": "目标受众，如「25-35岁职场女性」「大学生」「宝妈」"},
                    "style": {"type": "string", "description": "风格偏好: 干货科普/故事代入/挑战测评/轻松娱乐"},
                },
                "required": ["topic", "platform"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "AI 文生图（Seedream）。根据文字描述生成图片，用于封面/海报/配图。",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "图片描述提示词，越详细效果越好"},
                    "model": {"type": "string", "enum": ["pro", "lite", "4.5", "4.0"], "description": "模型，默认 pro"},
                    "size": {"type": "string", "enum": ["1K", "2K", "3K", "4K"], "description": "输出尺寸，默认 2K"},
                    "aspect_ratio": {"type": "string", "description": "宽高比: 1:1 / 16:9 / 9:16 / 4:3 / 3:4 / 3:2 / 2:3"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_video",
            "description": "AI 视频生成（Seedance）。文生视频或图生视频，异步生成。测试用 480p 1s 省额度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "视频描述提示词"},
                    "resolution": {"type": "string", "enum": ["480p", "720p", "1080p"], "description": "分辨率，测试请用 480p"},
                    "duration": {"type": "integer", "description": "时长(秒)，2-12，测试请用 2"},
                    "image_url": {"type": "string", "description": "参考图URL（图生视频时提供，文生视频留空）"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_video_status",
            "description": "查询 Seedance 视频生成任务进度。传入之前返回的 task_id，完成后会返回视频链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "视频任务的 task_id（如 cgt-xxxxxxxxxxxx）"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_tts",
            "description": "AI 文字转语音（豆包 TTS）。将脚本文案合成为配音音频 MP3。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待合成文本，最长3000字符"},
                    "speaker": {"type": "string", "enum": ["zh_female_qingxin", "zh_female_tianmei", "zh_female_zhixing", "zh_female_wenrou"], "description": "音色: qingxin=清新女声, tianmei=甜美女声, zhixing=知性女声, wenrou=温柔女声"},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索互联网获取最新热点、趋势数据、竞品信息。用于了解当前流行话题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或问题"},
                    "max_results": {"type": "integer", "description": "返回条数(1-8)，默认 5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "knowledge_search",
            "description": "检索本地知识库中的创作规范、平台标准、脚本模板、分镜格式等专业资料。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词或问题"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sensitive_word_filter",
            "description": "检查文本是否包含敏感词、隐私信息（手机号/身份证号）或违规内容，返回风险等级(pass/review/block)。创作完成后应主动调用此工具审查内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "待审查的完整文本内容"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_material",
            "description": "分析上传的图片/视频/音频素材。豆包多模态识别内容、风格特征、适合的创作角度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "素材文件的本地路径"},
                    "file_type": {"type": "string", "enum": ["image", "video", "audio"], "description": "素材类型"},
                },
                "required": ["file_path", "file_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "concat_video",
            "description": "视频拼接/合并。将多个短视频按顺序拼接为一个完整视频，支持硬切(cut)或淡入淡出(fade)过渡效果。适用于将多段素材合并成最终成片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要拼接的视频文件本地路径列表，按拼接顺序排列，至少 2 个",
                    },
                    "transition": {
                        "type": "string",
                        "enum": ["cut", "fade"],
                        "description": "过渡方式: cut=硬切换(默认，适合快节奏), fade=交叉淡入淡出(适合叙事过渡)",
                    },
                },
                "required": ["video_paths"],
            },
        },
    },
]

# ══════════════════════════════════════════════════════════════
# Tool Executors
# ══════════════════════════════════════════════════════════════

def _exec_create_content(args: dict) -> dict:
    """创作流水线 — 直接调用 p4_agent pipeline_adapter"""
    from pipeline_adapter import create_content
    result = create_content(
        topic=args.get("topic", ""),
        target_audience=args.get("target_audience", "通用"),
        platform=args.get("platform", "douyin"),
        duration=args.get("duration", "60s"),
        style=args.get("style", "通用"),
        provider="deepseek",
    )
    return {
        "ok": result.get("ok", False),
        "pipeline_id": result.get("pipeline_id", ""),
        "schemes_count": len(result.get("schemes", [])),
        "schemes": result.get("schemes", []),
        "recommendation": result.get("recommendation", {}),
        "raw_markdown": result.get("raw_markdown", ""),
        "error": result.get("error"),
    }


def _exec_generate_image(args: dict) -> dict:
    """Seedream 文生图"""
    if not ARK_API_KEY:
        return {"ok": False, "error": "ARK_API_KEY 未设置，请先配置火山方舟 Key"}

    prompt = args.get("prompt", "").strip()
    model = args.get("model", "pro")
    size = args.get("size", "2K")
    aspect_ratio = args.get("aspect_ratio", "1:1")

    MODEL_ENDPOINTS = {
        "pro": "ep-20260726092049-jklk6",
        "lite": "ep-20260726093953-hgkbz",
        "4.5": "ep-20260726093919-8br8x",
        "4.0": "ep-20260726093814-k7ffv",
    }
    ASPECT_PIXELS = {
        "1:1": "2048x2048", "16:9": "2816x1584", "9:16": "1584x2816",
        "4:3": "2368x1776", "3:4": "1776x2368", "3:2": "2496x1664",
        "2:3": "1664x2496", "21:9": "3136x1344",
    }

    endpoint = MODEL_ENDPOINTS.get(model, MODEL_ENDPOINTS["pro"])
    final_size = ASPECT_PIXELS.get(aspect_ratio, size) if model == "pro" and size == "2K" else size

    payload = json.dumps({
        "model": endpoint,
        "prompt": prompt,
        "response_format": "url",
        "size": final_size,
        "watermark": True,
    }, ensure_ascii=False).encode("utf-8")

    req = _ur.Request(
        "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {ARK_API_KEY}"},
    )
    with _ur.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    img_url = data.get("data", [{}])[0].get("url", "")
    if not img_url:
        return {"ok": False, "error": f"Seedream 无图片 URL: {str(data)[:300]}"}

    suffix = ".png" if args.get("output_format") == "png" else ".jpg"
    filename = f"exagent_img_{uuid.uuid4().hex[:8]}{suffix}"
    local_path = str(_IMG_DIR / filename)
    _ur.urlretrieve(img_url, local_path)

    return {
        "ok": True,
        "image_url": f"/uploads/ai_images/{filename}",
        "local_path": local_path,
        "model": model,
        "size": final_size,
    }


def _exec_generate_video(args: dict) -> dict:
    """Seedance 文生视频/图生视频，提交后自动轮询等待完成（最长 60 秒）"""
    if not ARK_VIDEO_KEY:
        return {"ok": False, "error": "ARK_VIDEO_KEY 未设置，请先配置火山方舟视频 Key"}

    def _extract_video_url(data: dict) -> str:
        """从火山 Seedance API 返回中提取 video_url，兼容单对象和数组格式"""
        content = data.get("content")
        # 格式1: content 是单对象 {"video_url": "..."}
        if isinstance(content, dict) and content.get("video_url"):
            return content["video_url"]
        # 格式2: content 是数组 [{"video_url": "..."}]
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("video_url"):
                    return c["video_url"]
        # 格式3: 顶层直接有 video_url / output_url / url
        for key in ("video_url", "output_url", "url"):
            if data.get(key):
                return data[key]
        return ""

    prompt = args.get("prompt", "").strip()
    resolution = args.get("resolution", "1080p")
    duration = args.get("duration", 5)
    image_url = args.get("image_url", "").strip()

    # 拼接参数到 prompt
    params = [f"--resolution {resolution}", f"--duration {duration}"]
    full_prompt = f"{prompt}  {' '.join(params)}"

    content = [{"type": "text", "text": full_prompt}]
    if image_url:
        content.append({"type": "image_url", "image_url": {"url": image_url}})

    SEEDANCE_MODEL = "doubao-seedance-1-0-pro-250528"
    resp = requests.post(
        "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
        json={"model": SEEDANCE_MODEL, "content": content},
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {ARK_VIDEO_KEY}"},
        timeout=30,
    )
    resp.encoding = "utf-8"
    data = resp.json()
    task_id = data.get("id", "")
    if not task_id:
        return {"ok": False, "error": f"提交失败: {data}"}

    # 自动轮询等待完成（最长 60 秒，480p 5s 通常在 30-60s 内完成）
    max_polls = 12
    for poll in range(max_polls):
        time.sleep(5)
        try:
            sr = requests.get(
                f"https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}",
                headers={"Authorization": f"Bearer {ARK_VIDEO_KEY}"},
                timeout=15,
            )
            sd = sr.json() if sr.text else {}
            status = sd.get("status", sd.get("state", "unknown"))
            if status in ("succeeded", "done", "completed"):
                video_url = _extract_video_url(sd)
                return {
                    "ok": True,
                    "task_id": task_id,
                    "status": "succeeded",
                    "video_url": video_url,
                    "prompt": prompt,
                    "resolution": resolution,
                    "duration": duration,
                    "message": "视频已生成完成",
                }
            elif status in ("failed", "error"):
                return {
                    "ok": False,
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(sd.get("error", "任务失败")),
                }
        except Exception:
            pass

    # 超时 — 返回 task_id 供后续查询
    return {
        "ok": True,
        "task_id": task_id,
        "status": "pending",
        "prompt": prompt,
        "resolution": resolution,
        "duration": duration,
        "message": f"视频任务 {task_id[:12]}... 仍在处理中。请稍后让我查询状态。",
    }


def _exec_query_video_status(args: dict) -> dict:
    """查询 Seedance 视频任务状态"""
    if not ARK_VIDEO_KEY:
        return {"ok": False, "error": "ARK_VIDEO_KEY 未设置"}
    task_id = args.get("task_id", "").strip()
    if not task_id:
        return {"ok": False, "error": "缺少 task_id"}

    resp = requests.get(
        f"https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}",
        headers={"Authorization": f"Bearer {ARK_VIDEO_KEY}"},
        timeout=30,
    )
    data = resp.json() if resp.text else {}
    status = data.get("status", data.get("state", "unknown"))

    result = {"ok": True, "task_id": task_id, "status": status}
    if status in ("succeeded", "done", "completed"):
        video_url = _extract_video_url(data)
        result["video_url"] = video_url
        result["message"] = "视频已生成完成"
    elif status in ("failed", "error"):
        result["ok"] = False
        result["error"] = str(data.get("error", "任务失败"))
        result["message"] = "视频生成失败"
    else:
        result["message"] = f"任务状态: {status}，请稍后再查"
    return result


def _exec_generate_tts(args: dict) -> dict:
    """豆包 TTS 文字转语音"""
    from multimodal.doubao_tts import generate_tts as _tts

    text = args.get("text", "").strip()
    speaker = args.get("speaker", "zh_female_qingxin")

    result = _tts(text=text, speaker=speaker, audio_format="mp3")
    if result.get("success"):
        # 解码 base64 音频保存到本地
        import base64
        audio_url = ""
        audio_b64 = result.get("audio_base64", "")
        if audio_b64:
            audio_bytes = base64.b64decode(audio_b64)
            tts_dir = _IMG_DIR.parent / "tts"
            tts_dir.mkdir(parents=True, exist_ok=True)
            filename = f"exagent_tts_{uuid.uuid4().hex[:8]}.mp3"
            local_path = tts_dir / filename
            local_path.write_bytes(audio_bytes)
            audio_url = f"/uploads/tts/{filename}"
        elif result.get("url"):
            # base64 为空时，从临时 URL 下载音频
            try:
                import requests as _req
                tts_dir = _IMG_DIR.parent / "tts"
                tts_dir.mkdir(parents=True, exist_ok=True)
                filename = f"exagent_tts_{uuid.uuid4().hex[:8]}.mp3"
                local_path = tts_dir / filename
                r = _req.get(result["url"], timeout=60, proxies={"http": None, "https": None})
                r.raise_for_status()
                local_path.write_bytes(r.content)
                audio_url = f"/uploads/tts/{filename}"
            except Exception as dl_err:
                print(f"[TTS] URL 下载失败: {dl_err}", file=sys.stderr)

        if not audio_url:
            return {"ok": False, "error": "TTS 返回成功但没有可用的音频数据（base64 和 url 均为空）"}

        return {
            "ok": True,
            "duration": result.get("duration", 0),
            "audio_url": audio_url,
            "message": f"TTS 配音生成成功，时长 {result.get('duration', 0):.1f} 秒，[点击下载音频](http://127.0.0.1:8000{audio_url})",
        }
    return {"ok": False, "error": result.get("error", "TTS 失败")}


def _exec_web_search(args: dict) -> dict:
    """网络搜索"""
    from tools import web_search
    try:
        result = web_search(
            str(args.get("query", "")),
            int(args.get("max_results", 5)),
        )
        return {"ok": True, "engine": result.get("engine", "?"), "results": result.get("results", [])}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_knowledge_search(args: dict) -> dict:
    """知识库检索"""
    from tools import knowledge_search
    try:
        result = knowledge_search(str(args.get("query", "")))
        return {"ok": True, "source": result.get("source", "?"), "results": result.get("results", [])}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exec_sensitive_filter(args: dict) -> dict:
    """敏感词过滤"""
    from tools import sensitive_word_filter
    try:
        result = sensitive_word_filter(str(args.get("content", "")))
        return {"ok": True, "risk_level": result.get("risk_level", "?"), "review_text": result.get("review_text", ""), "flagged_terms": result.get("flagged_terms", "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _resolve_file_path(raw: str) -> str | None:
    """Resolve a file path from AI tool args. Tries:
    1. Exact path
    2. Relative to _IMG_DIR's parent uploads/agent_uploads/
    3. Extract filename from path and look in agent_uploads/
    """
    if not raw:
        return None
    p = Path(raw)
    if p.exists():
        return str(p)

    # Try relative to agent_uploads
    agent_uploads = _IMG_DIR.parent / "agent_uploads"
    # If raw is like "/uploads/agent_uploads/xxx.jpg", extract filename
    if raw.startswith("/uploads/agent_uploads/"):
        candidate = agent_uploads / Path(raw).name
        if candidate.exists():
            return str(candidate)
    # Try raw as relative to agent_uploads
    candidate = agent_uploads / Path(raw).name
    if candidate.exists():
        return str(candidate)

    return None


def _find_ffmpeg() -> str | None:
    """Look up FFmpeg via imageio_ffmpeg (bundled binary)."""
    try:
        import imageio_ffmpeg as _iff
        return _iff.get_ffmpeg_exe()
    except Exception:
        return None


def _exec_analyze_material(args: dict) -> dict:
    """多模态素材分析"""
    file_path = args.get("file_path", "")
    file_type = args.get("file_type", "image")

    resolved = _resolve_file_path(file_path)
    if not resolved:
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    from multimodal import analyze_image, analyze_video, transcribe_audio

    if file_type == "video":
        result = analyze_video(resolved)
    elif file_type == "audio":
        result = transcribe_audio(resolved)
    else:
        result = analyze_image(resolved)

    # multimodal 模块返回 success/error，统一转为 ok/error
    return {
        "ok": result.get("success", False),
        "success": result.get("success", False),
        "error": result.get("error", ""),
        **result,
    }


def _exec_concat_video(args: dict) -> dict:
    """FFmpeg 视频拼接"""
    import subprocess, tempfile, os as _os

    video_paths = args.get("video_paths", [])
    transition = args.get("transition", "cut")

    if not video_paths or len(video_paths) < 2:
        return {"ok": False, "error": "至少需要 2 个视频文件路径"}

    # 解析传入的路径（AI 可能不传绝对路径）
    resolved_paths = []
    for vp in video_paths:
        r = _resolve_file_path(vp)
        if not r:
            return {"ok": False, "error": f"视频文件不存在: {vp}"}
        resolved_paths.append(r)

    ff = _find_ffmpeg() or shutil.which("ffmpeg") or "ffmpeg"
    out_name = f"concat_{uuid.uuid4().hex[:8]}.mp4"
    out_dir = Path(__file__).resolve().parent / "backend" / "uploads" / "ai_videos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name

    try:
        if transition == "cut":
            # concat demuxer: 无损拼接
            concat_list = tempfile.mktemp(suffix=".txt")
            with open(concat_list, "w", encoding="utf-8") as f:
                for vp in resolved_paths:
                    f.write(f"file '{Path(vp).as_posix()}'\n")

            try:
                subprocess.run(
                    [ff, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                     "-c", "copy", str(out_path)],
                    check=True, capture_output=True, timeout=300,
                )
            except subprocess.CalledProcessError:
                # 编码不一致回退重新编码
                subprocess.run(
                    [ff, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                     "-c:v", "libx264", "-c:a", "aac", "-preset", "veryfast",
                     "-pix_fmt", "yuv420p", str(out_path)],
                    check=True, capture_output=True, timeout=300,
                )
            finally:
                try: _os.unlink(concat_list)
                except Exception: pass
        else:
            # xfade 交叉淡入淡出
            fade_dur = 0.5
            if len(video_paths) == 2:
                subprocess.run(
                    [ff, "-y", "-i", video_paths[0], "-i", video_paths[1],
                     "-filter_complex",
                     f"xfade=transition=fade:duration={fade_dur}:offset=2.0",
                     "-c:v", "libx264", "-c:a", "aac", "-preset", "veryfast",
                     "-pix_fmt", "yuv420p", str(out_path)],
                    check=True, capture_output=True, timeout=300,
                )
            else:
                # 多段: concat filter + fade in/out
                inputs = []
                fade_parts = []
                fade_labels = []
                for i in range(len(video_paths)):
                    inputs.extend(["-i", video_paths[i]])
                    lb = f"v{i}"
                    fade_labels.append(lb)
                    fade_parts.append(
                        f"[{i}:v]fade=t=in:st=0:d={fade_dur},"
                        f"fade=t=out:st=4.5:d={fade_dur},"
                        f"setpts=PTS-STARTPTS[{lb}]"
                    )
                label_concat = "".join(f"[{l}]" for l in fade_labels)
                filter_str = ";".join(fade_parts) + f";{label_concat}concat=n={len(video_paths)}:v=1:a=0[outv]"

                subprocess.run(
                    [ff, "-y", *inputs, "-filter_complex", filter_str,
                     "-map", "[outv]", "-c:v", "libx264", "-preset", "veryfast",
                     "-pix_fmt", "yuv420p", str(out_path)],
                    check=True, capture_output=True, timeout=300,
                )

    except FileNotFoundError:
        return {"ok": False, "error": "FFmpeg 未安装"}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": f"FFmpeg 执行失败: {e.stderr.decode()[:300] if e.stderr else str(e)}"}

    return {
        "ok": True,
        "operation": "concat",
        "transition": transition,
        "video_count": len(video_paths),
        "output_path": str(out_path),
        "url": f"/uploads/ai_videos/{out_name}",
    }


# ── 工具路由表 ──
TOOL_EXECUTORS = {
    "create_content": _exec_create_content,
    "generate_image": _exec_generate_image,
    "generate_video": _exec_generate_video,
    "query_video_status": _exec_query_video_status,
    "generate_tts": _exec_generate_tts,
    "web_search": _exec_web_search,
    "knowledge_search": _exec_knowledge_search,
    "sensitive_word_filter": _exec_sensitive_filter,
    "analyze_material": _exec_analyze_material,
    "concat_video": _exec_concat_video,
}


def execute_tool(name: str, arguments: dict) -> dict:
    """执行工具，路由到对应实现"""
    executor = TOOL_EXECUTORS.get(name)
    if not executor:
        return {"ok": False, "error": f"未知工具: {name}"}
    try:
        return executor(arguments)
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()[-500:]}


# ══════════════════════════════════════════════════════════════
# DeepSeek Function Calling
# ══════════════════════════════════════════════════════════════

def _call_deepseek(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """调用 DeepSeek API，支持 function calling"""
    payload: dict[str, Any] = {
        "model": DS_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    resp = requests.post(
        f"{DS_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {DS_API_KEY}", "Content-Type": "application/json; charset=utf-8"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=180,
    )
    if not resp.ok:
        raise RuntimeError(f"DeepSeek API 返回 HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    choice = data.get("choices", [{}])[0]
    msg = choice.get("message", {})

    return {
        "ok": True,
        "content": msg.get("content", "") or msg.get("reasoning_content", ""),
        "tool_calls": msg.get("tool_calls"),
        "run_id": data.get("id", ""),
        "usage": data.get("usage", {}),
    }


def _call_deepseek_stream(messages: list[dict], tools: list[dict] | None = None) -> Iterator[dict]:
    """流式调用 DeepSeek，逐 chunk yield"""
    payload: dict[str, Any] = {
        "model": DS_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    resp = requests.post(
        f"{DS_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {DS_API_KEY}", "Content-Type": "application/json"},
        json=payload,
        stream=True,
        timeout=180,
    )
    if not resp.ok:
        raise RuntimeError(f"DeepSeek API HTTP {resp.status_code}: {resp.text[:300]}")

    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data_str = line[5:].strip()
        if data_str == "[DONE]":
            break
        try:
            chunk = json.loads(data_str)
            yield chunk
        except json.JSONDecodeError:
            continue


def _collect_stream(stream: Iterator[dict]) -> dict:
    """消费流式 chunk，收集 content 和 tool_calls，返回和 _call_deepseek 同格式"""
    content_parts: list[str] = []
    tool_calls_acc: dict[int, dict] = {}   # index -> {id, function:{name, arguments}}
    usage = {}
    run_id = ""

    for chunk in stream:
        choices = chunk.get("choices", [])
        if not choices:
            continue
        delta = choices[0].get("delta", {})
        run_id = chunk.get("id", run_id)

        if "content" in delta and delta["content"]:
            content_parts.append(delta["content"])

        if "tool_calls" in delta:
            for tc in delta["tool_calls"]:
                idx = tc.get("index", 0)
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {"id": tc.get("id", ""), "type": "function", "function": {"name": "", "arguments": ""}}
                acc = tool_calls_acc[idx]
                if tc.get("id"):
                    acc["id"] = tc["id"]
                if tc.get("function", {}).get("name"):
                    acc["function"]["name"] += tc["function"]["name"]
                if tc.get("function", {}).get("arguments"):
                    acc["function"]["arguments"] += tc["function"]["arguments"]

        usage = chunk.get("usage", usage)

    tool_calls = [tool_calls_acc[i] for i in sorted(tool_calls_acc)] if tool_calls_acc else None

    return {
        "ok": True,
        "content": "".join(content_parts),
        "tool_calls": tool_calls,
        "run_id": run_id,
        "usage": usage,
    }


# ══════════════════════════════════════════════════════════════
# Orchestrator
# ══════════════════════════════════════════════════════════════

class AgentOrchestrator:
    """统一 Agent 编排器 — DeepSeek function calling + 多轮对话"""

    # 会话过期时间（秒），30 分钟无活动自动清理
    SESSION_TTL_SECONDS = 30 * 60
    # 最大会话数，超出时清理最旧的
    MAX_SESSIONS = 100

    def __init__(self):
        self.sessions: dict[str, list[dict]] = {}
        self._session_last_active: dict[str, float] = {}

    def _evict_expired(self) -> None:
        """清理过期会话（TTL 超时）和超出上限的旧会话。"""
        now = __import__("time").time()
        expired = [
            sid for sid, ts in self._session_last_active.items()
            if now - ts > self.SESSION_TTL_SECONDS
        ]
        for sid in expired:
            self.sessions.pop(sid, None)
            self._session_last_active.pop(sid, None)

        # 超出上限时，按最近活跃时间排序，删最旧的
        if len(self.sessions) > self.MAX_SESSIONS:
            sorted_sessions = sorted(self._session_last_active.items(), key=lambda x: x[1])
            overflow = len(self.sessions) - self.MAX_SESSIONS
            for sid, _ in sorted_sessions[:overflow]:
                self.sessions.pop(sid, None)
                self._session_last_active.pop(sid, None)

    def _touch_session(self, session_id: str) -> None:
        """记录会话活跃时间并触发清理。"""
        import time
        self._session_last_active[session_id] = time.time()
        # 每 10 次访问做一次过期清理（摊销开销）
        if len(self.sessions) % 10 == 0:
            self._evict_expired()

    def chat(self, message: str, session_id: str | None = None) -> dict:
        """
        一次对话轮次。

        Args:
            message: 用户输入
            session_id: 会话ID（None 则创建新会话）

        Returns:
            {reply, tool_calls_made, session_id, usage}
        """
        # 创建/恢复会话
        if not session_id or session_id not in self.sessions:
            session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
            self.sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

        self._touch_session(session_id)
        messages = self.sessions[session_id]
        messages.append({"role": "user", "content": message})

        tool_calls_made: list[dict] = []

        # 第一轮 DeepSeek 调用
        result = _call_deepseek(messages, tools=ORCHESTRATOR_TOOLS)

        # Function Calling 回环（最多 3 轮）
        fc_loop = 0
        while result.get("tool_calls") and fc_loop < 3:
            fc_loop += 1

            # 保存 assistant 消息
            assistant_msg = {
                "role": "assistant",
                "content": result.get("content", ""),
                "tool_calls": result["tool_calls"],
            }
            messages.append(assistant_msg)

            # 执行每个工具
            for tc in result["tool_calls"]:
                func_name = tc.get("function", {}).get("name", "")
                try:
                    func_args = json.loads(tc.get("function", {}).get("arguments", "{}"))
                except json.JSONDecodeError:
                    func_args = {}

                tool_result = execute_tool(func_name, func_args)

                tool_calls_made.append({
                    "tool": func_name,
                    "arguments": func_args,
                    "result_summary": _summarize_result(func_name, tool_result),
                    "result": tool_result,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

            # 工具结果送回模型
            result = _call_deepseek(messages, tools=ORCHESTRATOR_TOOLS)

        # 最终回复
        reply = result.get("content", "") or "抱歉，我暂时无法回答这个问题。"
        messages.append({"role": "assistant", "content": reply})

        # 裁剪历史（system + 最近 20 轮）
        if len(messages) > 42:
            self.sessions[session_id] = [messages[0]] + messages[-40:]

        return {
            "reply": reply,
            "tool_calls_made": tool_calls_made,
            "session_id": session_id,
            "usage": result.get("usage", {}),
        }

    def chat_stream(self, message: str, session_id: str | None = None) -> Generator[str, None, dict]:
        """流式对话 — 真正的实时流式编排，含工具调用进度反馈。

        SSE 事件类型:
        - text:       逐字输出最终 AI 回复
        - tool_call:  工具调用开始（前端显示 loading badge）
        - tool_result:工具调用完成（前端更新 badge 状态）
        - done:       对话结束（含 session_id / tool_calls_made / usage）
        - error:      异常信息
        """
        # 创建/恢复会话（逻辑复用 chat() 的开头部分）
        if not session_id or session_id not in self.sessions:
            session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
            self.sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

        self._touch_session(session_id)
        messages = self.sessions[session_id]
        messages.append({"role": "user", "content": message})

        tool_calls_made: list[dict] = []
        usage = {}

        # 第一轮: 流式调用 DeepSeek
        stream = _call_deepseek_stream(messages, tools=ORCHESTRATOR_TOOLS)
        result = _collect_stream(stream)

        # Function Calling 回环（最多 3 轮）
        fc_loop = 0
        while result.get("tool_calls") and fc_loop < 3:
            fc_loop += 1

            # 保存 assistant 消息
            messages.append({
                "role": "assistant",
                "content": result.get("content", ""),
                "tool_calls": result["tool_calls"],
            })

            # 执行每个工具，发送 tool_call / tool_result 事件
            for tc in result["tool_calls"]:
                func_name = tc.get("function", {}).get("name", "")
                try:
                    func_args = json.loads(tc.get("function", {}).get("arguments", "{}"))
                except json.JSONDecodeError:
                    func_args = {}

                # yield tool_call — 前端显示 "🔧 工具名 ⏳"
                yield f"event: tool_call\ndata: {json.dumps({'tool': func_name}, ensure_ascii=False)}\n\n"

                tool_result = execute_tool(func_name, func_args)
                summary = _summarize_result(func_name, tool_result)

                tool_calls_made.append({
                    "tool": func_name,
                    "arguments": func_args,
                    "result_summary": summary,
                    "result": tool_result,
                })

                # yield tool_result — 前端更新 badge + 自动入库媒体资源
                result_data: dict = {
                    "tool": func_name,
                    "summary": summary,
                }
                # 传递媒体 URL 给前端（用于自动入库和图片渲染）
                if func_name == "generate_image" and tool_result.get("ok"):
                    result_data["image_url"] = tool_result.get("image_url", "")
                    result_data["prompt"] = func_args.get("prompt", "")
                elif func_name == "generate_video" and tool_result.get("ok"):
                    result_data["video_url"] = tool_result.get("video_url", "")
                    result_data["task_id"] = tool_result.get("task_id", "")
                    result_data["prompt"] = func_args.get("prompt", "")
                elif func_name == "query_video_status" and tool_result.get("ok"):
                    result_data["video_url"] = tool_result.get("video_url", "")
                    result_data["task_id"] = tool_result.get("task_id", "")
                    result_data["prompt"] = tool_result.get("message", "")
                elif func_name == "generate_tts" and tool_result.get("ok"):
                    result_data["audio_url"] = tool_result.get("audio_url", "")
                    result_data["duration"] = tool_result.get("duration", 0)
                    result_data["audio_download_url"] = f"http://127.0.0.1:8000{tool_result.get('audio_url', '')}" if tool_result.get("audio_url") else ""
                yield f"event: tool_result\ndata: {json.dumps(result_data, ensure_ascii=False)}\n\n"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

            # 工具结果送回模型（流式）
            stream = _call_deepseek_stream(messages, tools=ORCHESTRATOR_TOOLS)
            result = _collect_stream(stream)

        # 若循环结束仍无文字内容（模型持续调工具触达上限或被截断），
        # 补发一次不带工具的请求，强制基于已有工具结果给出总结
        if not result.get("content", "").strip() and tool_calls_made:
            try:
                result = _collect_stream(_call_deepseek_stream(messages, tools=None))
            except Exception:
                pass

        # 最终回复
        reply = result.get("content", "") or "抱歉，我暂时无法回答这个问题。"
        usage = result.get("usage", {})
        messages.append({"role": "assistant", "content": reply})

        # 裁剪历史（system + 最近 20 轮）
        if len(messages) > 42:
            self.sessions[session_id] = [messages[0]] + messages[-40:]

        # 逐字符流式输出最终文本
        for ch in reply:
            yield f"event: text\ndata: {json.dumps({'content': ch}, ensure_ascii=False)}\n\n"

        # 完成事件
        yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'tool_calls_made': len(tool_calls_made), 'usage': usage}, ensure_ascii=False)}\n\n"

        return {"reply": reply, "tool_calls_made": tool_calls_made, "session_id": session_id, "usage": usage}

    def get_sessions(self) -> list[dict]:
        """列出活跃会话"""
        sessions = []
        for sid, msgs in list(self.sessions.items())[:20]:
            preview = ""
            for m in reversed(msgs):
                if m["role"] == "user":
                    preview = m["content"][:50]
                    break
            sessions.append({
                "session_id": sid,
                "message_count": len(msgs),
                "preview": preview or "新会话",
            })
        return sessions

    def get_session(self, session_id: str) -> list[dict] | None:
        """获取会话消息历史（不含 system prompt）"""
        msgs = self.sessions.get(session_id)
        if msgs is None:
            return None
        return [m for m in msgs if m["role"] != "system"]


# ══════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════

def _summarize_result(tool_name: str, result: dict) -> str:
    """生成工具结果摘要"""
    ok = result.get("ok", False)
    if not ok:
        return f"❌ {result.get('error', '失败')}"

    summarizers = {
        "create_content": lambda r: f"✅ 生成 {r.get('schemes_count', 0)} 套方案",
        "generate_image": lambda r: f"✅ 图片已生成: {r.get('image_url', '')}",
        "generate_video": lambda r: f"✅ 视频{'已生成' if r.get('video_url') else '任务已提交: ' + r.get('task_id', '')}",
        "query_video_status": lambda r: f"✅ 视频已生成: {r.get('video_url', '')}" if r.get("video_url") else f"⏳ {r.get('message', '处理中')}",
        "generate_tts": lambda r: f"✅ {r.get('message', 'TTS 成功')}",
        "web_search": lambda r: f"✅ 搜索到 {len(r.get('results', []))} 条结果",
        "knowledge_search": lambda r: f"✅ 知识库检索完成",
        "sensitive_word_filter": lambda r: f"✅ 风险等级: {r.get('risk_level', 'unknown')}",
        "analyze_material": lambda r: f"✅ 分析完成" if r.get("success") else f"❌ {r.get('error', '')}",
        "concat_video": lambda r: f"✅ 视频拼接完成: {r.get('video_count', 0)} 段视频已合并" if r.get("ok") else f"❌ {r.get('error', '')}",
    }

    fn = summarizers.get(tool_name, lambda r: "✅ 完成")
    return fn(result)


# ── 全局单例 ──
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
