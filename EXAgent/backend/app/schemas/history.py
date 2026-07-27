from pydantic import BaseModel
from typing import Optional


class HistoryItem(BaseModel):
    session_id: int
    topic: str
    platform: str
    status: str
    scheme_count: int
    created_at: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    size: int
