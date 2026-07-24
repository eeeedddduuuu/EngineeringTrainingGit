"""
知识库构建脚本

从 samples.xlsx 加载样例数据 → 清洗 → 分块 → Embedding → 存入 Chroma

用法：
    cd backend
    python ../scripts/build_knowledge_base.py          # 构建/重建知识库
    python ../scripts/build_knowledge_base.py --check  # 仅检查状态
"""
import sys
import argparse
from pathlib import Path

# 确保 backend/ 在 sys.path 中，以导入 app 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pandas as pd
from app.services.knowledge_base import kb_service


def build(args):
    """重建知识库"""
    samples_path = Path(__file__).resolve().parent.parent / "samples.xlsx"

    if not samples_path.exists():
        print(f"❌ 找不到样例数据文件: {samples_path}")
        sys.exit(1)

    # ── 1. 加载 ──
    print(f"📖 加载数据: {samples_path}")
    df = pd.read_excel(samples_path)
    print(f"   共 {len(df)} 条记录")

    # ── 2. 清洗: 拼接检索文本（标题 + 标签 + 内容摘要） ──
    df["search_text"] = df.apply(
        lambda r: (
            f"标题: {r.get('标题', '')}\n"
            f"标签: {r.get('标签/类别', '')}\n"
            f"平台: {r.get('平台', '')}\n"
            f"摘要: {r.get('内容摘要', '')}"
        ),
        axis=1,
    )

    documents = df["search_text"].tolist()

    # ── 3. 构建 metadata ──
    import json

    metadatas = []
    for _, r in df.iterrows():
        tags_str = str(r.get("标签/类别", ""))
        # 处理标签：可能是逗号分隔
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

        metadatas.append({
            "record_id": int(r.get("id", 0)),
            "title": str(r.get("标题", "")),
            "platform": str(r.get("平台", "")),
            "tags": json.dumps(tags, ensure_ascii=False),
            "source": str(r.get("来源", "")),
            "published_at": str(r.get("发布时间", "")),
        })

    # ── 4. 写入 Chroma ──
    print(f"🔨 开始构建知识库...")
    kb_service.reset()  # 清除旧数据
    kb_service.add_items(
        ids=[str(i) for i in range(len(documents))],
        documents=documents,
        metadatas=metadatas,
    )

    from app.config import CHROMA_DB_PATH
    print(f"✅ 知识库构建完成！共 {len(documents)} 条")
    print(f"   存储路径: {CHROMA_DB_PATH}")

    # ── 5. 快速验证 ──
    print("\n🔍 快速验证检索...")
    results = kb_service.search("短视频脚本创作", top_k=3)
    for i, r in enumerate(results, 1):
        print(f"   {i}. [{r.similarity:.3f}] {r.title}")


def check(args):
    """检查知识库状态"""
    exists = kb_service.collection_exists()
    print(f"知识库已构建: {'是 ✅' if exists else '否 ❌'}")
    if exists:
        col = kb_service.get_collection()
        print(f"条目数: {col.count()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI 创作助手知识库构建工具")
    parser.add_argument(
        "--check", action="store_true", help="仅检查知识库状态（不构建）"
    )
    args = parser.parse_args()

    if args.check:
        check(args)
    else:
        build(args)
