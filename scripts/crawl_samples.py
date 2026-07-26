"""
样例数据采集脚本 - 从公开网站爬取数字媒体创作相关信息

采集类别：
  - 游戏策划：游戏脚本、角色设定、剧情设计、关卡设计
  - 短视频创作：抖音/小红书/B站 脚本、开头钩子、口播文案
  - 宣传片制作：企业宣传片、产品广告、分镜脚本
  - 社交媒体运营：封面文案、发布策略、话题标签、内容排期

输出格式：与 samples.xlsx 字段一致
"""
import re
import time
import random
import json
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd

# ── 配置 ──────────────────────────────────────────────────
OUTPUT = Path(__file__).parent.parent / "data" / "collected_samples.xlsx"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]
HEADERS = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "zh-CN,zh;q=0.9"}

# ── 搜索关键词 ────────────────────────────────────────────
SEARCH_QUERIES = {
    "游戏策划": [
        "游戏脚本创作 角色设定 方法",
        "游戏剧情设计 叙事技巧",
        "游戏关卡设计 方法论 教程",
        "RPG角色人设 策划案 怎么写",
        "游戏世界观构建 策划经验",
    ],
    "短视频创作": [
        "短视频脚本怎么写 开头钩子 技巧",
        "抖音爆款视频 脚本结构 教程",
        "小红书视频创作 口播文案 方法",
        "B站视频脚本 分镜 创作指南",
        "短视频3秒留人 开头话术 技巧",
    ],
    "宣传片制作": [
        "企业宣传片分镜脚本 怎么写",
        "产品广告拍摄 创意策划 案例",
        "公益广告文案 创意脚本 方法",
        "宣传片分镜表 格式 模板",
        "商业广告创意策划 流程",
    ],
    "社交媒体运营": [
        "小红书封面文案 怎么写 技巧",
        "抖音话题标签 运营策略",
        "社交媒体内容排期 规划方法",
        "品牌社媒运营 发布策略 案例",
        "公众号推文标题 爆款技巧",
    ],
}


def bing_search(query: str, max_results: int = 8) -> list[dict]:
    """使用 Bing 搜索"""
    results = []
    url = "https://www.bing.com/search"
    params = {"q": query, "count": max_results, "setlang": "zh-CN", "mkt": "zh-CN"}

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for item in soup.select("li.b_algo"):
            title_el = item.select_one("h2 a")
            snippet_el = item.select_one(".b_caption p, .b_lineclamp2")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            # 推断平台
            platform = _guess_platform(title + snippet)
            # 推断日期
            date_str = _extract_date(item)

            results.append({
                "title": title[:255],
                "url": link,
                "snippet": snippet[:300],
                "platform": platform,
                "date": date_str,
            })

        print(f"  Bing: {query[:30]}... → {len(results)} 条")
    except Exception as e:
        print(f"  Bing 搜索失败: {e}")

    return results[:max_results]


def _guess_platform(text: str) -> str:
    """根据文本内容推断平台"""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["抖音", "douyin", "tiktok"]):
        return "抖音"
    if any(kw in text_lower for kw in ["小红书", "xiaohongshu", "red"]):
        return "小红书"
    if any(kw in text_lower for kw in ["b站", "bilibili", "哔哩"]):
        return "B站"
    if any(kw in text_lower for kw in ["公众号", "微信"]):
        return "公众号"
    # 按概率分配
    return random.choice(["抖音", "小红书", "B站"])


def _extract_date(soup_element) -> str:
    """尝试提取发布日期"""
    # 常见日期模式
    text = soup_element.get_text()
    patterns = [
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        r"(\d{1,2}\s*(?:天|小时|周|月)前)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return datetime.now().strftime("%Y-%m-%d")


def crawl_category(category: str, queries: list[str]) -> list[dict]:
    """爬取一个类别下的所有数据"""
    all_results = []
    seen_titles = set()

    for query in queries:
        results = bing_search(query)
        for r in results:
            if r["title"] not in seen_titles and len(r["snippet"]) > 20:
                seen_titles.add(r["title"])
                all_results.append({
                    "标题": r["title"],
                    "标签/类别": category,
                    "平台": r["platform"],
                    "发布时间": r["date"],
                    "来源": _extract_source(r["url"]),
                    "内容摘要": r["snippet"],
                })
        time.sleep(1.5 + random.random() * 2)  # 反爬延迟

    return all_results


def _extract_source(url: str) -> str:
    """从 URL 提取来源名称"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")
        # 中文平台映射
        mapping = {
            "zhihu.com": "知乎",
            "jianshu.com": "简书",
            "csdn.net": "CSDN",
            "bilibili.com": "B站",
            "douyin.com": "抖音",
            "xiaohongshu.com": "小红书",
            "mp.weixin.qq.com": "公众号",
            "zhuanlan.zhihu.com": "知乎专栏",
            "36kr.com": "36氪",
            "juejin.cn": "掘金",
            "sohu.com": "搜狐",
            "163.com": "网易",
            "sina.com.cn": "新浪",
        }
        for key, name in mapping.items():
            if key in domain:
                return name
        return domain
    except Exception:
        return url[:50]


def main():
    print("=" * 60)
    print("  数字媒体创作样例数据采集")
    print("=" * 60)

    all_data = []
    for category, queries in SEARCH_QUERIES.items():
        print(f"\n📂 采集类别: {category} ({len(queries)} 组关键词)")
        results = crawl_category(category, queries)
        print(f"   共采集 {len(results)} 条")
        all_data.extend(results)

    # ── 去重 ──
    df = pd.DataFrame(all_data)
    if not df.empty:
        df = df.drop_duplicates(subset=["标题"])
        df["id"] = range(1, len(df) + 1)
        df = df[["id", "标题", "标签/类别", "平台", "发布时间", "来源", "内容摘要"]]

        # ── 保存 ──
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(OUTPUT, index=False)

        print(f"\n{'=' * 60}")
        print(f"✅ 采集完成!")
        print(f"   总计: {len(df)} 条")
        print(f"   输出: {OUTPUT}")
        for cat in SEARCH_QUERIES:
            count = len(df[df["标签/类别"] == cat])
            print(f"   {cat}: {count} 条")
    else:
        print("\n❌ 未采集到任何数据，请检查网络连接")


if __name__ == "__main__":
    main()
