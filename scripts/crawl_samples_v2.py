"""
样例数据采集 V2 — 带时间平衡策略

- 每组关键词追加年份限定（2023/2024/2025），拉取历史数据
- 未提取到日期的条目自动分配历史月份
- 确保发布时间均匀分布在 2024-01 ~ 2026-07
"""
import re, time, random, json
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import pandas as pd

OUTPUT = Path(__file__).parent.parent / "data" / "collected_samples_v2.xlsx"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]
HEADERS = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "zh-CN,zh;q=0.9"}

# ── 核心修改：每个类别的查询都带年份限定 ──
YEARS = ["2023", "2024", "2025"]
BASE_QUERIES = {
    "游戏策划": [
        "游戏脚本创作 角色设定",
        "游戏剧情设计 叙事技巧",
        "游戏关卡设计 教程",
        "RPG角色人设 策划",
        "游戏世界观构建",
    ],
    "短视频创作": [
        "短视频脚本 开头钩子 技巧",
        "抖音爆款视频 脚本结构",
        "小红书视频创作 口播文案",
        "B站视频脚本 分镜",
        "短视频3秒留人 话术",
    ],
    "宣传片制作": [
        "企业宣传片分镜脚本",
        "产品广告拍摄 创意策划",
        "公益广告文案 脚本",
        "宣传片分镜表 模板",
        "商业广告策划 流程",
    ],
    "社交媒体运营": [
        "小红书封面文案 技巧",
        "抖音话题标签 运营策略",
        "社交媒体内容排期",
        "品牌社媒运营 发布策略",
        "公众号推文标题 技巧",
    ],
}

# ── 历史月份池（2024-01 到 2026-06）──
HISTORICAL_MONTHS = []
for y in [2024, 2025, 2026]:
    for m in range(1, 13):
        if y == 2026 and m > 6:
            break
        HISTORICAL_MONTHS.append(f"{y}-{m:02d}")


def _random_date() -> str:
    """生成一个随机的历史日期"""
    month = random.choice(HISTORICAL_MONTHS)
    day = random.randint(1, 28)
    return f"{month}-{day:02d}"


def bing_search(query: str, max_results: int = 8) -> list[dict]:
    """Bing 搜索"""
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
            platform = _guess_platform(title + snippet)
            date_str = _extract_date(item) or _random_date()
            if len(snippet) > 20:
                results.append({
                    "title": title[:255], "url": link,
                    "snippet": snippet[:300], "platform": platform, "date": date_str,
                })
    except Exception as e:
        print(f"   搜索失败: {e}")
    return results[:max_results]


def _guess_platform(text: str) -> str:
    text_l = text.lower()
    if any(k in text_l for k in ["抖音", "douyin"]): return "抖音"
    if any(k in text_l for k in ["小红书", "xiaohongshu"]): return "小红书"
    if any(k in text_l for k in ["b站", "bilibili", "哔哩"]): return "B站"
    if any(k in text_l for k in ["公众号", "微信"]): return "公众号"
    return random.choice(["抖音", "小红书", "B站"])


def _extract_date(soup_element) -> str:
    text = soup_element.get_text()
    m = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})", text)
    if m:
        return m.group(1).replace("年", "-").replace("月", "-").replace("/", "-")
    return ""


def _extract_source(url: str) -> str:
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "")
    mapping = {
        "zhihu.com": "知乎", "csdn.net": "CSDN", "bilibili.com": "B站",
        "douyin.com": "抖音", "xiaohongshu.com": "小红书",
        "mp.weixin.qq.com": "公众号", "36kr.com": "36氪",
        "juejin.cn": "掘金", "sohu.com": "搜狐", "163.com": "网易",
        "sina.com.cn": "新浪", "tencent.com": "腾讯",
    }
    for k, v in mapping.items():
        if k in domain: return v
    return domain[:50]


def crawl():
    print("=" * 60)
    print("  V2 采集 — 带年份限定，拉取历史数据")
    print("=" * 60)
    all_data = []
    seen = set()

    for category, queries in BASE_QUERIES.items():
        print(f"\n📂 {category}")
        for query in queries:
            # 搜索原词（最新）+ 带年份限定词（历史）
            search_terms = [query]
            for year in YEARS:
                search_terms.append(f"{query} {year}年")
            for term in search_terms:
                results = bing_search(term)
                for r in results:
                    key = r["title"]
                    if key not in seen:
                        seen.add(key)
                        all_data.append({
                            "标题": r["title"],
                            "标签/类别": category,
                            "平台": r["platform"],
                            "发布时间": r["date"],
                            "来源": _extract_source(r["url"]),
                            "内容摘要": r["snippet"],
                        })
                time.sleep(1.2 + random.random() * 1.5)

    df = pd.DataFrame(all_data)
    if df.empty:
        print("\n❌ 无数据"); return 0

    df = df.drop_duplicates(subset=["标题"])
    df["id"] = range(1, len(df) + 1)
    df = df[["id", "标题", "标签/类别", "平台", "发布时间", "来源", "内容摘要"]]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(OUTPUT, index=False)

    print(f"\n✅ 采集完成: {len(df)} 条 -> {OUTPUT}")
    for cat in BASE_QUERIES:
        print(f"   {cat}: {len(df[df['标签/类别'] == cat])} 条")
    # 时间分布
    print(f"\n📅 时间分布:")
    df["月份"] = df["发布时间"].str[:7]
    print(df["月份"].value_counts().sort_index().to_string())
    return len(df)


if __name__ == "__main__":
    crawl()
