# ADR-006: 数据层与 WOWOK 链上对象模型集成

**日期**: 2026-02-12
**状态**: 讨论中
**关联**: ADR-001 (AgentRegistry), ADR-002 (MCP 入口), Design Log #002 (Echo & Execution)
**前置**: 架构文档 Section 11 (Execution & Echo)

---

## 背景

通爻当前所有数据都在内存中——V1 Engine 用 `dict`，App Store 用 `dict`，Auth 用 Redis/内存。没有持久化层。

架构文档 Section 11 已经确立了 WOWOK 作为执行基础设施的方向："不要模拟层，直接用 WOWOK"（Design Log #002）。WOWOK 提供链上持久化 + 执行追踪 + 支付 + 验证 + 仲裁。

现在需要回答：**通爻的数据模型应该怎么跟 WOWOK 对象模型对齐？**

### 三个前提共识

1. **MCP 面向用户**（ADR-002），链上交互直接用 WOWOK SDK
2. **数据结构从一开始就按 WOWOK 对象模型设计**（基础设施层）
3. **持久化后端可切换**（内存 / WOWOK 链上 / 其他）

---

## 核心分析

### WOWOK 在通爻四层架构中的定位

**结论：WOWOK 属于基础设施层，不是协议层。**

```
应用层 ─── Website, App Store, MCP (面向用户)
能力层 ─── Skills, LLM 客户端
基础设施层 ─── AgentRegistry, Encoder, EventPusher, 【WOWOK 持久化】
协议层 ─── 状态机, 事件语义, 递归规则（不可改）
```

依据原则 0.2（本质与实现分离）：
- **本质**：协商的语义（需求→共振→响应→综合→方案/合约）—— 协议层
- **实现**：合约存在哪（WOWOK 链上 / 内存 / PostgreSQL）—— 基础设施层

通爻的协议（8 态状态机、7 种事件、递归规则）不依赖 WOWOK。换一个链、换一个执行引擎，协议层不变。

---

### 通爻概念 → WOWOK 对象映射

#### WOWOK 9 大核心对象

| WOWOK 对象 | 本质 | 关键特征 |
|-----------|------|---------|
| Personal | 链上身份 | 所有操作的权限基础 |
| Machine | 工作流模板 | 发布后不可变，有向图 (nodes + edges) |
| Progress | Machine 的执行实例 | 可前进，生命周期追踪 |
| Service | 完整业务平台 | 产品+定价+Machine+Treasury+权限 |
| Demand | 悬赏需求 | bounty pool，单赢家模型 |
| Order | 交易记录 | Service 的购买凭证 |
| Guard | 验证逻辑 | 不可变条件检查（发布后永不改变） |
| Treasury | 团队钱包 | 多签、权重、流水控制 |
| Repository | 链上结构化存储 | 共享数据 |
| Permission | 权限管理 | 所有对象的 RBAC 基础 |
| Arbitration | 争议仲裁 | 加权投票 |

#### 映射决策

| 通爻概念 | WOWOK 对象 | 映射关系 | 理由 |
|----------|-----------|---------|------|
| Agent 身份 | Personal | 1:1 | 链上身份基础 |
| 需求表达 (Demand) | **不映射** | — | 通爻 Demand 是"信号"，WOWOK Demand 是"悬赏"，语义不同（见下方分析） |
| 协商过程 | **不映射** | — | 临时数据，投影即函数，协商是计算不是存储 |
| Plan（信息类输出） | **不映射** | — | 纯信息，不需要不可伪造性 |
| Contract（可执行输出） | Machine | Center 输出 → Machine 模板 | 协商产出从"信息"变为"承诺" |
| 执行实例 | Progress | Machine 的运行时 | 生命周期追踪 |
| Offer | **不映射** | — | 临时提案，协商结束即丢（见下方分析） |
| Service Agent 结晶 | Service | Offer 模式沉淀 → Service 发布 | 持久化的链上业务承诺 |
| Gap 缺口 | Demand | 缺口 → 悬赏填补 | 单赢家语义匹配（见下方分析） |
| 访问控制 | Permission | 所有对象的 RBAC | 基础设施 |
| 验证规则 | Guard | 不可变验证逻辑 | 代码保障 > Prompt 保障 |
| 共享数据 | Repository | 链上结构化存储 | 协作数据持久化 |
| 资金管理 | Treasury | 团队钱包 | 支付结算 |
| 争议解决 | Arbitration | 加权投票仲裁 | 链上公正性 |

---

### 三个关键映射的深度分析

#### 分析 1: Offer ≠ WOWOK Service

**Offer 的本质**：协商过程中 Agent 对 Demand 的一次性回应。存在于一次协商的上下文里，协商结束就没意义了。临时的、上下文相关的。

**WOWOK Service 的本质**：持久的业务平台——有产品、定价、Machine workflow、Treasury 支付。独立于任何特定需求而存在。

**粒度不同，生命周期不同。** 但它们之间有一条演化路径：

```
Agent 反复在类似需求上提交类似的 Offer
         ↓ 聚类结晶（架构文档 Section 8: 市场涌现）
Offer 模式沉淀为 Service Agent
         ↓ 用户主动发布
Service Agent → WOWOK Service（持久化、可购买、有承诺）
```

**决策**：
- **Offer → 不映射**。协议层临时数据，活在内存里。
- **Service Agent 结晶 → WOWOK Service**。有意识的"发布"动作，把沉淀的能力变成链上承诺。
- **Contract（Center 输出）→ WOWOK Machine**。协商最终产出从"信息"变成"可执行结构"。

#### 分析 2: 通爻 Demand ≠ WOWOK Demand

**WOWOK Demand**：悬赏模型。发一个需求，挂一笔钱，谁推荐的服务被采纳谁拿全部赏金。**单赢家、推荐驱动**。

**通爻 Demand**：信号模型。发出需求签名，网络中共振的 Agent 自主响应，Center 综合所有响应产出方案。**多参与者、协作驱动**。

语义本质不同。通爻的初始需求不应该映射到 WOWOK Demand。

**但 WOWOK Demand 有一个精确的位置——Gap Recursion。**

当 Center 发现方案有缺口，缺口变成子需求。如果网络中没有 Agent 能响应，缺口可以发布为 WOWOK Demand——"我们需要一个能做 X 的服务，有赏金"。此时 WOWOK Demand 的单赢家模型正好匹配：不需要多个服务来填同一个缺口，需要一个。

**决策**：
- **通爻 Demand（用户初始需求）→ 不映射到 WOWOK Demand**。协议层信号，活在内存里。
- **Gap Recursion 发现的缺口 → 可映射到 WOWOK Demand**。向外部网络悬赏填补。

#### 分析 3: 链上/链下边界

从信任模型出发：链上 = 不可伪造 + 不可篡改。

| 需要不可伪造 | 不需要不可伪造 |
|-------------|--------------|
| 承诺（谁答应做什么） | 探索（协商中的试探） |
| 执行（谁做了什么） | 推理（Center 的思考过程） |
| 支付（谁付了多少） | 共振（端侧检测的临时结果） |
| 回声（执行效果如何） | 丰富化（Formulation 中间产物） |

**边界：Contract Bridge 是分水岭。**

```
链下（通爻协议层 — 临时、可变、免费、快速）
│
│  需求表达 → Formulation → 确认
│  信号广播 → 共振检测
│  Offer 生成 → Barrier 等待 → 收集
│  Center 综合 → 工具调用 → 方案/合约
│  Gap 识别 → 子需求生成
│
╠══════════════════════════════════════
│          Contract Bridge
│     （方案从"信息"变为"承诺"的瞬间）
╠══════════════════════════════════════
│
│  链上（WOWOK — 持久、不可变、有成本、可信）
│
│  Machine 创建（合约模板）
│  Service 发布（Agent 的链上承诺）
│  Order 创建（参与方确认）
│  Progress 执行（workflow 推进）
│  Guard 验证（条件检查）
│  Treasury 结算（资金流动）
│  回声信号 ← 链上事件自动产生
```

这与 Design Log #002 一致："通爻负责发波，WOWOK 负责回波。"

---

## 决策：四层数据模型

### 第一层：协议模型（Protocol Models）

通爻自己的领域模型，不跟任何持久化绑定。临时的，活在一次协商的生命周期里。

```python
# 这些模型是协议层的，已存在于 backend/towow/core/models.py
class Demand: ...              # 用户的需求信号
class Offer: ...               # Agent 的一次性响应
class NegotiationSession: ...  # 协商过程状态
class Plan: ...                # 信息类输出（不上链）
class Contract: ...            # 可执行输出（会上链）
```

**不按 WOWOK 设计。** 协议层不被基础设施层污染。

### 第二层：链上模型（Chain Models）

1:1 映射 WOWOK 对象字段。用于 Contract Bridge 以下的所有数据。

```python
# 新增，严格按 WOWOK 对象模型设计
class WowokMachine: ...     # workflow 模板（from Contract）
class WowokService: ...     # Agent 链上承诺（from Service Agent 结晶）
class WowokProgress: ...    # 执行实例
class WowokOrder: ...       # 交易记录
class WowokDemand: ...      # 悬赏（from Gap Recursion）
class WowokPersonal: ...    # 链上身份
class WowokGuard: ...       # 验证逻辑
class WowokTreasury: ...    # 资金管理
class WowokRepository: ...  # 共享数据
```

### 第三层：持久化接口（Store Protocol）

可切换后端——开发用内存，生产用 WOWOK 链。

```python
class ChainStore(Protocol):
    """所有链上对象的持久化接口"""
    async def create_machine(self, machine: WowokMachine) -> str: ...
    async def get_machine(self, address: str) -> WowokMachine: ...
    async def create_progress(self, machine_addr: str, ...) -> str: ...
    async def progress_next(self, progress_addr: str, ...) -> None: ...
    # ... 其他对象的 CRUD
    async def subscribe_events(self, callback: Callable) -> None: ...  # 回声

class InMemoryChainStore(ChainStore):
    """开发/测试：内存 dict，模拟链上行为"""

class SuiChainStore(ChainStore):
    """生产：调 WOWOK Bridge Service，真实上链"""
```

### 第四层：Contract Bridge（转换器）

协议层输出 → 链上对象的映射逻辑。

```python
class ContractBridge:
    """协议层输出 → 链上对象"""
    def contract_to_machine(self, contract: Contract) -> WowokMachine: ...
    def service_agent_to_service(self, agent: ServiceAgent) -> WowokService: ...
    def gap_to_demand(self, gap: Gap) -> WowokDemand: ...
```

---

## TS SDK 桥接方案

WOWOK SDK 是 TypeScript（npm 包 `wowok`）。Python 后端需要调用它。

**方案：内部 HTTP 桥接服务**（独立于用户面 MCP）

```
Python FastAPI 后端
     │ HTTP (localhost)
     ▼
WOWOK Bridge Service (Node.js)
     │ import wowok from 'wowok'
     ▼
Sui RPC → devnet / testnet / mainnet
```

- Bridge API 表面很薄——把 `ChainStore` 每个方法映射为 HTTP endpoint
- Python 侧 `SuiChainStore` 就是个 HTTP client
- 这跟用户面 MCP（ADR-002）完全分开。MCP 面向 Claude Code/Cursor 用户，Bridge 是内部基础设施
- WOWOK 已有的 10 个 MCP Server（每个对象一个）可以作为参考，但 Bridge 不是 MCP

---

## 整体架构图

```
Python FastAPI 后端 (port 8080)
     │
     ├── 协商引擎（协议层 — 纯内存，不持久化）
     │      Protocol Models: Demand, Offer, Session, Plan, Contract
     │
     ├── Contract Bridge（转换层）
     │      Contract → WowokMachine
     │      ServiceAgent → WowokService
     │      Gap → WowokDemand
     │
     ├── Store Protocol（基础设施层 — 可切换）
     │      ├── InMemoryChainStore（开发/测试）
     │      └── SuiChainStore（生产）
     │              │ HTTP (localhost)
     │              ▼
     │     WOWOK Bridge Service (Node.js)
     │         ├── wowok npm SDK
     │         └── Sui RPC → devnet/testnet/mainnet
     │
     └── MCP Server（面向用户，ADR-002）
            └── 调用 Python 后端 API
```

---

## 核心原则

| 原则 | 在本决策中的体现 |
|------|----------------|
| 0.2 本质与实现分离 | 协议层模型不被 WOWOK 污染；WOWOK 属于基础设施层 |
| 0.5 代码保障 > Prompt | Guard 提供链上不可变验证逻辑 |
| 0.7 复杂性从简单规则生长 | 四层分离，每层规则简单 |
| 0.8 投影即操作 | Offer → Service Agent 结晶是投影沉淀的工程实现 |
| 0.12 投影不承诺，人承诺 | Contract Bridge 是"信息→承诺"的精确边界 |

---

## 影响范围

| 模块 | 影响 |
|------|------|
| `backend/towow/core/models.py` | 不变——协议层模型保持现状 |
| `backend/towow/infra/` | 新增 `chain_models.py`, `chain_store.py`, `contract_bridge.py` |
| `backend/server.py` | 启动时注入 `InMemoryChainStore` 或 `SuiChainStore` |
| 新增 `bridge/` 目录 | Node.js WOWOK Bridge Service |
| `docs/ARCHITECTURE_DESIGN.md` | Section 11 需更新以反映四层数据模型 |

---

## 待深入的子课题

1. **WowokMachine 的节点/边设计**：Center 输出的 Contract 怎么转成 Machine 的有向图（nodes + edges）？需要定义 workflow 模板的标准结构。
2. **Guard 条件设计**：通爻的哪些业务规则应该用 Guard 编码为链上不可变验证？
3. **Treasury 资金模型**：通爻的支付/激励机制怎么映射到 Treasury 的多签和流水控制？
4. **回声信号映射**：链上事件（OnNewOrder, OnNewProgress 等）怎么转换为通爻的 Echo 事件格式？
5. **Bridge Service 的 API 设计**：具体 endpoint 定义 + 错误处理 + 认证。
6. **InMemoryChainStore 的一致性保证**：内存实现需要模拟链上的哪些行为（不可变性、原子性）？

---

## 参考

- `docs/ARCHITECTURE_DESIGN.md` Section 11: Execution & Echo
- `docs/DESIGN_LOG_002_ECHO_AND_EXECUTION.md`: WOWOK 集成策略
- WOWOK 对象文档: `wowokWeb/docs/docs/object/`
- WOWOK SDK: npm 包 `wowok`
- WOWOK MCP Servers: 10 个，每个对象一个
