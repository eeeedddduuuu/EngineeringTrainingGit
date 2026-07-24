"""
数据库初始化脚本
用法: python init_db.py
功能: 创建所有表 + 插入种子数据（示例知识库条目）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.business import CreationSession, Scheme, AgentLog, KnowledgeItem, Review
from app.utils.security import hash_password


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
            preferences={"platforms": ["douyin", "xiaohongshu"], "content_types": ["护肤", "美食"], "style": "干货+轻松"}
        )
        db.add(test_user)
        print("      测试用户 test/123456 创建完成 [OK]")

    # 插入样例知识库条目
    if db.query(KnowledgeItem).count() == 0:
        samples = [
            {"title": "3个秋季护肤误区，你中了几个？", "content": "前3秒指出常见误区 → 逐一分析 → 推荐产品，结尾引导互动。核心要点：用对比方式突出误区与正确做法。", "tags": ["护肤", "干货", "好物推荐"], "platform": "douyin", "source": "抖音 @护肤达人小李"},
            {"title": "开学季宿舍好物清单｜学妹必看", "content": "开头展示杂乱宿舍 vs 改造后对比 → 逐件介绍好物 → 价格透明 → 使用效果展示。", "tags": ["好物推荐", "学生党", "宿舍"], "platform": "xiaohongshu", "source": "小红书 @生活家小王"},
            {"title": "2024秋冬季护肤趋势分析", "content": "权威数据开头 → 3大趋势逐一解读 → 品牌案例 → 实战建议。强调成分党和功效护肤。", "tags": ["护肤", "趋势", "秋冬"], "platform": "bilibili", "source": "B站 @美妆情报局"},
            {"title": "5分钟懒人早餐｜上班族必备", "content": "快速展示成品 → 分步食材准备 → 烹饪过程（倍速） → 成品展示 → 营养分析。", "tags": ["美食", "快手菜", "上班族"], "platform": "douyin", "source": "抖音 @厨房小白"},
            {"title": "iPhone 16 Pro 深度评测：值不值得买？", "content": "参数对比开场 → 外观/性能/续航/影像四大维度 → 竞品对比 → 购买建议。", "tags": ["数码", "评测", "手机"], "platform": "bilibili", "source": "B站 @科技评测室"},
            {"title": "大理3天2夜旅行攻略｜人均1500", "content": "行程总览 → Day1/2/3逐日详解 → 美食推荐 → 住宿建议 → 避坑指南。", "tags": ["旅行", "攻略", "大理"], "platform": "xiaohongshu", "source": "小红书 @旅行日记"},
            {"title": "秋天第一套穿搭｜2024流行色搭配", "content": "流行色解读 → 3套完整搭配展示 → 单品链接 → 价位选择 → 身材适配建议。", "tags": ["穿搭", "秋季", "流行色"], "platform": "xiaohongshu", "source": "小红书 @穿搭师CC"},
            {"title": "空气炸锅食谱合集｜10道懒人美食", "content": "开头展示10道成品 → 每道1分钟快速教程 → 时间温度总结表 → 避雷指南。", "tags": ["美食", "空气炸锅", "懒人"], "platform": "douyin", "source": "抖音 @美食工坊"},
            {"title": "2024双11数码好物推荐清单", "content": "价格对比图开场 → 按品类逐一推荐 → 历史最低价标注 → 购买渠道建议。", "tags": ["数码", "双11", "购物清单"], "platform": "douyin", "source": "抖音 @数码指南"},
            {"title": "敏感肌换季护肤全攻略｜皮肤科医生推荐", "content": "敏感肌特征自测 → 换季护肤4步法 → 产品成分解读 → 避雷成分清单。", "tags": ["护肤", "敏感肌", "换季"], "platform": "xiaohongshu", "source": "小红书 @皮肤科陈医生"},
        ]
        for s in samples:
            db.add(KnowledgeItem(
                title=s["title"], content=s["content"], tags=s["tags"],
                platform=s["platform"], source=s["source"]
            ))
        print(f"      {len(samples)} 条样例知识库条目插入完成 [OK]")

    db.commit()
    db.close()

    # 3. 输出摘要
    print(f"[3/3] 初始化完成！")
    print(f"      数据库路径: app.db")
    print(f"      测试账号: test / 123456")
    print(f"      知识库条目: {len(samples)} 条")


if __name__ == "__main__":
    init_database()
