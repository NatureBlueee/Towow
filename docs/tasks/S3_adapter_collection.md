# S3 — 自定义 Adapter 参考实现集

> 创建日期：2026-02-09
> 任务类型：SDK 生态 × 工程开发
> 优先级：Tier 0（立即可做，门槛低，生态价值高）
> PRD 状态：已细化
> 依赖：无硬依赖
> 关联任务：S1/S2（SDK 应用，可使用 S3 的 Adapter）、H4（验证实验，可能需要不同 LLM 的对比数据）

---

## 这个任务在项目中的位置

通爻 SDK 通过 `PlatformLLMClient` 和 `ProfileDataSource` 两个 Protocol 接口实现了与外部系统的解耦。当前 SDK 内置了 `ClaudeAdapter`（Anthropic API）和 `SecondMeAdapter`。但 SDK 的生态价值取决于它能接入多少不同的 LLM 和数据源。

**S3 扩大 SDK 的接入生态**——为常见的 LLM 提供商和数据源实现参考 Adapter，让更多开发者可以用自己熟悉的工具与通爻 SDK 交互。

```
SDK Protocol 接口
    ├── PlatformLLMClient ← [S3: 实现多个 LLM Adapter]
    │       ├── ClaudeAdapter（已有）
    │       ├── OpenAIAdapter（新）
    │       ├── OllamaAdapter（新）
    │       └── 更多...
    └── ProfileDataSource ← [S3: 实现数据源 Adapter]
            ├── SecondMeAdapter（已有）
            ├── JSONFileAdapter（新）
            └── 更多...
```

**与 V1/V2 解耦**：只实现 Protocol 接口，不修改核心代码。

---

## 为什么做这件事

1. **降低使用门槛**：不是每个开发者都有 Anthropic API Key。如果只支持 Claude，很多人连 SDK 示例都跑不起来。OpenAI Adapter 和 Ollama Adapter（本地模型）让更多人能立即开始。
2. **验证 Protocol 设计**：为不同的 LLM 实现同一个 `PlatformLLMClient`，是对 Protocol 接口设计质量的最好验证。如果某个 LLM 的 API 很难映射到 Protocol 接口，说明接口设计有问题。
3. **生态基础**：SDK 的长期价值在于生态。参考实现降低了社区贡献新 Adapter 的门槛——"照着这几个改就行"。

---

## 你要回答什么问题

**核心问题**：`PlatformLLMClient` Protocol 的接口设计是否足够通用，能自然地映射到不同 LLM 提供商的 API？

**子问题**：

1. OpenAI 的 Chat Completion API 能否完整映射到 `PlatformLLMClient.chat()` 的参数和返回值？tool calling 的处理方式是否兼容？
2. Ollama 的本地模型 API 与云端 API 的差异（无 tool calling、响应格式不同）对 Protocol 的挑战有多大？
3. 不同 LLM 在同一个协商场景中的表现差异有多大？（同一个需求，Claude vs GPT vs 本地模型的方案质量对比）
4. `ProfileDataSource` 接口是否足够灵活，能适配不同的数据格式（JSON 文件、数据库、API）？

---

## 我们提供什么

### 已有的 Adapter 参考

| 资源 | 位置 | 参考价值 |
|------|------|---------|
| `ClaudeAdapter` | `backend/towow/adapters/claude_adapter.py` | **核心参考**——看它如何实现 `PlatformLLMClient` |
| `SecondMeAdapter` | `backend/towow/adapters/secondme_adapter.py` | 数据源 Adapter 的参考 |
| Adapter 基类 | `backend/towow/adapters/base.py` | 公共工具函数 |
| Protocol 定义 | `backend/towow/core/protocols.py` | 你需要实现的接口定义 |

### SDK 文档

| 资源 | 位置 |
|------|------|
| SDK 开发者指南 | `backend/docs/SDK_GUIDE.md`（"扩展点"章节） |
| SDK 示例 | `backend/examples/`（`custom_skill.py` 展示了 Adapter 的使用方式） |

### `PlatformLLMClient` Protocol 速查

```python
class PlatformLLMClient(Protocol):
    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """发送 chat 请求，返回文本响应。"""
        ...
```

关键点：
- `tools` 参数用于 Center 的 function calling（output_plan、start_discovery 等）
- 返回值是 `str`（纯文本）或包含 tool_use 的结构化字符串
- `ClaudeAdapter` 中的 tool 解析逻辑可参考

---

## 子任务分解

### S3.1 — OpenAI Adapter

**描述**：为 OpenAI Chat Completion API（GPT-4o / GPT-4-turbo）实现 `PlatformLLMClient`。

**依赖**：无

**交付物**：
- `openai_adapter.py` 实现代码
- 单元测试（mock API 响应）
- 集成测试（用真实 API 跑一次协商）
- API 映射文档（OpenAI API 参数 ↔ Protocol 参数的对应关系）

**关键挑战**：
- OpenAI 的 tool calling 格式与 Anthropic 不同（`function_call` vs `tool_use`），需要做格式转换
- streaming 模式的差异处理

### S3.2 — Ollama Adapter（本地模型）

**描述**：为 Ollama 本地模型实现 `PlatformLLMClient`。让开发者可以用免费的本地模型（如 Llama 3、Mistral）运行协商。

**依赖**：无

**交付物**：
- `ollama_adapter.py` 实现代码
- 单元测试
- 集成测试（用本地 Ollama 跑一次协商）
- 本地模型限制说明（哪些功能受限、推荐的模型大小）

**关键挑战**：
- 大多数本地模型不支持原生 tool calling → 需要用 Prompt 模拟（在 system prompt 中描述可用 tool，解析文本输出中的 tool 调用）
- 本地模型的中文能力可能较弱 → 需要测试并记录

### S3.3 — JSON 文件数据源 Adapter

**描述**：实现一个从 JSON 文件读取 Agent Profile 的 `ProfileDataSource`。让开发者不需要任何外部服务就能提供画像数据。

**依赖**：无

**交付物**：
- `json_file_adapter.py` 实现代码
- 标准化的 JSON Schema（Agent Profile 的推荐格式）
- 示例数据文件（至少 10 个 Agent）
- 单元测试

### S3.4 — 跨 LLM 对比测试

**描述**：用同一个协商场景，分别使用 Claude、GPT、Ollama 本地模型运行，对比方案质量和成本。

**依赖**：S3.1 + S3.2

**交付物**：
- 对比测试报告：
  - 同一需求 × 3 个 LLM 的方案质量对比
  - Token 消耗和成本对比
  - 响应速度对比
  - Tool calling 兼容性评估
  - 推荐的 LLM 选择建议（什么场景用什么模型）

### S3.5 — Adapter 开发指南

**描述**：基于 S3.1-S3.3 的开发经验，编写一份"如何为通爻 SDK 写自定义 Adapter"的指南。

**依赖**：S3.1 + S3.2 + S3.3

**交付物**：
- **Adapter 开发指南**（1500-2000 字）：
  - 接口说明（要实现什么、每个方法的语义）
  - 常见坑（tool calling 格式差异、streaming 处理、错误重试）
  - 模板代码（可复制粘贴的骨架）
  - 测试策略（怎么测 Adapter）

---

## 做完了是什么样

### 产出清单

1. **3 个 Adapter 实现**：OpenAI、Ollama、JSON 文件数据源
2. **每个 Adapter 的单元测试和集成测试**
3. **跨 LLM 对比测试报告**
4. **Adapter 开发指南**

### 三级质量标准

**做完了（基本合格）**：
- 3 个 Adapter 可正常工作
- 每个 Adapter 有基本的单元测试
- 跨 LLM 对比有数据支撑

**做得好（超出预期）**：
- Adapter 代码质量足以被合并到 SDK 官方仓库
- 跨 LLM 对比发现了有意义的差异（比如某个 LLM 在 Center 聚合上明显更好）
- Adapter 开发指南清晰到社区成员可以独立写新 Adapter
- 发现了 `PlatformLLMClient` Protocol 的具体改进点

**做得出色（产生额外价值）**：
- 新增了第 4 个 Adapter（如 Google Gemini、DeepSeek、通义千问）
- 对比测试报告成为 SDK 文档的一部分（"选择 LLM 的建议"）
- 发现了本地模型在协商场景中的意外优势或限制，对 SDK 设计有影响

---

## 你必须遵守的

1. **只实现 Protocol 接口**，不修改核心代码
2. **每个 Adapter 必须有测试**——至少 mock 测试，最好有集成测试
3. **错误处理要完善**——网络超时、API 限流、模型不支持 tool calling 等场景都要处理
4. **文档要清晰**——每个 Adapter 文件头部要写清：用途、前置要求（API Key / Ollama 安装）、使用示例

---

## 你可以自己决定的

- 额外实现更多 Adapter（Gemini、DeepSeek、本地 vLLM 等）
- 是否实现 streaming 支持（非必须，但有加分）
- 是否为 Adapter 做性能优化（连接池、并发请求等）
- 代码组织方式（单文件 / 多文件 / 包结构）

---

## 对接方式

### 提交位置
- Adapter 代码：`research/S3_adapters/`（如果质量足够高，会被合并到 `backend/towow/adapters/`）
- 对比报告：`research/S3_adapters/comparison_report.md`
- 开发指南：`research/S3_adapters/adapter_guide.md`

### 建议周期
- S3.1（OpenAI）：3 天
- S3.2（Ollama）：3 天
- S3.3（JSON 文件）：1 天
- S3.4（对比测试）：2 天
- S3.5（开发指南）：1 天
- 总计：1.5-2 周

### 后续依赖
- S3 的 Adapter 被 S1/S2 应用直接使用
- 跨 LLM 对比报告影响 SDK 的"推荐配置"文档
- Adapter 开发指南成为 SDK 生态贡献的入口

---

*本 PRD 于 2026-02-09 任务审查中创建。S 系列任务与 V1/V2 核心开发完全解耦。*
*参考文档：`backend/docs/SDK_GUIDE.md`、`backend/towow/core/protocols.py`、`backend/towow/adapters/claude_adapter.py`*
