# ToWow 项目交接文档

> **交接日期**: 2025-01-23
> **交接目标**: 让队友接手开发一个**真实可用的应用**，而非模拟系统

---

## 重要警告：模拟思维是根本性错误

### 问题描述

在之前的开发过程中，存在严重的**"模拟思维"错误**：

```
错误做法：用 asyncio.sleep() 添加延迟来"模拟"协商过程
正确做法：建立真实的事件驱动依赖关系，前一步完成自然触发后一步
```

### 具体表现

1. **添加延迟来模拟阶段感**
   ```python
   # 错误代码示例（已存在于 config.py）
   FILTER_STAGE_DELAY = 1.5      # 筛选完成前延迟
   AGENT_RESPONSE_DELAY = 0.8    # 每个 agent 响应延迟
   ```

   **为什么这是错的？**
   - 延迟只是掩盖了依赖关系没理清楚的问题
   - 真实应用中，LLM 调用本身就需要时间，不需要人为延迟
   - 真实应用是"A完成 → 触发B"，不是"A完成 → 等1秒 → 触发B"

2. **Mock 数据直接返回**
   - 很多地方用 Mock 数据直接返回，跳过了真实 LLM 调用
   - 导致整个流程"瞬间完成"，然后用延迟去"模拟"真实感

### 正确的开发方向

```
目标：开发真实可用的应用
- 真实调用 LLM（不是 Mock）
- 真实的事件驱动（不是人为延迟）
- 真实的 Agent 协作（不是模拟消息传递）
```

---

## 一、项目概述

### 1.1 项目目标

ToWow 是一个**多 Agent 协商平台**，核心场景：
- 用户提出需求（如"找人帮我开发一个网站"）
- 系统筛选合适的候选人
- 多个 Agent 代表候选人进行协商
- 最终达成最优方案

### 1.2 项目结构

```
/Users/nature/个人项目/Towow/
├── .ai/                          # AI 辅助开发文档（重要！）
│   ├── epic-multiagent-negotiation/
│   │   ├── PRD-multiagent-negotiation-v3.md    # 产品需求文档
│   │   ├── TECH-multiagent-negotiation-v3.md   # 技术方案文档
│   │   ├── STORY-01.md ~ STORY-07.md           # 用户故事
│   │   ├── TASK-T01.md ~ TASK-T09.md           # 任务分解
│   │   └── PROJ-multiagent-negotiation-v3.md   # 项目规划
│   ├── DATABASE-CONNECTION.md     # 数据库连接文档（给 DBA）
│   ├── DEPLOYMENT-CONFIG.md       # 部署配置文档
│   └── HANDOVER-DOCUMENT.md       # 本交接文档
│
├── towow/                        # 后端代码（Python/FastAPI）
│   ├── api/
│   │   ├── main.py              # FastAPI 入口
│   │   └── routers/
│   │       ├── demand.py        # 需求提交 API（核心入口）
│   │       └── events.py        # SSE 事件推送
│   ├── openagents/
│   │   └── agents/
│   │       ├── coordinator.py   # 协调者 Agent
│   │       ├── channel_admin.py # 频道管理 Agent
│   │       ├── user_agent.py    # 用户代理 Agent
│   │       └── router.py        # Agent 消息路由
│   ├── config.py                # 配置文件（含错误的延迟配置）
│   └── venv/                    # Python 虚拟环境
│
├── towow-frontend/              # 前端代码（React/TypeScript）
│   ├── src/
│   │   ├── pages/
│   │   │   └── NegotiationPage.tsx  # 协商页面
│   │   ├── hooks/
│   │   │   └── useSSE.ts        # SSE 连接 Hook
│   │   └── stores/
│   │       └── eventStore.ts    # 事件状态管理
│   └── package.json
│
├── openagents/                  # OpenAgent 框架（独立仓库）
│   ├── README.md
│   ├── demos/                   # 示例项目
│   └── src/openagents/          # 框架源码
│
├── worktree-local-fix/          # Git Worktree: 本地修复分支
├── worktree-openagent/          # Git Worktree: OpenAgent 迁移分支
│   └── .ai/
│       ├── MIGRATION-openagent-analysis.md  # 迁移分析文档
│       └── TASK-openagent-migration.md      # 迁移任务分解
│
├── ToWow-Design-MVP.md          # 设计文档（手写，重要！）
├── OPENAGENTS_DEV_GUIDE.md      # OpenAgent 开发指南
├── TESTING_GUIDE.md             # 测试指南
└── start-dev.sh                 # 开发环境启动脚本
```

---

## 二、必读文档清单

### 2.1 设计文档（理解业务）

| 优先级 | 文档 | 说明 |
|--------|------|------|
| P0 | `ToWow-Design-MVP.md` | 手写的核心设计文档，包含业务逻辑、协商流程、Agent 架构 |
| P0 | `.ai/epic-multiagent-negotiation/PRD-multiagent-negotiation-v3.md` | PRD v3，产品需求细节 |
| P1 | `.ai/epic-multiagent-negotiation/TECH-multiagent-negotiation-v3.md` | 技术方案，API 设计、事件定义 |
| P1 | `.ai/epic-multiagent-negotiation/STORY-*.md` | 7 个用户故事 |

### 2.2 开发文档（理解实现）

| 优先级 | 文档 | 说明 |
|--------|------|------|
| P0 | `OPENAGENTS_DEV_GUIDE.md` | OpenAgent 开发指南 |
| P0 | `openagents/llm.txt` | **给大模型看的文档**，丢给 LLM 就知道如何开发 OpenAgent |
| P1 | `.ai/epic-multiagent-negotiation/TASK-*.md` | 9 个任务分解文档 |
| P2 | `TESTING_GUIDE.md` | 测试指南 |

### 2.3 运维文档

| 文档 | 说明 |
|------|------|
| `.ai/DATABASE-CONNECTION.md` | 数据库连接配置，交给 DBA |
| `.ai/DEPLOYMENT-CONFIG.md` | 部署配置，支持动态更新 |

---

## 三、两条开发路线

### 3.1 路线对比

| 对比项 | 本地分支 (fix/local-e2e) | OpenAgent 迁移 (feature/openagent-migration) |
|--------|--------------------------|---------------------------------------------|
| 当前状态 | 已合并到 main | 方案文档完成，待执行 |
| 代码位置 | `/Users/nature/个人项目/Towow/` | `/Users/nature/个人项目/Towow/worktree-openagent/` |
| 适用场景 | 快速验证、演示 | **生产部署（强制要求）** |
| 问题 | 存在"模拟思维"问题 | 需要按方案实施迁移 |

### 3.2 OpenAgent 是强制要求

```
重要：大型部署必须使用 OpenAgent，这是强制要求。
```

**原因：**
1. OpenAgent 提供完整的 Agent 生命周期管理
2. 内置 Studio UI 用于监控和调试
3. 支持多协议（HTTP、gRPC、MCP）
4. 避免重复造轮子
5. 社区维护，持续更新

### 3.3 OpenAgent 迁移文档

已完成的迁移分析文档：
- `worktree-openagent/.ai/MIGRATION-openagent-analysis.md` - 完整迁移分析
- `worktree-openagent/.ai/TASK-openagent-migration.md` - 迁移任务分解

**如何使用 OpenAgent：**
1. 阅读 `openagents/llm.txt`（这是给大模型看的，丢给 LLM 就知道如何开发）
2. 参考 `openagents/demos/` 目录下的示例
3. 按照迁移文档实施

---

## 四、遇到的问题记录

### 4.1 问题清单

| 编号 | 问题 | 根因 | 错误修复 | 正确方向 |
|------|------|------|----------|----------|
| P-01 | Submit 超时 30 秒 | 同步阻塞 LLM 调用 | 改异步 ✓ | - |
| P-02 | 一直显示"连接中" | channel_id 计算不一致 | 统一计算 ✓ | - |
| P-03 | 候选人只有 3 个 | Mock 数据太少 | 扩展到 12 个 | **应该查数据库** |
| P-04 | 响应收集停滞 | send_to_agent 是空 Mock | 新增 router.py | **应该用 OpenAgent 路由** |
| P-05 | 消息循环/重复处理 | 无去重机制 | 添加幂等性 ✓ | - |
| P-06 | SSE 双重连接 | React Strict Mode | 添加 isConnectingRef ✓ | - |
| **P-07** | **协商瞬间完成** | **Mock 直接返回** | **添加延迟（错误！）** | **真实调用 LLM** |

### 4.2 核心问题详解：P-07 协商瞬间完成

**问题现象：**
- 点击"开始协商"后，所有事件在毫秒级内连续发出
- 用户看不到协商过程，直接看到结果

**错误分析（之前的做法）：**
```python
# config.py 中添加的延迟配置（这是错误的！）
ENABLE_STAGE_DELAYS = True
FILTER_STAGE_DELAY = 1.5      # 筛选完成前延迟
AGENT_RESPONSE_DELAY = 0.8    # 每个 agent 响应延迟
```

**为什么是错的：**
1. 延迟只是"模拟"真实感，不是解决问题
2. 真正的问题是：**没有真实调用 LLM**
3. 如果真实调用 LLM，每次调用本身就需要时间，不需要人为延迟

**正确方向：**
```
真实应用 = 真实 LLM 调用 + 事件驱动
- Coordinator 调用 LLM 理解需求 → 发出 demand.understood 事件
- UserAgent 调用 LLM 生成响应 → 发出 offer.submitted 事件
- ChannelAdmin 调用 LLM 聚合方案 → 发出 proposal.distributed 事件

每一步都是真实的 LLM 调用，自然有时间消耗，不需要人为延迟。
```

### 4.3 问题修复历史

```
2025-01-22:
- 修复 P-01: 改为异步处理
- 修复 P-02: 统一 channel_id 计算
- 修复 P-03: 扩展 Mock 候选人
- 修复 P-04: 新增 router.py
- 修复 P-05: 添加幂等性控制
- 修复 P-06: 添加 isConnectingRef

2025-01-23:
- 错误修复 P-07: 添加延迟配置（这是模拟思维的错误！）
- 正确方向: 应该去掉 Mock，真实调用 LLM
```

---

## 五、开发经验与教训

### 5.1 核心教训：不要用模拟思维做真实应用

```
模拟思维 vs 真实应用思维

模拟思维（错误）：
- "LLM 调用太慢了，先用 Mock 数据"
- "协商过程太快了，加点延迟让它看起来真实"
- "消息路由太复杂了，先写个简单的模拟"

真实应用思维（正确）：
- "LLM 调用本身就需要时间，这是正常的"
- "每一步都有依赖关系，前一步完成才触发后一步"
- "用成熟框架（OpenAgent）处理 Agent 协作"
```

### 5.2 具体教训

| 教训 | 说明 |
|------|------|
| Mock 是临时的 | Mock 只用于单元测试，不能进入主流程 |
| 延迟是错误信号 | 如果需要添加延迟，说明依赖关系没理清楚 |
| 框架优于自研 | Agent 协作用 OpenAgent，不要重复造轮子 |
| 事件驱动 | 用事件驱动，不是轮询或延迟 |

### 5.3 正确的开发流程

```
1. 理解设计文档 → 明确业务流程和依赖关系
2. 使用 OpenAgent → 利用成熟框架处理 Agent 协作
3. 真实调用 LLM → 不用 Mock，直接对接 LLM API
4. 事件驱动 → 前一步完成自然触发后一步
5. 端到端测试 → 验证整个流程是否正确
```

---

## 六、待办事项

### 6.1 立即需要做的

| 任务 | 说明 | 负责人 |
|------|------|--------|
| 去掉延迟配置 | 删除 config.py 中的 STAGE_DELAY 配置 | 队友 |
| 真实 LLM 调用 | 确保所有 Agent 都真实调用 LLM | 队友 |
| OpenAgent 迁移 | 按迁移文档实施 | 队友 |

### 6.2 后续需要做的

| 任务 | 说明 |
|------|------|
| 数据库对接 | 候选人从数据库查询，不是 Mock |
| 部署配置 | 按 DEPLOYMENT-CONFIG.md 部署 |
| 监控告警 | 接入 OpenAgent Studio UI |

---

## 七、启动命令

### 7.1 本地开发

```bash
# 终端1 - 后端
cd /Users/nature/个人项目/Towow/towow
source venv/bin/activate
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 终端2 - 前端
cd /Users/nature/个人项目/Towow/towow-frontend
npm run dev
```

### 7.2 运行测试

```bash
cd /Users/nature/个人项目/Towow/towow
source venv/bin/activate
python -m pytest tests/ -v
```

### 7.3 Git Worktree 管理

```bash
# 查看所有 worktree
git worktree list

# 切换到 OpenAgent 迁移分支
cd /Users/nature/个人项目/Towow/worktree-openagent

# 切换到本地修复分支
cd /Users/nature/个人项目/Towow/worktree-local-fix
```

---

## 八、联系方式与分工

| 角色 | 职责 |
|------|------|
| 原开发者 (Claude) | 本文档作者，提供技术支持 |
| 队友 | 接手开发真实应用，部署到 OpenAgent |
| DBA | 数据库配置，参考 DATABASE-CONNECTION.md |

---

## 九、附录

### 9.1 关键代码文件

| 文件 | 作用 | 需要修改 |
|------|------|----------|
| `towow/api/routers/demand.py` | 需求提交入口 | 确保真实调用 LLM |
| `towow/openagents/agents/coordinator.py` | 协调者 | 迁移到 OpenAgent |
| `towow/openagents/agents/channel_admin.py` | 频道管理 | 迁移到 OpenAgent |
| `towow/openagents/agents/user_agent.py` | 用户代理 | 迁移到 OpenAgent |
| `towow/config.py` | 配置 | **删除延迟配置** |

### 9.2 事件类型

```
towow.demand.submitted      # 需求提交
towow.demand.understood     # 需求理解完成
towow.filter.completed      # 候选人筛选完成
towow.channel.created       # 协商频道创建
towow.demand.broadcast      # 需求广播给候选人
towow.offer.submitted       # 候选人提交报价
towow.aggregation.started   # 开始聚合方案
towow.proposal.distributed  # 方案分发给用户
towow.feedback.submitted    # 用户提交反馈
towow.gap.identified        # 识别到缺口
towow.subnet.triggered      # 触发子网解决缺口
towow.negotiation.finalized # 协商完成
```

### 9.3 OpenAgent 关键文件

```
openagents/
├── llm.txt                  # 给大模型看的开发指南（重要！）
├── README.md                # 框架说明
├── demos/
│   ├── 00_hello_world/      # 最简单的示例
│   ├── 01_startup_pitch_room/ # 多 Agent 协作示例
│   └── ...
└── src/openagents/          # 框架源码
```

---

**文档结束**

> 记住：**开发真实应用，不是模拟系统。**
