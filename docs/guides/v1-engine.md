# V1 协商引擎开发指南

V1 协商引擎的核心概念、模块结构和扩展方式。

## 核心概念

### 协商流程（8 状态）

```
CREATED → FORMULATING → FORMULATED → ENCODING → OFFERING → BARRIER_WAITING → SYNTHESIZING → COMPLETED
```

1. **Formulate**: 用户输入 → LLM 用 Profile 上下文丰富化 → 结构化意图
2. **Resonate**: 意图编码为向量 → 与 Agent 向量做相似度检测 → 激活列表
3. **Offer**: 激活的 Agent 并行生成 Offer（通过各自的 Adapter）
4. **Synthesize**: Center Agent 聚合 Offer，可追问、发现连接、触发子协商
5. **Complete**: 输出方案 (Plan)

### 四层架构

| 层 | 代码位置 | 职责 |
|----|---------|------|
| **协议层** | `core/` | 状态机、模型、事件、Protocol 接口 |
| **基础设施层** | `hdc/`, `adapters/`, `infra/` | 编码器、LLM Client、事件推送 |
| **能力层** | `skills/` | 6 个 Skill（LLM 调用逻辑） |
| **应用层** | `api/` | REST + WebSocket 端点 |

## 6 个 Protocol 接口

所有模块间通信通过 `core/protocols.py` 定义的 Protocol：

```python
# 向量编码
class Encoder(Protocol):
    async def encode(self, text: str) -> Vector: ...
    async def batch_encode(self, texts: list[str]) -> list[Vector]: ...

# 共振检测
class ResonanceDetector(Protocol):
    async def detect(self, demand_vec, agent_vecs, k_star, ...) -> list[tuple]: ...

# 端侧 LLM（Adapter）
class ProfileDataSource(Protocol):
    async def get_profile(self, agent_id: str) -> dict: ...
    async def chat(self, agent_id: str, messages: list) -> str: ...
    async def chat_stream(self, agent_id: str, messages: list) -> AsyncGenerator: ...

# 平台侧 LLM
class PlatformLLMClient(Protocol):
    async def chat(self, messages, system_prompt, tools) -> dict: ...

# Skill（能力单元）
class Skill(Protocol):
    name: str
    async def execute(self, context: dict) -> dict: ...

# 事件推送
class EventPusher(Protocol):
    async def push(self, event: NegotiationEvent) -> None: ...
    async def push_many(self, events: list[NegotiationEvent]) -> None: ...
```

## 扩展方式

### 添加新的 Adapter

实现 `ProfileDataSource` Protocol 即可：

```python
class MyAdapter:
    async def get_profile(self, agent_id: str) -> dict:
        # 返回 agent 的 profile 数据
        ...
    async def chat(self, agent_id: str, messages: list) -> str:
        # 与 agent 对话
        ...
```

现有 Adapter：
- `claude_adapter.py` — Claude API（默认通道）
- `secondme_adapter.py` — SecondMe OAuth2 + chat_stream

### 添加新的编码器

实现 `Encoder` Protocol：

```python
class MyEncoder:
    async def encode(self, text: str) -> np.ndarray:
        # text → vector
        ...
    async def batch_encode(self, texts: list[str]) -> list[np.ndarray]:
        return [await self.encode(t) for t in texts]
```

现有编码器：
- V1: `hdc/encoder.py` — MiniLM-L12-v2 (384d)
- V2: `field/encoder.py` — BGE-M3 (1024d) / mpnet (768d)

## API 端点

### REST

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/api/scenes` | 创建场景 |
| POST | `/v1/api/agents` | 注册 Agent |
| POST | `/v1/api/demand` | 提交需求 |
| POST | `/v1/api/confirm` | 确认 Formulation |
| POST | `/v1/api/action` | 用户操作（accept/reject） |

### WebSocket

```
ws://localhost:8080/v1/ws/{negotiation_id}
```

推送 7 种事件：`formulation.ready`, `resonance.activated`, `offer.received`, `barrier.complete`, `center.tool_call`, `plan.ready`, `sub_negotiation.started`

## 测试

```bash
cd backend && source venv/bin/activate
python -m pytest tests/towow/ -v              # 全部
python -m pytest tests/towow/test_engine.py   # 引擎测试
python -m pytest tests/towow/test_field/      # V2 Field 测试
```

## 关键文件

| 文件 | 说明 |
|------|------|
| `core/engine.py` | 编排引擎（状态机 + 流程控制） |
| `core/models.py` | 核心数据结构 |
| `core/protocols.py` | 6 个 Protocol 接口 |
| `skills/center.py` | Center Agent（tool-use, 5 个工具） |
| `api/routes.py` | REST + WS 端点 |

详见 [ARCHITECTURE_DESIGN.md](../ARCHITECTURE_DESIGN.md)。
