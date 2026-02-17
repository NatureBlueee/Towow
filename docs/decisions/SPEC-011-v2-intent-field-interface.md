# ADR-011 接口设计：V2 Intent Field Protocol

**关联**: ADR-011-v2-intent-field.md, Protocol Genome v0.3

## 数据类型

### Intent（唯一的粒子）

```python
@dataclass
class Intent:
    id: str           # 唯一标识，系统生成
    owner: str        # 所有者（agent_id / user_id）
    text: str         # 原始文本
    metadata: dict    # 来源、时间戳、标签等
    created_at: float # 创建时间（Unix timestamp）
```

Intent 是场中唯一的粒子。无论来源是用户显式输入、Agent Profile 碎片、还是行为反馈数据，在场中都是 Intent。

`owner` 字段用于聚合——同一 owner 的多个 Intent 在匹配时可按 owner 归组。

### FieldResult（Intent 级匹配结果）

```python
@dataclass
class FieldResult:
    intent_id: str    # 匹配到的 Intent ID
    score: float      # 相似度分数 [0, 1]
    owner: str        # Intent 所有者
    text: str         # 原始文本（用于展示/二次筛选）
    metadata: dict    # Intent 的 metadata
```

### OwnerMatch（Owner 级聚合结果）

```python
@dataclass
class OwnerMatch:
    owner: str                    # agent_id / user_id
    score: float                  # 聚合后的分数
    intents: list[FieldResult]    # 贡献了分数的 Intent 列表
```

聚合策略（max / top-k avg / weighted）是实现细节，不由 Protocol 规定。

## Protocol 接口

### IntentField（核心协议）

```python
@runtime_checkable
class IntentField(Protocol):
    """V2 Intent Field — 意图的持久场。"""

    async def deposit(self, text: str, owner: str,
                      metadata: dict | None = None) -> str:
        """
        Intent 进入场。

        参数：
            text: 自然语言文本（显式意图/Profile碎片/行为数据）
            owner: 所有者标识
            metadata: 可选的附加信息

        返回：intent_id（系统生成的唯一标识）

        语义：
            - text 经内部编码流水线转换为向量后存储
            - 同一 owner 可以有多个 Intent
            - deposit 是幂等的——相同 text + owner 不产生重复
        """
        ...

    async def match(self, text: str, k: int = 10) -> list[FieldResult]:
        """
        在场中找到与 text 最相关的 Intent。

        参数：
            text: 查询文本
            k: 返回数量上限

        返回：按 score 降序排列的 FieldResult 列表

        语义：
            - text 经内部编码后与场中所有 Intent 比较
            - 返回 Intent 级别的结果（同一 owner 可能出现多次）
            - 不包含查询自身（如果查询文本已 deposit）
        """
        ...

    async def match_owners(self, text: str, k: int = 10,
                           max_intents: int = 3) -> list[OwnerMatch]:
        """
        在场中找到与 text 最相关的 Owner。

        参数：
            text: 查询文本
            k: 返回的 Owner 数量上限
            max_intents: 每个 Owner 最多返回几个贡献 Intent

        返回：按 score 降序排列的 OwnerMatch 列表

        语义：
            - 底层调用 match 获取 Intent 级结果
            - 按 owner 聚合，每个 owner 只出现一次
            - 聚合策略由实现决定
        """
        ...

    async def remove(self, intent_id: str) -> None:
        """移除单个 Intent。不存在时静默。"""
        ...

    async def remove_owner(self, owner: str) -> int:
        """移除 owner 的所有 Intent。返回移除数量。"""
        ...

    async def count(self) -> int:
        """场中 Intent 总数。"""
        ...

    async def count_owners(self) -> int:
        """场中 Owner 总数。"""
        ...
```

### Encoder（内部接口）

```python
class Encoder(Protocol):
    """文本 → 密集向量。IntentField 的内部依赖，不对外暴露。"""

    def encode(self, text: str) -> np.ndarray:
        """单条文本编码。返回 float[D]。"""
        ...

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """批量编码。返回 float[N, D]。"""
        ...

    @property
    def dim(self) -> int:
        """向量维度。"""
        ...
```

### Projector（内部接口）

```python
class Projector(Protocol):
    """密集向量 → 二进制超向量。IntentField 的内部依赖，不对外暴露。"""

    def project(self, dense: np.ndarray) -> np.ndarray:
        """float[D] → binary packed bits。"""
        ...

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """两个投影向量的相似度。[0, 1]。"""
        ...

    def batch_similarity(self, query: np.ndarray,
                         candidates: np.ndarray) -> np.ndarray:
        """query vs N candidates。返回 float[N]。"""
        ...
```

## 编码流水线（内部）

```
deposit(text, owner, metadata)
  │
  ├─ chunked_encode(text)
  │    ├─ split_chunks(text) → list[str]     # 语义块切分
  │    ├─ encoder.encode_batch(chunks) → float[N, 768]
  │    ├─ bundle(vectors) → float[768]        # 超位置叠加
  │    └─ projector.project(bundle) → binary[10000]
  │
  └─ store(intent_id, binary_vector, owner, text, metadata)
```

```
match(text, k)
  │
  ├─ chunked_encode(text) → binary[10000]    # 同上
  ├─ projector.batch_similarity(query, all_vectors) → float[N]
  ├─ top_k(scores, k) → list[(intent_id, score)]
  └─ hydrate(results) → list[FieldResult]    # 附加 text/metadata
```

## 设计约束

1. **对外只接受 text**：调用方永远不接触向量。编码是 Field 的内部事务
2. **Encoder 和 Projector 可替换**：换 bge-large-1024d = 换 Encoder 实现；换 LSH = 换 Projector 实现。IntentField Protocol 不变
3. **Owner 聚合策略不在 Protocol 中固定**：max / top-k avg / weighted 由实现决定，可实验切换
4. **无 LLM 在匹配路径上**：deposit 和 match 都是纯计算，零外部 API 调用
5. **deposit 的切分策略由 Field 内部决定**：调用方传入一段文本，Field 决定怎么切（按句/按段/整体）。短文本（< 256 chars）整体编码，长文本自动切分

## 与 V1 Protocol 的差异

| 维度 | V1 (`IntentField`) | V2 (`IntentField`) |
|------|---------------------|---------------------|
| 输入 | `Vector`（调用方编码） | `str`（Field 内部编码） |
| 粒子 | 一个 ID = 一个 Agent | 一个 ID = 一个 Intent，一个 Agent 有多个 |
| 聚合 | 无（结果即 Agent 级） | Intent 级 + Owner 级聚合 |
| 编码 | 外部 Encoder 单独调用 | 内部 Encoder，自动 chunked bundle |
| 向量 | float32 cosine | SimHash binary Hamming |
| 操作 | insert / search | deposit / match（语义对齐 Genome） |
