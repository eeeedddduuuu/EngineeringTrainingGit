"""知识库检索路由 — /api/knowledge/search"""
from fastapi import APIRouter, Query
from app.services.knowledge_base import kb_service
from app.schemas.knowledge import KnowledgeSearchResponse, KnowledgeResultItem

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    q: str = Query(..., min_length=1, description="检索关键词"),
    top_k: int = Query(5, ge=1, le=20, description="返回结果数量"),
):
    """
    知识库语义检索

    在 Chroma 向量库中根据语义相似度返回最相关的知识条目。
    每条结果包含标题、内容摘要、平台、标签、来源及相似度分数。
    """
    results = kb_service.search(q, top_k=top_k)

    return KnowledgeSearchResponse(
        query=q,
        results=[
            KnowledgeResultItem(
                id=r.id,
                title=r.title,
                content_snippet=r.content_snippet,
                platform=r.platform,
                tags=r.tags,
                source=r.source,
                published_at=r.published_at,
                similarity=r.similarity,
            )
            for r in results
        ],
    )
