# SecondMe 深度技术调研报告：作为通爻结晶模块端侧 Agent 的评估

> 调研日期：2026-02-18
> 背景：EXP-009 结晶 POC SIM-002 v1 催化 prompt 压倒性成功后，评估 SecondMe 开源项目能否作为生产阶段端侧 Agent 的实现层

---

## 一、SecondMe 核心架构理解

### 1.1 整体架构分层

SecondMe 采用三层架构，其核心在 `lpm_kernel/` 下：

**L0 — 原始记忆层（Raw Memory）**

位于 `/tmp/Second-Me/lpm_kernel/L0/`。L0Generator 负责从用户上传的文档（PDF、Markdown、图片、音频）中提取结构化 insight。它调用外部 LLM（通过 OpenAI 兼容接口，可以是 GPT-4、DeepSeek 等），对每个文档生成标题、摘要、关键词，并存储到 ChromaDB（向量数据库）和 SQLite（元数据）。关键逻辑：

```python
# L0/l0_generator.py — 文档处理后存为 "chunks" 进 ChromaDB
class L0Generator:
    def insighter(self, inputs: InsighterInput) -> Dict[str, str]:
        # 分 IMAGE / AUDIO / DOCUMENT 三条路径，最终返回 title + insight
```

**L1 — 自我画像层（Identity Shades）**

位于 `/tmp/Second-Me/lpm_kernel/L1/`。L1Generator 在 L0 数据基础上，通过 LLM 生成用户的"兴趣域分析"（Shade）和全局传记（Bio）。Shade 是 SecondMe 最核心的个性化单元：每个 Shade 包含领域名、方面名、图标、描述、内容、时间线。全局 Bio 是所有 Shade 的综合人格画像，支持第三人称和第二人称两个视角版本。

```python
# L1/prompt.py — L1 最核心的 prompt，从 Shade 集合生成用户全局画像
GLOBAL_BIO_SYSTEM_PROMPT = """You are a clever and perceptive individual...
Based on the information provided above, construct a comprehensive multi-dimensional profile...
1. A summary of key personality traits
2. An overview of the user's main interests
3. Speculation on the user's likely occupation..."""
```

**L2 — 个人化模型层（LoRA Fine-tuning，可选）**

位于 `/tmp/Second-Me/lpm_kernel/L2/`。L2 是完整的 LoRA 微调流水线，基于 L0/L1 生成的数据合成训练集，使用 llama.cpp 跑本地推理。合成数据类型包括 SelfQA、Preference QA、Diversity 数据、Context 数据。这是 SecondMe 最重的部分，实际上是可选的——不训练 L2 也可以用 L0+L1 增强的 RAG 模式。

### 1.2 上下文存储与管理

| 存储层 | 技术 | 内容 |
|--------|------|------|
| 原始文档 | SQLite (`documents` 表) + 文件系统 | 用户上传的 PDF/MD/文本/图片/音频 |
| 文档 chunks | ChromaDB (`document_chunks` 集合) | 向量化的文本片段，用于 L0 RAG |
| L1 Shades | SQLite (`l1` 表) | 兴趣域分析 JSON，含 embedding |
| 全局 Bio | SQLite | 综合人格画像（third/second person） |
| Status Bio | SQLite | 近期活动状态（last 1 day / last 7 days） |

### 1.3 RAG 机制（关键细节）

RAG 在 `kernel2/services/knowledge_service.py` 中实现，分两层：

```python
class L0KnowledgeRetriever:
    # 向量相似度检索 ChromaDB chunks
    # similarity_threshold=0.7, max_chunks=3
    def retrieve(self, query: str) -> str:
        similar_chunks = self.embedding_service.search_similar_chunks(query, limit=3)
        # 过滤 similarity < 0.7 的结果，返回拼接文本

class L1KnowledgeRetriever:
    # 从 global_bio.shades 中检索最相似的 Shade
    # 实时计算 query embedding 与每个 shade 的相似度
    def retrieve(self, query: str) -> str:
        # 返回 top-3 shades 的 title + description
```

检索触发时机：在构建 system prompt 时，`KnowledgeEnhancedStrategy.build_prompt()` 用当前 user message 查 L0/L1，将结果拼入 system prompt。

### 1.4 对话接口（API）

**本地端点**（每个 SecondMe 实例自己运行，Flask 8002 端口）：
- `POST /api/kernel2/chat` — OpenAI 兼容，SSE 流式输出
- `POST /api/talk/chat` — 另一套 talk 接口，逻辑相同
- `POST /api/talk/advanced_chat` — 三阶段增强推理（需求增强→专家解答→验证）

**公网端点**（通过 secondme.io 路由到用户实例）：
- `POST /api/chat/{instance_id}` — 同 OpenAI Chat Completions 格式
- `POST /api/chat/{instance_id}/chat/completions` — 同上

**Space（多 Agent 讨论）接口**：
- `POST /api/space/create` — 创建多方讨论
- `POST /api/space/{space_id}/start` — 异步启动讨论

**MCP 接口**（`/tmp/Second-Me/mcp/mcp_local.py`）：
- 通过 FastMCP 暴露 `get_response` 工具，内部调用本地 `/api/kernel2/chat`

### 1.5 "我"（投影）的构建方式

SecondMe 的"我"通过两条路径注入推理：

**路径 A（RAG 注入，生产默认）**：每次 chat 时，`KnowledgeEnhancedStrategy` 动态检索 L0 chunks + L1 shades，拼入 system prompt，让通用 LLM（GPT-4/Claude 等）以用户上下文作答。

**路径 B（L2 LoRA，完整个性化）**：本地运行微调后的 llama.cpp 模型，模型权重本身已经 bake 了用户的语言风格和知识偏好。

通爻目前已有的 `SecondMeAdapter`（`backend/towow/adapters/secondme_adapter.py`）对接的是 SecondMe 的 OAuth2 + chat_stream API，拉取 shades/memories 构建 profile，但实际调用的还是 SecondMe 的推理服务。

---

## 二、与端侧 Agent 需求的逐条契合度评估

端侧 Agent 三个需求：**a) 接收外部输入（触发上下文 + 催化观察）**，**b) 检索主人相关上下文**，**c) 生成一段自然语言回复**。

### 需求 a：接收外部输入

**契合度：高，但接口语义需适配**

SecondMe 的 `/api/kernel2/chat` 支持标准 OpenAI messages 格式，可以通过 `messages` 数组传入任意外部上下文：

```json
{
  "messages": [
    {"role": "system", "content": "【催化剂观察】当前轮次: 第2轮\n..."},
    {"role": "user", "content": "【触发输入】请基于你的真实情况表达你的立场"}
  ],
  "metadata": {"enable_l0_retrieval": true, "enable_l1_retrieval": true}
}
```

**实际障碍**：SecondMe 的 `ChatRequest` 模型定义如下：

```python
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]  # 只能传字符串内容
    metadata: Optional[Dict[str, Any]]
```

接口完全可以接收催化观察作为 system message，但 SecondMe 内部的 `ParticipantStrategy`（Space 模块用的）会在 system prompt 末尾强行追加它自己的角色描述模板，这部分会与催化协议的 system prompt 冲突。**不过这是 Space 模块专属的，直接用 `/api/kernel2/chat` 不经过 Space 就不存在这个问题。**

### 需求 b：检索主人相关上下文

**契合度：高，机制完整，开箱即用**

通过 `enable_l0_retrieval: true` + `enable_l1_retrieval: true`，SecondMe 会自动：
1. 用 user message 内容向 ChromaDB 检索 top-3 最相似的原始文档 chunks（L0）
2. 用同样的 query 对所有 L1 Shades 做 cosine similarity，返回 top-3 最相关的兴趣域分析（L1）
3. 将检索结果拼入 system prompt

这正好对应"主人的完整上下文（Profile、历史、偏好）"。用户通过 SecondMe 界面持续上传的文档、日记、对话记录都会进 ChromaDB，每次 chat 时 RAG 自动召回相关内容。

**限制**：L1 Shades 的检索是实时计算所有 shades 的 embedding，当 shades 数量大（>100）时延迟较高。另外 similarity_threshold=0.7 是硬编码的，当触发上下文太抽象时可能什么都检索不到。

### 需求 c：生成自然语言回复

**契合度：完全满足**

SecondMe 的核心功能就是这个——基于用户上下文的自然语言生成。无论是走 RAG+通用 LLM 路径（路径 A）还是本地 L2 微调模型（路径 B），输出都是自然语言文本。

**关键点**：SecondMe 的路径 A（RAG 注入 + 通用 LLM）对于实验阶段完全够用，且可以立即接入。路径 B（L2 微调）需要用户完成训练，对多个 Agent 的实验场景来说有额外部署成本，但个性化质量更高。

---

## 三、适配方案

### 3.1 最小适配（直接可用）

通爻已有的 `SecondMeAdapter` 已经接入了 SecondMe 的 `chat_stream` API，获取 profile（user_info + shades + softmemory）并能发起对话。**现有适配器已经覆盖了端侧 Agent 的基础需求**，不需要改动 SecondMe 本身。

### 3.2 结晶协议专用适配

需要封装一个 `CrystallizationParticipantAdapter`，核心改动在 system prompt 构建逻辑：

**构建思路**：调用 SecondMe 的 `/api/kernel2/chat`，在 messages 中：
- 第一条 `system` message：端侧 prompt v1（来自 `tests/crystallization_poc/prompts/`）+ SecondMe 的 L1 Global Bio（从 `/api/loads/current` + L1 API 获取）
- 第二条及以后：催化观察轮次历史
- 最后一条 `user` message：当前轮催化输出

```python
# 伪代码示意，实际应在 Towow 的 adapters 层封装，不改动 SecondMe
async def generate_crystallization_reply(
    self,
    catalyst_observation: str,
    round_history: list[str],
    endpoint_prompt: str,  # 端侧 prompt v1
) -> str:
    # 从 SecondMe 拉取 L1 Bio 作为固定上下文
    l1_bio = await self._fetch_global_bio()

    messages = [
        {"role": "system", "content": f"{endpoint_prompt}\n\n{l1_bio}"},
        *[{"role": "assistant", "content": h} for h in round_history],
        {"role": "user", "content": catalyst_observation},
    ]

    return await self.chat(
        messages=messages,
        metadata={"enable_l0_retrieval": True}
    )
```

**需要新增的 API 调用**：SecondMe 目前没有暴露直接返回 Global Bio 文本的单独端点（L1 的数据通过训练流程管理），需要调用 `/api/loads/current` 获取 name，再从 kernel 的 L1 相关端点获取 Bio。实际上，对于通爻，用 SecondMe OAuth2 获取到的 `shades` 和 `bio`（已经在 `SecondMeAdapter.fetch_and_build_profile()` 中拉取）就已经是 L1 层的完整数据了。

### 3.3 Space 模块的直接复用可行性

SecondMe 的 **Space 模块**（`/api/space/`）在代码层面与结晶协议高度相似：
- `create_space(title, objective, host, participants)` — 创建多方讨论
- 内部有 3 轮固定讨论，每轮每个参与者轮流发言
- `HostOpeningStrategy`、`ParticipantStrategy`、`HostSummaryStrategy` 三个角色策略

**但不建议直接用 Space 模块替换催化协议**，原因：
1. Space 的轮次逻辑（3 轮固定）和角色（host + participants 对称）与结晶协议不同（催化Agent 不对称，有信息差识别职责）
2. Space 无法注入外部催化 prompt，策略是硬编码在源码里的
3. Space 的收敛条件不存在（纯固定轮次），结晶协议要催化剂判断收敛
4. 改 SecondMe 内部代码违反了"协议层不可改，基础设施层可替换"原则

---

## 四、替代方案扫描

如果 SecondMe 不满足，以下方案按适配难度排序：

| 方案 | 上下文持久化 | API 可调用性 | 个性化程度 | 部署难度 | 评分 |
|------|------------|------------|----------|---------|------|
| **SecondMe（RAG 路径）** | ChromaDB + SQLite | 完整 OpenAI 兼容 API | 高（L1 Shades + L0 docs） | 低（Docker 一键） | ★★★★★ |
| **纯 JSON Profile + Claude/GPT** | JSON 文件 | 直接 API 调用 | 中（依赖 Profile 质量） | 极低 | ★★★★ |
| **Mem0**（开源记忆层）| 向量 + 图存储 | REST API | 中（通用记忆，无人格层） | 低 | ★★★ |
| **LangChain Memory + Agent** | 多种可选 | 需要自行封装 | 低（工具组合，无个性化） | 中 | ★★ |
| **MemGPT / Letta** | 分层记忆（core/archival） | REST API | 中（有自我管理记忆） | 中 | ★★★ |

**纯 JSON Profile + Claude/GPT** 方案的具体形式：用一个足够丰富的 JSON/Markdown Profile 文件代替 SecondMe 的整个技术栈，通过直接调用 Claude API，在每轮 system prompt 中注入 Profile 全文。这正是 `tests/crystallization_poc/` 目前实验用的架构：Agent Profile 直接写在 prompt 里。

---

## 五、推荐方案与理由

### 推荐：两阶段策略

**实验阶段（当前）：纯 JSON Profile + Claude API**

现有结晶 POC（SIM-001/SIM-002）已经验证了这个路径的有效性，且 v1 催化 prompt 取得了压倒性成功（Ground Truth 发现率 30% → 80%）。这个阶段不需要 SecondMe——Profile 就是真实性的最佳近似，控制变量少，迭代快。

继续推进 SIM-003 等实验时，保持这个架构，重点在催化 prompt 优化和 Profile 丰富度上。

**生产阶段：SecondMe 作为端侧 Agent 层**

当结晶协议的 prompt 机制稳定后，SecondMe 提供的价值在于：
1. 用户自主维护 Profile（上传文档、日记、对话记录），比手写 JSON Profile 更真实
2. L0 RAG 检索让 Agent 在结晶讨论中能召回具体的文档片段，而不只是摘要性描述
3. 已有 `/api/kernel2/chat` 完全兼容通爻 `SecondMeAdapter` 的调用方式
4. L2 微调模型（可选）可以让语言风格真正个性化

**适配工作量估算**：

通爻已有的 `SecondMeAdapter` 已经完成了 80% 的工作。剩余的适配仅需：
1. 在 `SecondMeAdapter.chat()` 调用前，构造包含催化观察和端侧 prompt 的 messages 格式（~50 行新代码）
2. 从 SecondMe profile 中提取 Global Bio 注入固定系统人格（已有 shades/memories 数据，拼接即可）
3. 在 `enable_l0_retrieval` 中用催化当轮关键词做 RAG 触发，而非 user 的原始发言

**关键技术确认**：

SecondMe 的 `/api/kernel2/chat` 是一个标准的 OpenAI 兼容 SSE 流式接口，通过 `metadata.enable_l0_retrieval` 开关控制 RAG。接口完全支持在 messages 中传入结晶协议的催化观察，SecondMe 会在内部自动检索主人相关上下文并生成基于真实 Profile 的回复。这正好满足端侧 Agent 的 a/b/c 三个需求，且接口契约不需要改动 SecondMe 源码。

---

## 附：相关代码位置

- `backend/towow/adapters/secondme_adapter.py` — 已有适配器（约 80% 完成）
- `tests/crystallization_poc/prompts/` — 端侧 + 催化 prompt 模板
- `tests/crystallization_poc/simulations/sim002_3person_v1/` — v1 催化成功案例
