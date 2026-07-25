"""
数据库初始化脚本
用法: python init_db.py
功能: 创建所有表 + 插入种子数据（P5 50条知识库样本 + 测试用户）
数据来源: samples.xlsx（P5 提供，50条真实短视频内容样本）
"""
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.business import CreationSession, Scheme, AgentLog, KnowledgeItem, Review
from app.utils.security import hash_password


def _load_samples_from_excel():
    """从 samples.xlsx 加载 P5 的 50 条知识库样本。
    返回 list[dict]，字段与 KnowledgeItem 模型对齐。
    xlsx 列: id | 标题 | 标签/分类 | 平台 | 发布时间 | 来源 | 内容摘要
    """
    xlsx_path = Path(__file__).parent.parent / "samples.xlsx"
    if not xlsx_path.exists():
        print(f"      [WARN] samples.xlsx 未找到 ({xlsx_path})，跳过知识库导入")
        return []

    try:
        import pandas as pd
    except ImportError:
        print("      [WARN] pandas 未安装，跳过知识库导入")
        return []

    df = pd.read_excel(xlsx_path)
    samples = []
    for _, row in df.iterrows():
        # 列位置映射（避免中文列名编码问题）
        title = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
        tags_raw = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
        platform_raw = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
        pub_date = row.iloc[4] if pd.notna(row.iloc[4]) else None
        source = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ""
        content = str(row.iloc[6]) if pd.notna(row.iloc[6]) else ""

        # 标签解析：支持 "/" 或 "," 分隔
        tags = [t.strip() for t in tags_raw.replace(",", "/").split("/") if t.strip()]

        # 平台名规范化
        platform_map = {
            "B站": "bilibili",
            "bilibili": "bilibili",
            "抖音": "douyin",
            "douyin": "douyin",
            "小红书": "xiaohongshu",
            "xiaohongshu": "xiaohongshu",
            "快手": "kuaishou",
            "kuaishou": "kuaishou",
        }
        platform = platform_map.get(platform_raw, platform_raw.lower())

        # 发布时间解析
        published_at = None
        if pub_date is not None:
            try:
                published_at = pd.Timestamp(pub_date).to_pydatetime()
            except Exception:
                pass

        samples.append({
            "title": title,
            "content": content,
            "tags": tags,
            "platform": platform,
            "source": source,
            "published_at": published_at,
        })

    return samples


def init_database():
    print("=== 数据库初始化 ===")

    # 1. 创建所有表
    print("[1/3] 创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("      所有表创建完成 [OK]")

    # 2. 插入种子数据
    print("[2/3] 插入种子数据...")
    db = SessionLocal()

    # 创建测试用户
    if db.query(User).count() == 0:
        test_user = User(
            username="test",
            password_hash=hash_password("123456"),
            email="test@example.com",
            preferences={
                "platforms": ["douyin", "xiaohongshu"],
                "content_types": ["护肤", "美食"],
                "style": "干货+轻松",
            },
        )
        db.add(test_user)
        print("      测试用户 test/123456 创建完成 [OK]")

    # 从 P5 的 samples.xlsx 加载知识库条目
    if db.query(KnowledgeItem).count() == 0:
        samples = _load_samples_from_excel()
        if samples:
            for s in samples:
                db.add(KnowledgeItem(
                    title=s["title"],
                    content=s["content"],
                    tags=s["tags"],
                    platform=s["platform"],
                    source=s["source"],
                    published_at=s["published_at"],
                ))
            print(f"      P5 知识库样本 {len(samples)} 条插入完成 [OK]")
        else:
            print("      [SKIP] 未找到有效样本数据")
    else:
        print("      知识库条目已存在，跳过导入")

    db.commit()
    db.close()

    # 3. 输出摘要
    print(f"[3/3] 初始化完成！")
    print(f"      数据库路径: backend/app.db")
    print(f"      测试账号: test / 123456")
    # 重新打开只读连接统计实际条数
    db2 = SessionLocal()
    count = db2.query(KnowledgeItem).count()
    db2.close()
    print(f"      知识库条目: {count} 条")


if __name__ == "__main__":
    init_database()
