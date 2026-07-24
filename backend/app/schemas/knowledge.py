from pydantic import BaseModel
from typing import Optional


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
