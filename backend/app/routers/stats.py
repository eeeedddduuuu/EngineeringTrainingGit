"""统计看板路由 — 基于 samples.xlsx 真实数据 + 数据库实时统计

来源：P5 feature/data-kb-v2（50条样本，25个月数据）
集成：P3 添加 JWT 认证依赖 + 合并到 feature/backend
"""
import base64
import random
import time
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

import jieba
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from wordcloud import WordCloud

from app.database import get_db
from app.models.user import User
from app.models.business import CreationSession, Scheme, Review
from app.schemas.stats import StatsResponse, TopicDist, PlatformDist, MonthlyTrend, DashboardSummary, WordCloudResponse, WordCloudItem
from app.utils.deps import get_current_user

jieba.setLogLevel(20)

router = APIRouter(prefix="/api", tags=["统计"])

SAMPLES_PATH = Path(__file__).parent.parent.parent.parent / "samples.xlsx"


def _load_samples() -> pd.DataFrame:
    """加载样例数据，模块级缓存"""
    if not hasattr(_load_samples, "_cache"):
        if SAMPLES_PATH.exists():
            df = pd.read_excel(SAMPLES_PATH)
            if "发布时间" in df.columns:
                df["发布时间"] = pd.to_datetime(df["发布时间"], errors="coerce")
            _load_samples._cache = df
        else:
            _load_samples._cache = pd.DataFrame()
    return _load_samples._cache


@router.get("/stats/samples", response_model=StatsResponse)
def get_stats(current_user: User = Depends(get_current_user)):
    """
    样例数据统计接口（基于 50 条真实样本）

    返回：
    - total_samples: 样本总数
    - topic_distribution: 主题/类别分布
    - platform_distribution: 平台分布（抖音/小红书/B站）
    - monthly_trends: 月度发布趋势（25个月）
    """
    df = _load_samples()

    if df.empty:
        return StatsResponse(
            total_samples=0,
            topic_distribution=[],
            platform_distribution=[],
            monthly_trends=[],
        )

    topic_col = "标签/类别" if "标签/类别" in df.columns else None
    platform_col = "平台" if "平台" in df.columns else None

    # ── 主题分布 ──
    topic_distribution: list[TopicDist] = []
    if topic_col:
        topic_counts = df[topic_col].value_counts().to_dict()
        topic_distribution = [
            TopicDist(name=str(k), count=v) for k, v in topic_counts.items()
        ]

    # ── 平台分布 ──
    platform_distribution: list[PlatformDist] = []
    if platform_col:
        platform_counts = df[platform_col].value_counts().to_dict()
        platform_distribution = [
            PlatformDist(platform=str(k), count=v)
            for k, v in platform_counts.items()
        ]

    # ── 月度趋势 ──
    monthly_trends: list[MonthlyTrend] = []
    if "发布时间" in df.columns and df["发布时间"].notna().any():
        monthly = (
            df.dropna(subset=["发布时间"])
            .set_index("发布时间")
            .resample("ME")
            .size()
        )
        monthly_trends = [
            MonthlyTrend(month=idx.strftime("%Y-%m"), count=int(v))
            for idx, v in monthly.items()
        ]

    return StatsResponse(
        total_samples=len(df),
        topic_distribution=topic_distribution,
        platform_distribution=platform_distribution,
        monthly_trends=monthly_trends,
    )


@router.get("/statistics/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    看板汇总统计（P2 前端数据看板使用）

    返回：
    - total_sessions: 总创作会话数
    - in_progress: 进行中的会话数
    - pending_review: 待审核方案数
    - completed_this_week: 本周完成的会话数
    - total_schemes: 方案总数
    - total_users: 注册用户总数
    """
    now = datetime.utcnow()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    total_sessions = db.query(func.count(CreationSession.id)).scalar() or 0
    in_progress = db.query(func.count(CreationSession.id)).filter(
        CreationSession.status == "processing"
    ).scalar() or 0
    pending_review = db.query(func.count(Scheme.id)).filter(
        Scheme.id.in_(db.query(Review.scheme_id).filter(Review.status == "pending"))
    ).scalar() or 0
    completed_this_week = db.query(func.count(CreationSession.id)).filter(
        CreationSession.status == "completed",
        CreationSession.created_at >= week_start,
    ).scalar() or 0
    total_schemes = db.query(func.count(Scheme.id)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0

    return DashboardSummary(
        total_sessions=total_sessions,
        in_progress=in_progress,
        pending_review=pending_review,
        completed_this_week=completed_this_week,
        total_schemes=total_schemes,
        total_users=total_users,
    )


# ── 中文停用词表 ──
_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
    "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
    "自己", "这", "他", "她", "它", "们", "那", "及", "与", "或", "等", "为", "以",
    "将", "对", "把", "被", "从", "让", "但", "而", "且", "所", "如", "之", "其",
    "可以", "这个", "那个", "已经", "还是", "这些", "那些", "因为", "所以", "如果",
    "虽然", "然而", "然后", "之后", "之前", "能够", "需要", "应该",
    "通过", "进行", "使用", "一种", "每个", "一些", "许多", "其他",
    "中", "更", "较", "最", "非常", "十分", "特别", "真正", "完全", "更加",
    "还", "再", "又", "才", "只", "便", "即", "却", "仍", "亦", "尚", "未", "无", "非",
}

# ── 中文字体路径探测 ──
def _detect_cjk_font():  # -> Optional[str]
    """探测系统中可用的中文字体"""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",      # Microsoft YaHei
        "C:/Windows/Fonts/simhei.ttf",     # SimHei
        "C:/Windows/Fonts/simsun.ttc",     # SimSun
        "C:/Windows/Fonts/STKAITI.TTF",    # KaiTi
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


@router.get("/stats/wordclouds", response_model=WordCloudResponse)
def get_wordclouds(current_user: User = Depends(get_current_user)):
    """
    词云接口 — 基于 samples.xlsx 的中文分词生成两张词云 PNG。

    返回 base64 编码的 PNG 图片列表：
    - 🏷️ 标题关键词云
    - 📝 内容摘要词云
    """
    df = _load_samples()

    if df.empty:
        return WordCloudResponse(wordclouds=[])

    font_path = _detect_cjk_font()
    # 暖色调调色板（与前端 warm earth-tone 一致）
    WC_COLORS = ["#d48c5c", "#c08050", "#b87040", "#a0724a", "#8a6a4a", "#c9976b"]

    result: list[WordCloudItem] = []

    for wc_label, col_name in [
        ("🏷️ 标题关键词云", "标题"),
        ("📝 内容摘要词云", "内容摘要"),
    ]:
        if col_name not in df.columns:
            continue

        text = " ".join(df[col_name].dropna().astype(str).tolist())
        if not text.strip():
            continue

        words = [
            w.strip() for w in jieba.cut(text)
            if len(w.strip()) >= 2 and w.strip() not in _STOPWORDS
        ]
        if not words:
            continue

        wc = WordCloud(
            width=600,
            height=380,
            background_color="#fcf9f5",
            font_path=font_path,
            max_words=80,
            collocations=False,
            margin=10,
            prefer_horizontal=0.75,
            color_func=lambda *a, **kw: random.choice(WC_COLORS),
        )
        wc.generate(" ".join(words))

        buf = BytesIO()
        wc.to_image().save(buf, format="PNG")
        result.append(WordCloudItem(
            label=wc_label,
            base64=base64.b64encode(buf.getvalue()).decode(),
        ))

    return WordCloudResponse(wordclouds=result)
