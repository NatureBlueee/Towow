"""
Database - SQLite + SQLAlchemy 数据层

提供用户持久化存储和协商历史持久化（ADR-007）。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# 数据库路径
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "app.db"

# SQLAlchemy 基类
Base = declarative_base()


# ============ 模型定义 ============

class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    skills = Column(JSON, default=list)  # List[str]
    specialties = Column(JSON, default=list)  # List[str]
    secondme_id = Column(String(128), index=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    self_intro = Column(Text, nullable=True)

    # 开放注册字段 (ADR-009)
    email = Column(String(256), nullable=True, unique=True, index=True)
    phone = Column(String(32), nullable=True)
    subscribe = Column(Boolean, default=False)
    raw_profile_text = Column(Text, nullable=True)
    source = Column(String(32), default="secondme")  # secondme | playground | mcp

    # OAuth2 Token 存储
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "skills": self.skills or [],
            "specialties": self.specialties or [],
            "secondme_id": self.secondme_id,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "self_intro": self.self_intro,
            "email": self.email,
            "phone": self.phone,
            "subscribe": self.subscribe,
            "raw_profile_text": self.raw_profile_text,
            "source": self.source,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NegotiationHistory(Base):
    """协商历史主记录（ADR-007）"""
    __tablename__ = "negotiation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    negotiation_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)  # agent_id
    scene_id = Column(String(64), index=True)
    demand_text = Column(Text, nullable=False)               # 用户原始输入
    demand_mode = Column(String(20), default="manual")       # manual | surprise | polish
    assist_output = Column(Text, nullable=True)              # "通向惊喜"生成的文本
    formulated_text = Column(Text, nullable=True)            # 丰富化后的需求
    status = Column(String(20), default="pending")           # pending | negotiating | completed | failed
    plan_output = Column(Text, nullable=True)                # 方案文本
    plan_json = Column(JSON, nullable=True)                  # 方案结构化数据
    center_rounds = Column(Integer, default=0)
    scope = Column(String(64), default="all")
    agent_count = Column(Integer, default=0)
    chain_ref = Column(String(128), nullable=True)           # 链上 Machine address (ADR-006)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    offers = relationship("NegotiationOffer", back_populates="negotiation", lazy="select")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "negotiation_id": self.negotiation_id,
            "user_id": self.user_id,
            "scene_id": self.scene_id,
            "demand_text": self.demand_text,
            "demand_mode": self.demand_mode,
            "assist_output": self.assist_output,
            "formulated_text": self.formulated_text,
            "status": self.status,
            "plan_output": self.plan_output,
            "plan_json": self.plan_json,
            "center_rounds": self.center_rounds,
            "scope": self.scope,
            "agent_count": self.agent_count,
            "chain_ref": self.chain_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NegotiationOffer(Base):
    """协商 Offer 详情（ADR-007）"""
    __tablename__ = "negotiation_offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    negotiation_id = Column(
        String(64),
        ForeignKey("negotiation_history.negotiation_id"),
        nullable=False,
        index=True,
    )
    agent_id = Column(String(64), nullable=False)
    agent_name = Column(String(100), default="")
    resonance_score = Column(Float, default=0.0)
    offer_text = Column(Text, default="")                    # 完整 Offer 内容
    confidence = Column(Float, nullable=True)
    agent_state = Column(String(20), default="")             # offered | exited
    source = Column(String(20), nullable=True)               # SecondMe | Claude
    created_at = Column(DateTime, default=datetime.now)

    negotiation = relationship("NegotiationHistory", back_populates="offers")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "resonance_score": self.resonance_score,
            "offer_text": self.offer_text,
            "confidence": self.confidence,
            "agent_state": self.agent_state,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============ 数据库连接 ============

_engine = None
_SessionLocal = None


def _migrate_schema(engine):
    """检测旧表缺失列并 ALTER TABLE ADD COLUMN。

    SQLAlchemy create_all() 只建新表不改旧表，
    所以新增列必须手动迁移。
    """
    import sqlite3

    with engine.connect() as conn:
        raw = conn.connection  # 底层 sqlite3 connection

        # 获取 users 表现有列名
        cursor = raw.execute("PRAGMA table_info(users)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        # 需要存在的列 → (列名, SQL 类型, 默认值)
        required_cols = [
            ("email", "VARCHAR(256)", None),
            ("phone", "VARCHAR(32)", None),
            ("subscribe", "BOOLEAN", "0"),
            ("raw_profile_text", "TEXT", None),
            ("source", "VARCHAR(32)", "'secondme'"),
        ]

        for col_name, col_type, default in required_cols:
            if col_name not in existing_cols:
                default_clause = f" DEFAULT {default}" if default is not None else ""
                sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_type}{default_clause}"
                raw.execute(sql)
                logger.warning("MIGRATION: added column users.%s (%s)", col_name, col_type)

        raw.commit()


def get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{DB_PATH}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(_engine)
        _migrate_schema(_engine)
        logger.info(f"Database initialized at {DB_PATH}")
    return _engine


def get_session():
    """获取数据库会话"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


# ============ User CRUD ============

def create_user(
    agent_id: str,
    display_name: str,
    skills: List[str],
    specialties: List[str],
    secondme_id: Optional[str] = None,
    bio: Optional[str] = None,
    avatar_url: Optional[str] = None,
    self_intro: Optional[str] = None,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    token_expires_at: Optional[datetime] = None,
) -> User:
    session = get_session()
    try:
        user = User(
            agent_id=agent_id,
            display_name=display_name,
            skills=skills,
            specialties=specialties,
            secondme_id=secondme_id,
            bio=bio,
            avatar_url=avatar_url,
            self_intro=self_intro,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"Created user: {agent_id}")
        return user
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create user: {e}")
        raise
    finally:
        session.close()


def get_user_by_agent_id(agent_id: str) -> Optional[User]:
    session = get_session()
    try:
        return session.query(User).filter(User.agent_id == agent_id).first()
    finally:
        session.close()


def get_user_by_secondme_id(secondme_id: str) -> Optional[User]:
    session = get_session()
    try:
        return session.query(User).filter(User.secondme_id == secondme_id).first()
    finally:
        session.close()


def get_all_users(active_only: bool = False) -> List[User]:
    session = get_session()
    try:
        query = session.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.all()
    finally:
        session.close()


def update_user(agent_id: str, **kwargs) -> Optional[User]:
    session = get_session()
    try:
        user = session.query(User).filter(User.agent_id == agent_id).first()
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            session.commit()
            session.refresh(user)
            logger.info(f"Updated user: {agent_id}")
        return user
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update user: {e}")
        raise
    finally:
        session.close()


def delete_user(agent_id: str) -> bool:
    session = get_session()
    try:
        user = session.query(User).filter(User.agent_id == agent_id).first()
        if user:
            session.delete(user)
            session.commit()
            logger.info(f"Deleted user: {agent_id}")
            return True
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to delete user: {e}")
        raise
    finally:
        session.close()


# ============ Playground User CRUD (ADR-009) ============

def get_user_by_email(email: str) -> Optional[User]:
    """通过邮箱查找用户（quick-register 去重用）。"""
    session = get_session()
    try:
        return session.query(User).filter(User.email == email).first()
    finally:
        session.close()


def get_user_by_phone(phone: str) -> Optional[User]:
    """通过手机号查找用户（quick-register 去重用）。"""
    session = get_session()
    try:
        return session.query(User).filter(User.phone == phone).first()
    finally:
        session.close()


def create_playground_user(
    agent_id: str,
    display_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    subscribe: bool = False,
    raw_profile_text: str = "",
) -> User:
    """创建 Playground 来源的用户。source='playground'。"""
    session = get_session()
    try:
        user = User(
            agent_id=agent_id,
            display_name=display_name,
            email=email,
            phone=phone,
            subscribe=subscribe,
            raw_profile_text=raw_profile_text,
            source="playground",
            skills=[],
            specialties=[],
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info("Created playground user: %s (email=%s)", agent_id, email or "none")
        return user
    except Exception as e:
        session.rollback()
        logger.error("Failed to create playground user: %s", e)
        raise
    finally:
        session.close()


def get_playground_users() -> List[User]:
    """获取所有 Playground 用户（启动时恢复用）。"""
    session = get_session()
    try:
        return session.query(User).filter(User.source == "playground").all()
    finally:
        session.close()


# ============ NegotiationHistory CRUD (ADR-007) ============

def save_negotiation(
    negotiation_id: str,
    user_id: str,
    demand_text: str,
    scene_id: str = "",
    demand_mode: str = "manual",
    scope: str = "all",
    agent_count: int = 0,
    assist_output: Optional[str] = None,
) -> NegotiationHistory:
    """创建协商历史记录。在 negotiate() 提交时和 assist_demand() 完成时调用。"""
    session = get_session()
    try:
        history = NegotiationHistory(
            negotiation_id=negotiation_id,
            user_id=user_id,
            demand_text=demand_text,
            scene_id=scene_id,
            demand_mode=demand_mode,
            status="pending",
            scope=scope,
            agent_count=agent_count,
            assist_output=assist_output,
        )
        session.add(history)
        session.commit()
        session.refresh(history)
        logger.info(f"History: saved negotiation {negotiation_id} (user={user_id}, mode={demand_mode})")
        return history
    except Exception as e:
        session.rollback()
        logger.error(f"History: failed to save negotiation {negotiation_id}: {e}")
        raise
    finally:
        session.close()


def update_negotiation(negotiation_id: str, **kwargs) -> Optional[NegotiationHistory]:
    """更新协商历史字段（status, plan_output, formulated_text 等）。"""
    session = get_session()
    try:
        history = session.query(NegotiationHistory).filter(
            NegotiationHistory.negotiation_id == negotiation_id
        ).first()
        if history:
            for key, value in kwargs.items():
                if hasattr(history, key):
                    setattr(history, key, value)
            session.commit()
            session.refresh(history)
            logger.info(f"History: updated negotiation {negotiation_id} ({list(kwargs.keys())})")
        return history
    except Exception as e:
        session.rollback()
        logger.error(f"History: failed to update negotiation {negotiation_id}: {e}")
        raise
    finally:
        session.close()


def save_offers(negotiation_id: str, offers: List[Dict[str, Any]]) -> None:
    """批量保存 Offer 详情。每个 offer dict 应含 agent_id, agent_name, offer_text 等字段。"""
    session = get_session()
    try:
        for offer_data in offers:
            offer = NegotiationOffer(
                negotiation_id=negotiation_id,
                agent_id=offer_data.get("agent_id", ""),
                agent_name=offer_data.get("agent_name", ""),
                resonance_score=offer_data.get("resonance_score", 0.0),
                offer_text=offer_data.get("offer_text", ""),
                confidence=offer_data.get("confidence"),
                agent_state=offer_data.get("agent_state", ""),
                source=offer_data.get("source", ""),
            )
            session.add(offer)
        session.commit()
        logger.info(f"History: saved {len(offers)} offers for {negotiation_id}")
    except Exception as e:
        session.rollback()
        logger.error(f"History: failed to save offers for {negotiation_id}: {e}")
        raise
    finally:
        session.close()


def get_user_history(
    user_id: str,
    scene_id: Optional[str] = None,
) -> List[NegotiationHistory]:
    """获取用户的全部协商历史，按时间倒序。"""
    session = get_session()
    try:
        query = session.query(NegotiationHistory).filter(
            NegotiationHistory.user_id == user_id
        )
        if scene_id:
            query = query.filter(NegotiationHistory.scene_id == scene_id)
        return query.order_by(NegotiationHistory.created_at.desc()).all()
    finally:
        session.close()


def get_negotiation_detail(
    negotiation_id: str,
) -> Tuple[Optional[NegotiationHistory], List[NegotiationOffer]]:
    """获取单次协商的详情（含所有 Offer）。"""
    session = get_session()
    try:
        history = session.query(NegotiationHistory).filter(
            NegotiationHistory.negotiation_id == negotiation_id
        ).first()
        if not history:
            return None, []
        offers = session.query(NegotiationOffer).filter(
            NegotiationOffer.negotiation_id == negotiation_id
        ).order_by(NegotiationOffer.resonance_score.desc()).all()
        return history, offers
    finally:
        session.close()


def save_assist_output(
    user_id: str,
    scene_id: str,
    demand_mode: str,
    assist_output: str,
    raw_text: str = "",
) -> NegotiationHistory:
    """保存"通向惊喜"或"润色"的输出。创建一条 status=draft 的历史记录。"""
    from towow.core.models import generate_id
    session = get_session()
    try:
        history = NegotiationHistory(
            negotiation_id=generate_id("assist"),
            user_id=user_id,
            demand_text=raw_text or assist_output,
            scene_id=scene_id,
            demand_mode=demand_mode,
            assist_output=assist_output,
            status="draft",
        )
        session.add(history)
        session.commit()
        session.refresh(history)
        logger.info(f"History: saved assist output (user={user_id}, mode={demand_mode})")
        return history
    except Exception as e:
        session.rollback()
        logger.error(f"History: failed to save assist output: {e}")
        raise
    finally:
        session.close()
