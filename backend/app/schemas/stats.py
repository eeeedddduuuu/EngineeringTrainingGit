"""统计看板 Schema（与 docs/api_schema.md 严格一致）"""
from pydantic import BaseModel


class TopicDist(BaseModel):
    name: str
    count: int


class PlatformDist(BaseModel):
    platform: str
    count: int


class MonthlyTrend(BaseModel):
    month: str
    count: int


class StatsResponse(BaseModel):
    total_samples: int
    topic_distribution: list[TopicDist]
    platform_distribution: list[PlatformDist]
    monthly_trends: list[MonthlyTrend]
