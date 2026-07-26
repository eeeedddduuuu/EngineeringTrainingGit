from pydantic import BaseModel, Field
from typing import Optional


class SchemeBrief(BaseModel):
    """方案摘要（列表用，含完整数据供前端渲染）"""
    id: int
    version: str
    title: Optional[str] = None
    hook: Optional[str] = None
    scenes: Optional[list] = None
    hashtags: Optional[list] = None
    cover_text: Optional[str] = None
    storyboard_json: Optional[dict] = None
    score: float = 0.0
    rank: int = 0
    recommendation_reason: Optional[str] = None


class SceneDetail(BaseModel):
    seq: int
    type: str = ""
    duration: str = ""
    description: str = ""
    voiceover: str = ""


class SchemeDetail(BaseModel):
    """方案详情"""
    id: int
    session_id: int
    version: str
    title: Optional[str] = None
    hook: Optional[str] = None
    scenes: Optional[list] = None
    storyboard_json: Optional[dict] = None
    hashtags: Optional[list] = None
    cover_text: Optional[str] = None
    score: float = 0.0
    rank: int = 0
    recommendation_reason: Optional[str] = None


class SchemeListResponse(BaseModel):
    session_id: int
    topic: str
    platform: str
    created_at: str
    schemes: list[SchemeBrief]


class CompareRequest(BaseModel):
    scheme_ids: list[int] = Field(..., min_length=2, max_length=3)


class CompareResponse(BaseModel):
    schemes: list[SchemeDetail]
    diff_summary: str = ""
