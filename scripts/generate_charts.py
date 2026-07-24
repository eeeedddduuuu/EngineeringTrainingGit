"""
统计图表生成脚本

从 samples.xlsx 生成：
- 主题分布饼图
- 平台分布柱状图
- 月度发布趋势折线图
- 标签词云

输出到 data/charts/ 目录
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

# ── 中文字体配置 ──
# Windows 常见中文字体
_CN_FONTS = [
    "Microsoft YaHei",
    "SimHei",
    "KaiTi",
    "SimSun",
    "Noto Sans CJK SC",
]
for _f in _CN_FONTS:
    try:
        fm.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [_f, "DejaVu Sans"]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "charts"


def load_data():
    path = Path(__file__).resolve().parent.parent / "samples.xlsx"
    if not path.exists():
        print(f"❌ 找不到 {path}")
        sys.exit(1)
    df = pd.read_excel(path)
    df["发布时间"] = pd.to_datetime(df["发布时间"], errors="coerce")
    return df


def generate_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data()
    print(f"📊 加载 {len(df)} 条样例数据")

    # ── 1. 主题分布饼图 ──
    fig, ax = plt.subplots(figsize=(8, 6))
    topic_counts = df["标签/类别"].value_counts()
    colors = ["#4ECDC4", "#FF6B6B", "#FFE66D", "#95E1D3", "#F38181", "#AA96DA"]
    wedges, texts, autotexts = ax.pie(
        topic_counts.values,
        labels=topic_counts.index,
        autopct="%1.1f%%",
        colors=colors[: len(topic_counts)],
        startangle=90,
        pctdistance=0.75,
    )
    ax.set_title("样例主题分布", fontsize=16, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "topic_distribution.png", dpi=150)
    plt.close(fig)
    print("✅ 主题分布饼图 → data/charts/topic_distribution.png")

    # ── 2. 平台分布柱状图 ──
    fig, ax = plt.subplots(figsize=(8, 5))
    platform_counts = df["平台"].value_counts()
    bars = ax.bar(
        platform_counts.index,
        platform_counts.values,
        color=["#FF6B6B", "#4ECDC4", "#FFE66D"],
        edgecolor="white",
        linewidth=0.8,
    )
    for bar, val in zip(bars, platform_counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(val), ha="center", va="bottom", fontsize=13, fontweight="bold")
    ax.set_title("平台分布", fontsize=16, fontweight="bold")
    ax.set_ylabel("样例数量", fontsize=12)
    ax.set_ylim(0, max(platform_counts.values) * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "platform_distribution.png", dpi=150)
    plt.close(fig)
    print("✅ 平台分布柱状图 → data/charts/platform_distribution.png")

    # ── 3. 月度发布趋势折线图 ──
    fig, ax = plt.subplots(figsize=(10, 5))
    monthly = df.dropna(subset=["发布时间"]).set_index("发布时间").resample("ME").size()
    ax.plot(
        monthly.index.strftime("%Y-%m"),
        monthly.values,
        marker="o",
        linewidth=2.5,
        markersize=8,
        color="#FF6B6B",
        markerfacecolor="white",
        markeredgewidth=2,
    )
    ax.fill_between(range(len(monthly)), monthly.values, alpha=0.1, color="#FF6B6B")
    ax.set_title("月度发布趋势", fontsize=16, fontweight="bold")
    ax.set_xlabel("月份", fontsize=12)
    ax.set_ylabel("样例数量", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "monthly_trends.png", dpi=150)
    plt.close(fig)
    print("✅ 月度趋势折线图 → data/charts/monthly_trends.png")

    # ── 4. 高频标签统计 (从标签/类别列) ──
    fig, ax = plt.subplots(figsize=(10, 5))
    tag_counts = df["标签/类别"].value_counts()
    bars = ax.barh(
        tag_counts.index[::-1],
        tag_counts.values[::-1],
        color=colors[: len(tag_counts)],
        edgecolor="white",
        linewidth=0.8,
    )
    for bar, val in zip(bars, tag_counts.values[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=12, fontweight="bold")
    ax.set_title("标签类别分布", fontsize=16, fontweight="bold")
    ax.set_xlabel("数量", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "tag_distribution.png", dpi=150)
    plt.close(fig)
    print("✅ 标签分布横向柱状图 → data/charts/tag_distribution.png")

    print("\n🎉 全部图表生成完成！")


if __name__ == "__main__":
    generate_all()
