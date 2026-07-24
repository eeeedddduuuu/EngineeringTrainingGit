"""统计看板路由 — 基于 samples.xlsx 真实数据

P3 对接说明：
  - 数据源为项目根目录 samples.xlsx（50 条样例）
  - P3 集成时加入 Depends(get_current_user) 即可
"""
from pathlib import Path
import pandas as pd
from fastapi import APIRouter
from app.schemas.stats import StatsResponse, TopicDist, PlatformDist, MonthlyTrend

router = APIRouter(prefix="/api", tags=["统计"])

SAMPLES_PATH = Path(__file__).parent.parent.parent.parent / "samples.xlsx"


def _load_samples() -> pd.DataFrame:
    """加载样例数据，模块级缓存"""
    if not hasattr(_load_samples, "_cache"):
        if SAMPLES_PATH.exists():
            df = pd.read_excel(SAMPLES_PATH)
            if "发布时间" in df.columns:
                df["发布时间"] = pd.to_datetime(df["发布时间"], errors="coerce")
            _load_samples._cache = df
        else:
            _load_samples._cache = pd.DataFrame()
    return _load_samples._cache


@router.get("/stats/samples", response_model=StatsResponse)
def get_stats():
    """
    样例数据统计接口

    返回：
    - total_samples: 样本总数
    - topic_distribution: 主题/类别分布
    - platform_distribution: 平台分布
    - monthly_trends: 月度发布趋势

    P3 集成备忘：加入认证依赖
      current_user: User = Depends(get_current_user)
    """
    df = _load_samples()

    if df.empty:
        return StatsResponse(
            total_samples=0,
            topic_distribution=[],
            platform_distribution=[],
            monthly_trends=[],
        )

    topic_col = "标签/类别" if "标签/类别" in df.columns else None
    platform_col = "平台" if "平台" in df.columns else None

    # ── 主题分布 ──
    topic_distribution: list[TopicDist] = []
    if topic_col:
        topic_counts = df[topic_col].value_counts().to_dict()
        topic_distribution = [
            TopicDist(name=str(k), count=v) for k, v in topic_counts.items()
        ]

    # ── 平台分布 ──
    platform_distribution: list[PlatformDist] = []
    if platform_col:
        platform_counts = df[platform_col].value_counts().to_dict()
        platform_distribution = [
            PlatformDist(platform=str(k), count=v)
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
            MonthlyTrend(month=idx.strftime("%Y-%m"), count=int(v))
            for idx, v in monthly.items()
        ]

    return StatsResponse(
        total_samples=len(df),
        topic_distribution=topic_distribution,
        platform_distribution=platform_distribution,
        monthly_trends=monthly_trends,
    )
