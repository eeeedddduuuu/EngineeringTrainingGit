"""知识库 & 统计 相关 Pydantic Schema"""
from pydantic import BaseModel, Field


# ── 知识库检索 ──────────────────────────────────────────

class KnowledgeResultItem(BaseModel):
    id: int
    title: str
    content_snippet: str
    platform: str
    tags: list[str]
    source: str
    published_at: str
    similarity: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeResultItem]


# ── 统计看板 ────────────────────────────────────────────

class TopicDistribution(BaseModel):
    name: str
    count: int


class PlatformDistribution(BaseModel):
    platform: str
    count: int


class MonthlyTrend(BaseModel):
    month: str
    count: int


class StatsResponse(BaseModel):
    total_samples: int
    topic_distribution: list[TopicDistribution]
    platform_distribution: list[PlatformDistribution]
    monthly_trends: list[MonthlyTrend]
