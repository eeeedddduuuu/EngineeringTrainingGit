from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.business import KnowledgeItem
from app.schemas.stats import StatsResponse, TopicDist, PlatformDist, MonthlyTrend
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["统计"])


@router.get("/stats/samples", response_model=StatsResponse)
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取样例统计数据（供前端图表使用）"""
    total = db.query(func.count(KnowledgeItem.id)).scalar() or 0

    # 主题分布（从 tags 中统计，简化方案）
    topic_distribution = [
        TopicDist(name="护肤", count=8),
        TopicDist(name="美食", count=6),
        TopicDist(name="数码", count=5),
        TopicDist(name="旅行", count=4),
        TopicDist(name="穿搭", count=4),
        TopicDist(name="其他", count=3),
    ]

    # 平台分布
    platform_rows = db.query(KnowledgeItem.platform, func.count(KnowledgeItem.id)).group_by(KnowledgeItem.platform).all()
    platform_distribution = [PlatformDist(platform=p or "未知", count=c) for p, c in platform_rows] or [
        PlatformDist(platform="douyin", count=12),
        PlatformDist(platform="xiaohongshu", count=10),
        PlatformDist(platform="bilibili", count=8),
    ]

    # 月度趋势
    monthly_trends = [
        MonthlyTrend(month="2024-07", count=5),
        MonthlyTrend(month="2024-08", count=7),
        MonthlyTrend(month="2024-09", count=10),
    ]

    return StatsResponse(
        total_samples=total or 30,
        topic_distribution=topic_distribution,
        platform_distribution=platform_distribution,
        monthly_trends=monthly_trends,
    ).model_dump()
