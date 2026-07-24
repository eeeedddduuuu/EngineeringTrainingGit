"""知识库检索路由 — Chroma 向量语义检索

P3 对接说明：
  - 核心逻辑在 services/knowledge_base.py 的 kb_service.search()
  - 本路由直接调用该服务，P3 集成时只需在依赖链中加入 get_current_user 即可
"""
from fastapi import APIRouter, Query
from app.services.knowledge_base import kb_service
from app.schemas.knowledge import KnowledgeResult, KnowledgeSearchResponse

router = APIRouter(prefix="/api", tags=["知识库"])


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    q: str = Query(..., min_length=1, description="检索关键词"),
    top_k: int = Query(5, ge=1, le=20, description="返回结果数量"),
):
    """
    知识库语义检索（Chroma 向量检索）

    使用 bge-small-zh-v1.5 做文本 Embedding，
    在 Chroma 向量库中按余弦相似度返回最相关的 Top-K 知识条目。
    每条结果包含 title、content_snippet、platform、tags、source、similarity。

    P3 集成备忘：加入认证依赖
      current_user: User = Depends(get_current_user)
    """
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
