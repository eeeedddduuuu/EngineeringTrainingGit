"""
Agent 模块 — 4 个 Agent 的统一接口
每个 Agent 封装了：Prompt 加载、工具选择、Provider 调用、结果解析
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

from providers import run_provider
from tools import TOOL_DEFINITIONS, execute_tool

CST = timezone(timedelta(hours=8))
AGENTS_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = AGENTS_DIR.parent / "prompts"


def _load_prompt(agent_name: str, version: str = "v1") -> dict[str, Any]:
    """加载 YAML Prompt 模板。"""
    prompt_file = PROMPTS_DIR / f"{agent_name}_{version}.yaml"
    if prompt_file.exists():
        with open(prompt_file, encoding="utf-8") as f:
            return yaml.safe_load(f)
    # 回退：查找任意版本的该 Agent prompt
    candidates = list(PROMPTS_DIR.glob(f"{agent_name}_*.yaml"))
    if candidates:
        with open(candidates[0], encoding="utf-8") as f:
            return yaml.safe_load(f)
    raise FileNotFoundError(f"找不到 Agent '{agent_name}' 的 Prompt 文件，已搜索: {prompt_file}")


def _now_text() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def _build_system_prompt(prompt_config: dict, extra_context: dict | None = None) -> str:
    """从 YAML 配置构建完整 system prompt。"""
    base = prompt_config.get("system_prompt", "")
    if extra_context:
        lines = [base, "\n## 额外上下文"]
        for k, v in extra_context.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)
    return base


def run_agent(
    agent_name: str,
    user_input: str,
    provider: str = "mock",
    provider_config: dict | None = None,
    extra_context: dict | None = None,
    on_chunk=None,
) -> dict[str, Any]:
    """
    统一的 Agent 运行接口。

    Args:
        agent_name: Agent 名称 (trend / script / review / publish)
        user_input: 用户输入
        provider: Provider 名称 (mock / coze / dify / deepseek)
        provider_config: Provider 配置
        extra_context: 额外上下文（如前置 Agent 的输出）
        on_chunk: 流式回调函数

    Returns:
        {
            "ok": bool,
            "agent_name": str,
            "answer": str,
            "run_id": str,
            "tools_called": list,
            "latency_ms": int,
            "tokens_used": int,  # 仅 DeepSeek
            "created_at": str,
        }
    """
    start_time = datetime.now(CST)

    # 1. 加载 Prompt
    prompt_config = _load_prompt(agent_name)
    system_prompt = _build_system_prompt(prompt_config, extra_context)

    # 2. 构建完整输入
    full_prompt = f"{system_prompt}\n\n用户输入：{user_input}"

    # 3. 选择需要的工具
    tool_names = prompt_config.get("tools_required", [])
    tools = [t for t in TOOL_DEFINITIONS if t["function"]["name"] in tool_names] if tool_names else None

    # 4. 调用 Provider
    result = run_provider(provider, full_prompt, provider_config, on_chunk=on_chunk, tools=tools)

    # 5. 处理 Function Calling（DeepSeek 专有）
    tools_called: list[dict] = []
    if result.get("tool_calls"):
        for tc in result["tool_calls"]:
            func_name = tc.get("function", {}).get("name", "")
            func_args = json.loads(tc.get("function", {}).get("arguments", "{}"))
            tool_result = execute_tool(func_name, func_args)
            tools_called.append({
                "tool": func_name,
                "arguments": func_args,
                "result": tool_result,
            })

    # 6. 计算耗时
    end_time = datetime.now(CST)
    latency_ms = int((end_time - start_time).total_seconds() * 1000)

    return {
        "ok": result.get("ok", False),
        "agent_name": agent_name,
        "prompt_version": prompt_config.get("version", "unknown"),
        "provider": provider,
        "answer": result.get("answer", ""),
        "run_id": result.get("run_id", f"agent-run-{uuid.uuid4().hex[:8]}"),
        "tools_called": tools_called,
        "latency_ms": latency_ms,
        "tokens_used": result.get("raw", {}).get("usage", {}).get("total_tokens", 0),
        "created_at": _now_text(),
        "raw": result.get("raw", {}),
    }


def run_agent_pipeline(
    user_input: str,
    provider: str = "mock",
    provider_config: dict | None = None,
    enable_trend: bool = True,
    enable_review: bool = True,
    enable_publish: bool = True,
) -> dict[str, Any]:
    """
    运行完整的 Agent 流水线：热点分析 → 脚本创作 → 合规审查 → 发布策略。

    返回每个 Agent 的结果和整体评分。
    """
    pipeline_id = f"pipeline-{uuid.uuid4().hex[:8]}"
    results: dict[str, Any] = {
        "pipeline_id": pipeline_id,
        "created_at": _now_text(),
        "provider": provider,
        "agents": {},
    }

    # Agent 1: 热点分析（可选）
    trend_result = None
    if enable_trend:
        trend_result = run_agent("trend", user_input, provider, provider_config)
        results["agents"]["trend"] = trend_result

    # Agent 2: 脚本创作（核心，必跑）
    script_context = {}
    if trend_result and trend_result.get("ok"):
        script_context["热点分析结果"] = trend_result.get("answer", "")[:1000]
    script_result = run_agent("script", user_input, provider, provider_config, extra_context=script_context)
    results["agents"]["script"] = script_result

    # Agent 3: 合规审查（可选）
    if enable_review and script_result.get("ok"):
        review_result = run_agent(
            "review",
            f"请审查以下内容：\n{script_result['answer'][:2000]}",
            provider, provider_config,
        )
        results["agents"]["review"] = review_result

    # Agent 4: 发布策略（可选）
    if enable_publish and script_result.get("ok"):
        publish_result = run_agent(
            "publish",
            f"内容：{script_result['answer'][:1500]}\n用户原始需求：{user_input}",
            provider, provider_config,
        )
        results["agents"]["publish"] = publish_result

    return results
