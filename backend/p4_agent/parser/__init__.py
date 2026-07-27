"""
Markdown → JSON 解析器
将 Agent 输出的 Markdown 文本解析为 P3 Scheme 表的结构化字段。
同时保留原始 Markdown 供前端渲染。
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _extract(pattern: str, text: str, default: str = "") -> str:
    """从文本中用正则提取第一个捕获组（非贪婪）。"""
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else default


def _extract_all(pattern: str, text: str) -> list[str]:
    """从文本中用正则提取所有匹配。"""
    return [m.strip() for m in re.findall(pattern, text, re.MULTILINE | re.DOTALL)]


def _parse_tags(tag_text: str) -> list[str]:
    """解析标签文本 '#tag1 #tag2' → ['#tag1', '#tag2']"""
    return re.findall(r"#\S+", tag_text)


def _parse_markdown_table(table_text: str) -> list[dict[str, str]]:
    """
    解析 Markdown 表格为 scenes 列表。
    输入:
      | 时间 | 类型 | 内容 |
      |------|------|------|
      | 0-3s | 钩子 | 特写脸部+大字标题 |
      | 3-15s | 问题指出 | 误区1... |
    输出:
      [{"seq":1, "time":"0-3s", "type":"钩子", "content":"特写脸部+大字标题"}, ...]
    """
    lines = table_text.strip().split("\n")
    rows: list[dict[str, str]] = []

    # 过滤掉分隔线行（包含 --- 的行）
    data_lines = [l for l in lines if not re.match(r"^\|[\s\-:|]*\|$", l.strip())]

    if len(data_lines) < 2:
        return rows

    # 第一行是表头
    header_line = data_lines[0]
    headers = [h.strip() for h in header_line.split("|")[1:-1]]

    for idx, line in enumerate(data_lines[1:], start=1):
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= len(headers):
            row: dict[str, str] = {"seq": idx}
            for h, c in zip(headers, cells):
                # 统一列名
                key = h.lower()
                if key in ("时间", "time", "时长", "duration"):
                    row["time"] = c
                elif key in ("类型", "type", "镜头类型"):
                    row["type"] = c
                elif key in ("内容", "content", "描述", "description", "画面描述"):
                    row["content"] = c
                else:
                    row[key] = c
            rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# 单版本解析
# ---------------------------------------------------------------------------
def _parse_version_block(block: str, version: str) -> dict[str, Any]:
    """
    解析单个版本块（如 "## 版本 A：干货科普型" 到 "## 版本 B" 之间的内容）。
    返回 P3 Scheme 表对应结构。
    """
    title = _extract(r"\*\*标题\*\*[:：]\s*(.+)", block)
    hook = _extract(r"\*\*开头钩子[^)]*\)?\*\*[:：]\s*(.+)", block)
    cover_text = _extract(r"\*\*封面文案\*\*[:：]\s*(.+)", block)

    # 标签
    tag_text = _extract(r"\*\*标签\*\*[:：]\s*(.+)", block)
    hashtags = _parse_tags(tag_text)

    # 脚本结构 → scenes (解析 Markdown 表格)
    structure_start = None
    for pat in (r"\*\*脚本结构\*\*[:：]\s*", r"\*\*分镜结构\*\*[:：]\s*"):
        m = re.search(pat, block)
        if m:
            structure_start = m.end()
            break

    scenes: list[dict[str, str]] = []
    if structure_start is not None:
        rest = block[structure_start:]
        # 先尝试 Markdown 表格
        table_match = re.search(r"\|.+\|", rest)
        if table_match:
            table_start = table_match.start()
            table_lines: list[str] = []
            for line in rest[table_start:].split("\n"):
                if line.strip().startswith("|"):
                    table_lines.append(line)
                elif table_lines:
                    break
            table_text = "\n".join(table_lines)
            scenes = _parse_markdown_table(table_text)
        else:
            # 回退：解析列表格式 "0-3s 描述内容" / "0-3s 类型 描述"
            list_lines: list[str] = []
            for line in rest.split("\n"):
                stripped = line.strip()
                if not stripped or stripped.startswith("**"):
                    if list_lines: break
                    continue
                # 匹配 "0-3s ..." 或 "0-3s 类型 ..." 格式
                if re.match(r"\d+[-~]\d+s\b", stripped) or re.match(r"\d+[-~]\d+min\b", stripped):
                    list_lines.append(stripped)
                elif list_lines:
                    break
            for idx, line in enumerate(list_lines):
                # 解析 "0-3s 描述" 或 "0-3s 类型 描述"
                m = re.match(r"(\d+[-~]\d+(?:s|min))\s*(.+)$", line)
                if m:
                    duration = m.group(1)
                    rest_text = m.group(2).strip()
                    scenes.append({"seq": idx + 1, "type": "", "duration": duration, "description": rest_text, "voiceover": ""})

    return {
        "version": version,
        "title": title,
        "hook": hook,
        "scenes": scenes,
        "hashtags": hashtags,
        "cover_text": cover_text,
    }


def _parse_recommendation(text: str) -> dict[str, str]:
    """解析推荐块。"""
    best = _extract(r"\*\*推荐方案\*\*[:：]\s*(.+)", text)
    reason = _extract(r"\*\*理由\*\*[:：]\s*(.+)", text)
    return {"best_version": best, "reason": reason}


# ---------------------------------------------------------------------------
# 主解析函数
# ---------------------------------------------------------------------------
def parse_script_output(markdown_text: str) -> dict[str, Any]:
    """
    解析脚本 Agent 的 Markdown 输出。

    Args:
        markdown_text: Agent 回答全文（包含版本 A/B/C + 推荐）

    Returns:
        {
            "schemes": [
                {
                    "version": "A",
                    "title": "...",
                    "hook": "...",
                    "scenes": [{"seq":1, "time":"0-3s", "type":"钩子", "content":"..."}],
                    "hashtags": ["#tag1", "#tag2"],
                    "cover_text": "...",
                    "score": 0.0,
                    "rank": 0,
                    "recommendation_reason": "",
                },
                ...
            ],
            "recommendation": {"best_version": "B", "reason": "..."},
        }
    """
    text = markdown_text.strip()

    # 按版本标题 + 推荐标题分段
    version_blocks = re.split(r"(?:^|\n)(?=##\s*(?:版本\s*[A-Ca-c]|推荐\b))", text)

    schemes: list[dict[str, Any]] = []
    recommendation: dict[str, str] = {}

    for block in version_blocks:
        # 判断是版本块还是推荐块
        version_match = re.match(r"##\s*版本\s*([A-Ca-c])\s*[:：]?", block)
        if version_match:
            version = version_match.group(1).upper()
            schemes.append(_parse_version_block(block, version))
        elif re.match(r"##\s*推荐", block):
            recommendation = _parse_recommendation(block)

    # 二次处理：从推荐块回填 recommendation_reason 到推荐方案
    if recommendation.get("best_version"):
        best_ver = recommendation["best_version"].strip().upper()
        for s in schemes:
            if s["version"] == best_ver:
                s["recommendation_reason"] = recommendation.get("reason", "")

    # 设置默认 rank（按推荐排序，推荐的第一）
    for i, s in enumerate(schemes):
        s.setdefault("score", 5.0)
        s.setdefault("rank", i + 1)
    if recommendation.get("best_version"):
        best_ver = recommendation["best_version"].strip().upper()
        # 去掉可能的 "版本 " 前缀
        best_ver = best_ver.replace("版本", "").replace(" ", "").strip()
        for s in schemes:
            if s["version"].upper() == best_ver:
                s["rank"] = 1
                s["recommendation_reason"] = recommendation.get("reason", "")
            elif s.get("rank") == 1:
                s["rank"] = 2

    return {
        "schemes": schemes,
        "recommendation": recommendation,
    }


def parse_pipeline_result(pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """
    解析完整流水线结果，提取所有可用字段。

    Args:
        pipeline_result: run_agent_pipeline() 的返回值

    Returns:
        {
            "pipeline_id": "...",
            "agent_logs": [...],  # 可直接写入 agent_logs 表
            "schemes": [...],      # 可直接写入 schemes 表
            "recommendation": {...},
            "raw_markdown": "...", # 原始 Markdown 供前端渲染
        }
    """
    agents = pipeline_result.get("agents", {})
    script_agent = agents.get("script", {})
    script_answer = script_agent.get("answer", "") if script_agent else ""

    # 解析脚本输出
    parsed = parse_script_output(script_answer) if script_answer else {"schemes": [], "recommendation": {}}

    # 构建 agent_logs 列表
    agent_logs = []
    for name, result in agents.items():
        agent_logs.append({
            "agent_name": name,
            "input_json": {"pipeline_id": pipeline_result.get("pipeline_id", "")},
            "output_json": {
                "ok": result.get("ok"),
                "answer_preview": result.get("answer", "")[:500],
            },
            "tools_called": [tc.get("tool", "") for tc in result.get("tools_called", [])],
            "latency_ms": result.get("latency_ms", 0),
            "tokens_used": result.get("tokens_used", 0),
            "status": "success" if result.get("ok") else "failed",
        })

    return {
        "pipeline_id": pipeline_result.get("pipeline_id", ""),
        "provider": pipeline_result.get("provider", ""),
        "agent_logs": agent_logs,
        "schemes": parsed["schemes"],
        "recommendation": parsed["recommendation"],
        "raw_markdown": script_answer,
    }
