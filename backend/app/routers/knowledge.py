from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.business import KnowledgeItem
from app.schemas.knowledge import KnowledgeResult, KnowledgeSearchResponse
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["知识库"])


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """知识库关键词检索（简易版，进阶后接 Chroma 向量检索）"""
    # 简易全文搜索（生产环境应使用向量检索）
    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.title.contains(q) | KnowledgeItem.content.contains(q)
    ).limit(top_k).all()

    results = []
    for item in items:
        snippet = (item.content or "")[:200]
        results.append(KnowledgeResult(
            id=item.id,
            title=item.title,
            content_snippet=snippet,
            platform=item.platform,
            tags=item.tags,
            source=item.source,
            published_at=str(item.published_at) if item.published_at else None,
            similarity=0.85,  # 简易检索无相似度分数
        ))

    return KnowledgeSearchResponse(query=q, results=results).model_dump()
