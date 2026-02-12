# ADR-007: 用户历史数据持久化

**日期**: 2026-02-12
**状态**: 已实施
**关联**: ADR-006 (WOWOK 数据层集成)
**触发**: 用户反馈——"刷新后所有需求和协商结果全没了"

---

## 背景

当前所有运行时数据都在内存中（`app.state.*` 字典）。用户刷新页面后，前端 state 清空；后端即使没重启，前端也没有机制找回之前的协商记录。

这导致：
- 用户提交的需求刷新即丢
- "通向惊喜"生成的内容刷新即丢
- 已完成的协商方案刷新即丢
- 用户无法回顾任何历史操作

### 三种数据生命周期

| 层级 | 生命周期 | 例子 | 持久化方案 |
|------|---------|------|-----------|
| ① 临时态 | 秒级 | 正在跑的协商状态机、WS 连接 | 内存（现状，不变） |
| ② 历史态 | 天/月级 | 用户的需求、协商结果、操作记录 | **缺失——本 ADR 解决** |
| ③ 承诺态 | 永久 | 链上合约、执行记录 | WOWOK 链（ADR-006） |

## 选项分析

### 选项 A: SQLite + SQLAlchemy

- 优势：零运维，文件即数据库，项目已有 SQLAlchemy 依赖，单进程场景够用
- 优势：SQLAlchemy 让未来迁移 PostgreSQL 只需改连接字符串
- 劣势：并发写有限（但当前是单进程，不是问题）

### 选项 B: PostgreSQL

- 优势：生产级，Railway 原生支持
- 劣势：多一个外部依赖，本地开发需要额外配置
- 劣势：当前阶段用户量不需要

### 选项 C: Redis（已有）

- 优势：已经在用
- 劣势：不适合结构化历史查询，数据模型表达力弱

## 决策

**选项 A：SQLite 起步。** 当前是单进程、低并发场景，SQLite 完全够用。SQLAlchemy ORM 保证未来可无缝迁移到 PostgreSQL。

## 数据模型

### 要持久化的数据

| 数据 | 写入时机 | 查询场景 |
|------|---------|---------|
| 需求记录 | 用户提交需求时 | "我之前说过什么" |
| "通向惊喜"输出 | 流式完成时 | "分身替我想过什么" |
| 协商结果（方案） | 协商完成时 | "得到过什么方案" |
| 每条 Offer 详情 | Offer 收到时 | "谁提了什么方案" |
| 参与者 + 共振分数 | 协商完成时 | "谁参与了、匹配度如何" |
| 用户操作 | 用户确认/编辑/放弃时 | "我做过什么决定" |

### 不持久化的数据

- 协商中间状态机（临时态，完成即丢）
- WebSocket 事件流（实时推送，不是持久的）
- 编码向量（启动时重新计算）

### 表结构草案

```
negotiation_history
├── id (PK)
├── user_id (FK → agent_id)
├── scene_id
├── demand_text (用户原始输入)
├── demand_mode ("surprise" | "polish" | "manual")
├── formulated_text (丰富化后的需求，nullable)
├── assist_output ("通向惊喜"生成的文本，nullable)
├── status ("pending" | "negotiating" | "completed" | "failed")
├── plan_text (方案文本，nullable)
├── plan_json (方案结构化数据，nullable)
├── resonance_count (共振 Agent 数)
├── chain_ref (链上 Machine address，nullable — 关联 ADR-006)
├── created_at
└── updated_at

negotiation_offers
├── id (PK)
├── negotiation_id (FK → negotiation_history.id)
├── agent_id
├── agent_name
├── resonance_score
├── offer_text (完整 Offer 内容)
├── confidence
├── status ("received" | "included" | "excluded")
└── created_at

negotiation_participants
├── id (PK)
├── negotiation_id (FK → negotiation_history.id)
├── agent_id
├── agent_name
├── role ("resonated" | "offered" | "exited")
├── resonance_score
└── created_at
```

### 与 ADR-006 的关系

历史态（②）和承诺态（③）通过 `chain_ref` 字段关联：

```
协商引擎（内存①） ──完成──→ 历史数据库（②） ──用户确认上链──→ WOWOK 链（③）
                                  │                              │
                                  └── chain_ref ←────────────────┘
```

历史数据库的 schema 按产品需求设计，不按 WOWOK 对象模型设计。两者职责不同：
- 历史数据库：服务用户体验（"我做过什么"）
- WOWOK 链：服务信任和执行（"谁承诺了什么"）

## 新增 API

```
GET  /store/api/history?scene_id=hackathon&limit=20
     → 返回用户的协商历史列表

GET  /store/api/history/{negotiation_id}
     → 返回单次协商详情（含所有 Offer）
```

## 核心原则

| 原则 | 体现 |
|------|------|
| 0.2 本质与实现分离 | 历史态 vs 承诺态分离，各用合适的存储 |
| 0.7 简单规则生长 | SQLite → PostgreSQL，SQLAlchemy 让切换无痛 |

## 影响范围

| 模块 | 影响 |
|------|------|
| `backend/database.py` | 重写——新 schema，替代 legacy 表 |
| `backend/server.py` | 启动时初始化 DB 连接 |
| `apps/app_store/backend/routers.py` | 协商完成时写入历史；新增 history API |
| `website/` (前端) | 页面加载时拉取历史；展示历史列表/恢复 |
| `docs/ENGINEERING_REFERENCE.md` | 新增 history API 契约 |

## 已确认

- **全量保存，全量展示**：不设上限，每条协商历史都存，用户都能看到
- **列表 + 详情**：用户看到完整历史列表，每条都能点进去看详情（含所有 Offer）
- **不做删除**：当前阶段不需要
