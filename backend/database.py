"""
Database - SQLite + SQLAlchemy 数据层

提供用户和需求的持久化存储，替代原有的 JSON 文件存储。
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, Integer, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
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

    # OAuth2 Token 存储
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "skills": self.skills or [],
            "specialties": self.specialties or [],
            "secondme_id": self.secondme_id,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "self_intro": self.self_intro,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Requirement(Base):
    """需求模型"""
    __tablename__ = "requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    submitter_id = Column(String(64), index=True)  # agent_id
    status = Column(String(32), default="pending")  # pending, processing, completed, cancelled
    channel_id = Column(String(64), nullable=True, index=True)
    extra_data = Column(JSON, default=dict)  # 改名避免与 SQLAlchemy 的 metadata 冲突
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "requirement_id": self.requirement_id,
            "title": self.title,
            "description": self.description,
            "submitter_id": self.submitter_id,
            "status": self.status,
            "channel_id": self.channel_id,
            "metadata": self.extra_data or {},  # 对外仍然叫 metadata
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChannelMessage(Base):
    """Channel 消息模型"""
    __tablename__ = "channel_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(64), unique=True, nullable=False, index=True)
    channel_id = Column(String(64), nullable=False, index=True)
    sender_id = Column(String(64), nullable=False, index=True)  # agent_id
    sender_name = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(32), default="text")  # text, system, action
    extra_data = Column(JSON, default=dict)  # 改名避免与 SQLAlchemy 的 metadata 冲突
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "message_id": self.message_id,
            "channel_id": self.channel_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.extra_data or {},  # 对外仍然叫 metadata
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============ 数据库连接 ============

_engine = None
_SessionLocal = None


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
        # 创建表
        Base.metadata.create_all(_engine)
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
    """创建用户"""
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
    """根据 agent_id 获取用户"""
    session = get_session()
    try:
        return session.query(User).filter(User.agent_id == agent_id).first()
    finally:
        session.close()


def get_user_by_secondme_id(secondme_id: str) -> Optional[User]:
    """根据 secondme_id 获取用户"""
    session = get_session()
    try:
        return session.query(User).filter(User.secondme_id == secondme_id).first()
    finally:
        session.close()


def get_all_users(active_only: bool = False) -> List[User]:
    """获取所有用户"""
    session = get_session()
    try:
        query = session.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.all()
    finally:
        session.close()


def update_user(agent_id: str, **kwargs) -> Optional[User]:
    """更新用户"""
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
    """删除用户"""
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


# ============ Requirement CRUD ============

def create_requirement(
    requirement_id: str,
    title: str,
    description: str,
    submitter_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Requirement:
    """创建需求"""
    session = get_session()
    try:
        req = Requirement(
            requirement_id=requirement_id,
            title=title,
            description=description,
            submitter_id=submitter_id,
            channel_id=channel_id,
            extra_data=metadata or {},  # 使用 extra_data 字段
        )
        session.add(req)
        session.commit()
        session.refresh(req)
        logger.info(f"Created requirement: {requirement_id}")
        return req
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create requirement: {e}")
        raise
    finally:
        session.close()


def get_requirement(requirement_id: str) -> Optional[Requirement]:
    """获取需求"""
    session = get_session()
    try:
        return session.query(Requirement).filter(
            Requirement.requirement_id == requirement_id
        ).first()
    finally:
        session.close()


def get_all_requirements(
    status: Optional[str] = None,
    submitter_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Requirement]:
    """获取需求列表"""
    session = get_session()
    try:
        query = session.query(Requirement)
        if status:
            query = query.filter(Requirement.status == status)
        if submitter_id:
            query = query.filter(Requirement.submitter_id == submitter_id)
        return query.order_by(Requirement.created_at.desc()).offset(offset).limit(limit).all()
    finally:
        session.close()


def update_requirement(requirement_id: str, **kwargs) -> Optional[Requirement]:
    """更新需求"""
    session = get_session()
    try:
        req = session.query(Requirement).filter(
            Requirement.requirement_id == requirement_id
        ).first()
        if req:
            for key, value in kwargs.items():
                if hasattr(req, key):
                    setattr(req, key, value)
            session.commit()
            session.refresh(req)
            logger.info(f"Updated requirement: {requirement_id}")
        return req
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update requirement: {e}")
        raise
    finally:
        session.close()


# ============ ChannelMessage CRUD ============

def create_channel_message(
    message_id: str,
    channel_id: str,
    sender_id: str,
    content: str,
    sender_name: Optional[str] = None,
    message_type: str = "text",
    metadata: Optional[Dict[str, Any]] = None,
) -> ChannelMessage:
    """创建消息"""
    session = get_session()
    try:
        msg = ChannelMessage(
            message_id=message_id,
            channel_id=channel_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            message_type=message_type,
            extra_data=metadata or {},  # 使用 extra_data 字段
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)
        return msg
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create message: {e}")
        raise
    finally:
        session.close()


def get_channel_messages(
    channel_id: str,
    limit: int = 100,
    offset: int = 0,
    after_id: Optional[str] = None,
) -> List[ChannelMessage]:
    """获取 Channel 消息"""
    session = get_session()
    try:
        query = session.query(ChannelMessage).filter(
            ChannelMessage.channel_id == channel_id
        )
        if after_id:
            # 获取 after_id 对应消息的 id
            after_msg = session.query(ChannelMessage).filter(
                ChannelMessage.message_id == after_id
            ).first()
            if after_msg:
                query = query.filter(ChannelMessage.id > after_msg.id)
        return query.order_by(ChannelMessage.created_at.asc()).offset(offset).limit(limit).all()
    finally:
        session.close()


# ============ 数据迁移 ============

def migrate_from_json(json_file: Path) -> int:
    """从 JSON 文件迁移数据到 SQLite"""
    import json

    if not json_file.exists():
        logger.info(f"JSON file not found: {json_file}")
        return 0

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for agent_id, config in data.items():
            # 检查是否已存在
            existing = get_user_by_agent_id(agent_id)
            if existing:
                logger.info(f"User already exists: {agent_id}, skipping")
                continue

            create_user(
                agent_id=config.get("agent_id", agent_id),
                display_name=config.get("display_name", "Unknown"),
                skills=config.get("skills", []),
                specialties=config.get("specialties", []),
                secondme_id=config.get("secondme_id"),
                bio=config.get("bio"),
            )
            count += 1

        logger.info(f"Migrated {count} users from JSON")
        return count

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
