"""知识库检索效果定量评估 — Top-1/3/5 命中率 + 响应时间"""
import httpx
import time
import json

BASE = "http://localhost:8000"
TOKEN = None

def get_token():
    global TOKEN
    if TOKEN:
        return TOKEN
    import random, string
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    user = {"username": f"kbeval_{suffix}", "password": "eval123"}
    httpx.post(f"{BASE}/api/auth/register", json=user, timeout=10)
    r = httpx.post(f"{BASE}/api/auth/login", json=user, timeout=10)
    TOKEN = r.json()["access_token"]
    return TOKEN

def search(q: str, top_k: int = 5):
    token = get_token()
    start = time.perf_counter()
    r = httpx.get(
        f"{BASE}/api/knowledge/search",
        params={"q": q, "top_k": top_k},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    elapsed = time.perf_counter() - start
    if r.status_code != 200:
        return [], elapsed, f"HTTP {r.status_code}"
    data = r.json()
    results = []
    for item in data.get("results", []):
        results.append({
            "title": item["title"],
            "platform": item["platform"],
            "tags": item["tags"],
            "similarity": round(item["similarity"], 4),
        })
    return results, elapsed, None

# ── 评估用例: (查询, 期望类别关键词) ──
TEST_CASES = [
    # 精确类别匹配
    ("游戏策划角色", ["游戏", "策划"]),
    ("短视频脚本创作", ["短视频", "创作"]),
    ("宣传片拍摄", ["宣传片", "制作"]),
    ("社交媒体运营技巧", ["社交", "媒体", "运营"]),
    # 跨类别的语义查询
    ("如何写一个抖音视频脚本", ["短视频", "创作"]),
    ("小红书种草文案", ["社交", "媒体"]),
    ("B站品牌宣传怎么做", ["宣传片"]),
    ("游戏剧情世界观设计", ["游戏", "策划"]),
    # 平台相关
    ("抖音热门话题", ["短视频"]),
    ("B站创作教程", ["B站"]),
]

print("=" * 72)
print("知识库检索效果评估")
print(f"Embedding 模型: BAAI/bge-small-zh-v1.5 | 样本: 158 条 | {len(TEST_CASES)} 个测试查询")
print("=" * 72)

top1_hits = 0
top3_hits = 0
top5_hits = 0
total_time = 0
details = []

for i, (query, expected_keywords) in enumerate(TEST_CASES, 1):
    results, elapsed, error = search(query, top_k=5)
    total_time += elapsed

    # 命中判定：结果的 tags 或 title 包含任一期望关键词
    def is_hit(item):
        text = item["title"] + " " + " ".join(item.get("tags", []))
        return any(kw in text for kw in expected_keywords)

    top1 = results[0]["title"] if results else "N/A"
    top1_sim = results[0]["similarity"] if results else 0
    hit_1 = is_hit(results[0]) if results else False
    hit_3 = any(is_hit(r) for r in results[:3]) if results else False
    hit_5 = any(is_hit(r) for r in results[:5]) if results else False

    top1_hits += hit_1
    top3_hits += hit_3
    top5_hits += hit_5

    status = "✅" if hit_1 else ("🟡" if hit_3 else "❌")
    print(f"\n[{status}] #{i} 「{query}」 ({elapsed:.2f}s)")
    print(f"    Top-1: {top1[:50]}... [sim={top1_sim:.4f}]")
    if not hit_1 and results:
        print(f"    Top-2: {results[1]['title'][:50]}... [sim={results[1]['similarity']:.4f}]" if len(results)>1 else "")
        print(f"    Top-3: {results[2]['title'][:50]}... [sim={results[2]['similarity']:.4f}]" if len(results)>2 else "")

    details.append({
        "query": query,
        "expected_kw": expected_keywords,
        "top1_title": top1,
        "top1_sim": top1_sim,
        "elapsed": round(elapsed, 3),
        "top1_hit": hit_1,
        "top3_hit": hit_3,
        "top5_hit": hit_5,
    })

n = len(TEST_CASES)
avg_time = total_time / n
print("\n" + "=" * 72)
print("📊 评估汇总")
print("=" * 72)
print(f"  测试查询数:     {n}")
print(f"  Top-1 命中率:   {top1_hits}/{n} = {top1_hits/n*100:.1f}%")
print(f"  Top-3 命中率:   {top3_hits}/{n} = {top3_hits/n*100:.1f}%")
print(f"  Top-5 命中率:   {top5_hits}/{n} = {top5_hits/n*100:.1f}%")
print(f"  平均响应时间:   {avg_time:.3f}s")
print(f"  总耗时:         {total_time:.1f}s")

# 保存评估结果
output = {
    "model": "BAAI/bge-small-zh-v1.5",
    "total_samples": 158,
    "test_queries": n,
    "top1_hit_rate": f"{top1_hits/n*100:.1f}%",
    "top3_hit_rate": f"{top3_hits/n*100:.1f}%",
    "top5_hit_rate": f"{top5_hits/n*100:.1f}%",
    "avg_response_time_s": round(avg_time, 3),
    "details": details,
}
with open("kb_evaluation_result.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n评估结果已保存至: kb_evaluation_result.json")
