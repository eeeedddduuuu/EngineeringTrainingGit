"""知识库检索效果定量评估"""
import httpx
import time

BASE = "http://localhost:8000"

# 测试查询： (查询词, 期望匹配的标签)
TEST_QUERIES = [
    ("短视频脚本创作", "短视频创作"),
    ("游戏策划角色设计", "游戏策划"),
    ("社交媒体品牌运营", "社交媒体运营"),
    ("宣传片分镜拍摄技巧", "宣传片制作"),
    ("抖音爆款内容怎么做", "短视频创作"),
    ("B站游戏PV宣传片", "宣传片制作"),
    ("小红书运营涨粉攻略", "社交媒体运营"),
    ("手游抽卡系统策划", "游戏策划"),
    ("短视频开头钩子怎么写", "短视频创作"),
    ("企业品牌宣传片策划", "宣传片制作"),
]

print("=" * 65)
print("  知识库检索效果定量评估")
print("=" * 65)

total_ms = 0.0
top1_hits = 0
top3_hits = 0
top5_hits = 0
all_sims = []

for q, expected_tag in TEST_QUERIES:
    start = time.time()
    r = httpx.get(f"{BASE}/api/knowledge/search", params={"q": q, "top_k": 5}, timeout=30)
    elapsed_ms = (time.time() - start) * 1000
    total_ms += elapsed_ms

    results = r.json()["results"]

    # 命中判定：结果的 tags 中包含期望的标签类别
    top1_ok = expected_tag in results[0]["tags"] if results else False
    top3_ok = any(expected_tag in r2["tags"] for r2 in results[:3]) if len(results) >= 3 else top1_ok
    top5_ok = any(expected_tag in r2["tags"] for r2 in results) if results else False

    if top1_ok:
        top1_hits += 1
    if top3_ok:
        top3_hits += 1
    if top5_ok:
        top5_hits += 1

    top1_sim = results[0]["similarity"] if results else 0.0
    all_sims.append(top1_sim)

    print(f"\n[{q}] → 期望: {expected_tag}")
    print(f"  Top-1 相似度: {top1_sim:.3f}  命中: {'✓' if top1_ok else '✗'}")
    print(f"  Top-1: {results[0]['title'][:50] if results else 'N/A'}")

n = len(TEST_QUERIES)
print(f"\n{'=' * 65}")
print(f"  汇总")
print(f"{'=' * 65}")
print(f"  查询数:        {n}")
print(f"  Top-1 命中率:  {top1_hits}/{n} = {top1_hits / n * 100:.0f}%")
print(f"  Top-3 命中率:  {top3_hits}/{n} = {top3_hits / n * 100:.0f}%")
print(f"  Top-5 命中率:  {top5_hits}/{n} = {top5_hits / n * 100:.0f}%")
print(f"  平均相似度:    {sum(all_sims) / len(all_sims):.3f}")
print(f"  平均响应时间:  {total_ms / n:.0f} ms")
print(f"  最快/最慢:     {min(all_sims):.3f}s / {max(all_sims):.3f}s")
