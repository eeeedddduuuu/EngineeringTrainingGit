from pydantic import BaseModel
from typing import Optional


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


class DashboardSummary(BaseModel):
    total_sessions: int          # 总项目
    in_progress: int             # 进行中
    pending_review: int          # 待审核
    completed_this_week: int     # 本周完成
    total_schemes: int           # 方案总数
    total_users: int             # 用户总数


class WordCloudItem(BaseModel):
    label: str                   # 词云标题，如 "标题关键词云"
    base64: str                  # PNG base64 编码


class WordCloudResponse(BaseModel):
    wordclouds: list[WordCloudItem]
