from pydantic import BaseModel, Field
from typing import Optional


class ReviewRequest(BaseModel):
    scheme_id: int
    status: str = Field(..., pattern=r"^(approved|rejected)$")
    comment: Optional[str] = Field(default=None, max_length=1000)


class ReviewResponse(BaseModel):
    id: int
    scheme_id: int
    reviewer_id: int
    status: str
    comment: Optional[str] = None
    created_at: str
