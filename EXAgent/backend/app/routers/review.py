from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.business import Review, Scheme
from app.schemas.review import ReviewRequest, ReviewResponse
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["审核"])


@router.get("/reviews")
def list_reviews(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, pattern=r"^(pending|approved|rejected)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    审核列表（P2 审核看板使用）

    支持按状态筛选 + 分页，返回审核记录含关联方案信息
    """
    q = db.query(Review)

    if status:
        q = q.filter(Review.status == status)

    total = q.count()
    reviews = q.order_by(Review.created_at.desc()).offset((page - 1) * size).limit(size).all()

    items = []
    for r in reviews:
        scheme = db.query(Scheme).filter(Scheme.id == r.scheme_id).first()
        items.append({
            "id": r.id,
            "scheme_id": r.scheme_id,
            "scheme_title": scheme.title if scheme else "",
            "scheme_version": scheme.version if scheme else "",
            "reviewer_id": r.reviewer_id,
            "status": r.status,
            "comment": r.comment,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items,
    }


@router.post("/review", response_model=ReviewResponse)
def create_review(req: ReviewRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """提交审核意见"""
    scheme = db.query(Scheme).filter(Scheme.id == req.scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "方案不存在"})

    review = Review(
        scheme_id=req.scheme_id,
        reviewer_id=current_user.id,
        status=req.status,
        comment=req.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return ReviewResponse(
        id=review.id, scheme_id=review.scheme_id, reviewer_id=review.reviewer_id,
        status=review.status, comment=review.comment, created_at=str(review.created_at),
    ).model_dump()


@router.put("/review/{review_id}", response_model=ReviewResponse)
def update_review(review_id: int, req: ReviewRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """修改审核意见"""
    review = db.query(Review).filter(Review.id == review_id, Review.reviewer_id == current_user.id).first()
    if not review:
        raise HTTPException(status_code=404, detail={"error": "not_found", "detail": "审核记录不存在或无权修改"})

    review.status = req.status
    review.comment = req.comment
    db.commit()
    db.refresh(review)

    return ReviewResponse(
        id=review.id, scheme_id=review.scheme_id, reviewer_id=review.reviewer_id,
        status=review.status, comment=review.comment, created_at=str(review.created_at),
    ).model_dump()
