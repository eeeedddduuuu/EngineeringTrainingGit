from typing import Optional
from pydantic import BaseModel, Field


class CreationRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255)
    target_audience: str = Field(..., min_length=1, max_length=100)
    platform: str = Field(..., pattern=r"^(douyin|xiaohongshu|bilibili)$")
    duration: str = Field(..., pattern=r"^(30s|60s|3min)$")
    style: str = Field(default="通用", max_length=100)
    provider: str = Field(default="mock", pattern=r"^(mock|deepseek|coze)$")
    image_url: Optional[str] = Field(default=None, max_length=1024)  # 多模态：素材图片 URL
    uploaded_file_ids: Optional[list[str]] = Field(default=None)  # 多模态：已上传文件ID列表


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending / processing / completed / failed
    progress: Optional[str]
    result: Optional[dict]


class CompareRequest(BaseModel):
    scheme_ids: list[int] = Field(..., min_length=2, max_length=3)
