# ADR-011: V2 Intent Field

**日期**: 2026-02-15
**状态**: 已批准
**关联**: Protocol Genome v0.3, Phase 0-2 实验报告 (`tests/field_poc/EXPERIMENT_REPORT.md`)

## 背景

V1 协商引擎验证了"投影-匹配-判定"基本链路可以工作（221 个测试，447 个 Agent，App Store 端到端演示）。但 Genome v0.3 §8 识别出 V1 的五个结构性偏差：

1. **Intent 分叉**：demand 和 profile 走不同数据路径（formulate vs AgentRegistry）
2. **过度工程化**：五步固定管道（formulate→resonate→offer→synthesize→approve），非可组合操作
3. **无持久场**：每次请求扫描全 Agent 池，HTTP 请求-响应心智模型
4. **越界透镜**：synthesize 在 approve 之前做了"什么值得呈现"的判定
5. **无循环**：终端式 approve（yes/no 即结束），无反馈-递归机制

同时，Phase 0-2 实验锁定了编码策略：

- Phase 0: MiniLM-384d 基线 14/20 通过，L4 仅 1/5
- Phase 1: mpnet-768d + chunked bundle + SimHash binary 最优（16/20，L4 3-4/5）
- Phase 2: Raw encode 赢了所有 LLM formulation 策略（3/6 vs 1-2/6）

**核心问题**：V1 的偏差不是 bug，是架构层面的世界观偏移。修补 V1 不如从 Genome v0.3 干净重建。

## 选项分析

### 选项 A: 重构 V1

在现有 `backend/towow/` 上改造：统一 Intent 数据结构，拆除 synthesize，增加持久场。

- 优势：复用已有 221 个测试和基础设施代码
- 劣势：V1 的固定管道架构（状态机 8 状态 + 5 个 Skill 模块）深度耦合。统一 Intent 需要改 models.py、engine.py、所有 5 个 skill、所有 API schema——实际上是全量重写但受旧架构约束。改到一半两边都不干净

### 选项 B: V2 独立模块，V1 保留为参考

新建独立的 Field 模块，实现 Genome v0.3 的协议边界（encode + field + match + visibility）。V1 代码不动，作为参考实现。

- 优势：干净的架构映射，不受 V1 心智模型束缚。V1 仍然可运行。两个版本可以并行验证
- 劣势：不能复用 V1 基础设施代码（但 V1 基础设施代码本身不多——主要是 LLM client 和 event pusher，这些属于应用层不属于 Field）

## 决策

**选项 B：V2 独立模块。**

V2 Intent Field 是一个独立模块，不导入、不依赖 V1 的任何代码。V1 保留在 `backend/towow/` 作为参考实现。

## 核心设计决策

### 决策 1：Intent 统一（Genome §2）

demand 和 profile 是同一种粒子——Intent。一种数据结构，一条编码路径。

- 用户输入 "我需要一个懂 Rust 的全栈工程师" → Intent
- Agent Profile "全栈工程师，5年 Rust 经验" → Intent
- 用户的隐式画像碎片 "今天在B站看了个音乐可视化" → Intent
- 链上行为数据 "完成了 3 次交付，评分 4.8" → Intent

来源不同，编码后处理方式完全相同。

### 决策 2：两个协议动词（Genome §3）

协议边界内只有两个动词：

- **deposit**: Intent 进入场。`text → encode → store`
- **match**: Intent 在场中找到相关 Intent。`text → encode → nearest → results`

encode/project/bundle/nearest 是实现细节，不是协议动词。remove/update 是场管理操作，不是协议核心。

### 决策 3：编码策略锁定（Phase 1-2 实验）

| 维度 | 决策 | 实验证据 |
|------|------|----------|
| 嵌入模型 | paraphrase-multilingual-mpnet-base-v2 (768d) | Phase 1: L4 从 1/5 → 3-4/5 |
| 编码方式 | Chunked Bundle（每个语义块独立编码后超位置叠加） | Phase 1: Hits 42→45/95 |
| 向量类型 | SimHash 10,000-dim binary | Phase 1: 几乎无损，存储 2.5x 效率 |
| 相似度 | Hamming similarity | 纯位运算，<100ns/comparison |
| 匹配管道 | Raw encode → nearest，零 LLM | Phase 2: raw 3/6 > LLM 最好 2/6 |

### 决策 4：多 Intent per Agent（Genome §2 推论）

一个 Agent（或用户）在场中不是一个向量，而是一群 Intent。每个有意义的文本碎片独立编码、独立存入。

理由：
- Phase 2 证明 bundle 8-13 个碎片后噪声淹没信号（D_raw_bundle 不如 A_raw）
- Genome 说 demand = profile = Intent，那一个人的 profile 有 N 个碎片 = N 个 Intent
- 匹配时按来源聚合，不压缩为单一向量

### 决策 5：Formulation 是协议外的 UX 功能（Genome §6 + Phase 2）

Formulation 帮用户把话说清楚，但不参与匹配管道。

- 匹配管道：raw text → encode → nearest（零 LLM）
- Formulation：可选的 UX 层，在 deposit 之前帮用户润色/展开意图
- Agent 侧：注册时 Profile 已经是 formulated 状态，不需要运行时 formulation

### 决策 6：协议止于可见性（Genome §7）

V2 Field 只负责 encode + field + match + visibility。

- offer（Agent 独立回应）→ 应用层
- synthesize（聚合为方案）→ 应用层
- approve（用户判断）→ 自然行为，不需要设计

某些应用需要 offer+synthesize（如 V1 的协商），某些只需要可见性（如搜索/推荐）。Field 不预设哪种。

### 决策 7：对外接口只接受 text

Field 的公开接口参数是 `text: str`，内部处理编码和投影。调用方不需要知道 mpnet、SimHash、chunked bundle。

## 影响范围

| 影响 | 说明 |
|------|------|
| 新模块 | `backend/towow/field/` — 全新 V2 实现，替换当前 V1 Field 代码 |
| V1 代码 | 不改动。保留在 `backend/towow/core/`, `skills/`, `api/` |
| 前端 | 未来需要新的 API endpoint 消费 V2 Field（当前无消费方） |
| 测试 | 新建 V2 测试套件。Phase 0-2 POC 代码在 `tests/field_poc/` 保留 |
| 文档 | 本 ADR + PLAN-011 + 接口设计 |

## 开放问题（来自 Genome §10，V2 不需要立即解决）

1. 场的结构：持久索引 vs 事件流？当前先实现内存持久索引
2. 聚合策略：多 Intent 匹配后按 Agent 聚合，用 max / top-k avg / weighted？需实验验证
3. 碎片切分：什么算"一个有意义的碎片"？当前由调用方决定粒度
4. 换手率度量：阴阳循环的度量方式，V2 初版不实现
5. 更大嵌入模型：bge-large-1024d 可能进一步提升 L4，待实验
