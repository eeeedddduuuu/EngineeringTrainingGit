"""知识库检索 Schema（与 docs/api_schema.md 严格一致）"""
from typing import Optional
from pydantic import BaseModel


class KnowledgeResult(BaseModel):
    id: int
    title: str
    content_snippet: str
    platform: Optional[str] = None
    tags: Optional[list] = None
    source: Optional[str] = None
    published_at: Optional[str] = None
    similarity: float = 0.0


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeResult]
