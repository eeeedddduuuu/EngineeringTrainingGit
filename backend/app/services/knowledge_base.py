"""
Chroma 知识库服务
- 使用 sentence-transformers 做文本 Embedding
- 基于 Chroma 向量数据库做相似度检索
"""
import os
from dataclasses import dataclass
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config import CHROMA_DB_PATH


@dataclass
class KnowledgeResult:
    """知识库检索单条结果"""
    id: int
    title: str
    content_snippet: str
    platform: str
    tags: list[str]
    source: str
    published_at: str
    similarity: float


class KnowledgeBaseService:
    """Chroma 知识库服务（单例模式）"""

    _instance: Optional["KnowledgeBaseService"] = None

    def __new__(cls) -> "KnowledgeBaseService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 中文 Embedding 模型
        self._model_name = os.getenv(
            "EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"
        )
        self._embedding_model: Optional[SentenceTransformer] = None

        # Chroma 客户端
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    # ------------------------------------------------------------------
    # Embedding 模型（懒加载，避免启动时下载大文件）
    # ------------------------------------------------------------------
    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            print(f"[KnowledgeBase] 加载 Embedding 模型: {self._model_name}")
            self._embedding_model = SentenceTransformer(self._model_name)
        return self._embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转为向量列表"""
        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    # ------------------------------------------------------------------
    # 集合管理
    # ------------------------------------------------------------------
    @property
    def collection_name(self) -> str:
        return "knowledge_items"

    def get_collection(self):
        """获取或创建 Chroma collection"""
        return self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def collection_exists(self) -> bool:
        """检查 collection 是否已存在且有数据"""
        try:
            col = self._client.get_collection(self.collection_name)
            return col.count() > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------
    def add_items(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
    ):
        """批量写入知识条目（自动 Embedding）"""
        collection = self.get_collection()
        embeddings = self.embed(documents)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        print(f"[KnowledgeBase] 已写入 {len(ids)} 条记录")

    def reset(self):
        """删除旧 collection（重建用）"""
        try:
            self._client.delete_collection(self.collection_name)
            print(f"[KnowledgeBase] 已删除旧 collection: {self.collection_name}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[KnowledgeResult]:
        """
        相似度检索

        Args:
            query: 查询文本
            top_k: 返回 Top-K 结果

        Returns:
            按相似度降序排列的结果列表
        """
        if not query.strip():
            return []

        collection = self.get_collection()

        if collection.count() == 0:
            return []

        query_embedding = self.embed([query])[0]

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        items: list[KnowledgeResult] = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            # cosine distance → similarity (0~1)
            similarity = 1.0 - distance

            # 截取 content_snippet（最多 200 字符）
            doc = results["documents"][0][i] or ""
            snippet = doc[:200] + ("..." if len(doc) > 200 else "")

            # tags 在 Chroma metadata 中以 JSON 字符串存储，需反序列化
            raw_tags = meta.get("tags", "[]")
            if isinstance(raw_tags, str):
                import json
                try:
                    parsed_tags = json.loads(raw_tags)
                except (json.JSONDecodeError, TypeError):
                    parsed_tags = []
            else:
                parsed_tags = raw_tags if isinstance(raw_tags, list) else []

            items.append(KnowledgeResult(
                id=int(meta.get("record_id", 0)),
                title=meta.get("title", ""),
                content_snippet=snippet,
                platform=meta.get("platform", ""),
                tags=parsed_tags,
                source=meta.get("source", ""),
                published_at=meta.get("published_at", ""),
                similarity=round(similarity, 4),
            ))

        # 按相似度降序排列
        items.sort(key=lambda x: x.similarity, reverse=True)
        return items


# 全局单例
kb_service = KnowledgeBaseService()
