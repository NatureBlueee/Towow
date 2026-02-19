# WOWOK × 通爻：技术商业深度分析报告

> 调研日期：2026-02-18
> 背景：EXP-009 结晶协议收敛后需要对接执行层，评估 WOWOK 作为通爻执行层的可行性与关系定位

---

## 一、WOWOK 核心机制理解

### 1.1 本质定位

WOWOK（wowok.net，GitHub: wowok-ai）是运行在 **SUI 区块链**（Move 语言）上的一个 **可组合智能合约协议**。它的核心命题是：将协作从"人与人之间的承诺"变成"代码与代码之间的自执行逻辑"。

官方口号：*"A New Language of Collaboration"*

用一句话总结：**WOWOK 是一套链上的协作基础设施，把业务流程、资金托管、权限验证、争议仲裁全部链上化，通过 AI Agent（MCP）进行自然语言交互操作。**

---

### 1.2 技术架构：三层结构

**第一层：区块链层（SUI/Move）**

WOWOK 协议本身以 Move 语言的智能合约对象形式存在于 SUI 链上。SUI 的对象模型与 WOWOK 的设计高度契合——每个 WOWOK 对象（Demand、Service、Machine 等）都是链上的独立对象，有唯一 ID，可被独立拥有和引用。

重要发现：WOWOK session 配置中有 `"network": "sui testnet"` 和 `"wowok testnet"` 两种网络选项，暗示 WOWOK 可能在规划自己独立的链，当前仍以 SUI 为主。

**第二层：协议对象层（8 大可组合对象）**

| 对象 | 核心功能 | 角色定位 |
|------|----------|----------|
| **Demand** | 发布需求 + 悬赏池 + 收集推荐 | 需求方表达意图 |
| **Service** | 发布服务 + 不可变承诺条款 | 供给方定义能力 |
| **Machine** | 工作流模板（节点+转换+权限） | 协作流程蓝图 |
| **Progress** | Machine 的执行实例 | 单个任务的运行时 |
| **Guard** | 链上布尔条件（验证逻辑） | 智能门控条件 |
| **Repository** | 链上数据仓库（跨组织引用） | 共享知识库 |
| **Treasury** | 资金托管 + 可编程支付 | 价值结算 |
| **Permission** | 细粒度访问控制 | 角色权限管理 |
| **Arbitration** | 争议处理与仲裁 | 纠纷解决 |

**第三层：AI Agent 接入层（MCP）**

WOWOK 为每个对象都提供了独立的 MCP Server，AI Agent 通过自然语言与协议交互：

```
wowok_machine_mcp_server   # Machine + Progress 操作
wowok_demand_mcp_server    # 需求表达
wowok_service_mcp_server   # 服务发布
wowok_permission_mcp_server
wowok_guard_mcp_server
wowok_treasury_mcp_server
wowok_repository_mcp_server
wowok_personal_mcp_server
wowok_query_mcp_server
```

这意味着：任何接入 MCP 的 AI Agent（Claude、GPT-4o、Cursor、Trae、Kiro 等），都可以自然语言指令操作 WOWOK 链上对象，无需编写合约代码。

---

### 1.3 Machine 对象深度剖析

Machine 是 WOWOK 的核心差异化对象。

**Machine vs Progress 的关系（类比代码世界）：**
- Machine = 类定义（Class），不可变蓝图
- Progress = 实例（Instance），每个实际任务一个

**Machine 内部结构：**

```json
{
  "nodes": [
    {
      "name": "阶段名称",
      "pairs": [{
        "prior_node": "前驱节点（空字符串=起始节点）",
        "threshold": 2,
        "forwards": [{
          "name": "操作名称",
          "namedOperator": "角色模板名",
          "weight": 1,
          "guard": "条件验证对象"
        }]
      }]
    }
  ]
}
```

**namedOperator 的意义：** Machine 定义"需要一个 order_approver 角色"，但不指定谁。Progress 创建时，才将 `order_approver` 绑定到具体的链上地址（alice、bob 等）。这使得同一 Machine 模板可以被无限复用于不同的人员配置。

**Threshold+Weight 逻辑（加权投票）：**

| threshold | forwards weights | 业务含义 |
|-----------|-----------------|----------|
| 1 | [1] | 单人审批即可 |
| 2 | [1,1] | 双人共同审批 |
| 2 | [2] | 高权限单人审批 |
| 3 | [2,1,1] | 经理+任一普通人，或三个普通人 |
| 0 | any | 自动推进（无审批要求） |

**发布不可逆性：** `bPublished: true` 后工作流拓扑冻结，不可修改（只能克隆创建新版本）。这保障了合约的可信性——一旦发布，参与者无法修改规则。

---

### 1.4 Demand 对象：WOWOK 的"匹配层"

这是理解 WOWOK vs 通爻关系的关键对象。

Demand 的工作流：
1. 需求方发布 Demand（描述+悬赏池，默认 7 天有效）
2. 任何人可以向 Demand 推荐一个 Service 对象（附推荐理由）
3. 需求方浏览推荐，选择最佳
4. 悬赏池转给推荐者（不是服务提供者，是推荐者）

**关键洞察：**
WOWOK 的 Demand 是一个**推荐激励系统**，不是一个自动匹配系统。它依赖人工推荐（人或 AI Agent 手动 present service），而不是算法自动发现。Guard 可以设置推荐者的资质过滤条件，但不能自动发现最合适的 Service。

**这就是通爻的切入点。**

---

### 1.5 商业模式分析

**WOWOK 如何产生价值？**

1. **链上 gas 费**：每次合约操作需要 SUI gas 费。协议层本身不直接收费。
2. **协议原生 Token**：WOWOK npm 包关键词中有 `WOW` token，暗示存在协议级代币，但未找到公开的 token 经济学文档。
3. **生态工具商业化**：MCP Server、SDK、可能的企业服务。
4. **数据作为资产**：链上数据的所有权模型，Repository 对象支持跨组织共享，可能形成数据市场。

**当前生态现状（2026-02-18 数据）：**

- GitHub 最高 repo 仅 3 stars（examples），wowok_agent 只有 1 star
- GitHub followers: 11 人
- 官网显示 "2,915 businesses built this week"（待验证真实性）
- npm package `wowok` 版本 1.8.3，129 个版本，active 开发中
- 文档完整度高，MCP Server 生态完整（9 个独立 Server）
- 仍主要在 SUI testnet 运行，mainnet 状态未明确
- 社区极小，早期项目

**结论：WOWOK 是一个技术完整度较高但社区极早期的项目，处于 0→1 阶段。**

---

## 二、与通爻的关系矩阵

### 2.1 层次定位对比

```
┌──────────────────────────────────────────────────────┐
│                    用户意图层                          │
│         （人类知道自己要什么，但不知道找谁）              │
├──────────────────────────────────────────────────────┤
│              通爻：协议层（匹配+发现）                   │
│  模块一：意图场（谁应该在同一房间？）→ 向量匹配，零LLM    │
│  模块二：结晶（如何发现彼此价值？）→ 催化Agent+端侧对话   │
│  输出：协作构型（谁做什么/得什么/付出什么）              │
├──────────────────────────────────────────────────────┤
│              WOWOK：执行层（协议化+结算）                │
│  Machine：将协作构型变成链上工作流合约                   │
│  Progress：单个任务的链上执行实例                        │
│  Treasury：资金托管与自动支付                           │
│  Guard：条件验证与里程碑触发                            │
│  Arbitration：争议处理                                 │
├──────────────────────────────────────────────────────┤
│                    区块链层（SUI）                      │
│           （不可篡改性、共识、数字资产）                  │
└──────────────────────────────────────────────────────┘
```

---

### 2.2 互补维度分析

**互补点 1：通爻解决"找到谁"，WOWOK 解决"如何执行"**

通爻的结晶输出是自然语言协作构型：
- A 负责 X，B 负责 Y，C 负责 Z
- 三方互相验收，完成后按比例获得收益
- 时间线：6 周

这个协作构型本身没有任何执行保障。没有人能证明 A 真的做了 X，也没有人能保证收益真的按比例分配。

WOWOK Machine 精确填补这个空缺：
- 每个任务 = 一个 node
- 角色 = namedOperator（绑定到链上地址）
- 依赖关系 = pairs
- 验收标准 = threshold + weight + Guard
- 资金 = Treasury 锁定，条件满足自动释放

**通爻产出协作意图，WOWOK 执行协作承诺。** 这是真正的垂直互补，没有重叠。

**互补点 2：WOWOK 的 Demand 对象需要通爻的发现层**

WOWOK Demand 的最大痛点：依赖手动推荐（人或 Agent 手动 present service）。这是一个搜索范式——需求方等着被找到，或者推荐者手动推送。

通爻的意图场恰好解决这个问题：

```
WOWOK Demand（意图表达）→ 向量嵌入 → 通爻意图场
                                      ↓ 多视角匹配
WOWOK Service（能力发布）→ 向量嵌入 → 通爻意图场
                                      ↓ 发现共振/互补/对冲关系
                              通知相关方：你们可能需要彼此
```

通爻可以作为 WOWOK Demand 的"智能发现前端"，自动将相关 Service 推送给 Demand，而不需要人工手动推荐。

**互补点 3：WOWOK 链上执行数据可回流通爻意图场**

一次 WOWOK 协作完成后，链上会有：
- 哪些角色完成了哪些节点
- 验收结果（通过/失败/仲裁）
- 实际支付数据
- 时间线数据

这些数据是真实的协作结果，比 Profile 描述更可信。这些数据可以：
1. 更新参与者在通爻意图场中的向量表示（Profile 的实证版本）
2. 增加匹配置信度（有真实执行记录的 Agent 权重更高）
3. 形成跨时间的"协作历史"，让未来匹配更精准

这构成了一个数据飞轮：**通爻发现 → WOWOK 执行 → 执行数据回流通爻 → 更好的发现**。

---

### 2.3 竞争/替代维度分析

**WOWOK 有没有匹配层？**

直接结论：**没有。** WOWOK 的 Demand 对象是一个被动的"悬赏公告栏"，不是主动匹配引擎。

WOWOK Demand 的限制：
- 需求方发布 Demand，等待他人推荐 Service
- Guard 可以设置推荐者资质条件，但这是过滤（黑名单/白名单），不是发现（相似度搜索）
- 无向量嵌入、无语义搜索、无多视角查询、无自动聚合

WOWOK 的文档中没有任何关于"自动匹配"、"语义发现"、"相似度计算"的内容。它的 Repository 对象是链上数据存储，不是语义检索。

**WOWOK 是否可能自己做匹配层？**

理论上可以，但有几个结构性障碍：

1. **栈不同**：WOWOK 是链上协议，Move/SUI 合约做向量嵌入计算几乎不可能（计算密集，链上成本极高）。即使做 off-chain 的 AI 层，也需要重建通爻已有的整个技术栈。

2. **定位不同**：WOWOK 定位是"可组合协议层"，不是 AI 服务。他们的 AI 接入策略是让外部 AI（Claude、GPT 等）通过 MCP 操作协议，而不是自己训练/部署 AI 模型。

3. **竞争动机弱**：WOWOK 从匹配层获益是间接的（更多 Demand 被满足 → 更多链上交易 → 更多 gas 费）。匹配层做好了，通爻受益更直接。

4. **时间线问题**：WOWOK 当前只有 11 GitHub followers，专注在核心协议建设。做匹配层需要大量 ML 基础设施，超出当前能力边界。

**结论：WOWOK 与通爻竞争的概率极低，互补关系是主导。**

---

## 三、通爻→WOWOK 数据流设计

### 3.1 映射逻辑

结晶收敛后，通爻产出的协作构型需要转化为 WOWOK Machine JSON：

| 通爻概念 | WOWOK 对象 | 说明 |
|----------|------------|------|
| 协作构型（谁做什么） | Machine nodes | 每个任务/阶段一个 node |
| 参与者角色 | namedOperator | 角色名，Progress 时绑定地址 |
| 任务依赖关系 | pairs（prior_node） | 有向依赖图 |
| 验收标准 | threshold + weight | 加权投票逻辑 |
| 约束条件 | Guard | 链上布尔验证 |
| 收益分配 | Treasury | 条件触发的自动支付 |
| 争议处理 | Arbitration | 分歧解决机制 |

### 3.2 完整数据流

```
用户意图 → 通爻意图场（模块一）
              ↓ 多视角向量匹配
            发现相关 Agent 集合
              ↓ 按关系类型分层（共振/互补/对冲）
            选出参与者（top-K，~8人上限）
              ↓
            结晶循环（模块二）
              ↓ 催化 Agent × 端侧 Agent 多轮对话
            收敛 → 协作构型
              ↓
            方案生成 Agent
              ↓ prompt：自然语言方案 → WOWOK Machine JSON
            Machine JSON 输出
              ↓
            调用 wowok_machine_mcp_server
              ↓ 创建 Machine → 发布 → 创建 Progress → 绑定角色
            链上执行
              ↓ 任务完成 → Guard 验证 → Treasury 结算
            执行数据回流
              ↓
            更新参与者在通爻意图场中的向量权重
```

### 3.3 关键技术实现要点

**方案生成 Agent 的 prompt 设计要点：**

```
输入：结晶收敛后的自然语言协作构型
输出：WOWOK Machine JSON schema

映射规则：
- 每个"参与者做X"→ 一个 node，name = 任务名
- 时序依赖 → pairs 中的 prior_node
- 多人验收 → threshold > 1，多个 forwards
- 自动推进（无需审批）→ threshold: 0
- 角色名 = 通爻参与者标识符（如 participant_a_role）
```

这个映射是**确定性的**（给定协作构型，Machine JSON 是唯一的），不是创造性的。适合用 LLM 做 schema 转换，但需要严格的 JSON 格式验证。

**参与者地址绑定：**

Progress 创建时，namedOperator 绑定到实际链上地址。这要求通爻系统在结晶前就确认参与者的 SUI 钱包地址（或通过 wowok_personal_mcp_server 管理账户）。

---

## 四、战略建议

### 4.1 基本战略：主动互补，而非等待

通爻和 WOWOK 分处同一价值链的不同位置，没有直接竞争。但"自然互补"不会自动产生价值，需要主动设计接口。

建议的战略姿态：**把 WOWOK 作为通爻的默认执行层进行深度集成，不是作为可选插件。**

理由：
- 通爻的核心价值主张是"发现协作可能"，如果发现后没有执行机制，价值减半
- WOWOK 的 Machine + Treasury + Arbitration 组合提供了通爻目前缺少的完整执行闭环
- 在 WOWOK 生态极早期时接入，有机会影响其 API 设计，形成深度耦合而不是浅层适配

### 4.2 近期优先级（结晶 POC Phase 3）

当前 EXP-009 已完成 SIM-002，v1 催化 prompt 成功。下一阶段是把自然语言方案对接到 WOWOK Machine。

**建议路径：**

1. 在 SIM-003 中加入"方案生成"步骤：结晶收敛后，让方案生成 Agent 输出 WOWOK Machine JSON
2. 使用 `wowok_machine_mcp_server` 在 SUI testnet 实际部署 Machine
3. 验证整个流程：通爻发现 → 结晶收敛 → Machine 部署 → Progress 创建 → 模拟执行

这是一个完整的端到端 POC，比单独的催化实验更有说服力，对投资人和外部合作方都是更强的信号。

### 4.3 中期战略：通爻作为 WOWOK 的"发现层前端"

**可以明确提的商业定位：**

> "通爻是 WOWOK 的 AI 发现层。WOWOK 解决'如何执行'，通爻解决'找到谁'和'发现价值'。两者共同构成从意图到结算的完整 AI Agent 协作栈。"

具体表现：
- WOWOK Demand 对象可以被通爻意图场索引（Demand 描述 → 向量嵌入 → 场中的意图节点）
- WOWOK Service 对象可以成为通爻 Agent 的 Profile（Service 能力描述 → 向量表示）
- 通爻的匹配结果可以自动向相关 Service 发送推荐（填补 WOWOK Demand 的手动推荐瓶颈）

这对 WOWOK 有直接价值：他们的 Demand 悬赏利用率会显著提升。

### 4.4 风险评估

**风险 1：WOWOK 项目夭折（高概率需要关注）**

当前 WOWOK 社区极小（11 followers，3 stars）。如果项目未能获得足够资金和用户，集成工作会浪费。

缓解方案：集成设计采用"协议层抽象"——通爻的输出是通用的协作构型 JSON，WOWOK Machine 是其中一个目标格式。如果 WOWOK 不成，同样的协作构型可以对接其他执行层（如 Gnosis Safe multisig、Syndicate 协议、甚至简单的 PDF 合同）。

**风险 2：SUI 区块链的生态不确定性**

WOWOK 深度绑定 SUI。SUI 目前是主流 Layer 1 之一（TVL 已进前 10），但如果 WOWOK 规划自己的链（session 中出现 "wowok mainnet/testnet"），可能存在迁移风险。

**风险 3：WOWOK 进入匹配层（低概率）**

如果 WOWOK 获得大额融资并决定自己做 AI 匹配层，会与通爻形成竞争。但基于当前的技术栈差异和定位差异，这种情况在 18 个月内发生的概率极低。

---

## 五、需要进一步确认的关键问题

**关于 WOWOK 自身：**

1. **WOW Token 经济学**：WOWOK 是否有原生代币？token 分配方案？这决定其商业模式是否可持续。目前在官方文档中没有找到 token 经济学说明，可能是早期故意不公开。

2. **WOWOK 主网状态**：`"wowok mainnet/testnet"` 的出现暗示他们可能在规划自己的链。这是否意味着未来会从 SUI 迁移？时间线是什么？

3. **"2,915 businesses built this week"**：官网主页这个数字是否是真实链上交易数据？还是营销数字？需要通过链上数据验证。

4. **团队背景**：wowok-ai GitHub 有 2 contributors，11 followers。这是几人团队？有没有公开融资记录？

**关于通爻×WOWOK 接口：**

5. **namedOperator 地址绑定的时机**：结晶参与者需要在绑定 Progress 时提供 SUI 钱包地址。这个在通爻的用户旅程中应该在哪个阶段收集？（建议：SecondMe Profile 中包含 SUI 地址字段）

6. **WOWOK 是否支持 off-chain 预言机（Oracle）**：结晶的某些验收条件可能涉及链下数据（如"代码提交记录"、"用户增长数据"），WOWOK Guard 能否引用 off-chain 数据？

7. **WOWOK 方是否有合作意向**：在联系 WOWOK 团队之前，先完成 SIM-003（包含 Machine 部署）作为技术验证，然后用这个 POC 去接触 WOWOK 团队，探讨正式集成合作。

---

## 六、总结

WOWOK 与通爻的关系是**极度互补、几乎无竞争**的。

用一个类比表达：

> 通爻像是 LinkedIn 的 AI 增强版（找到谁）加上咨询公司的智能化（理解价值），WOWOK 像是 DocuSign 加 Stripe 的链上原生版（执行承诺+自动结算）。两者加起来才是完整的"AI Agent 经济协作栈"——从意图到价值发现，到协议化承诺，到链上结算。

从通爻的角度，**最高优先级行动是在 SIM-003 中完成一个完整的端到端 POC**：通爻结晶收敛 → 方案生成 → WOWOK Machine 部署。这既是技术验证，也是对外展示的最强论文素材，同时是开启 WOWOK 正式合作谈判的最好名片。

---

## 附：相关文件

- `docs/research/005-wowok-machine-reference.md` — 已有的 WOWOK Machine 格式参考（完整 JSON schema 和映射模板）
- `docs/design-logs/DESIGN_LOG_006_CRYSTALLIZATION_PROTOCOL.md` — 通爻模块二完整设计文档
- `docs/decisions/ADR-014-module2-crystallization-implementation.md` — 模块二实现决策（包含 WOWOK 对接决策）
