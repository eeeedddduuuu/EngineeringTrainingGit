from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.business import CreationSession, Scheme
from app.schemas.scheme import SchemeBrief, SchemeDetail, SchemeListResponse, CompareRequest, CompareResponse
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["方案"])


@router.get("/schemes", response_model=SchemeListResponse)
def list_schemes(session_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取某次会话的所有方案"""
    session = db.query(CreationSession).filter(
        CreationSession.id == session_id,
        CreationSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "会话不存在"})

    schemes = db.query(Scheme).filter(Scheme.session_id == session_id).order_by(Scheme.rank).all()
    return SchemeListResponse(
        session_id=session.id,
        topic=session.topic,
        platform=session.platform,
        created_at=str(session.created_at),
        schemes=[SchemeBrief(id=s.id, version=s.version, title=s.title, hook=s.hook, score=s.score or 0, rank=s.rank or 0) for s in schemes]
    ).model_dump()


@router.get("/scheme/{scheme_id}", response_model=SchemeDetail)
def get_scheme(scheme_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取单个方案详情"""
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "方案不存在"})

    # 校验归属
    session = db.query(CreationSession).filter(CreationSession.id == scheme.session_id).first()
    if session and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={"error": "forbidden", "detail": "无权访问此方案"})

    return SchemeDetail(
        id=scheme.id, session_id=scheme.session_id, version=scheme.version,
        title=scheme.title, hook=scheme.hook, scenes=scheme.scenes,
        storyboard_json=scheme.storyboard_json, hashtags=scheme.hashtags,
        cover_text=scheme.cover_text, score=scheme.score or 0, rank=scheme.rank or 0,
        recommendation_reason=scheme.recommendation_reason,
    ).model_dump()


@router.post("/schemes/compare", response_model=CompareResponse)
def compare_schemes(req: CompareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A/B 方案对比"""
    schemes = db.query(Scheme).filter(Scheme.id.in_(req.scheme_ids)).all()
    if len(schemes) < 2:
        raise HTTPException(status_code=400, detail={"error": "invalid_request", "detail": "需要至少2个有效方案ID"})

    details = []
    for s in schemes:
        details.append(SchemeDetail(
            id=s.id, session_id=s.session_id, version=s.version,
            title=s.title, hook=s.hook, scenes=s.scenes,
            storyboard_json=s.storyboard_json, hashtags=s.hashtags,
            cover_text=s.cover_text, score=s.score or 0, rank=s.rank or 0,
            recommendation_reason=s.recommendation_reason,
        ))

    best = max(schemes, key=lambda x: x.score or 0)
    worst = min(schemes, key=lambda x: x.score or 0)
    diff = (best.score or 0) - (worst.score or 0)
    diff_summary = f"{best.version}方案综合得分最高({best.score})，在开头吸引力和结构紧凑度方面表现更优（领先{diff:.1f}分）。"

    return CompareResponse(schemes=details, diff_summary=diff_summary).model_dump()
