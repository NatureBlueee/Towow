# PLAN-011: V2 Intent Field 实现方案

**关联**: ADR-011, ADR-011-interface-design, Protocol Genome v0.3
**日期**: 2026-02-15

## 概述

基于 ADR-011 的决策，实现 V2 Intent Field 模块。V2 完全替换 `backend/towow/field/` 下的 V1 代码，不导入 V1 任何模块。

## 文件结构

```
backend/towow/field/
├── __init__.py              # 公开 API: IntentField, FieldResult, OwnerMatch
├── protocols.py             # Protocol 定义: IntentField, Encoder, Projector
├── types.py                 # 数据类型: Intent, FieldResult, OwnerMatch
├── encoder.py               # MpnetEncoder: text → float[768]
├── projector.py             # SimHashProjector: float[768] → binary[10000]
├── field.py                 # MemoryField: IntentField 实现（持久内存场）
├── chunker.py               # 文本切分: text → list[str]
└── pipeline.py              # 编码流水线: text → packed binary (组合 encoder+projector)
```

7 个文件，每个职责单一，可独立测试。

## 模块依赖图

```
protocols.py  types.py          ← 零依赖，纯定义
     ↓           ↓
encoder.py  projector.py        ← 依赖 numpy, sentence-transformers
     ↓           ↓
     pipeline.py                ← 组合 encoder + projector + chunker
         ↓
      field.py                  ← 组合 pipeline + 存储 + 聚合
         ↓
     __init__.py                ← 公开接口
```

## 各模块实现细节

### 1. protocols.py — 接口定义

从 ADR-011-interface-design 直接映射。定义三个 Protocol：
- `IntentField`: deposit, match, match_owners, remove, remove_owner, count, count_owners
- `Encoder`: encode, encode_batch, dim
- `Projector`: project, similarity, batch_similarity

### 2. types.py — 数据类型

```python
@dataclass
class Intent:
    id: str
    owner: str
    text: str
    metadata: dict
    created_at: float

@dataclass
class FieldResult:
    intent_id: str
    score: float
    owner: str
    text: str
    metadata: dict

@dataclass
class OwnerMatch:
    owner: str
    score: float
    intents: list[FieldResult]
```

### 3. encoder.py — MpnetEncoder

```python
class MpnetEncoder:
    """paraphrase-multilingual-mpnet-base-v2 (768d)"""

    def __init__(self, model_name: str = "paraphrase-multilingual-mpnet-base-v2"):
        self._model = SentenceTransformer(model_name)

    def encode(self, text: str) -> np.ndarray:         # → float32[768]
    def encode_batch(self, texts: list[str]) -> np.ndarray:  # → float32[N, 768]

    @property
    def dim(self) -> int: return 768
```

**工程决策**：
- 模型在 `__init__` 时加载一次，后续调用复用
- `encode_batch` 使用 sentence-transformers 内置 batch 编码，比循环调用 `encode` 快 5-10x
- 返回 float32 numpy 数组，已归一化

### 4. projector.py — SimHashProjector

从 POC `hdc.py` 的 `SimHash` 类重写，增加：

```python
class SimHashProjector:
    def __init__(self, input_dim: int = 768, D: int = 10_000, seed: int = 42):
        rng = np.random.RandomState(seed)
        self._planes = rng.randn(D, input_dim).astype(np.float32)
        self.D = D
        # 预计算 popcount 查找表
        self._popcount_lut = np.array([bin(i).count("1") for i in range(256)], dtype=np.int32)

    def project(self, dense: np.ndarray) -> np.ndarray:        # → packed uint8[1250]
    def batch_project(self, dense: np.ndarray) -> np.ndarray:   # → packed uint8[N, 1250]
    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
    def batch_similarity(self, query: np.ndarray, candidates: np.ndarray) -> np.ndarray:
```

**相对 POC 的改进**：
- `batch_project` 返回 2D numpy 数组 `uint8[N, 1250]` 而非 list（支持向量化操作）
- `batch_similarity` 接受 2D candidates 矩阵，XOR + popcount 全向量化
- popcount 查找表在 `__init__` 预计算，不在每次调用时重建
- 超平面矩阵 `_planes` 用固定 seed=42，全网一致

**超平面矩阵生命周期**：
- 由 seed 决定性生成，不需要持久化存储
- 换 seed = 所有已存向量失效（需要重新编码）
- V2 初版 seed 固定为 42，未来如需更换通过配置管理

### 5. chunker.py — 文本切分

```python
def split_chunks(text: str, max_chars: int = 256) -> list[str]:
    """
    文本 → 语义块列表。

    策略：
    - 短文本（≤ max_chars）：整体作为一个 chunk
    - 长文本：按句号/换行切分，相邻短句合并至 max_chars 以内

    返回至少一个 chunk。
    """
```

**工程决策**：
- 切分粒度由 Field 内部决定，调用方不控制
- 短文本（一句话的查询、单个 Profile 字段）不切分
- 长文本按自然句/段落边界切分，不在词中间断开
- 中文按句号（。！？）和换行切分
- `max_chars=256` 对应 mpnet 的有效 token 窗口（~128 tokens ≈ 200-300 中文字符）
- 不用 LLM 做语义切分——保持零外部调用

### 6. pipeline.py — 编码流水线

```python
class EncodingPipeline:
    """组合 Encoder + Projector + Chunker 为统一编码流水线。"""

    def __init__(self, encoder: Encoder, projector: Projector):
        self._encoder = encoder
        self._projector = projector

    def encode_text(self, text: str) -> np.ndarray:
        """
        text → packed binary vector

        流程：
        1. split_chunks(text) → list[str]
        2. encoder.encode_batch(chunks) → float[N, 768]
        3. projector.batch_project(dense_vecs) → uint8[N, 1250]
        4. bundle_binary(binary_vecs) → uint8[1250]
        """

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        """批量编码多段文本。每段独立走 chunk+bundle 流水线。"""
```

**bundle 算法**（从 POC `bundle_binary` 重写）：
- 多数投票：每个 bit 位置，统计 1 的个数，过半 → 1
- 偶数输入时随机打破平局（seed 基于文本 hash，确保确定性）
- 单 chunk 时直接返回（不 bundle）

### 7. field.py — MemoryField 实现

```python
class MemoryField:
    """
    内存持久场。实现 IntentField Protocol。

    存储结构：
    - _intents: dict[str, Intent]           # intent_id → Intent 对象
    - _vectors: np.ndarray                   # uint8[N, 1250] 紧凑矩阵
    - _id_index: list[str]                   # 行号 → intent_id 映射
    - _owner_index: dict[str, set[str]]      # owner → {intent_id, ...}
    """

    def __init__(self, pipeline: EncodingPipeline):
        self._pipeline = pipeline
        self._lock = asyncio.Lock()
        # ...
```

**关键设计**：

**向量矩阵紧凑存储**：所有向量存为一个 `uint8[N, 1250]` 的 2D numpy 数组，而非 dict/list。`batch_similarity` 直接在矩阵上操作，无需逐个比较。

**Owner 索引**：`dict[str, set[str]]` 维护 owner → intent_ids 映射，`match_owners` 聚合时 O(1) 查找。

**聚合策略**（`match_owners` 内部）：
- 初版使用 **top-1 max**：每个 owner 取其最高分 Intent 的 score 作为 owner score
- 返回 OwnerMatch 时附带该 owner 的 top-N 个贡献 Intent
- 聚合策略作为 `__init__` 参数，可切换为 top-k avg 或 weighted（Phase 3 实验验证后决定）

**deposit 幂等性**：
- 同一 `(owner, text)` 组合不重复存储
- 用 `hash(owner + text)` 作为去重键
- intent_id 使用 `uuid4` 生成

**向量矩阵增长策略**：
- 初始分配 1024 行
- 满了翻倍（amortized O(1) append）
- 删除时标记为空行（懒回收），批量整理在 count > 2x active 时触发

## 构建顺序（增量可运行）

```
Step 1: types.py + protocols.py
         → 纯定义，零依赖，可直接验证类型

Step 2: encoder.py
         → 加载 mpnet 模型，encode("hello") 返回 float[768]
         → 可独立测试

Step 3: projector.py
         → SimHash 投影，project(float[768]) 返回 uint8[1250]
         → 可独立测试

Step 4: chunker.py + pipeline.py
         → 组合 encoder + projector，encode_text("一段文字") 返回 uint8[1250]
         → 可独立测试

Step 5: field.py
         → deposit/match/match_owners 全链路
         → 端到端测试

Step 6: __init__.py + 集成
         → 公开接口，挂载到 server.py（可选）
```

每步完成后系统可运行，不依赖后续步骤。

## 测试策略

### 单元测试（每个模块）

| 模块 | 测试内容 |
|------|----------|
| encoder | encode 返回 float32[768]；encode_batch 返回正确形状；相同文本编码一致 |
| projector | project 返回 uint8[1250]；相似文本 Hamming similarity 高；不相似文本低 |
| chunker | 短文本不切分；长文本按句切分；空文本返回空列表 |
| pipeline | encode_text 端到端；单 chunk vs 多 chunk 结果都是 uint8[1250] |
| field | deposit 返回 id；match 返回排序结果；match_owners 聚合正确；remove 生效；幂等性 |

### 集成测试（复用 POC 数据）

用 `tests/field_poc/test_queries.py` 的 20 条查询 + 447 Agent Profile 数据：
- 加载所有 Agent Profile → deposit 进场
- 跑 20 条查询 → match_owners
- 验证 Phase 1 的结果可复现（mpnet-chunk-binary: 15-16/20 pass）

### Phase 3 实验

**目标**：验证"多 Intent per Agent"架构是否优于"单向量 per Agent"。

**实验设计**：
用 `tests/field_poc/test_profiles.py` 的 6 条测试（含碎片化 Profile）：

| 对照组 | 方式 | 预期 |
|--------|------|------|
| A_single | 每个 Agent 的所有碎片 bundle 为一个向量 deposit | Phase 2 的 D_raw_bundle 水平 |
| B_multi | 每个碎片独立 deposit，match_owners 聚合 | 预期优于 A（噪声碎片不参与聚合） |
| C_baseline | 只 deposit Agent Profile（无用户碎片），raw query match | Phase 1 水平（对照基线） |

**聚合策略子实验**（在 B_multi 上）：
- max: 取 owner 最高分 Intent
- top3_avg: 取 owner top-3 Intent 平均分
- weighted: 按 rank 加权

**评估标准**：同 Phase 1/2 — Top-10 命中数 ≥ min_hits 即 PASS。

## Skill 调度

| 文件 | 负责 Skill | 说明 |
|------|-----------|------|
| types.py, protocols.py | `towow-dev` | 纯数据定义 |
| encoder.py | `towow-eng-hdc` | 嵌入模型集成 |
| projector.py | `towow-eng-hdc` | SimHash 算法 |
| chunker.py | `towow-dev` | 文本处理 |
| pipeline.py | `towow-eng-hdc` | 编码流水线组合 |
| field.py | `towow-dev` + `towow-eng-hdc` | 场实现 + 向量操作 |
| 测试 | `towow-eng-test` | 测试策略和用例设计 |

## 不做的事

- **不做 HTTP API**：V2 Field 是纯 Python 模块，不对外暴露 REST endpoint。API 层属于应用层，后续按需添加
- **不做 WOWOK 集成**：反馈循环（§4）是未来工作
- **不做 Formulation**：已确认为协议外 UX 功能，不在 Field 模块内
- **不做衰减机制**：Intent 时效性（§10 开放问题 2）留待后续
- **不改 V1 代码**：V1 保持现状
