"""
Agent 稳定性测试 — 相同输入反复调用 5 次，检查输出一致性
"""
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "p4_agent"))

import pytest

# 尝试导入（注：p4_agent 的 parser 模块名与 Python stdlib 冲突）
try:
    from p4_agent.pipeline_adapter import create_content
    P4_OK = True
except (ImportError, RuntimeError) as e:
    P4_OK = False
    P4_REASON = str(e)

pytestmark = pytest.mark.skipif(not P4_OK, reason=f"p4_agent 不可用: {P4_REASON if not P4_OK else ''}")


STABILITY_TEST_CASES = [
    {"name": "护肤干货", "topic": "秋季护肤好物推荐",
     "target_audience": "25-35岁职场女性", "platform": "douyin",
     "duration": "60s", "style": "干货科普"},
    {"name": "美食测评", "topic": "网红零食真实测评",
     "target_audience": "18-28岁学生党", "platform": "xiaohongshu",
     "duration": "60s", "style": "测评种草"},
    {"name": "旅行剧情", "topic": "一个人的旅行日记",
     "target_audience": "20-35岁文艺青年", "platform": "bilibili",
     "duration": "3min", "style": "剧情故事"},
]
ITERATIONS = 5


def _run(case):
    return create_content(
        topic=case["topic"], target_audience=case["target_audience"],
        platform=case["platform"], duration=case["duration"],
        style=case["style"], provider="mock",
        enable_trend=False, enable_review=False, enable_strategy=False,
    )


class TestAgentStability:
    @pytest.mark.parametrize("case", STABILITY_TEST_CASES)
    def test_scheme_count_stability(self, case):
        results = [_run(case) for _ in range(ITERATIONS)]
        for i, r in enumerate(results):
            assert r.get("ok"), f"第{i+1}次调用失败: {r.get('error')}"
        counts = [len(r["schemes"]) for r in results]
        assert all(c == 3 for c in counts), f"方案数量不一致: {counts}"

    @pytest.mark.parametrize("case", STABILITY_TEST_CASES)
    def test_score_ranking_stability(self, case):
        rankings = {"A": [], "B": [], "C": []}
        for _ in range(ITERATIONS):
            r = _run(case)
            for s in r["schemes"]:
                rankings[s["version"]].append(s.get("rank", 0))
        for ver, ranks in rankings.items():
            if ranks:
                assert len(set(ranks)) == 1, f"版本{ver}排名不一致: {ranks}"

    @pytest.mark.parametrize("case", STABILITY_TEST_CASES)
    def test_structure_stability(self, case):
        required = {"version", "title", "hook", "scenes", "hashtags", "cover_text", "score", "rank"}
        for i in range(ITERATIONS):
            r = _run(case)
            for s in r["schemes"]:
                missing = required - set(s.keys())
                assert not missing, f"第{i+1}次方案{s.get('version','?')}缺字段: {missing}"

    @pytest.mark.parametrize("case", STABILITY_TEST_CASES)
    def test_scenes_completeness(self, case):
        for i in range(ITERATIONS):
            r = _run(case)
            for s in r["schemes"]:
                scenes = s.get("scenes", [])
                assert len(scenes) > 0, f"第{i+1}次方案{s.get('version')}无分镜"
                for sc in scenes:
                    assert "seq" in sc or "type" in sc, "分镜缺必要字段"

    @pytest.mark.parametrize("case", STABILITY_TEST_CASES)
    def test_response_time_stability(self, case):
        times_ms = []
        for i in range(ITERATIONS):
            start = time.perf_counter()
            r = _run(case)
            elapsed = (time.perf_counter() - start) * 1000
            times_ms.append(elapsed)
            assert r.get("ok"), f"第{i+1}次调用失败"
        avg = sum(times_ms) / len(times_ms)
        print(f"\n  [{case['name']}] 平均耗时: {avg:.0f}ms, 最大: {max(times_ms):.0f}ms")
        assert max(times_ms) < 5000, f"最大响应时间{max(times_ms):.0f}ms超标"

    @pytest.mark.parametrize("case", STABILITY_TEST_CASES)
    def test_hashtags_validity(self, case):
        for i in range(ITERATIONS):
            r = _run(case)
            for s in r["schemes"]:
                hashtags = s.get("hashtags", [])
                assert len(hashtags) > 0, f"第{i+1}次方案{s.get('version')}无标签"
                for tag in hashtags:
                    assert tag.startswith("#"), f"标签'{tag}'不以#开头"

    def test_stability_snapshot(self):
        case = STABILITY_TEST_CASES[0]
        snapshot = {"test_case": case["name"], "iterations": ITERATIONS, "results": []}
        for i in range(ITERATIONS):
            r = _run(case)
            snapshot["results"].append({
                "iteration": i + 1, "ok": r.get("ok"),
                "scheme_count": len(r.get("schemes", [])),
                "schemes": [{"version": s.get("version"), "title": s.get("title", "")[:50],
                             "score": s.get("score"), "rank": s.get("rank")}
                            for s in r.get("schemes", [])],
            })
        out = Path(__file__).resolve().parent / "agent_stability_snapshot.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"\n  稳定性快照已保存: {out}")
        for item in snapshot["results"]:
            assert item["ok"]
            assert item["scheme_count"] == 3
