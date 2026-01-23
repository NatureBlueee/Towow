# ToWow 数据库连接文档

> **文档路径**: `.ai/DATABASE-CONNECTION.md`
> **版本**: v1.0
> **创建日期**: 2026-01-22
> **目标读者**: DBA 同学、后端开发、DevOps

---

## 1. 数据库架构概述

### 1.1 数据库类型

| 项目 | 说明 |
|------|------|
| **数据库** | PostgreSQL 15+ |
| **异步驱动** | asyncpg (SQLAlchemy 2.0 async) |
| **同步驱动** | psycopg2-binary (备用/迁移脚本) |
| **ORM** | SQLAlchemy 2.0 (Declarative Mapping) |
| **迁移工具** | Alembic 1.12+ |

### 1.2 表结构

项目共包含 **4 张核心表**：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ToWow Database Schema                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐         ┌──────────────────────────┐         │
│  │  agent_profiles  │         │        demands           │         │
│  ├──────────────────┤         ├──────────────────────────┤         │
│  │ id (UUID, PK)    │         │ id (UUID, PK)            │         │
│  │ name (VARCHAR)   │         │ title (VARCHAR)          │         │
│  │ agent_type       │         │ description (TEXT)       │         │
│  │ description      │         │ user_id (VARCHAR)        │         │
│  │ capabilities ◆   │         │ requirements ◆           │         │
│  │ pricing_info ◆   │         │ budget ◆                 │         │
│  │ config ◆         │         │ deadline (TIMESTAMP)     │         │
│  │ is_active        │         │ status (VARCHAR)         │         │
│  │ rating           │         │ tags ◆                   │         │
│  │ total_collabs    │         │ extra_metadata ◆         │         │
│  │ created_at       │         │ created_at               │         │
│  │ updated_at       │         │ updated_at               │         │
│  └────────┬─────────┘         └────────────┬─────────────┘         │
│           │                                 │                        │
│           │ 1:N                             │ 1:N                    │
│           │                                 │                        │
│           ▼                                 ▼                        │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                    agent_responses                        │       │
│  ├──────────────────────────────────────────────────────────┤       │
│  │ id (UUID, PK)                                             │       │
│  │ demand_id (UUID, FK → demands.id, ON DELETE CASCADE)      │       │
│  │ agent_id (UUID, FK → agent_profiles.id, ON DELETE CASCADE)│       │
│  │ message (TEXT)                                            │       │
│  │ proposal ◆                                                │       │
│  │ status (VARCHAR)                                          │       │
│  │ relevance_score (FLOAT)                                   │       │
│  │ extra_metadata ◆                                          │       │
│  │ created_at, updated_at                                    │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                collaboration_channels                     │       │
│  ├──────────────────────────────────────────────────────────┤       │
│  │ id (UUID, PK)                                             │       │
│  │ name (VARCHAR)                                            │       │
│  │ description (TEXT)                                        │       │
│  │ demand_id (UUID, FK → demands.id, ON DELETE CASCADE)      │       │
│  │ participants ◆                                            │       │
│  │ status (VARCHAR)                                          │       │
│  │ context ◆                                                 │       │
│  │ message_count (INT)                                       │       │
│  │ last_message_at (TIMESTAMP)                               │       │
│  │ settings ◆                                                │       │
│  │ created_at, updated_at                                    │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ◆ = JSONB 类型                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 表详细定义

#### 1.3.1 agent_profiles (Agent 配置表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PRIMARY KEY | Agent 唯一标识 |
| name | VARCHAR(255) | NOT NULL | Agent 名称 |
| agent_type | VARCHAR(50) | NOT NULL | Agent 类型 (translator/developer/...) |
| description | TEXT | NULLABLE | Agent 描述 |
| capabilities | JSONB | DEFAULT {} | 能力配置 (languages, specializations 等) |
| pricing_info | JSONB | DEFAULT {} | 定价信息 |
| config | JSONB | DEFAULT {} | Agent 配置 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |
| rating | FLOAT | NULLABLE | 评分 |
| total_collaborations | INT | DEFAULT 0 | 总协作次数 |
| created_at | TIMESTAMP WITH TZ | server_default=now() | 创建时间 |
| updated_at | TIMESTAMP WITH TZ | server_default=now(), onupdate | 更新时间 |

#### 1.3.2 demands (需求表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PRIMARY KEY | 需求唯一标识 |
| title | VARCHAR(500) | NOT NULL | 需求标题 |
| description | TEXT | NOT NULL | 需求描述 |
| user_id | VARCHAR(255) | NOT NULL | 创建用户 ID |
| requirements | JSONB | DEFAULT {} | 详细需求 |
| budget | JSONB | DEFAULT {} | 预算信息 |
| deadline | TIMESTAMP WITH TZ | NULLABLE | 截止时间 |
| status | VARCHAR(50) | DEFAULT 'draft' | 状态枚举 |
| tags | JSONB | DEFAULT [] | 标签数组 |
| extra_metadata | JSONB | DEFAULT {} | 扩展元数据 |
| created_at | TIMESTAMP WITH TZ | server_default=now() | 创建时间 |
| updated_at | TIMESTAMP WITH TZ | server_default=now(), onupdate | 更新时间 |

**状态枚举 (DemandStatus)**:
- `draft` - 草稿
- `published` - 已发布
- `matching` - 匹配中
- `matched` - 已匹配
- `completed` - 已完成
- `cancelled` - 已取消

#### 1.3.3 collaboration_channels (协作频道表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PRIMARY KEY | 频道唯一标识 |
| name | VARCHAR(255) | NOT NULL | 频道名称 |
| description | TEXT | NULLABLE | 频道描述 |
| demand_id | UUID | FK → demands.id, CASCADE | 关联需求 |
| participants | JSONB | NOT NULL, DEFAULT {} | 参与者信息 |
| status | VARCHAR(50) | DEFAULT 'active' | 状态枚举 |
| context | JSONB | DEFAULT {} | 协商上下文 |
| message_count | INT | DEFAULT 0 | 消息数量 |
| last_message_at | TIMESTAMP WITH TZ | NULLABLE | 最后消息时间 |
| settings | JSONB | DEFAULT {} | 频道设置 |
| created_at | TIMESTAMP WITH TZ | server_default=now() | 创建时间 |
| updated_at | TIMESTAMP WITH TZ | server_default=now(), onupdate | 更新时间 |

**状态枚举 (ChannelStatus)**:
- `active` - 活跃
- `paused` - 暂停
- `completed` - 已完成
- `closed` - 已关闭

#### 1.3.4 agent_responses (Agent 响应表)

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PRIMARY KEY | 响应唯一标识 |
| demand_id | UUID | FK → demands.id, CASCADE | 关联需求 |
| agent_id | UUID | FK → agent_profiles.id, CASCADE | 关联 Agent |
| message | TEXT | NOT NULL | 响应消息 |
| proposal | JSONB | DEFAULT {} | 提案详情 |
| status | VARCHAR(50) | DEFAULT 'pending' | 状态枚举 |
| relevance_score | FLOAT | NULLABLE | 相关性评分 |
| extra_metadata | JSONB | DEFAULT {} | 扩展元数据 |
| created_at | TIMESTAMP WITH TZ | server_default=now() | 创建时间 |
| updated_at | TIMESTAMP WITH TZ | server_default=now(), onupdate | 更新时间 |

**状态枚举 (ResponseStatus)**:
- `pending` - 待处理
- `accepted` - 已接受
- `rejected` - 已拒绝
- `withdrawn` - 已撤回

### 1.4 索引需求

项目已定义以下索引以优化查询性能：

```sql
-- agent_profiles 索引
CREATE INDEX ix_agent_profiles_agent_type ON agent_profiles (agent_type);
CREATE INDEX ix_agent_profiles_is_active ON agent_profiles (is_active);

-- demands 索引
CREATE INDEX ix_demands_user_id ON demands (user_id);
CREATE INDEX ix_demands_status ON demands (status);
CREATE INDEX ix_demands_created_at ON demands (created_at);

-- collaboration_channels 索引
CREATE INDEX ix_collaboration_channels_demand_id ON collaboration_channels (demand_id);
CREATE INDEX ix_collaboration_channels_status ON collaboration_channels (status);

-- agent_responses 索引
CREATE INDEX ix_agent_responses_demand_id ON agent_responses (demand_id);
CREATE INDEX ix_agent_responses_agent_id ON agent_responses (agent_id);
CREATE INDEX ix_agent_responses_status ON agent_responses (status);
```

**建议额外索引** (根据实际查询模式):

```sql
-- JSONB 索引 (如需高频查询 capabilities)
CREATE INDEX ix_agent_profiles_capabilities_gin ON agent_profiles USING GIN (capabilities);

-- 复合索引 (如需按状态+时间排序)
CREATE INDEX ix_demands_status_created ON demands (status, created_at DESC);
```

---

## 2. 连接配置

### 2.1 环境变量说明

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `DATABASE_URL` | 完整数据库连接字符串 | `postgresql://towow:password@localhost:5432/towow` | 见下方格式 |
| `POSTGRES_USER` | PostgreSQL 用户名 | `towow` | `towow_admin` |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | `password` | `your_secure_password` |
| `POSTGRES_DB` | 数据库名称 | `towow` | `towow_production` |
| `POSTGRES_PORT` | PostgreSQL 端口 | `5432` | `5432` |

### 2.2 连接字符串格式

**标准格式 (同步驱动)**:
```
postgresql://<user>:<password>@<host>:<port>/<database>
```

**异步格式 (asyncpg)**:
```
postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>
```

**示例**:
```bash
# 本地开发
DATABASE_URL=postgresql://towow:password@localhost:5432/towow

# Docker 环境 (docker-compose 内部网络)
DATABASE_URL=postgresql+asyncpg://towow:password@db:5432/towow

# 生产环境 (带 SSL)
DATABASE_URL=postgresql+asyncpg://towow_admin:xxx@prod-db.xxx.rds.amazonaws.com:5432/towow?sslmode=require
```

### 2.3 连接池配置建议

当前代码中的连接池配置 (`database/connection.py`):

```python
self.engine = create_async_engine(
    database_url,
    echo=False,           # 生产环境关闭 SQL 日志
    pool_size=10,         # 连接池大小
    max_overflow=20       # 允许超出的最大连接数
)
```

**生产环境推荐配置**:

| 参数 | 开发环境 | 生产环境 | 说明 |
|------|----------|----------|------|
| `pool_size` | 5-10 | 20-50 | 基础连接池大小 |
| `max_overflow` | 10-20 | 30-50 | 超出时允许的额外连接 |
| `pool_timeout` | 30 | 30 | 获取连接超时 (秒) |
| `pool_recycle` | 3600 | 1800 | 连接回收时间 (秒) |
| `pool_pre_ping` | False | True | 使用前检测连接有效性 |

**生产环境连接池配置示例**:
```python
engine = create_async_engine(
    database_url,
    echo=False,
    pool_size=30,
    max_overflow=50,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

---

## 3. 本地开发环境

### 3.1 方式一：使用 Docker Compose (推荐)

```bash
# 1. 启动 PostgreSQL 容器
docker-compose up -d db

# 2. 等待数据库就绪 (healthcheck 通过)
docker-compose ps

# 3. 初始化数据库表
cd towow
python scripts/init_db.py

# 4. (可选) 加载测试数据
python scripts/init_db.py --sample-data

# 5. (可选) 加载 100 个 Mock Agent
python scripts/init_db.py --mock-agents
```

**docker-compose.yml 数据库配置**:
```yaml
db:
  image: postgres:15-alpine
  container_name: towow-db
  environment:
    - POSTGRES_USER=towow
    - POSTGRES_PASSWORD=password
    - POSTGRES_DB=towow
  volumes:
    - postgres_data:/var/lib/postgresql/data
  ports:
    - "5432:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U towow -d towow"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### 3.2 方式二：本地安装 PostgreSQL

```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt install postgresql-15
sudo systemctl start postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE USER towow WITH PASSWORD 'password';
CREATE DATABASE towow OWNER towow;
GRANT ALL PRIVILEGES ON DATABASE towow TO towow;
EOF
```

### 3.3 初始化脚本

```bash
# 完整初始化流程
cd towow

# 1. 创建表结构
python scripts/init_db.py

# 2. 重置数据库 (删除并重建)
python scripts/init_db.py --drop

# 3. 创建示例数据
python scripts/init_db.py --sample-data

# 4. 加载 Mock Agent (默认 100 个)
python scripts/init_db.py --mock-agents

# 5. 自定义 Mock Agent 数量
python scripts/init_db.py --mock-agents --mock-agents-count 50
```

### 3.4 测试数据

初始化脚本 (`--sample-data`) 会创建：

1. **Translation Expert** (agent_profiles)
   - 类型: translator
   - 能力: 50+ 语言翻译

2. **Code Reviewer** (agent_profiles)
   - 类型: developer
   - 能力: Python/JS/TS/Go 代码审查

3. **示例需求** (demands)
   - 标题: Translate Technical Documentation
   - 状态: draft

Mock Agent (`--mock-agents`) 会生成 100 个多样化的 Agent 配置，覆盖多种 agent_type。

---

## 4. 生产环境配置

### 4.1 推荐云服务对比

| 服务 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| **AWS RDS PostgreSQL** | 成熟稳定、自动备份、Multi-AZ | 成本较高 | 企业级生产环境 |
| **Supabase** | 免费额度、即时启动、内置认证 | 功能受限 | MVP/小型项目 |
| **Neon** | Serverless、按用量计费、分支功能 | 新服务 | 开发/测试环境 |
| **自建 PostgreSQL** | 完全控制、成本灵活 | 运维负担 | 有运维能力的团队 |

### 4.2 AWS RDS 配置建议

**实例类型建议**:

| 阶段 | 实例类型 | vCPU | 内存 | 存储 | 估算成本 |
|------|----------|------|------|------|----------|
| MVP | db.t3.micro | 2 | 1 GB | 20 GB gp2 | ~$15/月 |
| 生产初期 | db.t3.small | 2 | 2 GB | 50 GB gp3 | ~$30/月 |
| 规模化 | db.r6g.large | 2 | 16 GB | 100 GB gp3 | ~$150/月 |

**参数组配置**:
```
# 连接数
max_connections = 200

# 共享缓冲区 (内存的 25%)
shared_buffers = 512MB

# 工作内存
work_mem = 16MB

# 日志配置
log_statement = ddl
log_min_duration_statement = 1000  # 慢查询 1s
```

### 4.3 安全配置

#### 4.3.1 SSL/TLS 配置

```bash
# 连接字符串添加 SSL 参数
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?sslmode=require

# SSL 模式选项:
# - disable: 不使用 SSL
# - allow: 优先不用 SSL
# - prefer: 优先使用 SSL (默认)
# - require: 强制 SSL
# - verify-ca: 验证 CA 证书
# - verify-full: 验证 CA 证书 + 主机名
```

#### 4.3.2 密码策略

| 要求 | 说明 |
|------|------|
| 最小长度 | 16 字符以上 |
| 复杂度 | 大小写 + 数字 + 特殊字符 |
| 轮换周期 | 90 天 |
| 密码存储 | 使用 AWS Secrets Manager / Vault |

**示例 (AWS Secrets Manager)**:
```python
import boto3
import json

def get_db_credentials():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='towow/db/credentials')
    return json.loads(response['SecretString'])
```

#### 4.3.3 网络安全

```
生产环境网络拓扑:

┌─────────────────────────────────────────────────┐
│                    VPC                          │
│  ┌────────────────────────────────────────┐    │
│  │           Public Subnet                 │    │
│  │  ┌──────────────┐  ┌──────────────┐    │    │
│  │  │   ALB/NLB    │  │   Bastion    │    │    │
│  │  └──────┬───────┘  └──────────────┘    │    │
│  └─────────┼──────────────────────────────┘    │
│            │                                    │
│  ┌─────────┼──────────────────────────────┐    │
│  │         │    Private Subnet            │    │
│  │  ┌──────▼───────┐                      │    │
│  │  │ App Servers  │                      │    │
│  │  │ (ECS/EKS)    │                      │    │
│  │  └──────┬───────┘                      │    │
│  └─────────┼──────────────────────────────┘    │
│            │                                    │
│  ┌─────────┼──────────────────────────────┐    │
│  │         │    Database Subnet           │    │
│  │  ┌──────▼───────┐                      │    │
│  │  │   RDS        │  (无公网访问)         │    │
│  │  │ PostgreSQL   │                      │    │
│  │  └──────────────┘                      │    │
│  └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

**安全组规则**:
```
# RDS 安全组
Inbound:
  - TCP 5432 from App Security Group (应用服务器)
  - TCP 5432 from Bastion Security Group (运维跳板)

Outbound:
  - All traffic to 0.0.0.0/0 (默认)
```

### 4.4 备份策略建议

| 备份类型 | 频率 | 保留期 | 说明 |
|----------|------|--------|------|
| 自动快照 (RDS) | 每日 | 7-35 天 | AWS 自动管理 |
| 手动快照 | 发布前 | 永久 | 重要版本前手动创建 |
| WAL 归档 | 实时 | 7 天 | 支持 PITR |
| 逻辑备份 (pg_dump) | 每周 | 30 天 | 跨版本迁移用 |

**恢复测试**:
- 每季度进行一次恢复演练
- 验证 PITR 到指定时间点的能力

---

## 5. 迁移支持

### 5.1 OpenAgent vs 本地实现的数据库一致性

无论使用 OpenAgent Network 还是本地 Mock Agent，数据库配置保持一致：

```
┌─────────────────────────────────────────────────────────────────┐
│                    数据库层 (统一)                               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   PostgreSQL 15+                          │ │
│  │  - agent_profiles                                         │ │
│  │  - demands                                                │ │
│  │  - collaboration_channels                                 │ │
│  │  - agent_responses                                        │ │
│  └───────────────────────────────────────────────────────────┘ │
│                            │                                    │
│              ┌─────────────┴─────────────┐                     │
│              ▼                           ▼                      │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │   本地 Mock Agent   │    │    OpenAgent        │            │
│  │   (当前 MVP 模式)   │    │   (未来分布式)       │            │
│  │                     │    │                     │            │
│  │  - 内存队列通信      │    │  - gRPC 网络通信    │            │
│  │  - 单进程           │    │  - 多节点           │            │
│  │  - 使用相同的        │    │  - 使用相同的        │            │
│  │    DB 服务层        │    │    DB 服务层        │            │
│  └─────────────────────┘    └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

**关键设计决策 (ADR-001)**:
- MVP 阶段使用本地 Mock Agent，所有 Agent 运行在同一进程
- 数据库模型和服务层与 OpenAgent 模式兼容
- 迁移到 OpenAgent 时，只需修改 Agent 间通信方式，数据库层无需改动

### 5.2 环境变量统一

所有环境使用相同的环境变量规范：

```bash
# .env.example - 适用于所有环境
DATABASE_URL=postgresql://towow:password@localhost:5432/towow

# Docker 环境会自动构建 URL:
# postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
```

### 5.3 配置热加载

当前实现使用 pydantic-settings 的延迟加载：

```python
# database/connection.py
class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://towow:password@localhost:5432/towow"

    class Config:
        env_prefix = "DATABASE_"

db_settings = DatabaseSettings()  # 启动时从环境变量加载
```

**热加载能力**:
- **当前**: 需要重启服务生效
- **建议增强**: 通过 Admin API 触发配置重载

```python
# 建议: 添加配置重载端点
@app.post("/admin/reload-config")
async def reload_config():
    global db_settings
    db_settings = DatabaseSettings()
    return {"status": "reloaded"}
```

### 5.4 数据库迁移 (Alembic)

项目已包含 Alembic 依赖，但尚未初始化迁移目录：

```bash
# 初始化 Alembic (首次)
cd towow
alembic init alembic

# 配置 alembic.ini
sqlalchemy.url = postgresql://towow:password@localhost:5432/towow

# 生成迁移脚本
alembic revision --autogenerate -m "Initial tables"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

**推荐目录结构**:
```
towow/
├── alembic/
│   ├── versions/
│   │   ├── 001_initial_tables.py
│   │   └── 002_add_indexes.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini
└── database/
    ├── models.py
    └── connection.py
```

---

## 6. 给 DBA 同学的对接清单

### 6.1 需要 DBA 提供什么

| 序号 | 项目 | 说明 | 格式示例 |
|------|------|------|----------|
| 1 | **连接字符串** | 完整的数据库连接信息 | `postgresql://user:pass@host:5432/db` |
| 2 | **用户凭证** | 数据库用户名和密码 | 通过 Secrets Manager 提供 |
| 3 | **SSL 证书** | 如需 verify-full 模式 | CA 证书文件 |
| 4 | **IP 白名单确认** | 应用服务器 IP 是否已加入 | - |
| 5 | **备份策略确认** | 备份时间窗口、保留策略 | - |

### 6.2 应用层需要的权限

```sql
-- 最小权限原则
GRANT CONNECT ON DATABASE towow TO towow_app;
GRANT USAGE ON SCHEMA public TO towow_app;

-- 表权限
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO towow_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO towow_app;

-- 未来表自动授权
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO towow_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO towow_app;

-- 迁移用户 (需要 DDL 权限)
GRANT CREATE ON SCHEMA public TO towow_migrate;
GRANT ALL ON ALL TABLES IN SCHEMA public TO towow_migrate;
```

**建议创建两个用户**:
- `towow_app`: 应用运行时使用 (DML only)
- `towow_migrate`: 迁移脚本使用 (DDL + DML)

### 6.3 监控指标建议

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| **连接数** | > 80% max_connections | 连接池耗尽风险 |
| **CPU 使用率** | > 80% 持续 5 分钟 | 性能瓶颈 |
| **磁盘使用率** | > 80% | 存储空间不足 |
| **复制延迟** (如有只读副本) | > 10 秒 | 读写分离数据不一致 |
| **死锁数量** | > 0 | 事务设计问题 |
| **慢查询数量** | > 100/分钟 | 需要索引优化 |
| **事务年龄** | > 1000000 | 需要 VACUUM |

**推荐监控工具**:
- AWS CloudWatch (RDS)
- pg_stat_statements (慢查询分析)
- pgBadger (日志分析)

### 6.4 常见操作 Runbook

#### 6.4.1 紧急回滚

```bash
# 使用 RDS 快照恢复
aws rds restore-db-instance-from-db-snapshot \
    --db-instance-identifier towow-restored \
    --db-snapshot-identifier towow-snapshot-20260122

# 或使用 PITR
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier towow-prod \
    --target-db-instance-identifier towow-restored \
    --restore-time 2026-01-22T10:00:00Z
```

#### 6.4.2 性能问题排查

```sql
-- 查看当前活跃连接
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- 查看慢查询 (需开启 pg_stat_statements)
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 查看表大小
SELECT relname, pg_size_pretty(pg_relation_size(relid))
FROM pg_stat_user_tables
ORDER BY pg_relation_size(relid) DESC;

-- 查看索引使用情况
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

#### 6.4.3 VACUUM 维护

```sql
-- 查看需要 VACUUM 的表
SELECT schemaname, relname, n_dead_tup, last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- 手动 VACUUM (一般由 autovacuum 自动执行)
VACUUM ANALYZE agent_profiles;
```

---

## 7. 快速启动指南 (Quick Start)

### 7.1 开发环境 (3 分钟启动)

```bash
# 1. 克隆项目
git clone <repo-url> && cd towow

# 2. 复制环境配置
cp towow/.env.example towow/.env

# 3. 启动 PostgreSQL
docker-compose up -d db

# 4. 初始化数据库
cd towow && python scripts/init_db.py --mock-agents

# 5. 启动应用
uvicorn api.main:app --reload

# 6. 验证
curl http://localhost:8000/health
```

### 7.2 生产环境 Checklist

- [ ] RDS 实例已创建并通过健康检查
- [ ] 数据库用户和权限已配置
- [ ] SSL/TLS 已启用 (sslmode=require)
- [ ] 连接字符串已存入 Secrets Manager
- [ ] 安全组规则已配置
- [ ] 备份策略已启用
- [ ] 监控告警已配置
- [ ] 初始化脚本已执行
- [ ] 应用可正常连接数据库

---

## 附录

### A. 相关文件路径

| 文件 | 路径 | 说明 |
|------|------|------|
| 数据库模块入口 | `towow/database/__init__.py` | 导出所有模型和服务 |
| 连接配置 | `towow/database/connection.py` | 连接池、Session 管理 |
| 数据模型 | `towow/database/models.py` | ORM 模型定义 |
| 服务层 | `towow/database/services.py` | CRUD 操作封装 |
| 初始化脚本 | `towow/scripts/init_db.py` | 数据库初始化 |
| Docker 配置 | `towow/docker-compose.yml` | 容器化部署 |
| 环境变量模板 | `towow/.env.example` | 配置模板 |

### B. 依赖版本

```
# requirements.txt (数据库相关)
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.12.0
asyncpg (通过 SQLAlchemy 安装)
pydantic-settings>=2.0.0
```

### C. 联系方式

如有数据库相关问题，请联系：
- 后端开发团队: [待填写]
- DBA 团队: [待填写]

---

> **文档维护**: 本文档随代码更新同步维护，最新版本请查看 `.ai/DATABASE-CONNECTION.md`
