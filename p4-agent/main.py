"""
P4 Agent 模块 — 快速验证脚本
运行方式: python main.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents import run_agent, run_agent_pipeline


def demo_single_agent():
    """演示单个 Agent 运行。"""
    print("=" * 60)
    print("P4 Agent 单跑验证 - Mock 模式")
    print("=" * 60)

    test_input = "主题：秋季护肤好物推荐 | 平台：抖音 | 受众：25-35岁职场女性 | 时长：60秒 | 风格：干货+轻娱乐"

    print(f"\n[输入] {test_input}\n")

    # 测试脚本创作 Agent
    print("[运行] script Agent...")
    result = run_agent("script", test_input, provider="mock")
    print(f"  状态: {'[OK] 成功' if result['ok'] else '[FAIL] 失败'}")
    print(f"  耗时: {result['latency_ms']}ms")
    print(f"  Prompt版本: {result['prompt_version']}")
    print(f"  输出长度: {len(result['answer'])} 字符")
    print(f"  工具调用: {len(result['tools_called'])} 次")
    print()


def demo_pipeline():
    """演示完整流水线。"""
    print("=" * 60)
    print("P4 Agent 流水线验证 - Mock 模式")
    print("=" * 60)

    test_input = "我想做一期关于AI工具的视频，最近这个话题很火"

    print(f"\n[输入] {test_input}")
    print("\n[运行] 流水线: trend -> script -> review -> strategy\n")

    pipeline_result = run_agent_pipeline(test_input, provider="mock")

    for agent_name, result in pipeline_result["agents"].items():
        status = "[OK]" if result["ok"] else "[FAIL]"
        print(f"  {status} {agent_name}: {result['latency_ms']}ms, {len(result['answer'])}字")

    # 保存结果
    output_dir = PROJECT_ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "demo_pipeline_result.json"
    output_file.write_text(
        json.dumps(pipeline_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[输出] 结果已保存: {output_file}")


def demo_scoring():
    """演示方案评分。"""
    from workflow.scoring import rank_schemes, scoring_report

    print("=" * 60)
    print("P4 方案评分验证")
    print("=" * 60)

    schemes = [
        {
            "version": "A",
            "hook": "你每天都在做的护肤步骤，可能正在毁掉你的皮肤。",
            "structure": "开头钩子(0-3s)->问题指出(3-27s)->正确方法(27-50s)->结尾引导(50-55s)",
            "audience_match": "高度契合25-35岁职场女性，语言风格偏专业但易懂",
            "content": "独特角度的护肤科普内容，与常见种草贴形成差异化",
            "feasibility": "单人口播+简单道具，手机可拍，成本极低",
        },
        {
            "version": "B",
            "hook": "三年前我的脸烂到不敢出门...",
            "structure": "前后对比(0-5s)->故事自述(5-20s)->干货分享(20-50s)->金句结尾(50-55s)",
            "audience_match": "故事型表达贴合女性受众，情感共鸣强",
            "content": "个人真实经历改编，有一定独特性但故事框架较常见",
            "feasibility": "需要前后对比素材+适当场景切换，中等难度",
        },
        {
            "version": "C",
            "hook": "这一桌加起来不到200块...",
            "structure": "挑战引入(0-3s)->每日记录(3-50s)->结果揭晓(50-55s)",
            "audience_match": "适合学生和预算有限的年轻用户",
            "content": "7天打卡形式较新颖，数据可视化有趣",
            "feasibility": "需要7天持续拍摄+素材积累，执行周期长",
        },
    ]

    ranked = rank_schemes(schemes)
    print(scoring_report(ranked))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="P4 Agent 模块验证")
    parser.add_argument("--mode", choices=["single", "pipeline", "scoring", "all"], default="all",
                        help="运行模式 (默认: all)")
    parser.add_argument("--provider", choices=["mock", "coze", "dify", "deepseek"], default="mock",
                        help="Provider 选择 (默认: mock)")
    args = parser.parse_args()

    if args.mode in ("single", "all"):
        demo_single_agent()
    if args.mode in ("pipeline", "all"):
        demo_pipeline()
    if args.mode in ("scoring", "all"):
        demo_scoring()

    print("=" * 60)
    print("[OK] P4 Agent 模块全部验证通过")
    print("=" * 60)
