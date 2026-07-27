"""
AI 数字媒体创作助手 — Provider 适配层
支持 Mock / Coze / Dify / DeepSeek 四种后端，统一接口。
来源：Day12 app.py Provider 层 + Day13 deepseek_client.py
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Callable

import requests


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def text_from_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Mock Provider — 本地模拟，离线可用
# 来源：Day12 app.py L196-326
# ---------------------------------------------------------------------------
def mock_provider(prompt: str) -> dict[str, Any]:
    """本地模拟 Agent，不依赖网络，用于先跑通系统。"""
    time.sleep(1.2)

    # 根据 prompt 前缀匹配返回内容
    if any(kw in prompt for kw in ["短视频", "抖音", "小红书", "B站", "脚本创作", "文案生成"]):
        answer = (
            "【短视频脚本 — 3个候选方案】\n\n"
            "## 版本 A：干货科普型\n"
            "**标题**: 3个秋季护肤误区，你中了几个？\n"
            "**开头钩子(0-3s)**: 你每天都在做的护肤步骤，可能正在毁掉你的皮肤。\n"
            "**脚本结构**:\n"
            "| 时间 | 类型 | 内容 |\n"
            "|------|------|------|\n"
            "| 0-3s | 钩子 | 特写脸部+大字标题 |\n"
            "| 3-15s | 问题指出 | 误区1：过度清洁 → 皮肤屏障受损 |\n"
            "| 15-27s | 问题指出 | 误区2：天天敷面膜 → 水合过度 |\n"
            "| 27-35s | 问题指出 | 误区3：不涂防晒 → 光老化 |\n"
            "| 35-50s | 正确方法 | 逐一给出正确替代方案 |\n"
            "| 50-55s | 结尾 | 总结+引导关注 |\n"
            "**标签**: #护肤误区 #秋季护肤 #干货分享\n"
            "**封面文案**: 停止！这些护肤习惯正在毁容\n\n"
            "## 版本 B：故事代入型\n"
            "**标题**: 我花了3年才明白，护肤品不是越贵越好\n"
            "**开头钩子(0-3s)**: 三年前我的脸烂到不敢出门...\n"
            "**脚本结构**:\n"
            "| 时间 | 类型 | 内容 |\n"
            "|------|------|------|\n"
            "| 0-5s | 钩子 | 前后对比图+「3年前 vs 现在」|\n"
            "| 5-20s | 故事 | 自述踩坑经历 |\n"
            "| 20-40s | 干货 | 分享正确护肤步骤 |\n"
            "| 40-50s | 结果 | 展示现在皮肤状态 |\n"
            "| 50-55s | 结尾 | 总结金句+引导互动 |\n"
            "**标签**: #护肤血泪史 #敏感肌 #精简护肤\n"
            "**封面文案**: 从烂脸到好皮肤，我只做对了一件事\n\n"
            "## 版本 C：挑战/测评型\n"
            "**标题**: 挑战7天只用5样护肤品，皮肤会发生什么？\n"
            "**开头钩子(0-3s)**: 这一桌加起来不到200块...\n"
            "**脚本结构**: 7天分阶段记录，每天30s精华\n"
            "**标签**: #护肤挑战 #平价护肤 #7天打卡\n"
            "**封面文案**: 200块搞定全套护肤？7天实测\n\n"
            "## 推荐\n"
            "**推荐方案: B（故事代入型）**\n"
            "**理由**: B方案开头钩子力度最强（前后对比视觉冲击），故事线适合平台算法推荐，"
            "干货+情感双重驱动，预期完播率最高。"
        )
    elif any(kw in prompt for kw in ["分镜", "动画", "剧情", "故事板"]):
        answer = (
            "【分镜脚本表】\n\n"
            "**整体节奏**: 开头氛围建立(20%)→发展探索(30%)→高潮冲突(30%)→结尾留白(20%)\n"
            "**转场方式**: 硬切为主，关键转折处使用淡入淡出\n\n"
            "| 镜号 | 景别 | 画面描述 | 运镜 | 时长 | 对白/旁白 | 音效 |\n"
            "|------|------|---------|------|------|----------|------|\n"
            "| 01 | 远景 | 废墟城市全景，夕阳逆光，尘埃漂浮 | 缓慢右摇 | 5s | (无) | 风声+低频嗡鸣 |\n"
            "| 02 | 中景 | 主角从画面右侧走入，影子拉长 | 固定→微推 | 3s | 脚步声由远及近 | 碎石踩踏声 |\n"
            "| 03 | 近景 | 主角停下，转头看向左侧废墟 | 跟拍转固定 | 2s | (无) | 风声渐强 |\n"
            "| 04 | POV | 主角视角：废墟深处有微弱橙光闪烁 | 缓慢推近 | 4s | (无) | 心跳声渐强 |\n"
            "| 05 | 中景 | 主角走向光源，手按在武器上 | 侧跟拍 | 3s | (无) | 金属摩擦声 |\n"
            "| 06 | 特写 | 一盏漂浮在半空的古铜色提灯 | 慢推+微升 | 5s | (无) | 火焰噼啪声+低语呢喃 |\n"
            "| 07 | 大特写 | 主角伸出手，指尖即将触碰灯体 | 极慢推 | 3s | (无) | 心跳+嗡鸣crescendo |\n"
            "| 08 | 全景 | 触碰瞬间，周围废墟开始发光变形 | 快速后拉+旋转 | 5s | (无) | 巨大共鸣声→骤然寂静 |\n\n"
            "**关键帧时间点**: 0s(全景建立) / 3s(角色入场) / 8s(POV视角) / 14s(触碰高潮)\n"
            "**情绪曲线**: 低(好奇)→中(探索)→高(发现)→极高(触碰)→留白(余韵)"
        )
    elif any(kw in prompt for kw in ["封面", "宣传", "海报", "概念图"]):
        answer = (
            "【AI 封面/宣传图提示词】\n\n"
            "## 版本 A：大气氛围型\n"
            "**Prompt**: 一位白色狐兽战士站在冰原废墟之巅，"
            "银色毛发在月光下泛微光，双持冰晶短刀，深蓝斗篷迎风飘扬。"
            "远处极光如绿色绸带在夜空中流淌，巨大冰柱如水晶般矗立。"
            "画面下方三分之一处留白，适合叠加标题文字。"
            "写实风格，电影级光影，冷蓝主色调，The Last of Us废墟感，"
            "动物角色，护目镜反射极光。\n"
            "**风格参考**: 电影海报 / 16:9 / 冷色调\n"
            "**适合平台**: B站封面（16:9横版）\n\n"
            "## 版本 B：对比冲突型\n"
            "**Prompt**: 画面二分割构图。左侧：白狐兽军战士，青绿色护目镜，"
            "黑色规整战术装备，篝火暖光照亮半张脸。"
            "右侧：白狐叛军突击手，红色护目镜，灰色模块化武装，"
            "雪夜冷光映照另半张脸。中间一柄断裂的制式步枪。"
            "写实动物毛发质感，电影海报构图，冷暖对比强烈。\n"
            "**风格参考**: 角色海报 / 1:1 / 冷暖对比\n"
            "**适合平台**: 小红书/公众号（1:1方形）\n\n"
            "## 版本 C：行动瞬间型\n"
            "**Prompt**: 动态抓拍，白狐兽军战士从冰崖跃下，"
            "双刀在空中划出冰晶轨迹，斗篷如翅膀般展开。"
            "仰角拍摄，天空为极光覆盖的星空背景，"
            "画面充满动感和张力。游戏宣传图风格，"
            "Motion blur效果，冰晶碎片飞溅。\n"
            "**风格参考**: 动作海报 / 9:16 / 高动感\n"
            "**适合平台**: 抖音（9:16竖版）\n\n"
            "## 推荐\n"
            "推荐版本 A 作为主封面（视觉冲击力最强，留白适合标题），"
            "版本 C 作为视频缩略图（动感强，点击率高）。"
        )
    elif any(kw in prompt for kw in ["热点", "趋势", "选题"]):
        answer = (
            "【热点趋势分析报告】\n\n"
            "## 本周热门选题方向\n\n"
            "### 1. AI工具实测系列 🔥🔥🔥🔥🔥\n"
            "- **热度**: 持续上升，小红书 #AI工具 话题 2.3亿浏览\n"
            "- **受众**: 25-35岁职场人群、学生\n"
            "- **角度建议**: \n"
            "  - A: 「用了30个AI工具后，我只推荐这5个」(测评型)\n"
            "  - B: 「AI生成短视频脚本，效果居然比我自己写的好？」(对比型)\n"
            "  - C: 「月薪3000的剪辑师 vs AI剪辑」(话题型)\n"
            "- **适合平台**: 抖音/B站(长测评) + 小红书(图文精华版)\n\n"
            "### 2. 沉浸式体验 🏠\n"
            "- **热度**: 抖音 #沉浸式 话题播放量超150亿\n"
            "- **受众**: 全年龄段\n"
            "- **角度建议**:\n"
            "  - A: 「凌晨4点的图书馆，有一种说不出的浪漫」(氛围型)\n"
            "  - B: 「沉浸式备赛24小时」(挑战型)\n\n"
            "### 3. 数字媒体人日常 🎬\n"
            "- **热度**: B站 #数媒专业 搜索量增长200%\n"
            "- **受众**: 数字媒体专业学生、从业者\n"
            "- **角度建议**:\n"
            "  - A: 「数媒专业的一天——从早八到凌晨」(vlog型)\n"
            "  - B: 「数媒人必备的10个工具」(干货型)\n"
        )
    else:
        answer = (
            "【AI 创作助手 · Mock 模式】\n\n"
            f"已收到您的创作需求：{prompt[:200]}\n\n"
            "## 生成方案\n"
            "此为 Mock 模式的模拟输出。接入真实 Coze/Dify/DeepSeek 后，"
            "这里会替换成平台返回的实际内容。Mock 模式保证离线可用，"
            "适合开发调试和演示。\n\n"
            "## 建议\n"
            "- 切换到 Coze/Dify/DeepSeek Provider 获取真实 AI 生成内容\n"
            "- 当前 Mock 返回的结构化格式与实际 Agent 输出格式一致"
        )

    return {
        "ok": True,
        "answer": answer,
        "run_id": f"mock-run-{uuid.uuid4().hex[:8]}",
        "raw": {"provider": "mock"},
    }


# ---------------------------------------------------------------------------
# Coze Provider — 字节跳动扣子平台（题目3主平台）
# 支持按 Agent 名称自动路由到对应的 Bot
# 来源：Day12 app.py L329-364 + P4 多 Agent 路由
# ---------------------------------------------------------------------------
def coze_provider(prompt: str, config: dict, agent_name: str = "script") -> dict[str, Any]:
    """调用 Coze Bot API，自动根据 agent_name 选择对应 Bot。"""
    token = str(config.get("token", "")).strip()
    bot_ids: dict = config.get("bot_ids", {})
    bot_id = str(bot_ids.get(agent_name, bot_ids.get("_default", ""))).strip()

    if not token:
        raise ValueError("Coze 配置不完整，请填写 token")
    if not bot_id:
        raise ValueError(
            f"Coze 未配置 Agent '{agent_name}' 的 bot_id，"
            f"请在 providers.json 的 coze.bot_ids 中填入该 Agent 对应的 Bot ID。"
            f"当前已配置: {list(bot_ids.keys())}"
        )

    response = requests.post(
        config.get("base_url", "https://api.coze.cn/open_api/v2/chat"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "bot_id": bot_id,
            "user": config.get("user", "p4-agent"),
            "query": prompt,
            "stream": False,
        },
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(
            f"Coze 请求失败（Agent={agent_name} Bot={bot_id}）："
            f"HTTP {response.status_code} {response.text[:300]}"
        )

    data = response.json()
    # Coze v2/v3 API — 提取 assistant 中 type=answer 的 content
    messages = data.get("messages", [])
    answers = []

    if messages:
        for m in messages:
            if m.get("role") in {None, "assistant"}:
                msg_type = m.get("type", "")
                content = m.get("content", "")
                # 优先取 type=answer，取 type=verbose
                if msg_type == "answer" and content:
                    answers.append(text_from_value(content))
                elif msg_type != "answer" and content:
                    # verbose 消息作为备选（可能含 tool_call、knowledge_recall 等）
                    pass

    # fallback: 直接取 content/answer 字段
    if not answers:
        content = data.get("content", "") or data.get("answer", "")
        if content:
            answers.append(text_from_value(content))

    return {
        "ok": True,
        "answer": "\n\n".join(answers) or "Coze 没有返回可展示的消息。",
        "run_id": str(data.get("conversation_id", data.get("id", ""))),
        "raw": data,
    }


# ---------------------------------------------------------------------------
# Dify Provider — 自托管工作流平台
# 来源：Day12 app.py L367-481
# ---------------------------------------------------------------------------
def dify_provider(prompt: str, config: dict, on_chunk: Callable | None = None) -> dict[str, Any]:
    api_key = str(config.get("api_key", "")).strip()
    if not api_key:
        raise ValueError("Dify 配置不完整，请填写 api_key")

    base_url = str(config.get("base_url", "https://api.dify.ai/v1")).rstrip("/")
    mode = str(config.get("mode", "chat")).lower()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    streaming = on_chunk is not None

    if mode == "chat":
        url = f"{base_url}/chat-messages"
        payload: dict[str, Any] = {
            "inputs": {"creative_brief": prompt, "content_type": "自动判断"},
            "query": prompt,
            "response_mode": "streaming" if streaming else "blocking",
            "user": config.get("user", "day12-user"),
        }
    else:
        url = f"{base_url}/workflows/run"
        payload = {
            "inputs": {"creative_brief": prompt, "content_type": "自动判断"},
            "response_mode": "streaming" if streaming else "blocking",
            "user": config.get("user", "day12-user"),
        }

    timeout = 300 if streaming else 120
    response = requests.post(url, headers=headers, json=payload, timeout=timeout, stream=streaming)
    if not response.ok:
        raise RuntimeError(f"Dify 请求失败：HTTP {response.status_code} {response.text[:300]}")

    if not streaming:
        data = response.json()
        if mode == "chat":
            return {
                "ok": True,
                "answer": text_from_value(data.get("answer", "")) or "Dify 没有返回可展示的结果。",
                "run_id": str(data.get("conversation_id", "")),
                "raw": data,
            }
        result_data = data.get("data", {})
        outputs = result_data.get("outputs", {})
        return {
            "ok": True,
            "answer": text_from_value(outputs.get("text") or outputs.get("answer") or outputs),
            "run_id": str(result_data.get("id", "")),
            "raw": data,
        }

    # streaming 模式：逐行解析 SSE
    answer_parts: list[str] = []
    run_id = ""
    last_raw: dict[str, Any] = {}

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        json_str = line[5:].strip()
        if not json_str:
            continue
        try:
            event = json.loads(json_str)
        except json.JSONDecodeError:
            continue

        last_raw = event
        run_id = event.get("conversation_id") or event.get("task_id") or run_id
        event_type = event.get("event", "")

        if event_type in ("message", "agent_message"):
            answer_parts.append(event.get("answer", ""))
            on_chunk("".join(answer_parts))
        elif event_type == "message_end":
            full = event.get("answer", "")
            if full:
                answer_parts = [full]
                on_chunk(full)
        elif event_type == "workflow_finished":
            outputs = event.get("data", {}).get("outputs", {})
            full = outputs.get("text") or outputs.get("answer") or ""
            if full:
                answer_parts = [full]
                on_chunk(full)
        elif event_type == "error":
            raise RuntimeError(f"Dify 流式错误：{event.get('message', event.get('code', 'unknown'))}")

    full_answer = "".join(answer_parts)
    return {
        "ok": True,
        "answer": text_from_value(full_answer) or "Dify 没有返回可展示的结果。",
        "run_id": str(run_id),
        "raw": last_raw,
    }


# ---------------------------------------------------------------------------
# DeepSeek Provider — OpenAI 兼容接口直连
# 来源：Day13 deepseek_client.py
# ---------------------------------------------------------------------------
def deepseek_provider(prompt: str, config: dict, tools: list[dict] | None = None,
                      messages_override: list[dict] | None = None) -> dict[str, Any]:
    api_key = str(config.get("api_key", "")).strip()
    if not api_key:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("DeepSeek 配置不完整，请填写 api_key 或设置 DEEPSEEK_API_KEY 环境变量")

    base_url = str(config.get("base_url", "https://api.deepseek.com/v1")).rstrip("/")
    model = str(config.get("model", "deepseek-chat"))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if messages_override:
        messages = messages_override
    else:
        messages: list[dict] = [
            {"role": "system", "content": config.get("system_prompt", "你是一名专业的数字媒体创作助手。")},
            {"role": "user", "content": prompt},
        ]

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": float(config.get("temperature", 0.7)),
        "max_tokens": int(config.get("max_tokens", 4096)),
        "stream": False,
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=120)
    if not response.ok:
        raise RuntimeError(f"DeepSeek 请求失败：HTTP {response.status_code} {response.text[:300]}")

    data = response.json()
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})

    # 推理模型内容在 reasoning_content 中
    content = message.get("content", "") or message.get("reasoning_content", "")

    # 处理 Function Calling 返回
    if message.get("tool_calls"):
        return {
            "ok": True,
            "answer": text_from_value(content),
            "tool_calls": message["tool_calls"],
            "run_id": data.get("id", ""),
            "raw": data,
        }

    # 推理模型（如 deepseek-v4-pro）内容在 reasoning_content 中
    content = message.get("content", "") or message.get("reasoning_content", "")
    return {
        "ok": True,
        "answer": text_from_value(content) or "DeepSeek 没有返回内容。",
        "run_id": data.get("id", ""),
        "raw": data,
    }


# ---------------------------------------------------------------------------
# 统一调度
# ---------------------------------------------------------------------------
def run_provider(
    provider: str, prompt: str, config: dict | None = None,
    on_chunk: Callable | None = None, tools: list[dict] | None = None,
    messages_override: list[dict] | None = None,
    agent_name: str = "script",
) -> dict[str, Any]:
    """统一的 Provider 调度入口。agent_name 用于 Coze 多 Bot 路由。"""
    cfg = config or {}
    provider = provider.lower().strip()

    if provider == "mock":
        return mock_provider(prompt)
    elif provider == "coze":
        return coze_provider(prompt, cfg.get("coze", {}), agent_name=agent_name)
    elif provider == "dify":
        return dify_provider(prompt, cfg.get("dify", {}), on_chunk=on_chunk)
    elif provider == "deepseek":
        return deepseek_provider(prompt, cfg.get("deepseek", {}), tools=tools, messages_override=messages_override)
    else:
        raise ValueError(f"不支持的 Provider: {provider}，可选: mock / coze / dify / deepseek")
