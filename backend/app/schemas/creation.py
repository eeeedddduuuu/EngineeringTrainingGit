from pydantic import BaseModel, Field


class CreationRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255)
    target_audience: str = Field(..., min_length=1, max_length=100)
    platform: str = Field(..., pattern=r"^(douyin|xiaohongshu|bilibili)$")
    duration: str = Field(..., pattern=r"^(30s|60s|3min)$")
    style: str = Field(default="通用", max_length=100)


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending / processing / completed / failed
    progress: str | None
    result: dict | None


class CompareRequest(BaseModel):
    scheme_ids: list[int] = Field(..., min_length=2, max_length=3)
