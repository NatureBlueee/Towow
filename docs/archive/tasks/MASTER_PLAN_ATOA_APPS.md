# AToA 应用生态 — 总体计划

> 创建日期：2026-02-09
> 状态：执行中
> 目标：基于 SDK 构建 5 个生产级 AToA 应用 + 1 个应用商城（App Store）

## 愿景

所有 AToA 应用共享同一个协议层。用户使用任何一个应用的入口，都能享受到所有应用的价值。不是"推荐你去用另一个应用"，而是"直接在当前界面给到其他应用的 Agent 产出的价值"。

**核心洞察**：响应范式在应用级别的应用——需求信号跨应用传播，相关的 Agent 无论属于哪个应用都会响应。

**例子**：用户在 AI 招聘应用中说"需要一个高级后端开发者"——
- 招聘应用的 Agent：从候选人库中响应
- 黑客松应用的 Agent：某个参赛者在上次黑客松中展示了优秀的后端能力
- 技能交换应用的 Agent：某个自由职业者有后端专长且可用
- 用户在招聘界面上直接看到这些跨应用的响应，直接获得价值

## 项目清单

| # | 应用 | 类型 | 优先级 | 状态 |
|---|------|------|--------|------|
| 1 | S1 黑客松组队 | SDK 应用 | P0 | 待开发 |
| 2 | S2 技能交换 | SDK 应用 | P0 | 待开发 |
| 3 | R1 AI 招聘 | SDK 应用 | P1 | 待开发 |
| 4 | M1 AI 相亲/匹配 | SDK 应用 | P1 | 待开发 |
| 5 | AS1 AToA 应用商城 | 平台/联邦 | P0 | 待设计 |

## 架构设计：跨应用共振

### 核心机制

```
┌─────────────────────────────────────────────────┐
│                AToA App Store                    │
│            （联邦信号路由层）                      │
│                                                  │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐        │
│  │ S1   │  │ S2   │  │ R1   │  │ M1   │  ...   │
│  │黑客松│  │技能  │  │招聘  │  │相亲  │        │
│  │组队  │  │交换  │  │      │  │      │        │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘        │
│     │         │         │         │             │
│     └────────┬┴─────────┴─────────┘             │
│              │                                   │
│     ┌────────▼────────┐                          │
│     │  Signal Router   │  需求信号在所有应用间传播 │
│     │  (协议层路由)     │  Agent 自主判断是否响应   │
│     └─────────────────┘                          │
└─────────────────────────────────────────────────┘
```

### 技术实现

每个应用 = 独立的 FastAPI 服务 + SDK 引擎实例

**联邦层**（App Store 服务）：
- 应用注册接口：每个 app 启动时注册自己的 agents
- 信号路由：当 App A 发起需求，路由到所有注册的 App
- 响应聚合：收集跨应用的 Offer，合并到 Center 的输入中
- 实现方式：共享的 `ProfileDataSource` 聚合所有应用的 Agent 数据

**关键设计决策**：
1. 联邦层不是新的引擎——它是在 SDK 的 `ProfileDataSource` 层做文章
2. 每个应用可以独立运行（不连接 App Store 也能用）
3. 连接 App Store 后，`ProfileDataSource` 自动扩展到跨应用 Agent
4. 协议层不变——只是 Agent 来源扩大了

### 共享基础

所有应用共享：
- `towow-sdk`（pip install）
- 共同的 `PlatformLLMClient` 实现（Anthropic/OpenAI/Mock）
- 共同的事件推送模式（WebSocket）
- 共同的前端组件模式（协商进度、方案展示）

每个应用独特的：
- `ProfileDataSource`（不同的画像数据结构）
- 定制的 `DemandFormulationSkill`（不同的需求理解方式）
- 定制的 `OfferGenerationSkill`（不同的响应方式）
- 场景特定的 UI

## 技术栈

- **后端**：FastAPI + towow-sdk + Python 3.10+
- **前端**：Next.js（与现有 website 一致）或轻量 HTML/CSS/JS
- **LLM**：Anthropic Claude（主）/ Mock（开发）
- **数据**：JSON 文件（V1）→ SQLite（V2）
- **部署**：各应用独立端口，App Store 做路由

## 执行计划

### Phase 1：基础 + S1（优先）
1. 创建共享应用模板（所有应用的骨架代码）
2. 构建 S1 黑客松组队应用（第一个完整的 SDK 应用）
3. 验证 SDK 可用性，记录开发体验

### Phase 2：S2 + App Store 架构
4. 构建 S2 技能交换平台
5. 设计并实现 App Store 联邦层
6. S1 和 S2 接入 App Store

### Phase 3：扩展应用
7. 构建 R1 AI 招聘应用
8. 构建 M1 AI 相亲/匹配应用
9. 所有应用接入 App Store

### Phase 4：验证跨应用共振
10. 端到端测试：一个需求跨 4 个应用产生响应
11. SDK 使用体验报告
12. 架构经验总结

## Teams 结构

### Team S1（黑客松组队应用）
- 后端开发：SDK 集成 + API 路由
- 前端开发：需求提交 + 协商进度 + 方案展示
- 数据设计：参赛者画像 + Skill 定制

### Team S2（技能交换平台）
- 后端开发：SDK 集成 + 不对称角色处理
- 前端开发：需求方/提供方双视角
- 数据设计：自由职业者画像 + 场景 Skill

### Team AS（App Store）
- 架构设计：联邦信号路由
- 后端开发：注册 + 路由 + 聚合
- 集成测试：跨应用协商

## SDK 反馈记录

开发过程中发现的 SDK 问题和建议，实时记录到：
`research/sdk_feedback/development_notes.md`

记录维度：
- API 可用性问题
- 文档缺失
- Protocol 设计建议
- 性能观察
- 错误处理体验

## 关键约束

1. **只用 SDK 公开 API** — `from towow import ...`
2. **不修改核心代码** — `backend/towow/` 下的文件不动
3. **中文优先** — 所有界面和内容
4. **生产级质量** — 不是 demo，是可以部署给用户用的
5. **解耦** — 每个应用独立可运行，App Store 是增强而非依赖

## 新 Skill 规划（Claude Code Skills）

可能需要创建的辅助技能：
- `atoa-app-dev`：AToA 应用开发的工程规范和最佳实践
- `app-store-arch`：应用商城/联邦架构的设计指导

## 文件结构规划

```
apps/
├── shared/                    # 共享基础
│   ├── base_app.py           # FastAPI 应用模板
│   ├── llm_clients.py        # LLM 客户端实现（Claude/Mock）
│   ├── event_handlers.py     # WebSocket 事件处理
│   └── frontend/             # 共享前端组件
│
├── S1_hackathon/             # 黑客松组队应用
│   ├── backend/
│   │   ├── app.py            # FastAPI 入口
│   │   ├── data_source.py    # ProfileDataSource 实现
│   │   ├── skills.py         # 场景定制 Skill
│   │   └── data/             # 参赛者画像数据
│   └── frontend/
│       └── ...
│
├── S2_skill_exchange/        # 技能交换平台
│   ├── backend/
│   │   ├── app.py
│   │   ├── data_source.py
│   │   ├── skills.py
│   │   └── data/
│   └── frontend/
│       └── ...
│
├── R1_recruitment/           # AI 招聘
│   └── ...（同上结构）
│
├── M1_matchmaking/           # AI 相亲
│   └── ...（同上结构）
│
└── app_store/                # AToA 应用商城
    ├── backend/
    │   ├── app.py            # App Store 服务
    │   ├── registry.py       # 应用注册
    │   ├── router.py         # 信号路由
    │   └── federation.py     # 联邦 ProfileDataSource
    └── frontend/
        └── ...
```
