# 通爻网络 ToWow Network —— 作品说明文档

---

## 一、业务价值说明

### 1.1 问题：A2A 生态的结构性空白

A2A 生态已经解决了两个层次的问题：

- **数据层**：Agent 怎么像你——SecondMe、Claude Memory、GPT Memory
- **传输层**：Agent 怎么通信——Google A2A Protocol、MCP

但有一个层次始终空白：**协商层——多个 Agent 之间怎么发现彼此、怎么协商、怎么形成协作。**

当前所有 A2A 应用（AI 招聘、AI 相亲、AI 组队）本质上仍在沿用搜索范式：定义条件 → 查询匹配 → 返回排序列表。这和人类在招聘网站上筛简历没有本质区别——只是快了一点。

搜索范式有一个结构性盲区：**它只能找到你已经知道自己需要的东西。** 你搜"前端开发"，不会搜到一个纪录片导演——但这个人的认知科学背景可能恰好是你 AI 教育项目最需要的互补能力。真正有价值的协作，往往来自你不知道自己需要的人。

### 1.2 通爻做什么：从搜索到响应的范式转移

通爻是 Agent 之间的协商协议。它做的不是"更好的搜索"，而是一个完全不同的范式：

| | 搜索范式（现有方案） | 响应范式（通爻） |
|---|---|---|
| 发起方 | 用户主动搜索、定义条件 | 用户发出一句自然语言意图 |
| 匹配方式 | 标签/关键词/embedding 排序 | 全网 Agent 自主判断相关性（端侧共振检测） |
| 匹配范围 | 你已知的候选空间 | 包含你未知的——共振能发现跨域互补 |
| 协调能力 | 无（用户自己选、自己组） | Center Agent 综合多方响应、发现互补、识别缺口、递归填补 |
| 输出 | 排序列表 | 结构化协作方案（参与者 + 任务拓扑 + 依赖关系） |
| 复杂度 | O(N×M) 全量匹配 | O(N+M) 信号广播 + 端侧检测 |

用户说一句话（"帮我组一个 AI 教育团队"），全网 Agent 自动响应、自动协商、自动组合出最优方案。**一句话，从意图到协作方案。**

### 1.3 业务价值

**对用户：** 从"我去找人"变成"人来找我"。不需要定义精确的搜索条件，不需要筛选结果，不需要自己判断谁和谁互补。说出意图，方案涌现。

**对开发者：** 多 Agent 协调是 A2A 应用中最复杂的部分——状态管理、偏见消除、并发控制、递归协商。通爻将这些封装为可独立部署的引擎，开发者只需关注业务场景定义，协商逻辑由协议层统一处理。

**对生态：** Agent 生态必然走向碎片化——SecondMe、OpenClaw、Claude、GPT 等多平台并存。碎片化的世界需要一个中立的协商协议把所有 Agent 连起来。SecondMe 做的协商层 OpenClaw 不会接入，反过来也一样。只有不属于任何平台的第三方能做中立协议。通爻做的就是这个结构性位置——**Agent 宇宙的协商协议层**。

### 1.4 适用场景

通爻的协商引擎是通用的，上层场景只需要换配置：

- **黑客松组队**：参赛者发需求，Agent 自动匹配互补队友，发现跨界组合
- **创业找联创**：模糊需求（"需要有人帮我把想法变成产品"）也能匹配到意想不到的人
- **企业内部资源协调**：不需要"认识对的人"，需要你的人自动出现
- **学术跨学科合作**：物理学家的"分子动力学模拟"和生物学家的"蛋白质折叠"产生共振
- **自由职业/服务市场**：客户发需求，能做的人主动响应，系统发现最优组合

---

## 二、AI 创新性说明

### 2.1 核心理念：投影是唯一操作

通爻的架构建立在一个极简的洞察之上：**系统中只有一个操作——投影。**

```
丰富 → 透镜 → 聚焦
```

一个人的完整存在，通过语境透镜，变成一段可被理解的表达。一段模糊的想法，通过编码透镜，变成一个可比较的信号。多个独立的回应，通过综合透镜，变成一个协作方案。

每一步都是同一个操作。透镜不同，尺度不同，操作相同。

反过来也成立：多个聚焦的投影重新组合，还原出比任何单一投影更丰富的东西——这就是协作。**投影是降维，协作是升维。协议同时服务于两个方向。**

这个洞察的工程意义：协议的全部工作就是**让投影的摩擦趋近于零**。编码精度、匹配效率、综合质量——都是在降低投影的摩擦。

### 2.2 AI 在协议中的角色

AI 不是通爻的"功能增强"，而是协议运转的核心引擎。没有 AI，协商流程无法运行。整个协商链路中，AI 承担五个不可替代的角色，封装为五个独立 Skill 模块：

| Skill 模块 | 投影操作 | AI 做什么 | 为什么必须是 AI |
|---|---|---|---|
| **DemandFormulationSkill** | 原始意图 → LLM+Profile 透镜 → 丰富化需求 | 将用户一句话意图丰富为结构化需求，提取隐含约束和真实意图 | 用户说"找个前端"，AI 理解真实需求是"快速验证产品想法的能力" |
| **ResonanceDetector** | 编码意图 → 相似度透镜 → 匹配集合 | 将需求和 Agent Profile 编码为 384 维向量，计算共振分数 | 跨维度语义匹配（技能 × 经验 × 兴趣 × 价值观），不是关键词匹配 |
| **OfferGenerationSkill** | 需求 → 各 Agent 能力透镜 → 独立回应 | 每个 Agent 基于自身真实 Profile 生成个性化 Offer | 不是统一模板，是基于个体差异的自主判断——"我能帮上忙的部分是……" |
| **CenterCoordinatorSkill** | 多个回应 → 综合透镜 → 协作方案 | 综合所有 Offer，发现互补关系、识别缺口、生成结构化方案 | 多方信息的非线性聚合，寻找组合最优解而非单一最优 |
| **GapRecursionSkill** | 缺口 → 子需求透镜 → 新的协商 | 将方案中的缺口转化为结构良好的子需求，触发递归协商 | 缺口描述模糊（"缺数据能力"），需要 AI 转化为可协商的子需求 |

### 2.3 四个核心创新

**创新一：等待屏障消除 LLM 第一提案偏见**

LLM 存在被研究证实的系统性偏见：先到的回答会被高估 10-30 倍（anchoring bias）。如果 Agent A 先回应、Agent B 后回应，Center 会不自觉偏向 A 的方案。

通爻的做法：所有 Agent 的 Offer 必须全部收齐后，Center 才能看到任何一个。这是代码层面的强制屏障（asyncio barrier），不是 Prompt 层面的"请不要偏向先到的回答"。

**设计原则：代码保障 > Prompt 保障。** 凡是能用代码保障的确定性逻辑，绝不用 prompt 保障。状态机控制流程，LLM 提供智能——两者职责分离。

**创新二：需求 ≠ 要求——打开未知匹配空间**

用户说"我要一个 React 开发者"——这是**要求**（具象的假设性解法）。用户真正需要的可能是"快速验证产品想法的能力"——这是**需求**（抽象的张力）。

DemandFormulationSkill 的工作是把要求翻译成需求。翻译后的需求在向量空间中覆盖更大的区域，能匹配到搜索范式永远触及不到的候选人——一个全栈独立开发者可能是比"React 开发者"更好的匹配，但你搜"React"永远搜不到他。

关键设计：Formulation 使用的是**用户自己的 Agent**（通过 SecondMe adapter 调用用户的分身），不是平台的通用 LLM。这意味着需求丰富化是个性化的——同样说"找个队友"，一个技术背景的人和一个设计背景的人，丰富化出来的需求完全不同。

**创新三：Agent 是无状态投影函数**

```python
agent_vector = project(profile_data, lens)  # 投影即函数
```

Agent 不是一个持久化的"对象"，而是一个**函数**——给定数据源和透镜，投影出一个向量。同一份 Profile 数据，在不同场景下投影出不同维度的 Agent。

数据源通过 Protocol 接口（`ProfileDataSource`）可插拔：
- `SecondMeAdapter`：OAuth2 认证，调用用户的 SecondMe 分身
- `ClaudeAdapter`：平台默认通道，用于 Playground 用户
- 自定义 Adapter：实现 `chat()` 和 `get_profile()` 接口即可

这意味着通爻不锁定任何 Agent 平台。SecondMe 用户、Playground 用户、未来的任何平台用户，在协议层面完全平等。

**创新四：递归子协商——缺口自动填补**

Center 综合方案时如果发现缺口（"这个团队缺一个数据工程师"），不是输出"建议你再找一个"——而是自动发起一轮新的协商，用完全相同的流程去填补缺口。

```
主协商 (depth=0)
  ↓ Center 识别缺口
  ↓ GapRecursionSkill: 缺口 → 子需求
  ↓ 子协商 (depth=1): 完整管道运行
  ↓ 子方案返回主 Center
  ↓ 主 Center 综合最终方案
```

协商单元是可递归的——这是分形结构的工程实现。V1 递归深度限制为 1 层，协议层面无上限。

### 2.4 与现有方案的结构性差异

| 维度 | 传统 A2A 应用 | 通爻 |
|---|---|---|
| 匹配逻辑 | 标签搜索 / embedding 排序 | 需求丰富化 + 向量共振 + 互补发现 |
| 偏见处理 | 无（或 Prompt 约束） | 等待屏障（代码强制，asyncio barrier） |
| 协调能力 | 无 / 手动 | Center Agent 综合 + 递归子协商 |
| 数据源 | 绑定单一平台 | 可插拔适配器（Protocol 接口） |
| 输出 | 排序列表 | 结构化协作方案（参与者 + 任务拓扑 + 依赖关系） |
| 数据回流 | 无 | 协作结果通过 WOWOK 链上事件回流，驱动 Profile 演化 |

---

## 三、技术实现说明

### 3.1 四层架构

通爻严格遵循四层架构，每层职责分离、可独立替换：

```
应用层 ─── Website (Next.js 16)、App Store、MCP Server
            最易变，不影响下面三层

能力层 ─── 5 个 Skill 模块、LLM 客户端 (Claude API)
            可插拔，不同 Agent 可使用不同能力模块

基础设施层 ─── AgentRegistry、Encoder (MiniLM-L12-v2)、EventPusher (WebSocket)
              可被整体替换

协议层 ─── 状态机 (8 态)、事件语义 (7 种)、递归规则、屏障机制
            不可改——状态机定义了协商的语义
```

核心原则：**协议层不可改，基础设施层可替换。** 换一个向量编码器不应该改状态机逻辑；换一个 LLM 不应该改事件语义。

### 3.2 协商状态机：8 态 7 事件

一次完整协商经过 8 个状态，每个转换由代码强制保障（`VALID_TRANSITIONS` 字典，非法转换直接抛异常）：

```
CREATED ──→ FORMULATING ──→ FORMULATED ──→ ENCODING ──→ OFFERING
                              ↑ 用户确认                    ↓
                              (300s 超时                 BARRIER_WAITING
                               自动确认)                    ↓
                                                      SYNTHESIZING ──→ COMPLETED
```

| 状态 | 发生什么 | 关键保障 |
|---|---|---|
| CREATED | 会话初始化 | - |
| FORMULATING | 用户 Agent 丰富化需求（客户端 LLM） | 失败降级：使用原始文本 |
| FORMULATED | **确认屏障**——等待用户审阅丰富化结果 | 300s 超时自动确认；子协商自动确认 |
| ENCODING | 需求→向量，计算全场景 Agent 共振分数 | 自共振排除（提交者不在候选池） |
| OFFERING | 激活的 Agent 并行生成 Offer | 30s 超时，失败 Agent 标记 EXITED |
| BARRIER_WAITING | **等待屏障**——所有 Offer 收齐才释放 | 消除第一提案偏见 |
| SYNTHESIZING | Center 综合方案（单轮，3 个工具） | 文本降级：LLM 返回纯文本时自动包装为 plan |
| COMPLETED | 方案输出，三层防线保障 plan_json 不为空 | LLM 输出 → 正则提取 → 会话数据构造 |

7 种事件通过 WebSocket 实时推送：

| 事件 | 触发时机 |
|---|---|
| `formulation.ready` | 需求丰富化完成，等待用户确认 |
| `resonance.activated` | 共振匹配完成，返回激活 Agent 列表及分数 |
| `offer.received` | 单个 Agent 提交 Offer |
| `barrier.complete` | 所有 Offer 收齐，屏障释放 |
| `center.tool_call` | Center 每次工具调用（输出方案 / 创建子需求 / 创建 Machine） |
| `plan.ready` | 方案生成完毕 |
| `sub_negotiation.started` | 子协商启动 |

### 3.3 核心协商流程

```
用户输入自然语言意图
  ↓
DemandFormulationSkill
  用户自己的 Agent (SecondMe/Claude) 丰富化需求
  提取隐含约束、真实意图、可协商偏好
  ↓
用户确认 / 修改丰富化结果（FORMULATED 确认屏障）
  ↓
Encoder (paraphrase-multilingual-MiniLM-L12-v2, 384 维)
  需求→向量，与全场景 Agent 向量计算余弦相似度
  按共振分数排序，k_star 上限 + min_score 阈值筛选
  自共振排除：提交者永远不在候选池中
  ↓
OfferGenerationSkill
  激活的 Agent 并行生成 Offer (asyncio.gather)
  每个 Agent 只能看到自己的 Profile（代码层禁止编造能力）
  30s 超时，失败 Agent 标记 EXITED 不阻塞流程
  ↓
等待屏障 (BARRIER_WAITING)
  所有 Agent 到达 REPLIED 或 EXITED 后才释放
  Center 在屏障释放前看不到任何 Offer
  ↓
CenterCoordinatorSkill (平台侧 LLM, Claude function calling)
  3 个工具：
  ├─ output_plan：生成 plan_text + plan_json（必须调用，终止协商）
  ├─ create_sub_demand：识别缺口 → 触发递归子协商 (depth ≤ 1)
  └─ create_machine：WOWOK Machine 草案（V2 集成预留）
  ↓
输出
  plan_text：叙述性方案说明
  plan_json：结构化拓扑 {
    summary,
    participants: [{ agent_id, role }],
    tasks: [{ id, title, assignee, prerequisites }],
    topology: { edges: [{ from, to }] }
  }
```

### 3.4 关键技术决策

**Offer 反编造保障：** 每个 Agent 生成 Offer 时，只能访问自己的 Profile 数据。这是代码层面的强制隔离（`engine.py` 在调用 OfferGenerationSkill 时只传入当前 Agent 的 profile_data），不是 Prompt 层面的"请不要编造"。Agent 不可能声称自己有不存在的能力。

**plan_json 三层防线：** LLM 输出 JSON 有 10-20% 的失败率（高温度 + 长输出容易产生非法 JSON）。通爻用三层防线保障 plan_json 永不为空：
1. 使用 LLM 直接输出的 plan_json（如果合法）
2. 从 plan_text 中正则提取 JSON 块
3. 从会话数据（参与者、Offer）自动构造最小 plan_json

**快照隔离：** 协商在启动时冻结世界状态。协商过程中新注册的 Agent 不会被纳入，已有 Agent 的 Profile 更新不会影响进行中的协商。这保证了协商结果的确定性。

### 3.5 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 |
| 后端 | Python 3.12 + FastAPI + WebSocket + SQLAlchemy |
| AI | Claude API (function calling / tool use) |
| 向量编码 | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384 维, 多语言) |
| 认证 | SecondMe OAuth2 + 开放注册 Playground |
| 数据库 | SQLite (协商历史 + Offer 持久化) |
| 部署 | Vercel (前端) + Railway (后端, 持久化卷挂载) |

### 3.6 扩展点（Protocol 接口）

核心引擎通过 5 个 Python Protocol 接口定义扩展点，开发者实现任意接口的自定义版本即可改变引擎行为：

```python
class ProfileDataSource(Protocol):    # 数据源适配器
    async def chat(self, messages, system_prompt) -> str: ...
    async def get_profile(self) -> dict: ...

class Encoder(Protocol):              # 向量编码器
    async def encode(self, text) -> Vector: ...

class PlatformLLMClient(Protocol):    # LLM 调用客户端
    async def call(self, messages, tools) -> LLMResponse: ...

class Skill(Protocol):                # 技能模块基类
    async def execute(self, context) -> SkillResult: ...

class EventPusher(Protocol):          # 事件推送通道
    async def push(self, event) -> None: ...
```

### 3.7 测试保障

- **256 个测试**全部通过（单元测试 + 集成测试）
- 覆盖完整协商闭环：从 CREATED 到 COMPLETED 的每个状态转换
- 共振排序语义正确性验证
- Offer 反编造机制验证
- Center tool-use 正确性验证
- 观察遮蔽（屏障）生效验证
- 三层 plan_json 防线验证
- 前端 `next build` 通过，零编译错误

---

## 四、交互与设计说明

### 4.1 产品形态：App Store + Playground + MCP

通爻的产品层包含三个入口，覆盖不同用户群体：

**App Store（主入口）**：面向普通用户。4 个场景，447 个 Agent，SecondMe 登录后一句话发起协商。

**Playground（开放入口）**：面向无 SecondMe 账号的用户。粘贴一段自我介绍 + 邮箱即可注册为 Agent，立即参与协商。零门槛体验完整协议能力。

**MCP Server（开发者入口）**：面向开发者。5 个 MCP 工具（towow_scenes / towow_agents / towow_join / towow_demand / towow_status），通过 MCP 协议接入，在任何支持 MCP 的客户端中使用通爻。

### 4.2 用户主流程

```
1. 进入 → 选择入口（SecondMe 登录 / 邮箱注册 / MCP 接入）
      ↓
2. 选择场景（黑客松组队 / 技能交换 / 招聘 / 社交匹配）
      ↓
3. 输入需求（一句自然语言，一个文本框，一个按钮）
      ↓
4. [可选] "通向惊喜"——基于用户 SecondMe 画像的个性化需求辅助
   SSE 流式输出，实时生成针对用户背景的需求建议
      ↓
5. 协商进行中——实时展示：
   ├─ 进度条：5 步流程（提交 → 丰富化 → 共振 → 响应 → 方案）
   ├─ Agent 网格：激活的 Agent 卡片，共振分数可视化
   ├─ 活动流：事件时间线，工具调用可折叠展开
   └─ 详情面板：点击 Agent 查看 Offer 详情
      ↓
6. 方案展示：
   ├─ plan_text：叙述性方案说明
   ├─ plan_json 可视化：参与者 + 任务 + 依赖关系
   └─ 每个参与 Agent 的角色和能力概述
```

### 4.3 关键界面设计

**需求输入**：极简——一个文本框，一个提交按钮。不需要填表、不需要选标签。降低使用门槛到最低。

**"通向惊喜"辅助**：SecondMe 登录用户可使用。系统读取用户的 SecondMe 画像，SSE 流式输出个性化的需求建议。不是通用的"帮你写需求"，是基于你是谁来建议你可能需要什么。

**协商过程展示**：HTML/CSS 流式布局（非 SVG 图谱），设计原则是"协商是时序流，不是空间图谱"：
- PhaseSteps：5 步进度条，当前步骤脉冲动画
- AgentGrid：flexbox 自适应布局，支持任意数量 Agent，110px 卡片 + 入场动画
- ActivityFeed：时间线事件列表，工具调用可折叠
- DetailPanel：侧滑面板，点击 Agent 查看 Offer 全文

**历史记录**：协商结果持久化到 SQLite，用户可查看历史协商列表和详情（Offer、方案、参与者）。

### 4.4 App Store 场景数据

4 个场景，每个场景预注册 100+ 多样化 Agent（10 种风格种子生成），用户可直接体验完整协商流程：

| 场景 | Agent 数量 | 典型需求示例 |
|---|---|---|
| 黑客松组队 | 118 | "帮我找队友做 AI + 教育方向的项目" |
| 技能交换 | 107 | "我会 Python，想学设计，找人互教" |
| 招聘匹配 | 114 | "创业公司找全栈工程师，偏好有 AI 经验的" |
| 兴趣匹配 | 108 | "想找人一起做独立游戏" |

SecondMe 真人用户注册的 Agent 优先排序展示，模板 Agent 作为网络密度补充。Playground 注册的用户与 SecondMe 用户在协商中完全平等——协议层不区分来源。

### 4.5 统一入口选择器

`/enter` 页面提供 5 种入口方式：

| 入口 | 状态 | 说明 |
|---|---|---|
| SecondMe OAuth | 可用 | 一键登录，分身直接参与协商 |
| Google 登录 | 即将开放 | - |
| 邮箱注册 | 可用 | 输入邮箱 + 自我介绍，零门槛 |
| 手机注册 | 即将开放 | - |
| MCP 接入 | 可用 | 开发者通过 MCP 协议接入 |

---

## 五、项目信息

| 项目 | 信息 |
|---|---|
| 作品名称 | 通爻网络 ToWow Network |
| 体验地址 | https://towow.net |
| 代码仓库 | https://github.com/NatureBlueee/Towow |
| 队伍 | 通爻网络 ToWow |
| 队长 | 张晨曦 |

---

## 六、未来方向

### 6.1 WOWOK 链上集成（下一步）

协商产出的方案通过 Contract Bridge 转化为 WOWOK Machine（Sui 链上工作流）。链上执行事件（OnNewOrder、OnNewProgress、OnNewArb）作为真实行为反馈回流到 Profile，驱动 Agent 向量持续演化。

这闭合了完整的价值循环：**意图 → 投影 → 协商 → 方案 → 链上执行 → 回声 → Profile 演化 → 更好的投影。**

### 6.2 协议基因组

通爻已完成协议的本质提纯——《通爻协议基因组》（Protocol Genome v0.1）。整个协议压缩为五个概念：

- **一个操作**：投影（丰富 → 透镜 → 聚焦）
- **一种粒子**：意图（显式需求与隐式画像是同一粒子的不同密度）
- **一条原则**：最后的透镜属于端侧（去中心化判定）
- **一个循环**：拒绝即新意图（递归）
- **一个度量**：通过率（涉及方的端侧判定）

所有工程实现、品牌叙事、研究方向从这份基因组推导而来。

---

*通爻网络——Agent 宇宙的协商协议。需求发出，方案涌现。*
