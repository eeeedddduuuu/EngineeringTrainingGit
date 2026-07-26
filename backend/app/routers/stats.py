"""统计看板路由 — 基于 samples.xlsx 真实数据 + 数据库实时统计

来源：P5 feature/data-kb-v2（50条样本，25个月数据）
集成：P3 添加 JWT 认证依赖 + 合并到 feature/backend
"""
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.business import CreationSession, Scheme, Review
from app.schemas.stats import StatsResponse, TopicDist, PlatformDist, MonthlyTrend, DashboardSummary
from app.utils.deps import get_current_user

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
def get_stats(current_user: User = Depends(get_current_user)):
    """
    样例数据统计接口（基于 50 条真实样本）

    返回：
    - total_samples: 样本总数
    - topic_distribution: 主题/类别分布
    - platform_distribution: 平台分布（抖音/小红书/B站）
    - monthly_trends: 月度发布趋势（25个月）
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


@router.get("/statistics/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    看板汇总统计（P2 前端数据看板使用）

    返回：
    - total_sessions: 总创作会话数
    - in_progress: 进行中的会话数
    - pending_review: 待审核方案数
    - completed_this_week: 本周完成的会话数
    - total_schemes: 方案总数
    - total_users: 注册用户总数
    """
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    total_sessions = db.query(func.count(CreationSession.id)).scalar() or 0
    in_progress = db.query(func.count(CreationSession.id)).filter(
        CreationSession.status == "processing"
    ).scalar() or 0
    pending_review = db.query(func.count(Scheme.id)).filter(
        ~Scheme.id.in_(db.query(Review.scheme_id).filter(Review.status.in_(["approved", "rejected"])))
    ).scalar() or 0
    completed_this_week = db.query(func.count(CreationSession.id)).filter(
        CreationSession.status == "completed",
        CreationSession.created_at >= week_start,
    ).scalar() or 0
    total_schemes = db.query(func.count(Scheme.id)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0

    return DashboardSummary(
        total_sessions=total_sessions,
        in_progress=in_progress,
        pending_review=pending_review,
        completed_this_week=completed_this_week,
        total_schemes=total_schemes,
        total_users=total_users,
    )
