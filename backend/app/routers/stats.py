"""统计看板路由 — /api/stats/samples"""
import pandas as pd
from pathlib import Path
from fastapi import APIRouter
from app.schemas.knowledge import (
    StatsResponse,
    TopicDistribution,
    PlatformDistribution,
    MonthlyTrend,
)

router = APIRouter(prefix="/api/stats", tags=["统计"])

# 样例数据路径（相对于项目根目录，即 backend/ 的上一级）
SAMPLES_PATH = Path(__file__).parent.parent.parent.parent / "samples.xlsx"


def _load_samples() -> pd.DataFrame:
    """加载样例数据，带缓存（模块级单次加载）"""
    if not hasattr(_load_samples, "_cache"):
        if SAMPLES_PATH.exists():
            df = pd.read_excel(SAMPLES_PATH)
            # 确保发布时间列存在
            if "发布时间" in df.columns:
                df["发布时间"] = pd.to_datetime(df["发布时间"], errors="coerce")
            _load_samples._cache = df
        else:
            _load_samples._cache = pd.DataFrame()
    return _load_samples._cache


@router.get("/samples", response_model=StatsResponse)
def get_sample_stats():
    """
    样例数据统计接口

    返回：
    - total_samples: 样本总数
    - topic_distribution: 主题/类别分布
    - platform_distribution: 平台分布
    - monthly_trends: 月度发布趋势
    """
    df = _load_samples()

    if df.empty:
        return StatsResponse(
            total_samples=0,
            topic_distribution=[],
            platform_distribution=[],
            monthly_trends=[],
        )

    # 标签列名可能是"标签/类别"（需要处理）
    topic_col = "标签/类别" if "标签/类别" in df.columns else None
    platform_col = "平台" if "平台" in df.columns else None

    # ── 主题分布 ──
    topic_dist: list[TopicDistribution] = []
    if topic_col:
        topic_counts = df[topic_col].value_counts().to_dict()
        topic_dist = [
            TopicDistribution(name=str(k), count=v) for k, v in topic_counts.items()
        ]

    # ── 平台分布 ──
    platform_dist: list[PlatformDistribution] = []
    if platform_col:
        platform_counts = df[platform_col].value_counts().to_dict()
        platform_dist = [
            PlatformDistribution(platform=str(k), count=v)
            for k, v in platform_counts.items()
        ]

    # ── 月度趋势 ──
    monthly_trends: list[MonthlyTrend] = []
    if "发布时间" in df.columns and df["发布时间"].notna().any():
        monthly = (
            df.dropna(subset=["发布时间"])
            .set_index("发布时间")
            .resample("ME")
            .size()
        )
        monthly_trends = [
            MonthlyTrend(
                month=idx.strftime("%Y-%m"),
                count=int(v),
            )
            for idx, v in monthly.items()
        ]

    return StatsResponse(
        total_samples=len(df),
        topic_distribution=topic_dist,
        platform_distribution=platform_dist,
        monthly_trends=monthly_trends,
    )
