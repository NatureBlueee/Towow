# PLAN-002: MCP Server 实现

**关联**: ADR-002 (已批准), SPEC-002-mcp-interface-design (阶段 ③ 完成)
**阶段**: ④ 实现方案

---

## 技术选型

| 决策 | 选择 | 理由 |
|------|------|------|
| 语言 | Python | 与 backend 同栈，共享理解 |
| SDK | `mcp` (官方 Python SDK) | MCPServer + @tool 装饰器，最简 |
| Transport | stdio | MCP 标准，Claude Code / Cursor 原生支持 |
| 后端 API | Store API (`/store/api/*`) | 已有全部所需端点，不需新增 backend 代码 |
| 分发 | pip install（本地 / PyPI） | Python 开发者熟悉 |

---

## 变更总览

| # | 文件 | 类型 | 说明 |
|---|------|------|------|
| 1 | `mcp-server/` | **新建目录** | MCP Server 独立包 |
| 2 | `mcp-server/pyproject.toml` | **新建** | 包定义 + 依赖 |
| 3 | `mcp-server/towow_mcp/server.py` | **新建** | MCP Server 主文件（5 个 tools） |
| 4 | `mcp-server/towow_mcp/client.py` | **新建** | Backend REST API 客户端 |
| 5 | `mcp-server/towow_mcp/config.py` | **新建** | 本地配置管理 (~/.towow/) |
| 6 | `mcp-server/README.md` | **新建** | 安装和使用说明 |

**后端零改动**。所有 MCP 操作通过已有 Store API 完成。

---

## 目录结构

```
mcp-server/
├── pyproject.toml           # 包定义，入口 towow-mcp
├── README.md                # 安装 + Claude Code 配置说明
└── towow_mcp/
    ├── __init__.py
    ├── server.py            # MCPServer + 5 个 @tool
    ├── client.py            # TowowClient（httpx，调 Store API）
    └── config.py            # ~/.towow/config.json 读写
```

---

## 变更 1-2: 包结构

### pyproject.toml

```toml
[project]
name = "towow-mcp"
version = "0.1.0"
description = "通爻网络 MCP Server — 在 Claude Code / Cursor 中连接通爻"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0",
    "httpx>=0.27",
]

[project.scripts]
towow-mcp = "towow_mcp.server:main"
```

安装方式：`pip install -e ./mcp-server` 或未来 `pip install towow-mcp`

---

## 变更 3: server.py — 5 个 MCP Tools

### V1 工具集（普通模式优先）

| Tool | 对应 Store API | 说明 |
|------|---------------|------|
| `towow_scenes` | `GET /store/api/scenes` | 列出场景 |
| `towow_agents` | `GET /store/api/agents?scope=...` | 列出 Agent |
| `towow_join` | `POST /store/api/quick-register` | 注册 Agent（复用 ADR-009） |
| `towow_demand` | `POST /store/api/negotiate` | 提交需求 + 轮询结果 |
| `towow_status` | `GET /store/api/negotiate/{id}` | 查看协商状态 |

### 工具语义

**`towow_scenes`** — 只读
```
输入: 无
输出: 场景列表 [{scene_id, name, description, agent_count}]
```

**`towow_agents`** — 只读
```
输入: scope (可选, 如 "scene:hackathon")
输出: Agent 列表 [{agent_id, display_name, source, bio}]
```

**`towow_join`** — 注册
```
输入: email, display_name, raw_text, scene_id (可选)
输出: agent_id, display_name, message
副作用: 持久化 agent_id 到 ~/.towow/config.json
```
- 复用 quick-register API（与 Playground / 入口页邮箱注册完全相同的后端）
- raw_text = 用户粘贴/描述的任意文本
- 注册后 agent_id 自动保存到本地配置，后续工具自动使用

**`towow_demand`** — 提交需求 + 等待结果
```
输入: intent (自然语言需求), scope (可选)
输出: negotiation_id, state, plan_output (如果已完成)
前置: 必须先 towow_join
```
- 从 config 读取 agent_id 作为 user_id
- 调 `POST /store/api/negotiate` 提交
- 轮询 `GET /store/api/negotiate/{id}` 等待完成（间隔 3s，最多 120s）
- 每次状态变化输出进度信息
- 完成后返回方案

**`towow_status`** — 查看状态
```
输入: negotiation_id (可选，默认最近一次)
输出: 完整协商状态 + 人类可读摘要
```

### 实现模式

```python
from mcp.server import MCPServer

app = MCPServer("towow")

@app.tool()
async def towow_scenes() -> str:
    """列出通爻网络中的所有场景。"""
    client = get_client()
    scenes = await client.get_scenes()
    # 格式化为可读文本
    ...

@app.tool()
async def towow_join(email: str, display_name: str, raw_text: str, scene_id: str = "") -> str:
    """加入通爻网络。提供你的邮箱、名字和自我介绍。"""
    client = get_client()
    result = await client.quick_register(email, display_name, raw_text, scene_id)
    save_config(agent_id=result["agent_id"])
    ...
```

### Skill 调度

| 子任务 | Skill |
|--------|-------|
| MCP 工具设计 | `arch`（接口已有，确认映射） |
| REST 客户端实现 | `towow-dev` |
| 工具实现 | `towow-dev` |
| README 文档 | `towow-dev` |

---

## 变更 4: client.py — Store API 客户端

```python
class TowowClient:
    def __init__(self, backend_url: str):
        self.base = backend_url  # e.g. "https://xxx.railway.app"
        self.http = httpx.AsyncClient(timeout=30)

    async def get_scenes(self) -> list[dict]: ...
    async def get_agents(self, scope="all") -> list[dict]: ...
    async def quick_register(self, email, name, raw_text, scene_id="") -> dict: ...
    async def negotiate(self, intent, scope, user_id) -> dict: ...
    async def get_negotiation(self, neg_id) -> dict: ...
```

所有方法直接调 Store API。URL 格式：`{base}/store/api/xxx`。

---

## 变更 5: config.py — 本地配置

```python
CONFIG_DIR = Path.home() / ".towow"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 配置结构
{
    "agent_id": "pg_xxxxxxxx",
    "display_name": "用户名",
    "backend_url": "https://xxx.railway.app",
    "last_negotiation_id": "neg_xxx"
}
```

- 首次 `towow_join` 时创建
- 后续工具自动读取 agent_id
- backend_url 默认指向生产环境，可通过环境变量 `TOWOW_BACKEND_URL` 覆盖

---

## 变更 6: README.md — 安装说明

内容包括：
1. 安装方式 (`pip install towow-mcp`)
2. Claude Code 配置 (`.claude/mcp.json`)
3. Cursor 配置
4. 快速上手示例（3 步：加入 → 提需求 → 看结果）

### Claude Code 配置示例

```json
{
  "mcpServers": {
    "towow": {
      "command": "towow-mcp",
      "args": []
    }
  }
}
```

---

## Store API 映射验证

| MCP 需要 | Store API 端点 | 状态 |
|----------|---------------|------|
| 列出场景 | `GET /store/api/scenes` | ✅ 已有 |
| 列出 Agent | `GET /store/api/agents?scope=xxx` | ✅ 已有 |
| 注册 Agent | `POST /store/api/quick-register` | ✅ 已有 (ADR-009) |
| 提交需求 | `POST /store/api/negotiate` | ✅ 已有 |
| 查询协商 | `GET /store/api/negotiate/{id}` | ✅ 已有 |
| 网络信息 | `GET /store/api/info` | ✅ 已有 |

**后端零改动确认**。所有端点都已存在。

---

## 端到端验证

### 链路: MCP 用户完整协商

```
用户在 Claude Code 中:
  "列出通爻网络的场景"
    → towow_scenes → GET /store/api/scenes → 返回场景列表

  "我想加入，我叫张三，邮箱 z@x.com，我是全栈工程师..."
    → towow_join → POST /store/api/quick-register → agent_id 保存到 ~/.towow/

  "我想组一个 hackathon 团队，需要前端和设计师"
    → towow_demand → POST /store/api/negotiate → 轮询 → 返回方案

  "看看刚才的协商结果"
    → towow_status → GET /store/api/negotiate/{id} → 返回详情
```

---

## 与 ADR-010 的交叉点

ADR-010 入口页的 MCP 按钮需要链接到某个页面。选项：
- `mcp-server/README.md` 的 GitHub URL
- 或在 website 建一个 `/mcp` 静态页（安装说明）

**建议**：先用 GitHub README 链接，后续再做漂亮的安装页。

---

## 不做（V1 scope 外）

- 开发者模式 8 个工具（V1 只做普通模式 5 个）
- create_scene（V1 用已有场景）
- Token 认证（V1 用 agent_id 直传，Store API 不需要认证）
- 模式切换
- 多入口身份联通（MCP + SecondMe）
- formulation 确认步骤（V1 的 Store negotiate API 是自动确认的）
