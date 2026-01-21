# TASK-003：数据库初始化

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-003 |
| 所属Phase | Phase 1：基础框架 |
| 依赖 | TASK-001 |
| 预估工作量 | 0.5天 |
| 状态 | 待开始 |

---

## 任务描述

初始化PostgreSQL数据库，创建表结构，配置连接池。

---

## 具体工作

### 1. 创建数据库连接

`database/connection.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import asynccontextmanager

Base = declarative_base()

class Database:
    def __init__(self, database_url: str):
        # 转换为异步URL
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=10,
            max_overflow=20
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    @asynccontextmanager
    async def session(self):
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        await self.engine.dispose()
```

### 2. 创建数据模型

`database/models.py`:

```python
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from .connection import Base

class AgentProfile(Base):
    """Agent简介"""
    __tablename__ = "agent_profiles"

    agent_id = Column(String(64), primary_key=True)
    user_name = Column(String(100), nullable=False)

    # 基础信息
    profile_summary = Column(Text)
    location = Column(String(100))

    # 能力与资源
    capabilities = Column(JSONB, default=list)
    interests = Column(JSONB, default=list)
    recent_focus = Column(Text)

    # 协作风格
    availability = Column(String(50))
    collaboration_style = Column(JSONB, default=dict)
    past_collaborations = Column(JSONB, default=list)

    # 元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_active_at = Column(DateTime)
    status = Column(String(20), default="active")


class Demand(Base):
    """需求记录"""
    __tablename__ = "demands"

    demand_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    initiator_agent_id = Column(String(64), ForeignKey("agent_profiles.agent_id"))

    # 需求内容
    raw_input = Column(Text, nullable=False)
    surface_demand = Column(Text)
    deep_understanding = Column(JSONB)

    # 状态
    status = Column(String(20), default="created")
    channel_id = Column(String(100))

    # 时间
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CollaborationChannel(Base):
    """协商Channel记录"""
    __tablename__ = "collaboration_channels"

    channel_id = Column(String(100), primary_key=True)
    demand_id = Column(UUID(as_uuid=True), ForeignKey("demands.demand_id"))

    # 参与者
    invited_agents = Column(JSONB, default=list)
    responded_agents = Column(JSONB, default=list)

    # 方案
    current_proposal = Column(JSONB)
    proposal_version = Column(Integer, default=0)

    # 状态
    status = Column(String(20), default="negotiating")
    negotiation_round = Column(Integer, default=0)

    # 时间
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)


class AgentResponse(Base):
    """Agent回应记录"""
    __tablename__ = "agent_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String(100), ForeignKey("collaboration_channels.channel_id"))
    agent_id = Column(String(64), ForeignKey("agent_profiles.agent_id"))

    # 回应内容
    response_type = Column(String(20))  # participate, decline, need_more_info
    contribution = Column(Text)
    conditions = Column(JSONB, default=list)
    reasoning = Column(Text)

    # 时间
    created_at = Column(DateTime, server_default=func.now())
```

### 3. 创建初始化脚本

`scripts/init_db.py`:

```python
import asyncio
import asyncpg
from database.connection import Database, Base
from database.models import AgentProfile, Demand, CollaborationChannel
import os

async def create_database():
    """创建数据库（如果不存在）"""
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )

    try:
        await conn.execute("CREATE DATABASE towow")
        print("✅ Database 'towow' created")
    except asyncpg.DuplicateDatabaseError:
        print("ℹ️  Database 'towow' already exists")
    finally:
        await conn.close()

async def init_tables():
    """创建表结构"""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/towow"
    )
    db = Database(database_url)

    await db.create_tables()
    print("✅ Tables created successfully")

    await db.close()

async def main():
    await create_database()
    await init_tables()
    print("✅ Database initialization complete")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. 创建数据库服务

`database/services.py`:

```python
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from .models import AgentProfile, Demand, CollaborationChannel

class AgentProfileService:
    """Agent简介服务"""

    @staticmethod
    async def get_all_active(session: AsyncSession) -> List[AgentProfile]:
        """获取所有活跃Agent"""
        result = await session.execute(
            select(AgentProfile).where(AgentProfile.status == "active")
        )
        return result.scalars().all()

    @staticmethod
    async def get_by_id(session: AsyncSession, agent_id: str) -> Optional[AgentProfile]:
        """根据ID获取Agent"""
        result = await session.execute(
            select(AgentProfile).where(AgentProfile.agent_id == agent_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> AgentProfile:
        """创建Agent简介"""
        profile = AgentProfile(**kwargs)
        session.add(profile)
        return profile


class DemandService:
    """需求服务"""

    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Demand:
        """创建需求"""
        demand = Demand(**kwargs)
        session.add(demand)
        return demand

    @staticmethod
    async def update_status(session: AsyncSession, demand_id: str, status: str):
        """更新需求状态"""
        await session.execute(
            update(Demand)
            .where(Demand.demand_id == demand_id)
            .values(status=status)
        )
```

---

## 验收标准

- [ ] PostgreSQL本地安装完成
- [ ] `scripts/init_db.py` 运行成功
- [ ] 所有表创建成功
- [ ] 可以通过服务类进行CRUD操作

---

## 产出物

- `database/connection.py` - 数据库连接管理
- `database/models.py` - ORM模型定义
- `database/services.py` - 数据服务层
- `scripts/init_db.py` - 初始化脚本

---

## PostgreSQL安装（macOS）

```bash
# 使用Homebrew安装
brew install postgresql@15

# 启动服务
brew services start postgresql@15

# 创建用户和数据库
createuser -s postgres
createdb towow

# 或使用psql
psql postgres
CREATE USER towow WITH PASSWORD 'your_password';
CREATE DATABASE towow OWNER towow;
```

---

**创建时间**: 2026-01-21

> Beads 任务ID：`towow-aej`
