# Towow SDK 开发者指南

> 基于一个协商原语，构建任意 Agent-to-Agent (AToA) 应用。
> 这是你唯一需要读的文档。

---

## 目录

- [通爻是什么](#通爻是什么)
- [AToA 思维方式](#atoa-思维方式)
- [快速开始](#快速开始)
- [架构：三层设计](#架构三层设计)
- [协商生命周期](#协商生命周期)
- [Skill 体系](#skill-体系)
- [扩展点](#扩展点)
- [AToA 应用设计指南](#atoa-应用设计指南)
- [反脆弱设计与常见问题](#反脆弱设计与常见问题)
- [API 参考](#api-参考)
- [示例代码](#示例代码)
- [安装与配置](#安装与配置)
- [文件导航](#文件导航)

---

## 通爻是什么

通爻是一个 AI Agent 协商引擎。它提供一个原语——**协商单元（Negotiation Unit）**——这个原语是：

- **自包含的**：不依赖外部的"更大系统"
- **可递归的**：子需求用同样的流程处理
- **可组合的**：多个单元可以并行或串行

用这一个原语，你可以构建任何需要多个 Agent 协调的应用：团队匹配、资源分配、交易协商、任务指派、协作规划，或者还没人想到过的东西。

### 核心洞察

传统多 Agent 系统用**搜索范式**：定义条件 → 查询数据库 → 过滤结果。通爻用**响应范式**：广播信号 → Agent 共振 → 主动回应。区别很关键：

- **搜索**找到你已经知道想要的
- **响应**发现你不知道存在的

用户说"我需要一个技术合伙人"。搜索找到关键词匹配的人。响应让一个 Profile 写着"纪录片导演、AI 伦理方向副业"的 Agent 与信号共振，提供意想不到的价值——用户永远不会搜索的视角。

### 三个核心概念

| 概念 | 是什么 | 类比 |
|------|-------|------|
| **投影（Projection）** | Agent 不是有状态的对象，而是投影函数：`profile_data x 透镜 -> 聚焦表达`。同一个人通过不同透镜可以有不同投影。 | 棱镜把白光分成彩色。每种颜色都是光的真实方面，不是副本。 |
| **共振（Resonance）** | Agent 不是被"搜索"或"查询"的。需求编码为向量信号广播到网络，向量共振的 Agent 主动回应。 | 音叉：敲一根，只有频率匹配的那些才会振动。 |
| **回声（Echo）** | 执行之后，真实世界的结果回声回 Agent 的 Profile，让它进化。系统从实际结果学习，不是从 LLM 的自我评判。 | （V2+，SDK 暂未包含） |

---

## AToA 思维方式

在写代码之前，你需要一个不同的心智模型。Agent-to-Agent 应用不是"给多用户 app 加了 AI 助手"。它们是协调系统，Agent 代表真实能力，自主协商。

### 五个设计原则

**1. 需求 ≠ 要求**

用户说"我需要一个有 5 年经验的 React 开发者"。这是*要求*——一个具体的假设性解法。真正的*需求*可能是"我需要一个能快速验证产品想法的人"。一个擅长快速原型的 Python 全栈开发者可能比那个 React 专家更能满足需求。

*对你的应用意味着什么*：不要按用户的要求做硬筛选。让需求经过 Formulation（丰富化），让 Center 整体评估所有 Offer。用户的要求往往是可协商的——他们只是自己不知道。

**2. 代码保障 > Prompt 保障**

任何能用代码保障的，绝不用 prompt 保障。LLM 有结构性偏见（第一提案偏见：对先看到的回复赋予 10-30 倍权重；锚定效应；坍缩估值）。Prompt 无法可靠消除这些。代码可以。

*SDK 用代码保障了什么*：
- **等待屏障（Barrier）**：所有 Agent 回复后 Center 才看到任何 Offer（消除第一提案偏见）
- **反编造（Anti-fabrication）**：每个 Agent 生成 Offer 时只能看到自己的 Profile
- **轮次上限**：Center 最多 2 轮，之后强制输出方案
- **状态机**：8 个状态，严格验证转换，无捷径
- **递归深度**：V1 子协商限制 depth=1

*Prompt 处理什么*：智能——理解上下文、评估质量、发现创意组合。这是 LLM 擅长的。

**3. 投影是基本操作**

系统中每一步都是同一个操作：丰富的东西通过透镜变成聚焦的东西。

```
人（丰富）      --[Profile 透镜]-->  Agent（聚焦）
原始意图        --[Formulation]-->   结构化需求
需求            --[编码]-->          向量信号
多个 Offer      --[Center]-->        方案
缺口            --[递归]-->          子需求
```

设计 AToA 应用时问自己："什么被投影了？透镜是什么？出来的聚焦表达是什么？"能回答这个，你就和架构对齐了。

**4. 简单规则，涌现复杂度**

好的架构不设计复杂性——设计简单规则，递归应用产生复杂性。通爻的整个协商流是一个循环：

```
信号 → 共振 → 回应 → 协调 → （有缺口？→ 递归） → 方案
```

这个循环在不同尺度上应用，产生：团队匹配、资源发现、冲突解决、能力评估、协作规划。如果你的应用设计需要很多特殊情况，基础规则可能没找对。

**5. Agent 呈现，人决策**

Agent 是投影，不是行为者。它们呈现信息、提供建议、提供视角。人做最终决策。这消除了多 Agent 系统的很多"并发问题"：双重承诺是人的问题，资源冲突由人管理，市场动态自平衡。

*对你的应用意味着什么*：不要构建复杂的分布式锁或资源预留。构建好的信息呈现。让人做最终裁决。

---

## 快速开始

### 安装

```bash
pip install towow-sdk                     # 仅核心（numpy）
pip install towow-sdk[claude,embeddings]  # Claude 适配器 + 嵌入模型
```

### 最小示例

```python
import asyncio
from towow import (
    EngineBuilder, NegotiationSession, DemandSnapshot,
    CenterCoordinatorSkill, DemandFormulationSkill, OfferGenerationSkill,
    LoggingEventPusher,
)
from towow.adapters.claude_adapter import ClaudeAdapter
from towow.infra.llm_client import ClaudePlatformClient

async def main():
    adapter = ClaudeAdapter(api_key="sk-ant-...", agent_profiles={
        "alice": {"name": "Alice", "role": "ML 工程师", "skills": ["Python", "PyTorch"]},
        "bob":   {"name": "Bob",   "role": "设计师",    "skills": ["Figma", "UX"]},
    })

    engine, defaults = (
        EngineBuilder()
        .with_adapter(adapter)
        .with_llm_client(ClaudePlatformClient(api_key="sk-ant-..."))
        .with_center_skill(CenterCoordinatorSkill())
        .with_formulation_skill(DemandFormulationSkill())
        .with_offer_skill(OfferGenerationSkill())
        .with_event_pusher(LoggingEventPusher())
        .with_display_names({"alice": "Alice", "bob": "Bob"})
        .build()
    )

    session = NegotiationSession(
        negotiation_id="my-first-negotiation",
        demand=DemandSnapshot(raw_intent="我需要一个技术合伙人"),
    )

    # 自动确认 Formulation（生产环境中用户通过 UI 确认）
    async def auto_confirm():
        for _ in range(60):
            await asyncio.sleep(1)
            if engine.is_awaiting_confirmation(session.negotiation_id):
                engine.confirm_formulation(session.negotiation_id)
                return

    asyncio.create_task(auto_confirm())
    result = await engine.start_negotiation(session=session, **defaults)

    print(f"状态: {result.state.value}")
    print(f"方案: {result.plan_output[:500]}")

asyncio.run(main())
```

完整可运行版本见 `examples/headless.py`。

---

## 架构：三层设计

```
┌─────────────────────────────────────────────────────┐
│                   你的应用                            │
│  （自定义适配器、Skill、工具、UI）                      │
├─────────────────────────────────────────────────────┤
│                   Towow SDK                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ 协议契约  │  │ Builder  │  │ 默认实现          │  │
│  │ (7 个)   │  │          │  │ （全部可替换）     │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│              密封协议层                                │
│  状态机 · 等待屏障 · 确认机制 · 递归控制               │
│  反编造 · 轮次限制 · 观察遮蔽                          │
│  （你不能改——你也不需要改）                             │
└─────────────────────────────────────────────────────┘
```

| 层 | 内容 | 能改吗？ |
|----|------|---------|
| **协议层** | 状态机（8 状态）、等待屏障、确认机制、递归深度、反编造、观察遮蔽、轮次限制 | **不能**（密封）。这些保障正确性。 |
| **契约层** | 7 个 Protocol 接口：`Encoder`、`ResonanceDetector`、`ProfileDataSource`、`PlatformLLMClient`、`Skill`、`EventPusher`、`CenterToolHandler` | **自己实现**。你面向这些接口编程。 |
| **实现层** | 默认 Skill、适配器、编码器、推送器 | **随意替换**。每个默认实现都只是参考——换掉任何一个。 |

### 为什么"密封"？

协议层编码了经过验证的设计知识：

- **等待屏障**：Google DeepMind (2025) 研究表明 LLM 对先看到的回复赋予 10-30 倍权重。屏障确保 Center 同时看到所有 Offer。Prompt 无法可靠修复这个。代码可以。
- **轮次上限（最多 2 轮）**：DeepMind 同时发现多轮迭代平均质量下降 3.5%，错误放大 4.4 倍。两轮是最优点。
- **观察遮蔽**：JetBrains Research (2025) 发现遮蔽上一轮的原始 Offer 同时保留推理，比摘要效果好 50%，成本低 50%。

你不需要考虑这些。引擎替你处理了。

---

## 协商生命周期

每次协商经过 8 个状态：

```
CREATED ─→ FORMULATING ─→ FORMULATED ─→ ENCODING ─→ OFFERING
                              │
                        [用户确认]
                                         ─→ BARRIER_WAITING ─→ SYNTHESIZING ─→ COMPLETED
                                                                    ↑     │
                                                                    └─────┘
                                                              （Center 工具循环：
                                                               ask_agent, start_discovery,
                                                               create_sub_demand）
```

### 逐步说明

| 状态 | 发生了什么 | 谁执行 |
|------|-----------|--------|
| `CREATED` | 创建 Session，包含原始需求 | 你的代码 |
| `FORMULATING` | 用户的 Agent 基于 Profile 丰富化原始意图。"我需要技术合伙人" 变成带上下文的结构化需求。 | `DemandFormulationSkill`（客户端 LLM） |
| `FORMULATED` | 引擎等待用户确认丰富化后的需求。这是人类检查点——用户看到意图是如何被解读的，可以调整。 | 你的 UI / 自动确认 |
| `ENCODING` | 确认后的需求编码为向量并广播。Profile 向量共振的 Agent 被选中（top-k* 相似度）。 | `Encoder` + `ResonanceDetector` |
| `OFFERING` | 每个共振的 Agent 生成 Offer。反编造保障：每个 Agent 只能看到自己的 Profile。Offer 并行生成。 | `OfferGenerationSkill`（客户端 LLM，每个 Agent） |
| `BARRIER_WAITING` | 引擎等待所有 Agent 回复（或超时/退出）。Center 看到任何 Offer 之前必须全部收集完。这就是屏障。 | 引擎（代码保障） |
| `SYNTHESIZING` | Center 协调所有 Offer。它可以：输出方案、追问 Agent、触发发现对话、或为缺口创建子需求。最多 2 轮。 | `CenterCoordinatorSkill`（平台侧 LLM + 工具） |
| `COMPLETED` | 方案输出完成。协商结束。 | 引擎 |

### 事件

引擎在每一步推送事件。你选择传输方式：

| 事件 | 何时触发 |
|------|---------|
| `formulation.ready` | Formulation 完成，等待确认 |
| `resonance.activated` | 共振筛选出 Agent |
| `offer.received` | 某个 Agent 提交了 Offer |
| `barrier.complete` | 所有 Agent 已回复，Center 开始 |
| `center.tool_call` | Center 使用了工具（ask_agent 等） |
| `plan.ready` | 最终方案输出 |
| `sub_negotiation.started` | 子协商被触发 |

---

## Skill 体系

Skill 是智能层。引擎提供确定性（状态机、屏障、转换）；Skill 提供智能（理解上下文的 LLM 调用）。

共 6 个 Skill。每个都可独立替换。

### 客户端 Skill（使用用户自己的 LLM）

这些 Skill 通过 `ProfileDataSource` 适配器调用用户的模型。用户的数据始终在自己控制下。

#### 1. DemandFormulationSkill — 需求丰富化

**做什么**：把用户的原始意图丰富化为结构化需求表达。

**为什么重要**：用户常常表达*要求*（"我要一个 5 年经验的 React 开发者"），而非*需求*（"我需要快速验证产品想法"）。这个 Skill 利用用户的 Profile 理解真实需求，添加帮助回应者的上下文。

**输入**：`raw_intent`、`agent_id`、`adapter`（可访问 Profile）
**输出**：`formulated_text`、`enrichments`（hard_constraints、negotiable_preferences、context_added）

**设计原则**：Formulation 不替换用户意图——而是丰富它。硬约束 vs 可协商偏好被显式分离，让 Center 知道哪些要遵守、哪些可以挑战。

```python
# 默认：用用户的 LLM + Profile 上下文
DemandFormulationSkill()

# 自定义：你自己的丰富化逻辑
class MyFormulationSkill(BaseSkill):
    async def execute(self, context):
        # 添加行业特定上下文、从你的数据库丰富化，等等
        return {"formulated_text": "...", "enrichments": {...}}
```

#### 2. OfferGenerationSkill — Offer 生成

**做什么**：生成 Agent 对需求的回应（Offer）。

**为什么重要**：每个 Agent 基于自己的 Profile 数据诚实回应。反编造保障意味着 prompt 里只有这个 Agent 的 Profile——它看不到其他 Agent 的数据或 Offer。

**输入**：`agent_id`、`demand_text`、`adapter`、`profile_data`
**输出**：`content`、`capabilities`（列表）、`confidence`（0.0-1.0）

**设计原则**：鼓励 Agent 思考意外价值："在这个需求的背景下，我的哪些经验可能有意想不到的价值？"这使跨领域发现成为可能——一个纪录片导演可能为产品设计提供叙事洞察。

```python
# 默认：用 Agent 的 LLM + Profile 上下文
OfferGenerationSkill()

# 自定义：特定领域的 Offer 格式
class MyOfferSkill(BaseSkill):
    async def execute(self, context):
        # 添加定价、可用性、作品链接等
        return {"content": "...", "capabilities": [...], "confidence": 0.85}
```

#### 3. ReflectionSelectorSkill — 特征提取

**做什么**：从 Agent 的 Profile 中提取文本特征，用于向量编码。

**为什么重要**：Agent 能与信号共振之前，它的 Profile 需要被投影到向量空间。这个 Skill 识别关键的能力维度。

**输入**：`agent_id`、`adapter`、`profile_data`
**输出**：`features`（文本描述列表）

**设计原则**：特征要具体（"3 年 React 开发经验"）而非笼统（"前端技能"）。每个特征成为 Agent 向量表达中的一个维度。

### 平台侧 Skill（使用平台的 LLM）

这些 Skill 使用 `PlatformLLMClient`——平台自己的 API 调用（通常是 Claude）。它们做协调，不代表任何特定 Agent。

#### 4. CenterCoordinatorSkill — 中心协调

**做什么**：中心协调器。接收所有 Offer 并综合出方案。

**为什么重要**：这是协商的核心智能。Center 不只是挑最好的 Offer——它找到组合、识别缺口、发现 Agent 之间互补的意外价值。

**输入**：`demand`、`offers`、`llm_client`、`participants`、`round_number`、`history`
**输出**：`tool_calls`（工具调用列表）

**Center 有 5 个工具**：

| 工具 | 做什么 | 触发 |
|------|-------|------|
| `output_plan` | 输出最终方案文本。**终止协商。** | 状态 → COMPLETED |
| `ask_agent` | 向特定 Agent 追问 | Agent 回复后，Center 再获得一轮 |
| `start_discovery` | 触发两个 Agent 之间的发现性对话 | 运行 `SubNegotiationSkill`，结果回流 Center |
| `create_sub_demand` | 为缺口创建子需求 | 新协商被触发（depth+1），结果回流 |
| `create_machine` | 创建 WOWOK Machine 草案用于链上执行 | （V1：桩） |

**设计原则**：Center 是拿着工具的 Agent，不是有输出类型的分类器。工具集就是边界——Center 做不了工具集以外的事。这是代码保障，不是 prompt 保障。你可以扩展这个工具集（见[自定义 Center 工具](#3-自定义-center-工具)）。

```python
# 默认：用 Claude + 5 个内置工具
CenterCoordinatorSkill()

# 自定义：改 prompt、评估标准等
class MyCenterSkill(CenterCoordinatorSkill):
    def _build_prompt(self, context):
        # 你自定义的 Center prompt
        return system_prompt, messages

    def _get_tools(self):
        # 给 Center 加自定义工具
        tools = super()._get_tools()
        tools.append({"name": "my_tool", ...})
        return tools
```

#### 5. SubNegotiationSkill — 发现性对话

**做什么**：发现两个 Agent 之间隐藏的互补性。

**为什么重要**：有时两个 Agent 表面上不相关，但深层有协同。Center 怀疑互补性存在时触发发现对话。

**输入**：`agent_a`、`agent_b`、`reason`、`llm_client`
**输出**：`discovery_report`（new_associations、coordination、additional_contributions、summary）

**设计原则**：V1 用第三方综合（一次 LLM 调用分析两个 Agent）。未来版本支持直接 Agent 对 Agent 对话。Skill 接口不变。

#### 6. GapRecursionSkill — 缺口递归

**做什么**：把识别出的缺口转化为独立的子需求。

**为什么重要**：当 Center 发现现有 Agent 无法完全满足需求时，它识别缺口，递归触发新的协商。子需求必须是自包含的——回应者不需要知道父需求的细节。

**输入**：`gap_description`、`demand_context`、`llm_client`
**输出**：`sub_demand_text`、`context`

**设计原则**：V1 递归深度由代码限制为 1。子需求经历完整的生命周期：formulation → encoding → offers → barrier → synthesis。同样的规则，不同的尺度。

### Skill 组合总览

```
                        ┌─ 客户端 ─┐              ┌── 平台侧 ──┐
                        │          │              │            │
用户意图 ──→ [Formulation] ──→ [Encoding] ──→ [Offer x N] ──→ [Center]
                                                                 │
                                                 ┌───────────────┼───────────────┐
                                                 ↓               ↓               ↓
                                           [ask_agent]   [SubNegotiation]  [GapRecursion]
                                            (追问)        (发现)            (递归)
```

---

## 扩展点

### 1. 自定义 LLM 适配器

接入任意 LLM 提供商作为 Agent 侧模型。

```python
from towow import BaseAdapter

class OpenAIAdapter(BaseAdapter):
    def __init__(self, api_key, agent_profiles):
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._profiles = agent_profiles

    async def get_profile(self, agent_id: str) -> dict:
        return self._profiles[agent_id]

    async def chat(self, agent_id, messages, system_prompt=None) -> str:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(messages)
        response = await self._client.chat.completions.create(
            model="gpt-4", messages=msgs,
        )
        return response.choices[0].message.content

    async def chat_stream(self, agent_id, messages, system_prompt=None):
        async for chunk in self._client.chat.completions.create(
            model="gpt-4", messages=msgs, stream=True
        ):
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

**要点**：不同 Agent 可以用不同适配器。Alice 用 Claude，Bob 用 GPT-4，Charlie 用本地 Ollama 模型。引擎不在乎——它只跟 `ProfileDataSource` 接口对话。

完整示例见 `examples/custom_adapter.py`。

### 2. 自定义 Skill

替换 6 个默认 Skill 中的任何一个为领域特定逻辑。

```python
from towow import BaseSkill

class ResumeOfferSkill(BaseSkill):
    """以结构化简历格式生成 Offer。"""

    @property
    def name(self) -> str:
        return "resume_offer"

    async def execute(self, context: dict) -> dict:
        agent_id = context["agent_id"]
        demand_text = context["demand_text"]
        adapter = context["adapter"]

        system, messages = self._build_prompt(context)
        raw = await adapter.chat(agent_id, messages, system)
        return self._validate_output(raw, context)

    def _build_prompt(self, context):
        return "你正在生成一份结构化简历...", [{"role": "user", "content": "..."}]

    def _validate_output(self, raw_output, context):
        return {"content": raw_output, "capabilities": [], "confidence": 0.8}
```

注册使用：
```python
engine, defaults = (
    EngineBuilder()
    .with_offer_skill(ResumeOfferSkill())
    # ...
    .build()
)
```

### 3. 自定义 Center 工具

给 Center 添加合成时可以使用的工具。这是最强大的扩展点——你可以让 Center 访问数据库、API 或任何外部系统。

```python
# 第一步：定义 handler（实现 CenterToolHandler 协议）
class SearchDBHandler:
    @property
    def tool_name(self) -> str:
        return "search_database"

    async def handle(self, session, tool_args, context):
        """
        context 包含：
          - adapter: ProfileDataSource
          - llm_client: PlatformLLMClient
          - display_names: dict[str, str]
          - neg_context: dict（skills、config）
          - engine: NegotiationEngine（用于递归调用）
        """
        rows = await db.search(tool_args["query"])
        return {"results": rows}  # 存入 Center 的 history

# 第二步：扩展 CenterCoordinatorSkill 以包含新工具的 schema
from towow import CenterCoordinatorSkill

class MyCenterSkill(CenterCoordinatorSkill):
    def _get_tools(self):
        tools = super()._get_tools()
        tools.append({
            "name": "search_database",
            "description": "搜索知识库获取相关信息。",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        })
        return tools

# 第三步：同时注册到引擎
engine, defaults = (
    EngineBuilder()
    .with_center_skill(MyCenterSkill())
    .with_tool_handler(SearchDBHandler())
    .build()
)
```

**重要**：`output_plan` 永远是内置的，不能被覆盖——它触发 COMPLETED 状态转换，这是协议层保障。

完整示例见 `examples/custom_tool.py`。

### 4. 自定义事件传输

用任意事件传输机制替换 WebSocket。

```python
class KafkaEventPusher:
    async def push(self, event):
        await kafka_producer.send("towow-events", event.to_dict())

    async def push_many(self, events):
        for e in events:
            await self.push(e)
```

内置选项：
- `WebSocketEventPusher` — 生产环境 Web 服务器
- `LoggingEventPusher` — 打印事件到控制台（开发用）
- `NullEventPusher` — 静默丢弃（无头模式）

### 5. 自定义编码器 / 共振检测器

替换向量编码和匹配算法。

```python
class OpenAIEncoder:
    async def encode(self, text: str):
        response = await openai.embeddings.create(model="text-embedding-3-large", input=text)
        return np.array(response.data[0].embedding)

    async def batch_encode(self, texts: list[str]):
        response = await openai.embeddings.create(model="text-embedding-3-large", input=texts)
        return [np.array(d.embedding) for d in response.data]

class FAISSResonanceDetector:
    async def detect(self, demand_vector, agent_vectors, k_star):
        # 构建 FAISS 索引，找 top-k*
        return [(agent_id, score), ...]
```

---

## AToA 应用设计指南

具体的应用构建模式。

### 模式 1：团队匹配

**场景**：创业者为黑客松组队。

```python
adapter = ClaudeAdapter(api_key=key, agent_profiles={
    "ml_eng": {"name": "Alice", "role": "ML 工程师", "skills": [...]},
    "designer": {"name": "Bob", "role": "UX 设计师", "skills": [...]},
    "pm": {"name": "Carol", "role": "产品经理", "skills": [...]},
    # ... 可能有几百个候选人
})

session = NegotiationSession(
    negotiation_id="hackathon-team",
    demand=DemandSnapshot(
        raw_intent="我需要一个团队在 48 小时内做出一个 AI 健康应用"
    ),
)
```

**发生了什么**：Formulation 用创始人的 Profile 上下文丰富化"健康应用"。Encoding 找到技能共振的 Agent。每个 Agent 生成诚实的 Offer。Center 找到最优组合——可能不是三个单独最强的人，而是互补最好的三个。

### 模式 2：资源分配

**场景**：公司需要把工程师分配到项目。

```python
# Agent 代表可用的工程师
# 自定义适配器从 HR 数据库拉取数据
class HRAdapter(BaseAdapter):
    async def get_profile(self, agent_id):
        return await hr_db.get_employee(agent_id)
    # ...

# 自定义 Center 工具检查项目约束
class CheckAvailabilityHandler:
    tool_name = "check_availability"
    async def handle(self, session, tool_args, context):
        return await calendar_api.get_availability(tool_args["agent_id"])
```

### 模式 3：多轮交易协商

**场景**：自由职业者和客户之间协商条款。

关键洞察：Center 最多 2 轮不是限制——是特性。Center 在第 1 轮问澄清问题，第 2 轮综合。如果交易需要更深的协商，用 `start_discovery` 探索双方的互补性。

### 模式 4：能力评估

**场景**：评估哪些团队成员能承担新技术挑战。

```python
session = NegotiationSession(
    negotiation_id="challenge-assessment",
    demand=DemandSnapshot(
        raw_intent="我们需要在 Q2 把单体架构迁移到微服务"
    ),
)
```

Center 看到所有 Offer 后能识别：谁有技能、哪里有缺口（触发 `create_sub_demand`）、哪对人可能有隐藏的互补性（触发 `start_discovery`）。

### 反模式：避免这些

**1. 别把通爻当搜索引擎用**。如果你只想按条件过滤列表，用数据库查询。通爻的价值在于协调和发现——协商过程本身。

**2. 别绕过屏障**。如果你想让 Center 先看到部分结果以"加速响应"，忍住。屏障存在是因为第一提案偏见是真实且可测量的。跳过它不是性能优化——是正确性损失。

**3. 别过度指定需求**。需求越刚性，发现空间越小。"Python 开发者，5 年经验，湾区，15 万年薪"会精确找到这个——其他什么都没有。"需要构建可扩展的数据管道"给 Agent 留出了用意想不到的方式回应的空间。

**4. 别把 Agent 当成可互换的**。每个 Agent 是独特的投影。两个简历相似的 ML 工程师可能基于 Profile 给出完全不同的视角。Center 的工作是评估每个人带来的独特价值。

---

## 反脆弱设计与常见问题

SDK 是 V1——它会有不完美的地方。以下是我们对此的设计态度和你可能遇到的情况。

### 反脆弱原则

通爻的核心设计不惧怕压力——压力让它变好：

**1. 容错优于容错**

每个 Skill 的 `_validate_output` 都采取"宽容解析"策略：
- LLM 返回了 JSON？正常解析。
- LLM 返回了 markdown 包裹的 JSON？自动剥离 code fence。
- LLM 返回了纯文本？降级处理（比如 Center 的纯文本回复自动包装为 `output_plan`）。
- LLM 返回了 `<think>` 标签？自动剥离。

系统不会因为 LLM 格式偏差而崩溃。**代码保障 > prompt 保障**的具体体现。

**2. 超时不是失败，是信息**

Agent 超时 → 标记为 `exited` → 屏障继续。协商不会卡住。超时本身就是有价值的信息（某个 Agent 不可用）。

**3. 递归有天花板**

子协商深度限制 depth=1。即使 LLM 不断识别缺口，代码也会阻止无限递归。最坏情况是 depth=1 的子协商输出一个"无法满足"的方案——这本身就是有价值的输出。

**4. 轮次有上限**

Center 最多 2 轮。即使 LLM 想继续循环（ask_agent → 回复 → ask_agent ...），第 2 轮后工具集被限制为 `output_plan` / `create_machine`，强制输出结果。

### 你可能遇到的问题

| 问题 | 为什么会发生 | 怎么处理 |
|------|------------|---------|
| **Formulation 输出不理想** | 用户 Profile 太简单，或 LLM 丰富化过度 | 1. 丰富 Profile 数据 2. 自定义 `DemandFormulationSkill` 的 prompt 3. 用户确认环节可以调整 |
| **共振选错了 Agent** | 向量编码的语义距离不准确 | 1. 换更好的 Encoder（OpenAI embedding、cohere 等） 2. 丰富 Agent 的 Profile 特征 3. 调整 k_star 参数 |
| **Offer 质量差** | Agent 端 LLM 能力有限，或 Profile 数据不够 | 1. 换更强的 LLM 适配器 2. 丰富 Profile 数据 3. 自定义 `OfferGenerationSkill` 的 prompt |
| **Center 不用某些工具** | Prompt 引导不够，或场景不触发 | 1. 自定义 Center prompt（override `_build_prompt`） 2. 增加更明确的上下文 |
| **Center 输出纯文本没有工具调用** | 某些 LLM 不稳定地遵循 tool-use | 已自动降级：纯文本包装为 `output_plan` |
| **子协商无意义** | LLM 识别了虚假缺口 | 1. 代码限制 depth=1，不会无限递归 2. 自定义 `GapRecursionSkill` 加更严格的验证 |
| **整个协商超时** | LLM API 延迟高 | 1. `offer_timeout` 参数控制单个 Offer 超时 2. `confirmation_timeout` 控制用户确认超时 |

### 给我们的反馈

我们希望从你那里听到：

**1. 协议层是否遗漏了什么保障？**

如果你发现一种情况是 LLM 的结构性偏见导致了系统性错误，而当前的代码保障没有覆盖到，这对我们最有价值。我们可能需要新的代码保障——不是新的 prompt。

**2. 哪个 Skill 的默认 prompt 最需要改进？**

每个 Skill 的 prompt 是"能力层"——可以持续优化。告诉我们哪个 Skill 在你的场景下表现最差，我们优先优化。

**3. 你需要什么新的 Center 工具？**

`output_plan`、`ask_agent`、`start_discovery`、`create_sub_demand`、`create_machine` 覆盖了基本场景。但你的应用可能需要 Center 做我们没想到的事——比如查数据库、调外部 API、写文件。目前你可以通过 CenterToolHandler 自己加。如果某类工具需求频繁出现，我们会考虑内置。

**4. 你的 Agent Profile 长什么样？**

我们提供的默认 Adapter 假设 Profile 是 JSON dict。但真实世界的 Profile 可能是：数据库记录、GraphQL 结果、PDF 简历、LinkedIn 页面。告诉我们你的 Profile 数据源长什么样，我们可能需要更多的参考 Adapter 实现。

**5. 哪里文档不够清楚？**

这份文档是第一版。如果你在某个地方卡住了、某个概念不理解、或者某个步骤的说明不够，直接告诉我们。

### 反馈渠道

- **GitHub Issues**: 报告 Bug、功能请求、文档问题
- **Discussion**: 分享你的 AToA 应用场景和设计思路
- **PR**: 贡献新的 Adapter、Skill、示例

---

## API 参考

### 导入

所有你需要的都从顶层包导入：

```python
from towow import (
    # 引擎
    NegotiationEngine, EngineBuilder,
    # 模型
    NegotiationSession, NegotiationState, DemandSnapshot,
    SceneDefinition, AgentIdentity, AgentParticipant, Offer,
    # 事件
    NegotiationEvent, EventType,
    # 错误
    TowowError, EngineError, SkillError, AdapterError,
    LLMError, EncodingError, ConfigError,
    # 协议
    Encoder, ResonanceDetector, ProfileDataSource,
    PlatformLLMClient, Skill, EventPusher, CenterToolHandler, Vector,
    # 基类
    BaseAdapter, BaseSkill,
    # 默认实现
    NullEventPusher, LoggingEventPusher, WebSocketEventPusher,
    # 默认 Skill
    CenterCoordinatorSkill, DemandFormulationSkill,
    OfferGenerationSkill, SubNegotiationSkill,
    GapRecursionSkill, ReflectionSelectorSkill,
)
```

### EngineBuilder

```python
engine, defaults = (
    EngineBuilder()
    # 引擎级（设置一次）
    .with_encoder(encoder)                    # 可选，默认 MiniLM-L12-v2
    .with_resonance_detector(detector)        # 可选，默认余弦相似度
    .with_event_pusher(pusher)                # 可选，默认 NullEventPusher
    .offer_timeout(30.0)                      # 单个 Agent Offer 超时（秒）
    .confirmation_timeout(300.0)              # 用户确认 Formulation 超时（秒）
    .with_tool_handler(handler)               # 自定义 Center 工具（可重复调用）
    # 每次运行的默认值
    .with_adapter(adapter)                    # 必填
    .with_llm_client(client)                  # 必填
    .with_center_skill(skill)                 # 可选
    .with_formulation_skill(skill)            # 可选
    .with_offer_skill(skill)                  # 可选
    .with_sub_negotiation_skill(skill)        # 可选
    .with_gap_recursion_skill(skill)          # 可选
    .with_display_names({"id": "名字"})       # 可选
    .with_k_star(5)                           # 共振 top-k
    .build()
)

# 返回 (NegotiationEngine, dict) — 把 defaults 解包到 start_negotiation：
result = await engine.start_negotiation(session=session, **defaults)
```

### NegotiationSession

```python
session = NegotiationSession(
    negotiation_id="unique-id",
    demand=DemandSnapshot(
        raw_intent="用户的原始文本",
        user_id="可选",
        scene_id="可选",
    ),
    max_center_rounds=2,  # 默认值
)

# 完成后：
session.state           # NegotiationState.COMPLETED
session.plan_output     # 最终方案文本
session.participants    # list[AgentParticipant]
session.center_rounds   # Center 用了几轮
session.event_history   # 完整事件日志
```

### 协议（契约）

| 协议 | 方法 | 使用方 |
|------|------|-------|
| `ProfileDataSource` | `get_profile()`、`chat()`、`chat_stream()` | Formulation、Offer、Reflection |
| `PlatformLLMClient` | `chat(messages, system_prompt, tools)` | Center、SubNegotiation、GapRecursion |
| `Encoder` | `encode(text)`、`batch_encode(texts)` | 编码阶段 |
| `ResonanceDetector` | `detect(demand_vec, agent_vecs, k_star)` | 编码阶段 |
| `Skill` | `name`、`execute(context)` | 所有 Skill |
| `EventPusher` | `push(event)`、`push_many(events)` | 所有阶段 |
| `CenterToolHandler` | `tool_name`、`handle(session, args, context)` | 合成阶段 |

### 错误体系

所有错误继承自 `TowowError`：

| 错误 | 何时抛出 |
|------|---------|
| `EngineError` | 无效状态转换、引擎内部错误 |
| `SkillError` | Skill 执行失败（LLM 输出格式错、超时） |
| `AdapterError` | 客户端 LLM 失败（认证、网络） |
| `LLMError` | 平台侧 LLM 失败 |
| `EncodingError` | 向量编码或共振检测错误 |
| `ConfigError` | 缺少配置、参数无效 |

### 默认 Skill

| Skill | 类 | 侧 | 可替换 |
|-------|-----|-----|--------|
| 需求丰富化 | `DemandFormulationSkill` | 客户端 | 是 |
| Offer 生成 | `OfferGenerationSkill` | 客户端 | 是 |
| 特征提取 | `ReflectionSelectorSkill` | 客户端 | 是 |
| 中心协调 | `CenterCoordinatorSkill` | 平台侧 | 是 |
| 发现对话 | `SubNegotiationSkill` | 平台侧 | 是 |
| 缺口递归 | `GapRecursionSkill` | 平台侧 | 是 |

---

## 示例代码

| 文件 | 演示内容 |
|------|---------|
| `examples/headless.py` | 无 Web 服务器的完整协商。最简单的完整用法。 |
| `examples/custom_adapter.py` | 接入任意 LLM 提供商（OpenAI、Ollama 等）作为 Agent 侧模型。 |
| `examples/custom_tool.py` | 给 Center 添加自定义工具（知识库搜索）。 |

---

## 安装与配置

### 从 PyPI（发布后）

```bash
pip install towow-sdk                          # 仅核心
pip install towow-sdk[claude]                  # + Claude 适配器
pip install towow-sdk[embeddings]              # + 嵌入模型
pip install towow-sdk[claude,embeddings]       # Claude + 嵌入
pip install towow-sdk[web]                     # + FastAPI Web 服务器
pip install towow-sdk[all]                     # 全部
pip install towow-sdk[dev]                     # + 测试依赖
```

### 从源码

```bash
cd backend
pip install -e .                    # 仅核心
pip install -e ".[all]"             # 所有可选依赖
pip install -e ".[dev]"             # 开发依赖
```

### 运行测试

```bash
cd backend
python -m pytest tests/towow/ -v    # 全部 190 个测试
```

### 环境变量

| 变量 | 是否必需 | 说明 |
|------|---------|------|
| `TOWOW_ANTHROPIC_API_KEY` | Claude 适配器需要 | Anthropic API 密钥 |

---

## 路线图

| 功能 | 状态 | 说明 |
|------|------|------|
| 核心引擎 | **已完成** | 8 状态机、屏障、确认、递归 |
| SDK 封装 | **已完成** | EngineBuilder、7 个 Protocol、pip install |
| 自定义 Center 工具 | **已完成** | CenterToolHandler + _get_tools() 扩展 |
| 无头模式 | **已完成** | NullEventPusher，脚本/Notebook/CI |
| 回声系统 | 计划中 | 真实世界结果回声进 Profile |
| WOWOK Machine | 计划中 | 协商输出的链上执行 |
| 直接 Agent 对话 | 计划中 | SubNegotiation 变为真正的来回对话 |
| 多人格（面具） | 计划中 | 一个人，多个投影 |

---

## 文件导航

快速定位 SDK 源码和相关文档。

### 核心代码

| 路径 | 内容 |
|------|------|
| [`towow/__init__.py`](../towow/__init__.py) | 公开 API 表面（34 个符号） |
| [`towow/builder.py`](../towow/builder.py) | EngineBuilder 流式构建器 |
| [`towow/core/engine.py`](../towow/core/engine.py) | 状态机 + 协商编排（密封协议层） |
| [`towow/core/models.py`](../towow/core/models.py) | 数据模型：Session、Offer、Demand 等 |
| [`towow/core/events.py`](../towow/core/events.py) | 9 种事件类型定义 |
| [`towow/core/protocols.py`](../towow/core/protocols.py) | 7 个 Protocol 契约 |
| [`towow/core/errors.py`](../towow/core/errors.py) | 错误体系 |

### Skill 实现

| 路径 | Skill |
|------|-------|
| [`towow/skills/base.py`](../towow/skills/base.py) | BaseSkill 抽象基类 |
| [`towow/skills/formulation.py`](../towow/skills/formulation.py) | DemandFormulationSkill — 需求丰富化 |
| [`towow/skills/offer.py`](../towow/skills/offer.py) | OfferGenerationSkill — Offer 生成 |
| [`towow/skills/center.py`](../towow/skills/center.py) | CenterCoordinatorSkill — 中心协调（5 个工具） |
| [`towow/skills/sub_negotiation.py`](../towow/skills/sub_negotiation.py) | SubNegotiationSkill — 发现性对话 |
| [`towow/skills/gap_recursion.py`](../towow/skills/gap_recursion.py) | GapRecursionSkill — 缺口递归 |
| [`towow/skills/reflection.py`](../towow/skills/reflection.py) | ReflectionSelectorSkill — 特征提取 |

### 适配器与基础设施

| 路径 | 内容 |
|------|------|
| [`towow/adapters/base.py`](../towow/adapters/base.py) | BaseAdapter 抽象基类 |
| [`towow/adapters/claude_adapter.py`](../towow/adapters/claude_adapter.py) | Claude 适配器（参考实现） |
| [`towow/infra/llm_client.py`](../towow/infra/llm_client.py) | ClaudePlatformClient（平台侧 LLM） |
| [`towow/infra/event_pusher.py`](../towow/infra/event_pusher.py) | WebSocket / Logging / Null 事件推送器 |
| [`towow/infra/config.py`](../towow/infra/config.py) | 配置管理 |
| [`towow/hdc/encoder.py`](../towow/hdc/encoder.py) | MiniLM-L12-v2 嵌入编码器 |
| [`towow/hdc/resonance.py`](../towow/hdc/resonance.py) | 余弦相似度共振检测 |

### 示例与测试

| 路径 | 内容 |
|------|------|
| [`examples/headless.py`](../examples/headless.py) | 无头模式完整协商 |
| [`examples/custom_adapter.py`](../examples/custom_adapter.py) | 自定义 LLM 适配器 |
| [`examples/custom_tool.py`](../examples/custom_tool.py) | 自定义 Center 工具 |
| [`tests/towow/test_sdk.py`](../tests/towow/test_sdk.py) | SDK 专项测试（10 个） |
| [`tests/towow/`](../tests/towow/) | 完整测试套件（190 个） |

### 架构文档

| 路径 | 内容 |
|------|------|
| [`docs/SDK_GUIDE.md`](SDK_GUIDE.md) | 本文档（SDK 开发者指南） |
| [`../../docs/ARCHITECTURE_DESIGN.md`](../../docs/ARCHITECTURE_DESIGN.md) | 通爻网络完整架构设计 |
| [`../../CLAUDE.md`](../../CLAUDE.md) | 项目开发指南 |
| [`pyproject.toml`](../pyproject.toml) | 包配置与依赖 |
