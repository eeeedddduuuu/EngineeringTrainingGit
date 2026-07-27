from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.business import CreationSession, Scheme
from app.schemas.history import HistoryItem, HistoryResponse
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["历史"])


@router.get("/history", response_model=HistoryResponse)
def get_history(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页获取当前用户的历史创作会话"""
    total = db.query(func.count(CreationSession.id)).filter(
        CreationSession.user_id == current_user.id
    ).scalar()

    sessions = db.query(CreationSession).filter(
        CreationSession.user_id == current_user.id
    ).order_by(CreationSession.created_at.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for s in sessions:
        scheme_count = db.query(func.count(Scheme.id)).filter(Scheme.session_id == s.id).scalar()
        items.append(HistoryItem(
            session_id=s.id, topic=s.topic, platform=s.platform,
            status=s.status, scheme_count=scheme_count,
            created_at=str(s.created_at),
        ))

    return HistoryResponse(items=items, total=total, page=page, size=size).model_dump()
