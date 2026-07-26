from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float
from app.database import Base


class CreationSession(Base):
    """创作会话表"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(255), nullable=False)
    target_audience = Column(String(100))
    platform = Column(String(50), nullable=False)       # douyin / xiaohongshu / bilibili
    duration = Column(String(10), nullable=False)        # 30s / 60s / 3min
    style = Column(String(100))
    image_url = Column(String(1024))                     # 多模态素材图片 URL（可选）
    status = Column(String(20), default="pending")       # pending / processing / completed / failed
    created_at = Column(DateTime, default=datetime.utcnow)


class Scheme(Base):
    """创作方案表（一次会话生成多个候选方案）"""
    __tablename__ = "schemes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    version = Column(String(1), nullable=False)          # A / B / C
    title = Column(String(255))
    hook = Column(String(500))
    scenes = Column(JSON)                                # [{"seq":1, "type":"...", ...}]
    storyboard_json = Column(JSON)                       # 分镜表 JSON
    hashtags = Column(JSON)                              # ["#tag1", ...]
    cover_text = Column(String(500))
    score = Column(Float, default=0.0)
    rank = Column(Integer, default=0)
    recommendation_reason = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentLog(Base):
    """Agent 调用日志表"""
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    agent_name = Column(String(50), nullable=False)      # trend / script / review / strategy
    input_json = Column(JSON)
    output_json = Column(JSON)
    tools_called = Column(JSON)
    latency_ms = Column(Integer)
    tokens_used = Column(Integer)
    status = Column(String(20), default="success")       # success / failed
    error_message = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeItem(Base):
    """知识库条目表"""
    __tablename__ = "knowledge_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(String(2000))
    tags = Column(JSON)
    platform = Column(String(50))
    source = Column(String(255))
    source_url = Column(String(500))
    embedding_id = Column(String(100))
    published_at = Column(DateTime)
    collected_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    """审核记录表"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scheme_id = Column(Integer, ForeignKey("schemes.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")       # pending / approved / rejected
    comment = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
