"""
Agent 工具集 — 不少于 5 个工具
来源：Day13 tools.py + Day11 敏感词过滤 + Day12 templates.json
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# 工具定义（Function Calling 格式）
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索公开网页或直接读取指定URL的内容。用于获取最新热点、趋势数据、竞品分析等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或网页URL",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最多返回几条结果，范围1-8",
                        "minimum": 1,
                        "maximum": 8,
                    },
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
                    "query": {
                        "type": "string",
                        "description": "要在知识库中检索的关键词或问题",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "最多返回几段相关内容，范围1-8",
                        "minimum": 1,
                        "maximum": 8,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sensitive_word_filter",
            "description": "检查生成内容是否包含敏感词、隐私信息或违规内容，返回风险等级(pass/review/block)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "需要审查的文本内容",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "template_matcher",
            "description": "根据目标平台、内容类型和时长，匹配最合适的创作模板结构。",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "目标发布平台：抖音/小红书/B站/公众号/微博",
                    },
                    "content_type": {
                        "type": "string",
                        "description": "内容类型：短视频/图文/长文/分镜脚本",
                    },
                    "duration": {
                        "type": "string",
                        "description": "预计时长，如 30s/60s/3min",
                    },
                },
                "required": ["platform", "content_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "查询指定城市的当前时间，用于判断发布时机。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "城市名，如：北京、上海、东京",
                    },
                },
                "required": [],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# 工具实现
# ---------------------------------------------------------------------------

TIMEZONE_ALIASES = {
    "北京": "Asia/Shanghai", "上海": "Asia/Shanghai", "中国": "Asia/Shanghai",
    "东京": "Asia/Tokyo", "伦敦": "Europe/London", "纽约": "America/New_York",
    "洛杉矶": "America/Los_Angeles", "巴黎": "Europe/Paris", "UTC": "UTC",
}

URL_PATTERN = re.compile(r"https?://[^\s<>　]+", re.IGNORECASE)

# 平台创作模板 — 来源：Day12 templates.json + 扩展
PLATFORM_TEMPLATES: dict[str, dict[str, Any]] = {
    "抖音": {
        "max_duration": 60,
        "formats": {
            "短视频": "开头钩子(0-3s)→问题/亮点(3-25s)→干货/展开(25-50s)→结尾引导(50-60s)",
            "分镜脚本": "镜号/景别/画面描述/运镜/时长/对白/音效，每镜3-8s，共8-15个镜头",
        },
        "style_keywords": "快节奏、强钩子、口语化、热点标签、BGM卡点",
    },
    "小红书": {
        "max_duration": 300,
        "formats": {
            "图文": "封面标题→痛点引入→解决方案(1.2.3.)→产品推荐→互动引导",
            "短视频": "封面3s→正片→总结→评论区引导",
        },
        "style_keywords": "精致排版、emoji标题、真实体验、干货清单、种草语气",
    },
    "B站": {
        "max_duration": 1200,
        "formats": {
            "短视频": "片头(5s)→引入(30s)→正片→结尾求三连(10s)",
            "分镜脚本": "镜号/景别/画面描述/运镜/时长/对白/音效，每镜5-15s，共10-20个镜头",
        },
        "style_keywords": "内容密度高、弹幕梗、片头要炸、节奏有起伏、适当玩梗",
    },
}


def clean_text(value: str) -> str:
    lines: list[str] = []
    for line in value.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line and (not lines or line != lines[-1]):
            lines.append(line)
    return "\n".join(lines)


def extract_url(value: str) -> str | None:
    match = URL_PATTERN.search(value)
    if not match:
        return None
    candidate = match.group(0)
    candidate = re.split(r"[一-鿿，。！？；：]", candidate, maxsplit=1)[0]
    return candidate.rstrip(".,!?;:)]}>")


# ===== 工具1: 网页搜索 =====
def read_web_page(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("网页地址必须是完整的 http:// 或 https:// URL")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template", "nav", "footer"]):
        tag.decompose()
    title = clean_text(soup.title.get_text(" ") if soup.title else "")
    root = soup.body or soup
    content = clean_text(root.get_text("\n"))
    if not content:
        raise RuntimeError("网页打开成功，但没有提取到正文")
    return {
        "engine": "Local page reader",
        "mode": "open",
        "url": response.url,
        "title": title,
        "content": content[:16000],
        "truncated": len(content) > 16000,
    }


def bing_search(query: str, max_results: int) -> dict[str, Any]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(
        "https://www.bing.com/search",
        params={"q": query, "count": max_results, "setlang": "zh-CN"},
        headers=headers, timeout=15,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    items: list[dict[str, str]] = []
    for result in soup.select("li.b_algo")[:max_results]:
        link = result.select_one("h2 a") or result.select_one("a")
        if not link:
            continue
        snippet_node = result.select_one(".b_caption p") or result.select_one("p")
        items.append({
            "title": clean_text(link.get_text(" "))[:300],
            "url": str(link.get("href", ""))[:1000],
            "snippet": clean_text(snippet_node.get_text(" ") if snippet_node else "")[:1200],
        })
    if not items:
        raise RuntimeError(f'Bing 没有找到与"{query}"相关的公开网页')
    return {"engine": "Bing", "mode": "search", "query": query, "results": items}


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("搜索内容不能为空")
    max_results = int(max_results)
    if not 1 <= max_results <= 8:
        raise ValueError("max_results 必须在 1 到 8 之间")

    url = extract_url(query)
    if url:
        try:
            return read_web_page(url)
        except RuntimeError as exc:
            page_error = exc
            fallback_query = query.replace(url, "").strip() or url
    else:
        page_error = None
        fallback_query = query

    ddgs_error = None
    results = []
    try:
        from ddgs import DDGS  # type: ignore
        results = DDGS(timeout=15).text(fallback_query, region="cn-zh", safesearch="moderate", max_results=max_results)
    except (ImportError, Exception) as exc:
        ddgs_error = exc

    items = [
        {"title": str(item.get("title", ""))[:300], "url": str(item.get("href", item.get("url", "")))[:1000],
         "snippet": str(item.get("body", item.get("snippet", "")))[:1200]}
        for item in results or []
    ]
    if not items:
        fallback = bing_search(fallback_query, max_results)
        if ddgs_error:
            fallback["fallback_reason"] = f"DDGS 不可用：{ddgs_error}"
        if page_error:
            fallback["page_read_error"] = str(page_error)
        return fallback

    result = {"engine": "DDGS / DuckDuckGo", "mode": "search", "query": fallback_query, "results": items}
    if page_error:
        result["page_read_error"] = str(page_error)
    return result


# ===== 工具2: 知识库检索 =====
def knowledge_search(query: str, top_k: int = 5) -> dict[str, Any]:
    """调用知识库检索接口（需 P5 部署后提供端点）。"""
    query = query.strip()
    if not query:
        raise ValueError("检索关键词不能为空")
    top_k = int(top_k)
    if not 1 <= top_k <= 8:
        raise ValueError("top_k 必须在 1 到 8 之间")

    # 尝试调用 P5 部署的知识库 API
    kb_url = "http://127.0.0.1:8090/api/knowledge/search"
    try:
        response = requests.get(kb_url, params={"q": query, "top_k": top_k}, timeout=5)
        if response.ok:
            return {"ok": True, "source": "API", "results": response.json().get("results", [])}
    except requests.RequestException:
        pass

    # P5 未部署时的本地简易检索
    return {
        "ok": True,
        "source": "local_fallback",
        "query": query,
        "results": [
            {"title": "知识库服务待启动", "content": f"知识库检索接口 {kb_url} 暂不可用，请启动 P5 服务。", "score": 1.0}
        ],
        "note": "P5 知识库服务未就绪，返回占位结果",
    }


# ===== 工具3: 敏感词过滤 =====
# 来源：Day11 时事_敏感词过滤代码.py
def sensitive_word_filter(content: str) -> dict[str, Any]:
    if not content or not content.strip():
        return {"risk_level": "pass", "review_text": "输入为空，无风险。", "flagged_terms": "无"}

    # 高风险词（block级别）
    high_risk = ["国家安全", "国家秘密", "颠覆", "分裂", "暴动", "恐怖袭击"]
    # 中风险词（review级别）
    mid_risk = ["突发事件", "内部人士", "知情人士", "震惊", "紧急", "速看", "删前快看", "绝对", "100%", "保证有效"]
    # 平台敏感词
    platform_sensitive = {
        "抖音": ["未成年", "暴力", "血腥", "色情"],
        "小红书": ["医美", "金融理财", "医疗建议"],
        "B站": ["引战", "人身攻击", "政治敏感"],
    }

    risk_level = "pass"
    flagged: list[str] = []

    # 隐私信息检测
    phone_pattern = re.compile(r"1[3-9]\d{9}")
    id_pattern = re.compile(r"\d{6}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]")

    if phone_pattern.search(content):
        risk_level = "review"
        flagged.append("检测到手机号")
    if id_pattern.search(content):
        risk_level = "review"
        flagged.append("检测到身份证号")

    # 关键词检测
    for word in high_risk:
        if word in content:
            risk_level = "block"
            flagged.append(f"高风险词: {word}")

    if risk_level != "block":
        for word in mid_risk:
            if word in content:
                risk_level = "review"
                flagged.append(f"中风险词: {word}")

    if risk_level == "pass":
        review_text = "敏感词检查通过，内容安全。"
    elif risk_level == "review":
        review_text = f"需要人工复核。触发项: {', '.join(flagged)}"
    else:
        review_text = f"内容包含高风险词汇，不得直接发布。触发项: {', '.join(flagged)}"

    return {
        "risk_level": risk_level,
        "review_text": review_text,
        "flagged_terms": ", ".join(flagged) if flagged else "无",
    }


# ===== 工具4: 创作模板匹配 =====
def template_matcher(platform: str, content_type: str, duration: str = "") -> dict[str, Any]:
    platform = platform.strip()
    content_type = content_type.strip()

    pt = PLATFORM_TEMPLATES.get(platform)
    if not pt:
        return {"ok": False, "error": f"不支持的平台: {platform}，支持: {list(PLATFORM_TEMPLATES.keys())}"}

    fmt = pt["formats"].get(content_type)
    if not fmt:
        return {"ok": False, "error": f"平台 {platform} 不支持内容类型: {content_type}，支持: {list(pt['formats'].keys())}"}

    return {
        "ok": True,
        "platform": platform,
        "content_type": content_type,
        "template_structure": fmt,
        "style_keywords": pt["style_keywords"],
        "max_duration_seconds": pt["max_duration"],
        "requested_duration": duration or "未指定",
    }


# ===== 工具5: 时间查询 =====
def get_current_time(timezone: str = "Asia/Shanghai") -> dict[str, Any]:
    zone_name = TIMEZONE_ALIASES.get(timezone.strip(), timezone.strip())
    try:
        current = datetime.now(ZoneInfo(zone_name))
    except KeyError:
        raise ValueError(f"不支持的时区：{timezone}")
    return {
        "timezone": zone_name,
        "time": current.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": current.strftime("%A"),
        "hour": current.hour,
    }


# ---------------------------------------------------------------------------
# 工具调度
# ---------------------------------------------------------------------------
def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "web_search":
            return web_search(str(arguments.get("query", "")), int(arguments.get("max_results", 5)))
        if name == "knowledge_search":
            return knowledge_search(str(arguments.get("query", "")), int(arguments.get("top_k", 5)))
        if name == "sensitive_word_filter":
            return sensitive_word_filter(str(arguments.get("content", "")))
        if name == "template_matcher":
            return template_matcher(
                str(arguments.get("platform", "")),
                str(arguments.get("content_type", "")),
                str(arguments.get("duration", "")),
            )
        if name == "get_current_time":
            return get_current_time(str(arguments.get("timezone", "Asia/Shanghai")))
        raise ValueError(f"未知工具：{name}")
    except (ValueError, RuntimeError) as exc:
        return {"ok": False, "error": str(exc)}


def tool_catalog() -> list[dict[str, str]]:
    return [{"name": t["function"]["name"], "description": t["function"]["description"]} for t in TOOL_DEFINITIONS]
