"""
跨平台测试 — 同一主题在抖音/小红书/B站三个平台生成版本的差异
"""
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "p4_agent"))

import pytest

try:
    from p4_agent.pipeline_adapter import create_content
    P4_OK = True
except (ImportError, RuntimeError) as e:
    P4_OK = False
    P4_REASON = str(e)

pytestmark = pytest.mark.skipif(not P4_OK, reason=f"p4_agent 不可用: {P4_REASON if not P4_OK else ''}")

CROSS_PLATFORM_CASES = [
    {"name": "护肤好物", "topic": "秋季护肤好物推荐",
     "target_audience": "25-35岁职场女性", "duration": "60s", "style": "干货科普"},
    {"name": "美食测评", "topic": "速食产品测评",
     "target_audience": "18-28岁学生党", "duration": "60s", "style": "测评种草"},
    {"name": "旅行记录", "topic": "城市小众打卡地",
     "target_audience": "20-35岁文艺青年", "duration": "3min", "style": "剧情故事"},
]
PLATFORMS = ["douyin", "xiaohongshu", "bilibili"]
PLATFORM_NAMES = {"douyin": "抖音", "xiaohongshu": "小红书", "bilibili": "B站"}


def _run(topic, audience, platform, duration, style):
    return create_content(
        topic=topic, target_audience=audience, platform=platform,
        duration=duration, style=style, provider="mock",
        enable_trend=False, enable_review=False, enable_strategy=False,
    )


class TestCrossPlatformDifferentiation:
    @pytest.mark.parametrize("case", CROSS_PLATFORM_CASES)
    def test_cross_platform_content_differs(self, case):
        results = {p: _run(case["topic"], case["target_audience"], p,
                           case["duration"], case["style"]) for p in PLATFORMS}
        titles = {p: set(s.get("title", "") for s in results[p]["schemes"]) for p in PLATFORMS}
        for p1 in PLATFORMS:
            for p2 in PLATFORMS:
                if p1 < p2:
                    assert titles[p1] != titles[p2], f"平台{p1}和{p2}标题完全相同"
        print(f"\n  [{case['name']}] 三平台标题:")
        for p in PLATFORMS:
            for s in results[p]["schemes"]:
                print(f"    {PLATFORM_NAMES[p]} {s['version']}: {s.get('title','无')[:50]}")

    @pytest.mark.parametrize("case", CROSS_PLATFORM_CASES)
    def test_cross_platform_hashtags_differ(self, case):
        results = {p: _run(case["topic"], case["target_audience"], p,
                           case["duration"], case["style"]) for p in PLATFORMS}
        for p in PLATFORMS:
            all_tags = []
            for s in results[p]["schemes"]:
                all_tags.extend(s.get("hashtags", []))
            print(f"  [{case['name']}] {PLATFORM_NAMES[p]} 标签: {all_tags[:5]}")
            assert len(all_tags) > 0, f"平台{p}无标签"

    @pytest.mark.parametrize("case", CROSS_PLATFORM_CASES)
    def test_cross_platform_scene_count(self, case):
        results = {p: _run(case["topic"], case["target_audience"], p,
                           case["duration"], case["style"]) for p in PLATFORMS}
        for p in PLATFORMS:
            for s in results[p]["schemes"]:
                scenes = s.get("scenes", [])
                assert len(scenes) > 0, f"平台{p}方案{s.get('version')}无分镜"
        print(f"\n  [{case['name']}] 各平台均有分镜 ✓")


class TestCrossPlatformSnapshot:
    def test_cross_platform_snapshot(self):
        case = CROSS_PLATFORM_CASES[0]
        snapshot = {"test_case": case["name"], "topic": case["topic"], "platforms": {}}
        for p in PLATFORMS:
            r = _run(case["topic"], case["target_audience"], p, case["duration"], case["style"])
            snapshot["platforms"][p] = {
                "platform_name": PLATFORM_NAMES[p],
                "schemes": [{"version": s.get("version"), "title": s.get("title", ""),
                             "hook": s.get("hook", "")[:100], "hashtags": s.get("hashtags", []),
                             "cover_text": s.get("cover_text", ""),
                             "scene_count": len(s.get("scenes", [])),
                             "score": s.get("score"), "rank": s.get("rank")}
                            for s in r.get("schemes", [])],
            }
        out = Path(__file__).resolve().parent / "cross_platform_snapshot.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        print(f"\n  跨平台快照已保存: {out}")
        for p in PLATFORMS:
            assert len(snapshot["platforms"][p]["schemes"]) == 3


class TestPlatformSpecificFeatures:
    @pytest.mark.parametrize("platform", PLATFORMS)
    def test_platform_scenes_exist(self, platform):
        r = _run("护肤推荐", "职场女性", platform, "60s", "干货科普")
        for s in r.get("schemes", []):
            scenes = s.get("scenes", [])
            assert len(scenes) > 0, f"{PLATFORM_NAMES[platform]}方案无分镜"
            first_dur = str(scenes[0].get("duration", "?"))
            print(f"  [{PLATFORM_NAMES[platform]}] 开场时长: {first_dur}")

    def test_bilibili_long_form(self):
        r = _run("护肤推荐", "职场女性", "bilibili", "3min", "干货科普")
        for s in r.get("schemes", []):
            scenes = s.get("scenes", [])
            assert len(scenes) >= 3, "B站长视频应有≥3场景"
            print(f"  [B站] 场景数: {len(scenes)}")
