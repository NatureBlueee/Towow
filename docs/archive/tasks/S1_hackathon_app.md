# S1 — 基于 SDK 构建黑客松组队应用

> 创建日期：2026-02-09
> 任务类型：SDK 应用验证 × 产品开发
> 优先级：Tier 0（立即可做，SDK 已就绪）
> PRD 状态：已细化
> 依赖：无硬依赖（SDK 已可用）
> 关联任务：B1（黑客松场景建模，上游——提供场景洞察）、S3（Adapter 实现集，可复用 S1 的反馈）、H2（Prompt 工程，S1 产出的体验报告可帮助 H2 聚焦优化方向）

---

## 这个任务在项目中的位置

通爻 SDK（`towow-sdk`）刚完成封装——EngineBuilder、7 个 Protocol 接口、6 个 Skill、pip install 即可使用。但 SDK 的真正质量还没有被**外部开发者**验证过。

**S1 是 SDK 的第一次外部可用性验证。** 你不是修改通爻核心代码，你是**使用** SDK 公开 API 构建一个完整的应用。你的体验直接决定了 SDK 对其他开发者是否好用。

```
[SDK 封装完成] → [S1: 基于 SDK 构建组队应用（你在这里）]
                    ├── 验证 SDK 可用性（API 是否好调、文档是否清楚）
                    ├── 产出第一个 SDK 应用范例
                    └── 产出使用体验报告（反馈给 SDK 维护者）
```

**与 V1/V2 核心开发完全解耦**：你面向的是 SDK 的 7 个 Protocol 接口（`ProfileDataSource`、`PlatformLLMClient`、`Skill`、`EventListener` 等），不碰核心引擎代码。核心引擎如何演化，不影响你的工作。

---

## 为什么做这件事

SDK 从"设计者认为好用"到"使用者确认好用"之间有一道巨大的鸿沟。设计者的盲点——什么概念"不言自明"、什么步骤"显然的"——只有真正用 SDK 构建应用的人才能发现。

**用日常语言说**：这就像你做了一个乐高套件，自己觉得说明书写得很清楚。但只有让一个孩子真的拿着说明书拼一遍，你才知道哪步会卡住。

S1 选择黑客松组队场景，因为：
1. 通爻的 demo 场景本身就是"找技术合伙人"——有真实的 Agent Profile 数据和联调经验可参考
2. 黑客松组队天然适合响应范式——你不知道最好的队友长什么样
3. 组队场景的复杂度适中——比"Hello World"有意义，比"完整平台"可控

---

## 你要回答什么问题

**核心问题**：一个开发者使用 `towow-sdk` 从零构建一个黑客松组队 Web 应用，整个过程是否顺畅？卡点在哪？

**子问题**：

1. **SDK 安装和初始化**：`pip install` → `from towow import EngineBuilder` → 第一次成功运行需要多长时间？有没有卡点？
2. **数据源接入**：实现 `ProfileDataSource` 接口来提供参赛者画像数据，是否直观？数据结构是否足够灵活？
3. **Skill 定制**：自定义 `DemandFormulationSkill` 让它适配组队场景（比如理解"我想找后端"背后的真实需求），定制体验如何？
4. **协商流程**：使用 `EngineBuilder` 配置完整的协商流程（formulation → offer → center → plan），是否能产出有意义的组队方案？
5. **事件监听**：通过 `EventListener` 实现实时进度展示（前端看到协商过程），接入体验如何？
6. **文档质量**：`SDK_GUIDE.md` 的内容是否足以指导你完成整个开发？哪些地方需要补充？

---

## 我们提供什么

### SDK 文档和安装

| 资源 | 位置 | 用途 |
|------|------|------|
| **SDK 开发者指南** | `backend/docs/SDK_GUIDE.md` | **你的主要参考文档**——960 行中文，含设计思想、Skill 体系、快速开始、反脆弱 |
| **SDK 安装** | `pip install git+https://github.com/NatureBlueee/Towow.git#subdirectory=backend` | 一行安装 |
| **SDK 示例** | `backend/examples/` | 3 个示例：`minimal_negotiation.py`、`custom_skill.py`、`headless_mode.py` |

### 已有的参考实现

| 资源 | 位置 | 参考价值 |
|------|------|---------|
| Team Matcher 前端 | `website/app/apps/team-matcher/` | 完整的组队 UI 流程 |
| V1 API 路由 | `backend/towow/api/routes.py` | SDK 如何被 Web 层调用 |
| Demo 场景数据 | `backend/towow/api/app.py`（lifespan 中的 seed 数据） | 5 个 Agent 的 Profile 结构 |

### SDK 核心接口（速查）

你需要实现的接口：

```python
# 1. 数据源——提供参赛者画像
class ProfileDataSource(Protocol):
    async def get_profile(self, agent_id: str) -> dict: ...

# 2. LLM 客户端——调用大模型
class PlatformLLMClient(Protocol):
    async def chat(self, system_prompt: str, messages: list[dict], ...) -> str: ...

# 3. 事件监听（可选）——实时推送进度
class EventListener(Protocol):
    async def on_event(self, event: NegotiationEvent) -> None: ...
```

你可以直接使用的内置组件：
- `EngineBuilder` — 一站式引擎配置
- 6 个内置 Skill（可用默认实现，也可继承定制）
- `ClaudeAdapter`（如果用 Anthropic API）

### 设计原则（与 S1 的关系）

| # | 原则 | 与 S1 的关系 |
|---|------|-------------|
| 0.2 | 本质与实现分离 | 你的应用面向 Protocol 编程，不依赖引擎内部实现 |
| 0.5 | 代码保障 > Prompt 保障 | 引擎的状态机、屏障、确认机制已由代码保障，你不需要在 Prompt 中重复 |
| 0.6 | 需求 ≠ 要求 | 你的 Formulation Skill 应该帮用户发现"要后端"背后的真实需求 |
| 0.8 | 投影是基本操作 | 同一个参赛者在不同黑客松中的"投影"不同 |

---

## 子任务分解

### S1.1 — 环境搭建 + SDK 初探

**描述**：安装 SDK，运行 3 个官方示例，确认环境正常。记录安装过程中遇到的任何问题。

**依赖**：无

**交付物**：
- 环境搭建日志（安装步骤 + 遇到的问题 + 解决方式）
- 3 个示例的运行结果截图/日志
- SDK 初体验笔记（第一印象、文档清晰度、概念理解度）

### S1.2 — 数据层设计与实现

**描述**：设计参赛者画像数据结构，实现 `ProfileDataSource`。数据可以是硬编码的 JSON（不需要数据库），但要足够真实（至少 10 个不同背景的参赛者）。

**依赖**：S1.1

**交付物**：
- 参赛者画像数据结构文档（哪些字段、为什么选这些字段）
- `ProfileDataSource` 实现代码
- 至少 10 个参赛者的样例数据
- 如果参考了 B1（场景建模）的产出，标注引用

### S1.3 — Skill 定制与协商配置

**描述**：根据组队场景的需要，定制 `DemandFormulationSkill`（理解组队需求）和可选的 `OfferGenerationSkill`（让 Agent 描述自己的组队价值）。使用 `EngineBuilder` 配置完整的协商流程。

**依赖**：S1.2

**交付物**：
- 定制 Skill 的代码 + 设计说明（为什么这样改 Prompt）
- EngineBuilder 配置代码
- 至少 3 次协商的运行日志（不同需求 → 不同组队方案）
- Skill 定制体验报告（容易吗？灵活吗？有什么限制？）

### S1.4 — Web 应用开发

**描述**：构建一个简单的 Web 界面，让用户可以：提交组队需求 → 查看协商过程 → 浏览组队方案。技术栈自选。

**依赖**：S1.3

**交付物**：
- 可运行的 Web 应用（前端 + 后端）
- 核心功能：需求提交、协商进度展示、方案浏览
- 部署说明（本地运行即可，不需要线上部署）

### S1.5 — 使用体验报告

**描述**：系统性地记录整个开发过程中的体验——什么顺畅、什么卡住了、文档哪里不清楚、API 哪里不好用。这是 S1 最核心的产出之一。

**依赖**：S1.4

**交付物**：
- **SDK 可用性报告**（2000-3000 字），至少包含：
  - 安装体验（顺畅/卡点）
  - API 设计评估（直观/困惑的接口）
  - 文档质量评估（哪些部分帮了忙、哪些缺失）
  - Skill 定制体验（灵活度、学习曲线）
  - 协商结果质量评估（方案是否有意义）
  - 对其他开发者的建议（"如果你也要基于 SDK 开发，先做 X 再做 Y"）
- **Bug 列表**（如果有）
- **改进建议列表**（API 改进、文档补充、示例增加）

---

## 做完了是什么样

### 产出清单

1. **可运行的黑客松组队 Web 应用** — 展示完整的组队协商流程
2. **SDK 可用性报告** — 开发过程中的体验、发现、建议
3. **应用代码** — 作为 SDK 应用的参考实现

### 三级质量标准

**做完了（基本合格）**：
- 应用可运行，展示完整的协商流程（需求 → Offer → 方案）
- 至少 10 个参赛者画像
- SDK 可用性报告诚实记录了开发体验
- 代码只调用 SDK 公开 API，不修改核心代码

**做得好（超出预期）**：
- 至少定制了 1 个 Skill，且定制效果明显（对比默认 Skill 的输出）
- 可用性报告中的发现被反馈到 SDK 维护者并被采纳
- 有真实用户（3+ 个人）试用并反馈
- 发现了 SDK 文档中"自以为清楚但实际不清楚"的地方

**做得出色（产生额外价值）**：
- 应用成为 SDK 的标杆应用案例，被其他开发者参考
- 可用性报告的洞察推动了 SDK API 的改进
- 在真实黑客松中使用，产出了"认知转变"案例（参赛者发现了意想不到的队友组合）
- 代码质量足以被提取为 SDK 的官方示例

---

## 你必须遵守的

### 硬性约束

1. **只使用 SDK 公开 API**：`from towow import ...` 是你与 SDK 交互的唯一方式。不要 import `towow.core.engine` 的内部实现，不要修改 `backend/towow/` 下的任何文件。
2. **面向 Protocol 编程**：实现 `ProfileDataSource`、`PlatformLLMClient` 等 Protocol 接口，不要绑定具体实现。
3. **中文优先**：界面和内容以中文为主。
4. **诚实报告**：遇到问题不要绕过——记录下来，这正是 S1 的核心价值。

### 与通爻设计原则的对齐

- 组队应用必须体现"响应范式"——不是搜索筛选，是发出需求等响应
- Formulation 应该帮用户发现"要求"背后的"需求"
- 方案应该展示多种可能性，不是"最优匹配"

---

## 你可以自己决定的

### 技术选型
- Web 框架：FastAPI / Flask / Django / 前端 React/Vue/Svelte + 后端 任何框架
- LLM：Anthropic Claude / OpenAI / 本地 Ollama
- 数据存储：内存 / JSON 文件 / SQLite
- 部署方式：本地运行即可

### 范围调整
- 如果时间有限，可以先做命令行版本（跳过 Web UI），聚焦 SDK 可用性验证
- 如果 B1（场景建模）已完成，可以直接使用其产出
- UI 简单即可——核心是验证 SDK，不是做精美前端

### 额外发现
- 如果发现 SDK 的某个 Protocol 接口设计不合理，在报告中详细说明并提出替代方案
- 如果发现组队场景有特殊需求是 SDK 当前不支持的，记录为"SDK 扩展建议"

---

## 对接方式

### 提交位置
- 应用代码：`apps/S1_hackathon_app/`
- 可用性报告：`research/S1_sdk_validation/report.md`

### 建议节奏
- S1.1（环境搭建）：1 天
- S1.2（数据层）：2 天
- S1.3（Skill 定制）：3 天
- S1.4（Web 应用）：3-5 天
- S1.5（体验报告）：2 天
- 总计：2 周

### 有问题找谁
- SDK 使用问题：参考 `backend/docs/SDK_GUIDE.md`，或向 SDK 维护者提 Issue
- 架构原则问题：Arch Skill / 创始人
- 组队场景问题：B1 任务负责人（如果 B1 已启动）

### 后续依赖
- S1 的可用性报告直接反馈到 SDK 的下一版改进
- S1 的应用代码可能被提取为 SDK 的官方示例
- S1 中 Skill 定制的经验可供 H2（Prompt 工程研究）参考

---

*本 PRD 于 2026-02-09 任务审查中创建。S 系列任务是 SDK 封装完成后新增的贡献方向，与 V1/V2 核心开发完全解耦。*
*参考文档：`backend/docs/SDK_GUIDE.md`、`docs/tasks/TASK_REVIEW_2026_02_09.md`*
