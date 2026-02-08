# 需求演示网络

一个展示 `requirement_network` 模块的演示网络，用于需求驱动的智能体工作流。

## 概述

本网络演示以下功能：
- 用户智能体以自然语言提交需求
- 自动为每个需求创建频道
- 管理智能体读取注册表并邀请相关智能体
- 协调者在邀请完成后分发任务
- 工作智能体以接受/拒绝/提议的方式响应

## 架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          需求演示网络                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  事件流程：                                                                   │
│                                                                              │
│  用户智能体                                                                   │
│      │                                                                       │
│      │ 1. 提交需求（自然语言）                                                 │
│      ▼                                                                       │
│  requirement_network 模块                                                    │
│      │                                                                       │
│      │ 2. 创建频道，发送 channel_created 事件                                  │
│      ▼                                                                       │
│  管理智能体                                                                   │
│      │                                                                       │
│      │ 3. 读取注册表，选择智能体，发送邀请                                      │
│      │ 4. 发送 invitations_complete 信号                                      │
│      ▼                                                                       │
│  协调者智能体                                                                  │
│      │                                                                       │
│      │ 5. 向每个智能体分发任务                                                 │
│      ▼                                                                       │
│  工作智能体（设计师、开发者）                                                   │
│      │                                                                       │
│      │ 6. 响应：接受 / 拒绝 / 提议                                            │
│      ▼                                                                       │
│  协调者 → 用户（通知）                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 组件

### 模块
- `openagents.mods.workspace.messaging` - 基于频道的通信
- `openagents.mods.workspace.requirement_network` - 需求工作流管理

### 智能体

| 智能体 | 类型 | 角色 |
|--------|------|------|
| admin | Python | 监控 channel_created，读取注册表，邀请智能体 |
| coordinator | Python | 分发任务，处理响应 |
| designer | Python | UI/UX 设计工作者（接受设计任务，拒绝编码任务） |
| developer | Python | 软件开发工作者（接受开发任务，拒绝设计任务） |
| user | Python | 提交需求，接收更新（交互式 CLI） |

## 快速开始

### 1. 启动网络

```bash
cd /home/ubuntu/works/openagents
openagents serve private_networks/requirement_demo
```

### 2. 启动管理智能体（新终端）

```bash
cd /home/ubuntu/works/openagents
python private_networks/requirement_demo/agents/admin_agent.py
```

### 3. 启动协调者智能体（新终端）

```bash
cd /home/ubuntu/works/openagents
python private_networks/requirement_demo/agents/coordinator_agent.py
```

### 4. 启动工作智能体（新终端）

```bash
# 设计师
python private_networks/requirement_demo/agents/designer_agent.py

# 开发者
python private_networks/requirement_demo/agents/developer_agent.py
```

### 5. 启动用户智能体（新终端）

```bash
python private_networks/requirement_demo/agents/user_agent.py
```

这将提供一个交互式 CLI 用于提交需求。

### 6.（可选）通过 Studio 连接

在浏览器中打开 http://localhost:8800 访问 Studio 界面。

### 7. 提交需求

在用户智能体 CLI 或 Studio 中提交需求：

```
我需要一个创业公司的落地页，要有现代设计、响应式布局，并与我们的后端 API 集成。
```

观察以下流程：
1. 创建新频道
2. 管理者读取注册表并邀请设计师 + 开发者
3. 协调者分发设计和开发任务
4. 工作者以接受/拒绝/提议方式响应

## 智能体组和密码

| 组 | 密码 | 哈希值 |
|----|------|--------|
| admin | admin | 8c6976e5... |
| coordinators | coordinator | bf24385... |
| workers | researcher | 3588bb7... |
| users | user | 04f8996... |

## 事件

本演示使用两类事件：

- **操作事件**：用于智能体动作的请求/响应事件（提交、读取、邀请等）
- **通知事件**：通知智能体状态变化的广播事件

### 完整事件参考

| 事件名称 | 类别 | 方向 | 处理者 | 描述 |
|----------|------|------|--------|------|
| `requirement_network.requirement.submit` | 操作 | 智能体 → 模块 | 模块 | 用户提交需求；创建频道并发送 channel_created |
| `requirement_network.registry.register` | 操作 | 智能体 → 模块 | 模块 | 工作者注册能力（技能、专长） |
| `requirement_network.registry.read` | 操作 | 智能体 → 模块 | 模块 | 管理者读取智能体注册表以查找相关智能体 |
| `requirement_network.agent.invite` | 操作 | 智能体 → 模块 | 模块 | 管理者邀请智能体加入需求频道 |
| `requirement_network.invitations.complete` | 操作 | 智能体 → 模块 | 模块 | 管理者发信号表示所有邀请已完成 |
| `requirement_network.channel.join` | 操作 | 智能体 → 模块 | 模块 | 工作者加入需求频道 |
| `requirement_network.channel.info` | 操作 | 智能体 → 模块 | 模块 | 获取需求频道信息 |
| `requirement_network.task.distribute` | 操作 | 智能体 → 模块 | 模块 | 协调者向工作者分配任务 |
| `requirement_network.task.respond` | 操作 | 智能体 → 模块 | 模块 | 工作者响应任务（接受/拒绝/提议） |
| `requirement_network.channel_created` | 通知 | 模块 → 管理者 | 管理者 | 新需求频道创建时广播 |
| `requirement_network.invitations_complete` | 通知 | 模块 → 协调者 | 协调者 | 所有智能体被邀请后广播 |
| `requirement_network.notification.agent_invited` | 通知 | 模块 → 工作者 | 工作者 | 向被邀请的工作者广播频道信息 |
| `requirement_network.notification.task_distributed` | 通知 | 模块 → 工作者 | 工作者 | 任务分配时向工作者广播 |
| `requirement_network.notification.task_response` | 通知 | 模块 → 协调者 | 协调者 | 工作者响应任务时广播 |
| `requirement_network.notification.user_update` | 通知 | 模块 → 用户 | 用户 | 向用户广播任务接受/拒绝/提议信息 |

### 事件流程图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              事件流程                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  用户智能体                                                                    │
│      │                                                                        │
│      │ ──────[requirement.submit]──────────────────────────────►  模块        │
│      │                                                            │           │
│      │                                                            │           │
│      │ ◄─────[notification.user_update]───────────────────────────┤           │
│                                                                   │           │
│  管理智能体                                                        │           │
│      │                                                            │           │
│      │ ◄─────[channel_created]────────────────────────────────────┤           │
│      │                                                            │           │
│      │ ──────[registry.read]──────────────────────────────────────►           │
│      │ ──────[agent.invite]───────────────────────────────────────►           │
│      │ ──────[invitations.complete]───────────────────────────────►           │
│                                                                   │           │
│  协调者智能体                                                      │           │
│      │                                                            │           │
│      │ ◄─────[invitations_complete]───────────────────────────────┤           │
│      │ ◄─────[notification.task_response]─────────────────────────┤           │
│      │                                                            │           │
│      │ ──────[task.distribute]────────────────────────────────────►           │
│                                                                   │           │
│  工作智能体（设计师、开发者）                                        │           │
│      │                                                            │           │
│      │ ◄─────[notification.agent_invited]─────────────────────────┤           │
│      │ ◄─────[notification.task_distributed]──────────────────────┤           │
│      │                                                            │           │
│      │ ──────[registry.register]──────────────────────────────────►           │
│      │ ──────[channel.join]───────────────────────────────────────►           │
│      │ ──────[task.respond]───────────────────────────────────────►           │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 操作事件（请求/响应）

这些事件由智能体发送以请求模块执行操作。

#### `requirement_network.requirement.submit`
- **发送者**：用户智能体
- **处理者**：模块
- **载荷**：
  ```json
  {
    "requirement_text": "构建一个落地页...",
    "priority": "high",
    "deadline": "2024-01-15",
    "tags": ["web", "design"]
  }
  ```
- **响应**：`{success, requirement_id, channel_id}`

#### `requirement_network.registry.register`
- **发送者**：工作智能体
- **处理者**：模块
- **载荷**：
  ```json
  {
    "skills": ["python", "react"],
    "specialties": ["web-development", "api-design"]
  }
  ```
- **响应**：`{success}`

#### `requirement_network.registry.read`
- **发送者**：管理智能体
- **处理者**：模块
- **访问权限**：仅管理组
- **响应**：`{success, agents: [{agent_id, capabilities, ...}]}`

#### `requirement_network.agent.invite`
- **发送者**：管理智能体
- **处理者**：模块
- **载荷**：
  ```json
  {
    "channel_id": "req-abc123",
    "agent_ids": ["designer", "developer"]
  }
  ```

#### `requirement_network.task.distribute`
- **发送者**：协调者智能体
- **处理者**：模块
- **载荷**：
  ```json
  {
    "channel_id": "req-abc123",
    "agent_id": "designer",
    "task_description": "设计 UI...",
    "task_details": {"type": "design", "deliverables": ["mockups"]}
  }
  ```
- **响应**：`{success, task_id}`

#### `requirement_network.task.respond`
- **发送者**：工作智能体
- **处理者**：模块
- **载荷**：
  ```json
  {
    "channel_id": "req-abc123",
    "task_id": "task-xyz",
    "response_type": "accept|reject|propose",
    "message": "我会处理这个...",
    "reason": "超出我的专业范围...",
    "alternative": "我建议..."
  }
  ```

### 通知事件（广播）

这些事件由模块广播以通知智能体状态变化。

#### `requirement_network.channel_created`
- **触发时机**：需求提交且频道创建后
- **接收者**：管理智能体
- **载荷**：
  ```json
  {
    "channel_id": "req-abc123",
    "requirement_id": "req-abc123",
    "requirement_text": "构建一个落地页...",
    "creator_id": "user"
  }
  ```

#### `requirement_network.invitations_complete`
- **触发时机**：管理者发出邀请完成信号后
- **接收者**：协调者智能体
- **载荷**：
  ```json
  {
    "channel_id": "req-abc123",
    "requirement_id": "req-abc123",
    "requirement_text": "构建一个落地页...",
    "invited_agents": ["designer", "developer"]
  }
  ```

#### `requirement_network.notification.agent_invited`
- **触发时机**：智能体被邀请加入频道时
- **接收者**：特定工作智能体
- **载荷**：
  ```json
  {
    "channel_id": "req-abc123",
    "requirement_id": "req-abc123",
    "requirement_text": "构建一个落地页..."
  }
  ```

#### `requirement_network.notification.task_distributed`
- **触发时机**：协调者分发任务时
- **接收者**：特定工作智能体
- **载荷**：
  ```json
  {
    "channel_id": "req-abc123",
    "task_id": "task-xyz",
    "task": {
      "description": "设计 UI...",
      "type": "design",
      "deliverables": ["mockups", "wireframes"]
    }
  }
  ```

#### `requirement_network.notification.task_response`
- **触发时机**：工作者响应任务时
- **接收者**：协调者智能体
- **载荷**：
  ```json
  {
    "channel_id": "req-abc123",
    "task_id": "task-xyz",
    "agent_id": "designer",
    "response_type": "accept",
    "content": {"message": "我会处理这个..."}
  }
  ```

#### `requirement_network.notification.user_update`
- **触发时机**：收到任务响应时
- **接收者**：用户智能体
- **载荷**：
  ```json
  {
    "requirement_id": "req-abc123",
    "channel_id": "req-abc123",
    "update_type": "task_accepted|task_rejected|task_proposed",
    "agent_id": "designer",
    "task_id": "task-xyz",
    "content": {"message": "..."}
  }
  ```

## 自定义

### 添加更多工作者

在 `agents/` 目录下创建新的 Python 文件，参考 `designer_agent.py` 或 `developer_agent.py` 的模式。

关键要素：
1. 继承 `WorkerAgent`
2. 定义 `SKILLS` 和 `SPECIALTIES` 类属性
3. 添加 `@on_event("requirement_network.notification.agent_invited")` 处理器
4. 添加 `@on_event("requirement_network.notification.task_distributed")` 处理器
5. 实现 `_analyze_task()` 来决定接受/拒绝/提议

示例结构：
```python
class MyWorkerAgent(WorkerAgent):
    default_agent_id = "my-worker"
    SKILLS = ["skill1", "skill2"]
    SPECIALTIES = ["specialty1"]

    @on_event("requirement_network.notification.agent_invited")
    async def handle_agent_invited(self, context: EventContext):
        # 注册能力并加入频道
        await self._register_capabilities()
        await self.requirement_adapter.join_requirement_channel(channel_id)

    @on_event("requirement_network.notification.task_distributed")
    async def handle_task_distributed(self, context: EventContext):
        # 分析任务并响应
        analysis = self._analyze_task(task_description, task_type)
        await self.requirement_adapter.respond_to_task(...)
```

### 修改选择逻辑

编辑 `admin_agent.py`：
- `skill_keywords` 字典将技能类别映射到关键词
- `_select_agents_for_requirement()` 实现选择逻辑

### 自定义任务分发

编辑 `coordinator_agent.py`：
- `_create_task_plan()` 创建任务分配
- 根据智能体类型或能力添加自定义逻辑

### 任务响应逻辑

编辑工作智能体（`designer_agent.py`、`developer_agent.py`）：
- `DEV_KEYWORDS` / `DESIGN_KEYWORDS` - 任务匹配的关键词
- `_analyze_task()` - 接受/拒绝/提议决策逻辑
- `_generate_acceptance_message()` - 自定义接受消息

## 文件结构

```
private_networks/requirement_demo/
├── network.yaml              # 网络配置
├── README.md                 # 英文说明文档
├── README_CN.md              # 中文说明文档（本文件）
├── mods/                     # 本地模块（网络专用）
│   └── requirement_network/  # requirement_network 模块
│       ├── __init__.py       # 模块导出
│       ├── mod.py            # 网络端模块逻辑
│       ├── adapter.py        # 智能体端适配器/工具
│       ├── requirement_messages.py  # Pydantic 消息模型
│       └── eventdef.yaml     # 事件定义
├── agents/
│   ├── admin_agent.py        # 管理智能体（Python）
│   ├── coordinator_agent.py  # 协调者智能体（Python）
│   ├── designer_agent.py     # 设计师工作者（Python）
│   ├── developer_agent.py    # 开发者工作者（Python）
│   ├── user_agent.py         # 用户智能体（Python，交互式）
│   ├── designer.yaml         # 设计师工作者（YAML，旧版）
│   ├── developer.yaml        # 开发者工作者（YAML，旧版）
│   └── user_agent.yaml       # 用户智能体（YAML，旧版）
└── data/                     # 运行时数据（自动创建）
```

## 本地模块

本演示使用**本地模块**（`./requirement_network`），存储在 `mods/` 文件夹中。本地模块允许您：
- 将自定义模块与网络文件夹自包含
- 将整个演示作为便携包分发
- 修改模块行为而不影响全局安装

在 network.yaml 中使用本地模块：
```yaml
mods:
  - name: ./my_custom_mod    # "./" 前缀表示 mods/ 文件夹中的本地模块
    enabled: true
    config:
      my_setting: value
```

注意：YAML 和 Python 两种智能体版本都可用。Python 智能体提供显式的事件处理逻辑，而 YAML 智能体使用基于 LLM 的触发器处理。

## 用户智能体 CLI 命令

启动用户智能体后，可以使用以下命令：

| 命令 | 描述 |
|------|------|
| `submit <文本>` | 提交新需求 |
| `status` | 显示所有需求及其状态 |
| `quit` | 退出智能体 |

示例：
```
user> submit 我需要一个电商网站的购物车功能，支持添加商品、修改数量和结算
user> status
user> quit
```

## Web 注册服务（动态用户系统）

除了预设的工作智能体（设计师、开发者），本演示还支持**动态用户注册**。用户可以通过 Web API 注册，系统会自动为其创建专属的 Worker Agent。

### 功能特性

- **SecondMe OAuth2 登录** - 使用 SecondMe 账号进行身份认证
- **动态 Agent 创建** - 注册后自动创建 Worker Agent
- **能力注册** - Agent 自动注册技能到网络 registry
- **持久化存储** - 用户配置保存到本地，服务重启后可恢复

### 启动 Web 服务

```bash
cd /Users/nature/个人项目/Towow/raphael/requirement_demo

# 设置环境变量（SecondMe OAuth2）
export SECONDME_CLIENT_ID=your_client_id
export SECONDME_CLIENT_SECRET=your_client_secret
export SECONDME_REDIRECT_URI=http://localhost:8080/api/auth/callback

# 可选配置
export SECONDME_API_BASE_URL=https://app.mindos.com
export SECONDME_AUTH_URL=https://app.me.bot/oauth
export ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# 启动服务
uvicorn web.app:app --reload --port 8080
```

### 环境变量说明

| 变量 | 必需 | 默认值 | 描述 |
|------|------|--------|------|
| `SECONDME_CLIENT_ID` | 是 | - | SecondMe 应用 ID |
| `SECONDME_CLIENT_SECRET` | 是 | - | SecondMe 应用密钥 |
| `SECONDME_REDIRECT_URI` | 是 | - | OAuth2 回调地址 |
| `SECONDME_API_BASE_URL` | 否 | `https://app.mindos.com` | SecondMe API 地址 |
| `SECONDME_AUTH_URL` | 否 | `https://app.me.bot/oauth` | SecondMe 授权页面 |
| `ALLOWED_ORIGINS` | 否 | `http://localhost:3000,http://localhost:8080` | CORS 允许的域名 |

### API 端点

#### 认证相关

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/auth/login` | GET | 获取 SecondMe 授权 URL |
| `/api/auth/callback` | GET | 处理 OAuth2 回调 |
| `/api/auth/complete-registration` | POST | 用户补填技能后完成注册 |
| `/api/auth/refresh` | POST | 刷新 Access Token |

#### Agent 管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/register` | POST | 直接注册（无需 OAuth） |
| `/api/agents` | GET | 列出所有已注册的 Agent |
| `/api/agents/{id}` | GET | 获取指定 Agent 详情 |
| `/api/agents/{id}/action` | POST | 启动/停止/重启 Agent |
| `/api/agents/start-all` | POST | 启动所有 Agent |
| `/api/agents/stop-all` | POST | 停止所有 Agent |

### OAuth2 认证流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     SecondMe OAuth2 流程                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 前端调用 GET /api/auth/login                                  │
│     └─ 返回 authorization_url 和 state                           │
│                                                                  │
│  2. 前端重定向用户到 authorization_url                             │
│     └─ 用户在 SecondMe 页面登录并授权                              │
│                                                                  │
│  3. SecondMe 重定向回 redirect_uri?code=xxx&state=xxx            │
│                                                                  │
│  4. 前端调用 GET /api/auth/callback?code=xxx&state=xxx           │
│     └─ 返回 open_id, name, avatar, access_token                  │
│     └─ needs_registration=true 表示新用户需要补填信息              │
│                                                                  │
│  5. 前端显示补填页面，用户填写技能和专长                             │
│                                                                  │
│  6. 前端调用 POST /api/auth/complete-registration                │
│     └─ 提交 access_token, open_id, skills, specialties           │
│     └─ 系统验证 token，创建 Agent                                 │
│     └─ 返回 agent_id                                             │
│                                                                  │
│  7. 完成！Agent 已连接到 OpenAgents 网络                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 注册示例

#### 方式一：通过 OAuth2 登录（推荐）

```bash
# 1. 获取授权 URL
curl http://localhost:8080/api/auth/login

# 2. 用户完成授权后，处理回调
curl "http://localhost:8080/api/auth/callback?code=AUTH_CODE&state=STATE"

# 3. 补填信息完成注册
curl -X POST http://localhost:8080/api/auth/complete-registration \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "ACCESS_TOKEN",
    "open_id": "OPEN_ID",
    "display_name": "张三",
    "skills": ["python", "react"],
    "specialties": ["web-development"],
    "bio": "全栈开发者"
  }'
```

#### 方式二：直接注册（测试用）

```bash
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "张三",
    "skills": ["python", "react", "api-design"],
    "specialties": ["web-development", "backend"],
    "secondme_id": "test_user_001",
    "bio": "全栈开发者"
  }'
```

### 启动已注册用户的 Agent

```bash
# 启动所有 Agent
curl -X POST http://localhost:8080/api/agents/start-all

# 或启动单个 Agent
curl -X POST http://localhost:8080/api/agents/user_xxx/action \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'
```

### 完整测试流程

```bash
# 终端 1：启动网络
PYTHONPATH="./mods:$PYTHONPATH" openagents network start .

# 终端 2：启动 Admin
python agents/admin_agent.py

# 终端 3：启动 Coordinator
python agents/coordinator_agent.py

# 终端 4：启动 Web 服务
uvicorn web.app:app --reload --port 8080

# 终端 5：注册用户并启动 Agent
curl -X POST http://localhost:8080/api/register \
  -H "Content-Type: application/json" \
  -d '{"display_name":"张三","skills":["python","react"],"specialties":["web"],"secondme_id":"test001"}'

curl -X POST http://localhost:8080/api/agents/start-all

# 终端 6：提交需求测试
python agents/user_agent.py
> submit 我需要一个 React 网站
```

### 文件结构

```
web/
├── __init__.py           # 包初始化
├── app.py                # FastAPI 应用（API 端点）
├── agent_manager.py      # Agent 生命周期管理
├── oauth2_client.py      # SecondMe OAuth2 客户端
└── tests/
    └── test_oauth2_client.py  # OAuth2 单元测试

agents/
└── dynamic_worker.py     # 动态 Worker Agent 模板
```

### 安全说明

1. **Token 验证** - `complete-registration` 端点会验证 access_token 的有效性
2. **CSRF 防护** - OAuth2 流程使用 state 参数防止 CSRF 攻击
3. **CORS 配置** - 生产环境需要配置 `ALLOWED_ORIGINS` 限制允许的域名
4. **敏感信息** - 日志中的敏感信息（如 open_id）已做脱敏处理
5. **线程安全** - OAuth2 客户端使用线程锁保护单例实例
