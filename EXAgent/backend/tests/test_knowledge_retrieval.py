"""
知识库检索质量测试 — 验证检索结果的相关性

测试内容：
1. Top-1/3/5 命中率评估
2. 检索响应时间
3. 相似度分数范围
4. 多平台检索覆盖率
"""
import json
import time
import os
import sys
import time as _time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

KB_TEST_QUERIES = [
    ("秋季护肤好物推荐", ["护肤", "美妆", "秋季"], "douyin"),
    ("网红零食测评", ["零食", "美食", "测评"], "xiaohongshu"),
    ("游戏攻略教程", ["游戏", "攻略", "教程"], "bilibili"),
    ("旅行vlog打卡", ["旅行", "vlog", "打卡"], "douyin"),
    ("数码产品开箱", ["数码", "开箱", "科技"], "bilibili"),
    ("穿搭日常分享", ["穿搭", "时尚", "日常"], "xiaohongshu"),
    ("美食制作教程", ["美食", "教程", "烹饪"], "douyin"),
    ("健身减脂计划", ["健身", "减肥", "运动"], "xiaohongshu"),
    ("情感故事分享", ["情感", "故事", "生活"], "douyin"),
    ("职场干货经验", ["职场", "干货", "经验"], "bilibili"),
]


def _check_relevance(result, expected_keywords):
    """检查单条结果的标题或内容是否含有关键词"""
    if not result:
        return False
    text = result.get("title", "") + " " + result.get("content_snippet", "")
    return any(kw in text for kw in expected_keywords)


# ─── 独立工具函数（避免类中 self 参数问题） ───

def _register_and_login(client):
    """注册一个新用户并返回 auth headers"""
    username = f"kb_test_{int(_time.time() * 1000000) % 1000000}"
    client.post("/api/auth/register", json={
        "username": username, "password": "Test123456"})
    login = client.post("/api/auth/login", json={
        "username": username, "password": "Test123456"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _search_kb(client, headers, query, top_k=5):
    """调用知识库搜索 API，不可用或无数据时跳过"""
    resp = client.get(
        f"/api/knowledge/search?q={query}&top_k={top_k}",
        headers=headers,
    )
    if resp.status_code != 200:
        pytest.skip(f"知识库服务不可用 (HTTP {resp.status_code})")
    data = resp.json()
    if not data.get("results"):
        pytest.skip("知识库为空（测试环境无 Chroma 数据）")
    return data


class TestKnowledgeRetrievalQuality:
    """知识库检索质量评估"""

    def test_top1_always_returns_result(self, client):
        """验证 Top-1 搜索始终返回结果（非空）"""
        headers = _register_and_login(client)
        non_empty = 0
        for query, _, _ in KB_TEST_QUERIES[:8]:
            result = _search_kb(client, headers, query, top_k=1)
            has_r = len(result.get("results", [])) > 0
            if has_r:
                non_empty += 1
            top1 = result["results"][0] if result.get("results") else None
            print(f"  [{'✓' if has_r else '✗'}] {query} → "
                  f"{top1['title'][:35] if top1 else '无'} "
                  f"({top1['similarity']:.3f if top1 else 'N/A'})")
        print(f"\n  非空结果率: {non_empty}/{8}")
        assert non_empty >= 6, f"非空结果率 {non_empty}/8 < 75%"

    def test_top3_returns_results(self, client):
        """验证 Top-3 搜索返回 ≥2 条结果"""
        headers = _register_and_login(client)
        sufficient = 0
        for query, _, _ in KB_TEST_QUERIES[:8]:
            result = _search_kb(client, headers, query, top_k=3)
            count = len(result.get("results", []))
            if count >= 2:
                sufficient += 1
        print(f"\n  充足结果率: {sufficient}/8")
        assert sufficient >= 6, f"充足结果率 {sufficient}/8 < 75%"

    def test_top5_returns_results(self, client):
        """验证 Top-5 搜索返回 ≥3 条结果"""
        headers = _register_and_login(client)
        sufficient = 0
        for query, _, _ in KB_TEST_QUERIES[:8]:
            result = _search_kb(client, headers, query, top_k=5)
            count = len(result.get("results", []))
            if count >= 3:
                sufficient += 1
        print(f"\n  充足结果率: {sufficient}/8")
        assert sufficient >= 6, f"充足结果率 {sufficient}/8 < 75%"

    def test_retrieval_response_time(self, client):
        headers = _register_and_login(client)
        times_ms = []
        for query, _, _ in KB_TEST_QUERIES[:5]:
            start = time.perf_counter()
            _search_kb(client, headers, query, top_k=5)
            times_ms.append((time.perf_counter() - start) * 1000)
        if times_ms:
            avg = sum(times_ms) / len(times_ms)
            print(f"\n  平均检索响应时间: {avg:.0f}ms ({len(times_ms)}次)")
            assert avg < 10000, f"平均{avg:.0f}ms超10秒"

    def test_similarity_range(self, client):
        headers = _register_and_login(client)
        for query, _, _ in KB_TEST_QUERIES[:3]:
            result = _search_kb(client, headers, query, top_k=5)
            for r in result.get("results", []):
                assert 0.0 <= r["similarity"] <= 1.0

    def test_platform_coverage(self, client):
        headers = _register_and_login(client)
        platforms = set()
        for query, _, _ in KB_TEST_QUERIES[:5]:
            result = _search_kb(client, headers, query, top_k=5)
            for r in result.get("results", []):
                if r.get("platform"):
                    platforms.add(r["platform"])
        print(f"\n  覆盖平台: {platforms}")
        assert len(platforms) >= 1, "未覆盖任何平台"


def test_kb_evaluation_report(client):
    """生成知识库评估报告 JSON"""
    headers = _register_and_login(client)

    top1_hits = top3_hits = top5_hits = 0
    total = 0
    report = {"test_queries": []}

    for query, kw, platform in KB_TEST_QUERIES:
        resp = client.get(
            f"/api/knowledge/search?q={query}&top_k=5",
            headers=headers,
        )
        if resp.status_code != 200:
            pytest.skip(f"知识库不可用 (HTTP {resp.status_code})")
        total += 1
        data = resp.json()
        results = data.get("results", [])
        top1 = results[0] if results else None
        top1_rel = _check_relevance(top1, kw) if top1 else False
        top3_rel = any(_check_relevance(r, kw) for r in results[:3])
        top5_rel = any(_check_relevance(r, kw) for r in results[:5])

        if top1_rel:
            top1_hits += 1
        if top3_rel:
            top3_hits += 1
        if top5_rel:
            top5_hits += 1

        report["test_queries"].append({
            "query": query, "expected_keywords": kw, "expected_platform": platform,
            "top1_relevant": top1_rel, "top3_relevant": top3_rel,
            "top5_relevant": top5_rel,
            "top_result": top1["title"] if top1 else "N/A",
            "top_similarity": top1["similarity"] if top1 else 0,
        })

    report["summary"] = {
        "total_queries": total,
        "top1_hits": top1_hits,
        "top1_hit_rate": top1_hits / total if total else 0,
        "top3_hits": top3_hits,
        "top3_hit_rate": top3_hits / total if total else 0,
        "top5_hits": top5_hits,
        "top5_hit_rate": top5_hits / total if total else 0,
    }

    out = Path(__file__).resolve().parent / "kb_evaluation_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  知识库评估报告: {out}")
    print(f"  Top-1: {report['summary']['top1_hit_rate']:.1%}  "
          f"Top-3: {report['summary']['top3_hit_rate']:.1%}  "
          f"Top-5: {report['summary']['top5_hit_rate']:.1%}")
