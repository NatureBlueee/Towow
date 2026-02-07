# Design Log #002: 回声、执行阶段与 WOWOK 集成（修订版）

> 讨论日期：2026-02-07
> 参与者：架构师 + 创始人
> 状态：✅ 已写入架构文档 Section 11
> 修订日期：2026-02-07（纠正理解错误，补充关键决策）
> 前置阅读：`docs/articles/03_回声.md`

**修订说明**：
- 初版基于对 WOWOK 的初步研究，存在理解错误
- 经过深入阅读 WOWOK 文档和讨论，纠正了关键概念
- 补充了 Machine Template、Service 创建、Progress 绑定、支付问题等关键决策

---

## 核心发现：系统只有半边

当前架构文档（1539行）描述了一个精美的前向系统：

```
需求 → 签名 → 广播 → 共振 → Offer → 方案
```

这是波的前半程。波出去了，不回来。

物理学中不存在"没有回声的波"。没有回声的系统不是场——是管道。管道只能传递，场才能让波反复折叠、干涉、涌现新结构。

**架构缺失的是第四步**：方案交付之后的执行、确认、反馈——回声。

---

## 关键纠偏：LLM 不能当回声

### 最初的错误方向

最初的提案是用 Center Agent 的"Offer 采纳判断"作为主要反馈信号——哪些 Offer 被选进方案，哪些没有，以此为 Agent 画像提供选择压力。

### 创始人的纠正

**"这太依赖大模型了。大模型是做不到的，它必须要跟真实世界产生真实的交互才对。"**

为什么 Center 判断不能做回声：

| 问题 | 说明 |
|------|------|
| **幻觉循环** | LLM 判断 LLM 的输出 = LLM 自我评估，继承所有偏见，没有外部校正 |
| **无锚定** | 不像抖音有"用户看了 3 秒还是 30 秒"这样的硬信号，Center 的"采纳"只是另一层 LLM 推理 |
| **颗粒度错误** | "被采纳"vs"未被采纳"是二值的，丢失了真实世界中无穷多的行为信号 |
| **系统仍然失明** | 方案交付后，系统不知道执行了没有、效果如何、用户是否满意 |

**核心认知：回声必须来自真实世界中人的真实行为——不是 LLM 的判断。**

### 抖音的启示

抖音的推荐系统只需要一个信号：**用户在这个视频上停留了多久**。不需要用户打分、点评、分类。一个来自真实行为的简单信号，比一千个来自模型判断的复杂信号都有用。

通爻需要找到自己的"停留时长"——一个来自真实世界、无需用户刻意提供、但准确反映价值的行为信号。

---

## 关键认知：方案不是终点，是起点

### Plan vs Contract

| | Plan（当前） | Contract（新） |
|--|-------------|---------------|
| 本质 | 被动文本（"建议你这么做"） | 可执行的协作流程（"到时候这么执行"） |
| 交付后 | 系统失明——不知道用户看了没、做了没 | 系统有眼——每一步执行都产生链上事件 |
| 反馈 | 无 | 每个真实行为（确认、交付、支付）都是回声信号 |
| 参与方 | 被动接收者 | 主动签署者——接受 = 真实的承诺行为 |

**Center 的输出应该从 `plan`（文本方案）变成 `contract`（可执行协作结构）。**

但这不是一个简单的格式变化——它需要一个**执行阶段**的基础设施。

---

## WOWOK：执行阶段的基础设施

### 什么是 WOWOK

WOWOK（Walk Work / WOW）是一个 AI 驱动的 Web3 协作协议，运行在 Sui 区块链上。它提供 9 个可组合的链上对象，覆盖了协作执行的全生命周期。

### 9 个核心对象（纠正：初版错误写为 8 个）

| WOWOK 对象 | 功能 | 对应通爻的什么 |
|------------|------|--------------|
| **Personal** | 链上个人/Agent 身份和画像 | Agent 身份（V1b+ 替代 UUID，走向 DID） |
| **Demand** | 链上需求表达，带条件激励 | demand.broadcast 的链上存证 |
| **Service** | 服务发布，带不可变承诺（购买后不可随意修改） | Agent/Offer 的链上表达 |
| **Machine** | workflow 模板定义（**本质**） | **协作合约——Center 输出的执行载体** |
| **Progress** | workflow 执行实例（**实现**） | Machine 的具体执行，绑定 operators 和数据 |
| **Service** | 服务/产品门户（**本质**） | Agent/Offer 的链上表达 |
| **Order** | 交易实例（**实现**） | Service 购买产生的具体订单 |
| **Guard** | 验证引擎（**定义条件，不是签名本身**） | Forward 操作中的验证逻辑 |
| **Treasury** | 多方支付/托管，可编程分配 | 经济激励 / 支付结算 |
| **Repository** | 跨组织数据注册表 | 交付物存储 / 声誉数据 |
| **Permission** | 基于角色的权限管理 | 信任模型 |
| **Arbitration** | 争议仲裁（买方投诉触发 `OnNewArb`） | 异常处理 |

**关键纠正（2026-02-07）**：
- **Machine/Progress 关系**：Machine = 模板（本质），Progress = 执行实例（实现）。类比：Machine = "外卖服务规则"，Progress = "这一单外卖"
- **Service/Order 关系**：Service = 业务平台（本质），Order = 交易实例（实现）。类比：Service = "花店"，Order = "这束玫瑰的订单"
- **Guard 不是签名**：Guard 是验证器（定义条件），签名在 Forward 操作里（operator 执行 progress_next）
- **Progress 可选绑定 Order**：通过 `Progress.task_address = Order` 关联，但不是强制的

### 关键映射：Machine + Progress + Forward = 回声的载体

**Machine**：Center 生成的方案不再是纯文本——它变成一个 Machine workflow 定义（JSON 格式）：
- 定义节点（nodes）、前进条件（forwards）、权限（permissions）
- 可以包含 Guard 验证（在 forward 中配置）
- Machine 生命周期：创建（可改）→ 发布（不可改）→ Service 使用

**Progress**：Machine 的执行实例：
- 绑定具体的 operators（谁执行每个角色）
- 可选绑定 task_address（关联 Order 或其他对象）
- 状态推进通过 `progress_next` 操作（执行 forward）

**Forward 操作**：真实的回声信号来源：
- Operator 执行 `progress_next` → 链上交易（带标准签名）
- 可以携带数据：`deliverable.msg`（文本/链接）、`deliverable.orders`（外部引用）
- 如果配置了 Guard → 验证通过后才能推进
- 触发链上事件：`OnNewProgress`

**回声信号的真实来源**：
- **Forward 操作本身**：operator 推进 workflow = 真实的行为信号
- **链上事件**：OnNewOrder（购买）、OnNewProgress（推进）、OnPresentService（推荐）、OnNewArb（仲裁）
- **Deliverable 数据**：Forward 携带的消息、评价、外部引用
- **Treasury 转账**：真实的资金流动
- **Progress 状态**：节点迁移、完成度

**每一个 Forward 操作都是一个回声脉冲**（不是"Guard 签名"）

---

## 完整的波：发波 + 回波

### 架构全景

```
【发波 — 通爻协议层】                    【回波 — 执行层（WOWOK）】

用户表达意图
    ↓
DemandFormulation
    ↓
HDC 签名编码 → 广播
    ↓
端侧共振检测
    ↓
OfferGeneration
    ↓
等待屏障 → CenterCoordinator
    ↓
方案生成 ──────────────────→ Contract 创建（Machine）
                                ↓
                           参与方确认（Guard）────→ 回声信号 ①
                                ↓
                           任务执行 + 交付（Repository）
                                ↓
                           验收确认（Guard）────→ 回声信号 ②
                                ↓
                           结算（Treasury）────→ 回声信号 ③
                                ↓
                           ←──────────────── 回声汇聚
    ↓
画像演化（Random Indexing + 选择压力）
    ↓
共振阈值自适应
    ↓
Service Agent 结晶（质量信号）
```

### 回声信号的分层（修订版）

| 层次 | 信号 | 来源 | 强度 | 成本 |
|------|------|------|------|------|
| L0 | 参与方是否接受合约 | Service 购买 → OnNewOrder 事件 | 中高 | 零（链上事件） |
| L1 | 任务是否按时交付 | Progress Forward 操作 | 中高 | 零 |
| L2 | 交付内容和质量 | Forward.deliverable.msg（文本/评价） | 高 | 零 |
| L3 | 是否完成支付/结算 | Treasury 转账事件 | 最高 | 零 |
| L4 | 用户是否产生后续需求 | 新的 demand.broadcast | 启发性 | 零 |

**所有回声信号的共同特征**：
- 来自真实的人的真实行为（不是 LLM 判断）
- 自然发生在协作流程中（用户不需要额外操作去"打分"）
- 链上不可篡改（信号质量有保障）
- 采集成本为零（链上事件自动可读）
- **全息数据**：Forward 本身就携带丰富的协作数据，不只是"事件类型"

**关键洞察**：Forward 操作是全息的协作数据，不是简单的"状态迁移"。每个 Forward 可以包含：
- 文本消息（deliverable.msg）
- 外部引用（deliverable.orders）
- 执行者信息（operator）
- 时间戳
- Guard 验证结果（如果有）
- 权重（weight）

这就是通爻的"停留时长"——不需要用户额外做任何事，协作执行的自然流程本身就在产生回声。

---

## 回声如何回流到系统

### 画像演化：从随机漂移到有向进化

**当前**（无回声）：
```
Agent 参与协商 → 协商超向量 → Random Indexing → 融入画像
```
问题：只要"参与了"就会融入，不区分有效参与和无效参与 = 随机漂移。

**有回声后**：
```
Agent 参与协商 → 协商超向量
    ↓
回声信号到达（合约执行结果）
    ↓
加权融入：
    - 合约被接受 + 执行完成 + 验收通过 → 高权重融入（正选择）
    - 合约被接受但执行失败 → 中等权重，但向量方向标记为"风险"
    - Offer 未被纳入合约 → 低权重融入（弱信号，不是负信号）
    - Offer 被纳入但参与方拒绝签约 → 负向微调（方案不切实际？）
    ↓
画像不再随机漂移，而是被"什么是真正有用的"引导着进化
```

### 共振阈值自适应

回声信号还能校准系统的共振灵敏度：

```
统计：某类共振模式 → 产出的 Offer → 进入方案 → 合约执行结果

如果某类共振总是产出好结果 → 阈值合理，保持
如果某类共振总是产出被忽略的 Offer → 阈值可能太松，收紧
如果某个领域的共振很少但命中率极高 → 可以适当放宽

不需要人工调参——回声的模式自然涌现出调参方向
```

### Service Agent 结晶的选择压力

回声信号解决了 Service Agent 结晶的质量问题：

```
无回声：高频参与 → 结晶。但高频 ≠ 高质量。
有回声：高频参与 + 回声正面 → 结晶。有了选择压力。
```

结晶条件从"参与了很多次"升级为"有效参与了很多次"。

---

## 场景作为最小完整循环

### 为什么场景是关键

全管道的反馈循环（需求 → 协商 → 合约 → 执行 → 结算 → 回声）在开放网络中很难一步到位。但在**场景**中，循环天然存在：

```
以"黑客松找搭子"为例：

① 用户发需求："找一个 AI 方向的技术合伙人"
② 协商 → 方案生成
③ 方案转化为合约："Alex 和小明组队，第一周出原型"
④ 黑客松期间 → 真实协作发生
⑤ 评审/展示 → 验收信号（是否有成果产出）
⑥ 回声回流 → 参与者画像进化

整个循环在 2-3 天内完成。
```

场景提供了：
- **有界的时间跨度**：循环可以快速完成
- **明确的成功标准**：黑客松有评审，创业社区有里程碑
- **自然的反馈机制**：参与者本来就会有后续行为
- **低摩擦的合约**：场景规则本身就是合约的一部分

**V1 路径：先在场景中验证完整循环，再推广到开放网络。**

---

## 协议层事件扩展

### 新增的执行阶段事件（修订版）

在现有的 6 个协议事件之后，新增执行阶段事件：

| 事件 | 语义 | WOWOK 对应 |
|------|------|-----------|
| `contract.create` | Center 方案转化为可执行合约 | Machine 创建（bPublished=false） |
| `contract.publish` | Machine 发布（不可修改） | Machine.publish (bPublished=true) |
| `contract.accept` | 参与方购买 Service/接受合约 | Service 购买 → Order 创建 → OnNewOrder |
| `task.progress` | workflow 推进到新节点 | Progress.next (Forward 操作) → OnNewProgress |
| `task.deliver` | 参与方提交交付物 | Forward.deliverable + Repository（可选） |
| `contract.complete` | Progress 执行到终点 | Progress 状态 = completed |
| `contract.settle` | 经济结算（如有） | Treasury 转账/结算 |

**纠正**：不存在 `Guard.sign` 操作。Guard 是验证器，不是签名。真实的签名在 Forward 操作（progress_next）中，由 operator 执行。

### 回声事件

| 事件 | 语义 | 触发 |
|------|------|------|
| `echo.pulse` | 单个回声脉冲到达 | 每个执行阶段事件自动生成 |
| `echo.digest` | 回声汇聚为画像更新 | 合约完成时批量处理 |

### Center 输出类型扩展

Center 的决策输出从 4 种变为 5 种：

| 类型 | 含义 | 后续 |
|------|------|------|
| `plan` | 方案已形成（文本，无执行追踪） | 适用于信息类/建议类需求 |
| `contract` | **方案已形成，且可转化为执行合约** | 创建 Machine 工作流 |
| `need_more_info` | 需要追问 | 不变 |
| `trigger_p2p` | 需要发现性对话 | 不变 |
| `has_gap` | 存在资源缺口 | 不变 |

`plan` 和 `contract` 的区别：不是所有方案都需要执行追踪。"推荐你看这本书"是 plan，"三个人组队做项目"是 contract。Center 判断用哪种输出。

---

## V1 实现路径（修订版 2026-02-07）

### 策略变更：不要模拟层，直接用 WOWOK

**初版方案**（V1a PostgreSQL 模拟 → V1b 链上）存在问题：
- 重复造轮子（两套实现）
- WOWOK MCP servers 可以本地运行（TS 代码，可调试）
- 模拟层会偏离真实链上行为

**修订后的 V1 策略**：

```
通爻网络
     ↓
WOWOK MCP (本地)
     ↓
Sui 本地测试网/开发网
```

**好处**：
- 只写一套集成代码
- V1 → V1b 只是切换网络（devnet → testnet → mainnet）
- 不需要模拟层，避免行为差异

### 保留轻量级抽象（EchoSource）

```python
class EchoSource:
    """回声信号源的抽象接口"""
    def subscribe(self, callback): ...

class WOWOKEchoSource(EchoSource):
    """真实实现：监听链上事件"""
    def __init__(self, mcp_client): ...
    def subscribe(self, callback):
        # 监听 OnNewOrder, OnNewProgress 等

class MockEchoSource(EchoSource):
    """测试实现：用于单元测试"""
    def subscribe(self, callback):
        # 生成模拟事件用于测试 Profile 更新逻辑
```

**关键**：不是模拟整个 WOWOK，只是抽象"回声信号源"这一层。这样可以在不上链的情况下测试 Profile 更新算法。

### V1 → V1b → V2 路线图

**V1**（开发阶段）：
- WOWOK MCP 连接本地测试网/devnet
- 使用"信用额度"（不涉及真实支付）
- 回声信号 = 链上事件（OnNewOrder, OnNewProgress 等）
- 目标：证明核心机制可以跑通

**V1b**（公测阶段）：
- 切换到 Sui testnet 或 mainnet
- 只需改配置，代码不变
- 开始引入真实支付（或继续用信用系统）

**V2**（优化阶段）：
- 完整的投影架构（多维度、动态权重）
- 性能优化（HDC 并行化、缓存策略）
- 更丰富的回声信号处理

### 支付问题的务实处理

**识别为复杂的多维度问题**（法律、商业、用户心理、运维）：

**V1 策略**：
- 使用"信用额度"或"模拟货币"
- 回声信号 = 信用消耗（链上记录，不可伪造）
- 不涉及真实货币，避开法律和用户心理问题

**未来探索**：
- 链下支付（支付宝/微信）+ 链上凭证
- 积分/信誉系统 + 周期性结算
- 支付宝/微信 MCP 集成（状态待确认）

**关键**：支付不是 V1 的阻塞问题。回声信号不一定要是"钱的流动"，可以是"信用的消耗"或"承诺的兑现"。

---

## 投影视角的验证

回到设计原则 0.8：投影是基本操作。执行阶段是否也是投影？

| 丰富的东西 | 透镜 | 聚焦的结果 |
|-----------|------|-----------|
| 方案（多方资源组合） | 合约化 | 可执行的 Machine 工作流 |
| 真实的协作过程 | 链上记录 | 回声信号序列 |
| 多次回声 | 加权融入 | 画像的有向进化 |

✅ 执行阶段仍然是投影操作的分形应用。系统自洽。

---

## 完备性的升级

回到设计原则 0.9：完备性 ≠ 完全性。

回声机制进一步强化了这个原则。Agent 的画像不是"存了所有历史"——它是通过与真实世界的**持续连接**（执行结果回流）来保持"活的"。画像的质量不在于数据量，而在于**回声通道的通畅性**。

这也是为什么场景很重要——场景提供了回声通道。没有场景的 Agent，画像只能靠注册信息维持（静态）。有场景的 Agent，画像被持续的回声塑造（动态）。

窗户（实时连通）vs 照片（过时数据），在这里得到了工程实现。

---

## 与现有 WOWOK 生态的关系

### WOWOK 已有的工程

- **10 个 MCP Server**：Demand / Service / Machine / Guard / Treasury / Repository / Permission / Arbitration / Personal / Query
- **wowok npm 包**：Sui 链交互的 TypeScript SDK
- **AMCP（Agent Multi-party Coordination Protocol）**：多 Agent 协调引擎（orchestrator, debate, phase-controller 等）
- **wowok_agent**：Agent 级别的链上交互

### 集成方式

```
通爻协议层（发波）          WOWOK 协议层（回波）
     │                         │
     │    Contract Bridge       │
     └────────┬────────────────┘
              │
    ┌─────────┴─────────┐
    │  合约转换层        │
    │  Plan → Machine    │
    │  Party → Service   │
    │  Check → Guard     │
    │  Pay → Treasury    │
    └───────────────────┘
              │
    ┌─────────┴─────────┐
    │  回声监听层        │
    │  Chain Events →    │
    │  Echo Signals →    │
    │  Profile Update    │
    └───────────────────┘
```

### AMCP 的重新定位

WOWOK 已有的 AMCP（Agent Multi-party Coordination Protocol）做的事情跟通爻的协商阶段有重叠。但角度不同：

- **AMCP**：偏向链上协作的工作流编排（debate、satisfaction judge、subnetwork）
- **通爻协商**：偏向信号发现和方案涌现（HDC 共振、Center 聚合、发现性对话）

两者不是竞争关系，而是互补：
- 通爻负责"谁跟谁应该在一起"（发现）
- WOWOK/AMCP 负责"在一起之后怎么做"（执行）

长期可能融合，V1 先清晰分工。

---

## WOWOK 链上事件 → 回声信号的直接映射

WOWOK 已经定义了 4 类链上事件，每一类都是天然的回声信号：

| 链上事件 | 含义 | 回声信号映射 |
|---------|------|------------|
| `OnNewOrder` | Service 生成新订单（= 参与方接受合约） | **echo.accept** — 最强的"方案被认可"信号 |
| `OnNewProgress` | Machine 生成新进展（= 里程碑完成） | **echo.progress** — 执行过程中的持续信号 |
| `OnPresentService` | 推荐者完成 Service 推荐给 Demand | **echo.match** — 发现/推荐层面的信号 |
| `OnNewArb` | 买方发起争议仲裁 | **echo.dispute** — 负面信号，但极有价值 |

这些事件在链上自动触发，**不需要额外开发回声采集系统**——WOWOK 已经把回声管道造好了。

### CipherStamp：安全通信层

WOWOK 还有一个端到端加密消息系统 CipherStamp：
- Signal Protocol 加密
- OpenTimestamps 时间戳证明
- 可能用于 Agent 之间的私密通信（SubNegotiation 场景）

这为未来的端侧 Agent 直接对话（Section 5 的"未来方案"）提供了安全基础设施。

---

## 补充关键决策（2026-02-07 深度讨论后）

### Machine Template 策略

**不预设 Template 库**，建立沉淀机制：
- **V1 启动**：Guidelines（本质）+ MCP 实时获取 WOWOK 实现 → LLM 生成 Machine JSON
- **运行积累**：成功执行的 Machine 自动沉淀到 Template 池
- **后续复用**：类似需求优先检索已有成功案例，微调复用
- **克隆机制**：Machine 本质是 JSON 文件，可以克隆修改

**Machine 生命周期**：
1. 创建（上链，bPublished=false，可修改）
2. 参与方确认、测试
3. 发布（bPublished=true，不可修改）
4. 创建 Service（使用已发布的 Machine）

**原因**：灵活性 + 自动同步 + 符合本质/实现分离 + Template 是涌现的结果

### Service 创建时机

**WOWOK Service** vs **通爻 Service Agent**：
- WOWOK Service = 链上的单次业务合约
- 通爻 Service Agent = 长期角色，从 Edge Agent 分化

**Service 创建流程**：
1. 协商 → Center 生成 plan + Machine JSON
2. 确认 → 参与方确认（Machine 上链但未发布）
3. 发布 → Machine.publish()
4. 创建 → WOWOK Service（使用已发布的 Machine）
5. 执行 → 参与方购买 Service → Order → Progress

**关键**：上链 ≠ 承诺，发布 = 承诺。提供了"确认缓冲期"。

### Progress 绑定策略

**Progress.task_address** 是可选的外部关联（一旦设置不可解绑）。

**不预设绑定规则**，而是描述本质，让 LLM 根据场景判断：
- 什么：Progress 与外部对象的可选关联
- 效果：外部系统可查询 Progress 状态，构建依赖图
- 考虑：是否需要持久关联？是否需要追溯？

**可能的选择**：
- 绑定 Order：Service 购买场景
- 绑定上游 task：供应链管理
- 不绑定：纯 workflow 执行

**原因**：符合"智能在 LLM，约束在代码"原则。

### 回声信号的统一架构

**核心思想**：所有协作事件都是信号源，不预设重要性。

**处理流程**：
```
链上事件（全息）
     ↓
多维投影（temporal, relational, semantic, structural, economic）
     ↓
HDC 编码
     ↓
场广播
     ↓
端侧共振 → Agent Profile 更新
```

**关键**：不要预设"哪些是回声信号"，让重要性从共振强度中涌现。

### 反脆弱设计

**策略**：
- 可观测性：记录关键指标
- 可回退性：保留简单方案作为 baseline
- 数据沉淀：即使功能失败，数据也有价值
- 渐进式引入：不一次性切换

**例子**：
- HDC 不如预期 → 回退到标签匹配，但保留协作数据
- 阈值设置不当 → 数据显示哪些不行，缩小搜索空间

## 待回答的问题（更新）

1. ✅ **合约的"软"程度** → 已解决：plan 和 contract 两种输出
2. ⬜ **Sui 链的数据成本** → 需要实测
3. ✅ **AMCP 状态** → 已确认：AMCP 已废弃，不用管
4. ⬜ **回声延迟** → 需要设计异步更新机制
5. ⬜ **合约违约** → 需要结合 Arbitration 对象设计

## 需要深入研究的子课题

以下标识为需要单独深入的子课题（不在此文档展开）：
1. HDC 编码策略（不同数据类型如何编码）
2. 投影维度设计（哪些维度必要，如何平衡权重）
3. 共振阈值策略（如何设定、动态调整）
4. Profile 更新算法（Random Indexing 参数、避免漂移）
5. 工程实现与性能（场广播机制、HDC 计算优化）

---

*写于发现我们需要造另一半世界的那个夜晚。*
*修订于纠正理解、深化决策的那个下午。*
