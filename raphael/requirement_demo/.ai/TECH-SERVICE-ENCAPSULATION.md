# Requirement Demo 服务封装技术方案

## 文档元信息

- **文档类型**: 技术方案 (TECH)
- **状态**: DRAFT
- **创建日期**: 2026-01-29
- **关联项目**: requirement_demo

---

## 1. 目标与范围

### 1.1 核心需求

将 requirement_demo 项目封装成一个可用的服务，实现：

1. **开放注册**: 任何人都可以注册成为 Worker Agent
2. **双重角色**: 所有人既是需求方又是供给方
3. **完整功能**: 注册后可以提交需求、响应需求、发消息到 Channel

### 1.2 范围边界

| 范围内 | 范围外 |
|--------|--------|
| SecondMe OAuth2 登录集成 | 其他 OAuth 提供商 |
| 动态 Agent 创建与管理 | Agent 自定义行为逻辑 |
| 数据持久化（JSON -> SQLite/PostgreSQL） | 分布式部署 |
| 基础安全性（Token 验证、CORS） | 高级安全（WAF、DDoS 防护） |

---

## 2. 现状分析

### 2.1 已完成功能

基于代码验证 [VERIFIED]：

| 功能 | 文件位置 | 状态 |
|------|----------|------|
| SecondMe OAuth2 客户端 | `web/oauth2_client.py` | 完成 |
| 用户注册 API | `web/app.py` | 完成 |
| Agent 生命周期管理 | `web/agent_manager.py` | 完成 |
| 动态 Worker Agent | `agents/dynamic_worker.py` | 完成 |
| 数据持久化（JSON） | `data/user_agents.json` | 基础版 |

### 2.2 SecondMe API 数据结构

基于 `oauth2_client.py:354-407` [VERIFIED]：

```python
# SecondMe /gate/lab/api/secondme/user/info 返回数据
{
    "code": 0,
    "data": {
        "openId": "xxx",           # 用户唯一标识（可能为空）
        "name": "用户名",          # 用户名
        "email": "xxx@xxx.com",   # 邮箱（用作备选唯一标识）
        "avatar": "https://...",  # 头像 URL
        "bio": "个人简介",         # 个人简介
        "selfIntroduction": "...", # 自我介绍 [ASSUMPTION - 需验证]
        "voiceId": "...",         # 语音 ID [ASSUMPTION - 需验证]
        "profileCompleteness": 80 # 资料完整度 [ASSUMPTION - 需验证]
    }
}
```

**注意**: 根据 `oauth2_client.py:396-397` 的注释，SecondMe API 当前不返回 `openId`，系统使用 `email` 作为备选唯一标识符。

### 2.3 当前数据结构

基于 `web/agent_manager.py:31-41` [VERIFIED]：

```python
@dataclass
class UserAgentConfig:
    agent_id: str              # 系统生成的 Agent ID
    display_name: str          # 显示名称
    skills: List[str]          # 技能列表
    specialties: List[str]     # 专长领域
    secondme_id: Optional[str] # SecondMe 用户标识
    bio: Optional[str]         # 个人简介
    created_at: str            # 创建时间
    is_active: bool            # 是否激活
```

---

## 3. 数据对标方案

### 3.1 字段映射表

| SecondMe 字段 | 我们的字段 | 映射方式 | 说明 |
|--------------|-----------|----------|------|
| `openId` / `email` | `secondme_id` | 直接映射 | 优先 openId，备选 email |
| `name` | `display_name` | 直接映射 | 可被用户覆盖 |
| `avatar` | `avatar_url` (新增) | 直接映射 | 头像 URL |
| `bio` | `bio` | 直接映射 | 个人简介 |
| `selfIntroduction` | `self_intro` (新增) | 直接映射 | 自我介绍（更详细） |
| - | `skills` | 用户补填 | 技能列表 |
| - | `specialties` | 用户补填 | 专长领域 |
| - | `agent_id` | 系统生成 | 基于 secondme_id 哈希 |
| - | `created_at` | 系统生成 | 注册时间 |
| - | `is_active` | 系统管理 | 激活状态 |

### 3.2 扩展后的数据结构

```python
@dataclass
class UserAgentConfig:
    # === 系统字段 ===
    agent_id: str              # 系统生成的 Agent ID (user_xxxxxxxx)
    created_at: str            # 创建时间 (ISO 8601)
    updated_at: str            # 更新时间 (ISO 8601)
    is_active: bool            # 是否激活

    # === SecondMe 同步字段 ===
    secondme_id: str           # SecondMe 用户标识 (openId 或 email)
    display_name: str          # 显示名称
    avatar_url: Optional[str]  # 头像 URL
    bio: Optional[str]         # 个人简介
    self_intro: Optional[str]  # 自我介绍（详细版）

    # === 用户补填字段 ===
    skills: List[str]          # 技能列表
    specialties: List[str]     # 专长领域

    # === Token 管理 ===
    access_token: Optional[str]   # 当前 access_token (加密存储)
    refresh_token: Optional[str]  # refresh_token (加密存储)
    token_expires_at: Optional[str]  # Token 过期时间

    # === 运行时状态 ===
    last_active_at: Optional[str]  # 最后活跃时间
    total_requirements: int = 0    # 提交的需求数
    total_responses: int = 0       # 响应的任务数
```

### 3.3 注册流程数据流

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         注册数据流                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. OAuth2 授权                                                          │
│     SecondMe ──► access_token, refresh_token, open_id                   │
│                                                                          │
│  2. 获取用户信息                                                          │
│     GET /gate/lab/api/secondme/user/info                                │
│     ──► name, email, avatar, bio, selfIntroduction                      │
│                                                                          │
│  3. 前端补填                                                              │
│     用户输入 ──► skills[], specialties[]                                 │
│                                                                          │
│  4. 完成注册                                                              │
│     POST /api/auth/complete-registration                                │
│     ──► 创建 UserAgentConfig                                            │
│     ──► 生成 agent_id (hash of secondme_id)                             │
│     ──► 保存到数据库                                                      │
│     ──► 启动 DynamicWorkerAgent                                         │
│                                                                          │
│  5. Agent 注册能力                                                        │
│     DynamicWorkerAgent.on_startup()                                     │
│     ──► register_capabilities(skills, specialties, agent_card)          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 封装方案

### 4.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Requirement Demo Service                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   Frontend   │    │   Web API    │    │  OpenAgents  │               │
│  │   (React)    │◄──►│  (FastAPI)   │◄──►│   Network    │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│         │                   │                   │                        │
│         │                   ▼                   │                        │
│         │            ┌──────────────┐           │                        │
│         │            │   Database   │           │                        │
│         │            │  (SQLite/    │           │                        │
│         │            │  PostgreSQL) │           │                        │
│         │            └──────────────┘           │                        │
│         │                   │                   │                        │
│         │                   ▼                   │                        │
│         │            ┌──────────────┐           │                        │
│         └───────────►│   SecondMe   │◄──────────┘                        │
│                      │   OAuth2     │                                    │
│                      └──────────────┘                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 需要完成的工作

#### Phase 1: 数据层升级 (P0)

| 任务 | 描述 | 工作量 |
|------|------|--------|
| 数据库迁移 | JSON -> SQLite (开发) / PostgreSQL (生产) | 2d |
| ORM 模型 | 使用 SQLAlchemy 定义数据模型 | 1d |
| 迁移脚本 | 现有 JSON 数据迁移到数据库 | 0.5d |
| Token 加密 | 敏感数据加密存储 | 0.5d |

#### Phase 2: API 完善 (P0)

| 任务 | 描述 | 工作量 |
|------|------|--------|
| 用户信息更新 | PUT /api/users/{id} - 更新技能/专长 | 0.5d |
| 需求提交 API | POST /api/requirements - 提交需求 | 1d |
| 需求列表 API | GET /api/requirements - 查看需求 | 0.5d |
| Channel 消息 API | POST /api/channels/{id}/messages | 1d |
| WebSocket 支持 | 实时消息推送 | 2d |

#### Phase 3: Agent 生命周期 (P1)

| 任务 | 描述 | 工作量 |
|------|------|--------|
| 自动重连 | Agent 断线自动重连 | 1d |
| 健康检查 | Agent 心跳检测 | 0.5d |
| 优雅关闭 | 服务重启时保存状态 | 0.5d |
| 并发控制 | 限制同时运行的 Agent 数量 | 0.5d |

#### Phase 4: 安全性 (P1)

| 任务 | 描述 | 工作量 |
|------|------|--------|
| JWT 认证 | 替换简单 Token 验证 | 1d |
| 速率限制 | API 请求频率限制 | 0.5d |
| 输入验证 | 防止注入攻击 | 0.5d |
| 审计日志 | 记录关键操作 | 0.5d |

#### Phase 5: 前端 (P2)

| 任务 | 描述 | 工作量 |
|------|------|--------|
| 登录页面 | SecondMe OAuth2 登录 | 1d |
| 注册补填页 | 技能/专长选择 | 1d |
| 仪表盘 | 用户状态、需求列表 | 2d |
| 需求详情 | Channel 消息展示 | 1d |

---

## 5. 数据库设计

### 5.1 表结构

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id VARCHAR(50) UNIQUE NOT NULL,      -- user_xxxxxxxx
    secondme_id VARCHAR(255) UNIQUE NOT NULL,  -- SecondMe 标识
    display_name VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    bio TEXT,
    self_intro TEXT,
    skills JSON NOT NULL DEFAULT '[]',         -- ["python", "react"]
    specialties JSON NOT NULL DEFAULT '[]',    -- ["web-development"]
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP,
    total_requirements INTEGER DEFAULT 0,
    total_responses INTEGER DEFAULT 0
);

-- Token 表（分离存储，便于加密）
CREATE TABLE user_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 需求表
CREATE TABLE requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id VARCHAR(50) UNIQUE NOT NULL,  -- req-xxxxxxxx
    channel_id VARCHAR(50) NOT NULL,
    creator_id INTEGER NOT NULL,
    requirement_text TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',           -- open, in_progress, completed, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users(id)
);

-- 任务响应表
CREATE TABLE task_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id INTEGER NOT NULL,
    responder_id INTEGER NOT NULL,
    task_id VARCHAR(50) NOT NULL,
    response_type VARCHAR(20) NOT NULL,          -- accept, reject, propose
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (requirement_id) REFERENCES requirements(id),
    FOREIGN KEY (responder_id) REFERENCES users(id)
);

-- 索引
CREATE INDEX idx_users_secondme_id ON users(secondme_id);
CREATE INDEX idx_users_agent_id ON users(agent_id);
CREATE INDEX idx_requirements_creator ON requirements(creator_id);
CREATE INDEX idx_requirements_status ON requirements(status);
CREATE INDEX idx_task_responses_requirement ON task_responses(requirement_id);
```

### 5.2 SQLAlchemy 模型

```python
# models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), unique=True, nullable=False)
    secondme_id = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    avatar_url = Column(Text)
    bio = Column(Text)
    self_intro = Column(Text)
    skills = Column(JSON, default=list)
    specialties = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime)
    total_requirements = Column(Integer, default=0)
    total_responses = Column(Integer, default=0)

    # Relationships
    tokens = relationship("UserToken", back_populates="user", uselist=False)
    requirements = relationship("Requirement", back_populates="creator")
    responses = relationship("TaskResponse", back_populates="responder")
```

---

## 6. API 设计

### 6.1 认证相关

```yaml
# 现有 API（保持不变）
GET  /api/auth/login                    # 获取 SecondMe 授权 URL
GET  /api/auth/callback                 # OAuth2 回调
POST /api/auth/complete-registration    # 完成注册
POST /api/auth/refresh                  # 刷新 Token

# 新增 API
GET  /api/auth/me                       # 获取当前用户信息
POST /api/auth/logout                   # 登出（清除 Token）
```

### 6.2 用户相关

```yaml
# 现有 API（保持不变）
GET  /api/agents                        # 列出所有 Agent
GET  /api/agents/{agent_id}             # 获取 Agent 详情
POST /api/agents/{agent_id}/action      # Agent 操作

# 新增 API
PUT  /api/users/me                      # 更新当前用户信息
PUT  /api/users/me/skills               # 更新技能列表
PUT  /api/users/me/specialties          # 更新专长列表
GET  /api/users/me/stats                # 获取用户统计
```

### 6.3 需求相关

```yaml
# 新增 API
POST /api/requirements                  # 提交需求
GET  /api/requirements                  # 需求列表（支持筛选）
GET  /api/requirements/{id}             # 需求详情
GET  /api/requirements/{id}/responses   # 需求的响应列表
POST /api/requirements/{id}/cancel      # 取消需求
```

### 6.4 Channel 相关

```yaml
# 新增 API
GET  /api/channels/{channel_id}         # Channel 详情
GET  /api/channels/{channel_id}/messages # 消息列表
POST /api/channels/{channel_id}/messages # 发送消息
WS   /api/channels/{channel_id}/ws      # WebSocket 实时消息
```

---

## 7. 安全性考虑

### 7.1 认证与授权

| 层级 | 措施 | 实现方式 |
|------|------|----------|
| 传输层 | HTTPS | Nginx/Caddy 反向代理 |
| 认证层 | JWT Token | PyJWT + RS256 |
| 授权层 | 基于角色 | 装饰器 @require_auth |
| 会话层 | Token 刷新 | refresh_token 机制 |

### 7.2 数据安全

| 数据类型 | 保护措施 |
|----------|----------|
| access_token | AES-256 加密存储 |
| refresh_token | AES-256 加密存储 |
| 用户密码 | 不存储（OAuth2） |
| 敏感日志 | 脱敏处理 |

### 7.3 API 安全

| 威胁 | 防护措施 |
|------|----------|
| CSRF | state 参数验证 |
| XSS | 输入过滤 + CSP |
| SQL 注入 | ORM 参数化查询 |
| 暴力破解 | 速率限制 |
| DDoS | 请求频率限制 |

---

## 8. 实现步骤

### 8.1 第一阶段：数据层 (Week 1)

```
Day 1-2: 数据库设计与迁移
├── 创建 SQLAlchemy 模型
├── 编写迁移脚本（Alembic）
├── 实现 JSON -> SQLite 数据迁移
└── 单元测试

Day 3-4: Token 管理
├── 实现 Token 加密存储
├── 实现 Token 自动刷新
├── 更新 OAuth2 流程
└── 集成测试
```

### 8.2 第二阶段：API 完善 (Week 2)

```
Day 1-2: 用户 API
├── PUT /api/users/me
├── GET /api/users/me/stats
└── 测试

Day 3-4: 需求 API
├── POST /api/requirements
├── GET /api/requirements
├── GET /api/requirements/{id}
└── 测试

Day 5: Channel API
├── GET /api/channels/{id}/messages
├── POST /api/channels/{id}/messages
└── 测试
```

### 8.3 第三阶段：Agent 优化 (Week 3)

```
Day 1-2: 生命周期管理
├── 自动重连机制
├── 健康检查
└── 优雅关闭

Day 3-4: WebSocket
├── 实时消息推送
├── 连接管理
└── 测试

Day 5: 性能优化
├── 并发控制
├── 连接池
└── 压力测试
```

---

## 9. 风险与预案

| 风险 | 影响 | 概率 | 预案 |
|------|------|------|------|
| SecondMe API 变更 | 登录失败 | 中 | 抽象 OAuth2 层，便于适配 |
| Agent 并发过高 | 系统崩溃 | 中 | 限制并发数，队列化启动 |
| Token 泄露 | 安全风险 | 低 | 加密存储，定期轮换 |
| 数据库性能 | 响应慢 | 低 | 索引优化，读写分离 |

---

## 10. 未决项

| 编号 | 问题 | 状态 | 负责人 |
|------|------|------|--------|
| [OPEN-1] | SecondMe API 是否有获取用户技能的接口？ | 待确认 | - |
| [OPEN-2] | 是否需要支持多种 OAuth 提供商？ | 待决策 | - |
| [OPEN-3] | Agent 最大并发数限制？ | 待决策 | - |
| [TBD-1] | 生产环境数据库选型（SQLite vs PostgreSQL） | 待决策 | - |

---

## 附录 A: SecondMe API 调研

### A.1 已确认的 API

基于 `oauth2_client.py` [VERIFIED]：

| API | 方法 | 用途 |
|-----|------|------|
| `/gate/lab/api/oauth/token/code` | POST | 授权码换 Token |
| `/gate/lab/api/oauth/token/refresh` | POST | 刷新 Token |
| `/gate/lab/api/secondme/user/info` | GET | 获取用户信息 |

### A.2 待调研的 API [ASSUMPTION]

| API | 用途 | 状态 |
|-----|------|------|
| `/api/user/skills` | 获取用户技能 | 待确认 |
| `/api/user/profile` | 获取完整资料 | 待确认 |
| `/api/user/connections` | 获取社交关系 | 待确认 |

---

## 附录 B: 代码引用

| 文件 | 行号 | 内容 |
|------|------|------|
| `web/oauth2_client.py` | 354-407 | get_user_info 实现 |
| `web/oauth2_client.py` | 396-397 | openId 备选逻辑 |
| `web/agent_manager.py` | 31-41 | UserAgentConfig 定义 |
| `web/app.py` | 48-65 | UserRegistrationRequest 定义 |
| `agents/dynamic_worker.py` | 47-56 | DynamicWorkerAgent 初始化 |
