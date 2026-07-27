"""知识库检索路由 — Chroma 向量语义检索

来源：P5 feature/data-kb-v2（Chroma + bge-small-zh-v1.5）
集成：P3 添加 JWT 认证依赖 + 懒加载防止启动阻塞
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.user import User
from app.schemas.knowledge import KnowledgeResult, KnowledgeSearchResponse
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api", tags=["知识库"])


def _get_kb_service():
    """懒加载知识库服务（避免 chromadb 未安装时阻塞启动）"""
    try:
        from app.services.knowledge_base import kb_service
        return kb_service
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "knowledge_unavailable", "detail": f"知识库服务暂不可用: {e}"},
        )


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    q: str = Query(..., min_length=1, description="检索关键词"),
    top_k: int = Query(5, ge=1, le=20, description="返回结果数量"),
    current_user: User = Depends(get_current_user),
):
    """
    知识库语义检索（Chroma 向量检索 + bge-small-zh-v1.5 Embedding）
    返回按余弦相似度降序的 Top-K 知识条目。
    """
    kb_service = _get_kb_service()
    results = kb_service.search(q, top_k=top_k)

    return KnowledgeSearchResponse(
        query=q,
        results=[
            KnowledgeResult(
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
