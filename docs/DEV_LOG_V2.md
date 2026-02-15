# V2 开发日志

## 概述

V2 Intent Field 是基于 Protocol Genome v0.3 的干净重建，不依赖 V1 任何代码。核心变化：Intent 统一（demand = profile = Intent）、持久内存场、多 Intent per Agent、零 LLM 匹配管道。

---

## 2026-02-14 ~ 02-15: Phase 0-2 实验（编码策略验证）

### Phase 0: 基线验证

> 脚本：`tests/field_poc/field_poc.py`

使用 V1 编码器（MiniLM-L12-v2, 384d）+ cosine similarity，20 条测试。

**结果**：14/20 通过 (70%)，L4（跨域模糊）仅 1/5。

### Phase 1: 编码策略对比

> 脚本：`tests/field_poc/comparison_poc.py` | 数据：`comparison_results.json`

4 策略 × 2 变体 = 8 组：

| 策略 | L4 | Total | Hits |
|------|----|-------|------|
| MiniLM-384d-flat-dense | 1/5 | 14/20 | 37/95 |
| MiniLM-384d-chunk-binary | 2/5 | 12/20 | 39/95 |
| **mpnet-768d-chunk-dense** | **4/5** | **16/20** | **45/95** |
| mpnet-768d-chunk-binary | 3/5 | 15/20 | 43/95 |

**锁定**：mpnet-768d + chunked bundle + SimHash 10,000-dim binary + Hamming similarity

### Phase 2: Formulation 验证

> 脚本：`tests/field_poc/formulation_poc.py` | 数据：`formulation_results.json`
> Profile 数据：`tests/field_poc/test_profiles.py`（6 条碎片化生活记录）

| 策略 | Total | Hits |
|------|-------|------|
| **A_raw（直接编码）** | **3/6** | **7/31** |
| B_llm_only | 1/6 | 6/31 |
| C_llm_profile | 2/6 | 5/31 |
| D_raw_bundle | 2/6 | 6/31 |

**结论**：Raw encode 赢了所有 LLM formulation 策略。Formulation 不在匹配管道中，作为 UX 层可选功能。

**完整报告**：`tests/field_poc/EXPERIMENT_REPORT.md`

---

## 2026-02-15: Genome v0.3 → V2 架构映射

### 读取 Protocol Genome v0.3（`docs/genome-v03.html`）

关键发现：
- §1: 协议中只有**一个操作**（投影：丰富→透镜→聚焦），V1 的五步是同一操作的不同实例
- §2: 只有**一种粒子**（Intent）。demand/profile/feedback 编码后处理方式完全相同
- §3: 协议边界 = encode + field + match + visibility。offer/synthesize/approve 属于应用层
- §4: 阴阳循环（意图→数据→意图），没有终端 approve 节点
- §6: Formulation 是不对称的——用户侧 formulate，Agent 侧不需要
- §8: V1 的 5 个偏差：Intent 分叉、过度工程化、无持久场、越界透镜、无循环

### V2 协议映射

| 概念 | V1 | V2 |
|------|----|----|
| 数据类型 | demand ≠ profile（两条路径） | Intent（统一） |
| 协议动词 | formulate → resonate → offer → synthesize → approve | **deposit** + **match** |
| 编码 | 外部 Encoder 调用 | Field 内部处理 |
| 场 | 每次请求扫描全池 | 持久内存场 |
| 每个 Agent | 一个向量 | **多个 Intent**（每个碎片独立存入） |
| 匹配结果 | Agent 级 | Intent 级 + Owner 级聚合 |
| LLM 在匹配中 | formulate 用 LLM | **零 LLM** |

用户确认："对的，你理解的很对"

---

## 2026-02-15: ADR-011 + 接口设计 + PLAN-011

### ADR-011: V2 Intent Field（`docs/decisions/ADR-011-v2-intent-field.md`）

**决策**：V2 独立模块，不改 V1。7 个核心设计决策：
1. Intent 统一
2. 两个协议动词（deposit/match）
3. 编码策略锁定（mpnet-768d + chunked bundle + SimHash binary）
4. 多 Intent per Agent
5. Formulation 是协议外 UX 功能
6. 协议止于可见性
7. 对外接口只接受 text

### 接口设计（`docs/decisions/ADR-011-interface-design.md`）

三个 Protocol + 三个数据类型：

```
Protocol:
  IntentField: deposit, match, match_owners, remove, remove_owner, count, count_owners
  Encoder: encode, encode_batch, dim
  Projector: project, batch_project, similarity, batch_similarity

Types:
  Intent(id, owner, text, metadata, created_at)
  FieldResult(intent_id, score, owner, text, metadata)
  OwnerMatch(owner, score, intents)
```

### PLAN-011（`docs/decisions/PLAN-011-v2-intent-field.md`）

7 个文件，6 步构建顺序。每步增量可运行。

---

## 2026-02-15: V2 Field 模块实现

### Skill 调度

| 阶段 | 加载的 Skill |
|------|-------------|
| ② ADR | `arch`（通过 lead 编排） |
| ③ 接口设计 | `arch` + `towow-eng-hdc` |
| ④ 实现方案 | `towow-eng` + `towow-eng-hdc` |
| ⑤ 代码实现 | `towow-dev` + `towow-eng-hdc` |

### 构建过程

**Step 1: types.py + protocols.py** — 纯定义，零依赖 ✅
**Step 2: encoder.py** — MpnetEncoder (768d)，加载模型 ~3s ✅
**Step 3: projector.py** — SimHashProjector，从 POC hdc.py 重写 ✅
- 改进：batch_project 返回 2D numpy；popcount LUT 预计算；batch_similarity 全向量化
**Step 4: chunker.py + pipeline.py** — 文本切分 + 编码流水线组合 ✅
**Step 5: field.py** — MemoryField 核心实现 ✅
- 紧凑向量矩阵 uint8[N, 1250]
- Owner 索引 dict[str, set[str]]
- 去重 hash(owner|text)
- 向量矩阵翻倍增长策略
**Step 6: __init__.py + routes.py 更新** ✅
- routes.py 从 V1 的 register/query 更新为 V2 的 deposit/match/match-owners
- server.py 初始化更新：InMemoryField → MemoryField(pipeline)
- profile_loader.py 保留（纯工具函数）
- V1 memory_field.py 删除

### 验证结果

```
deposit: 3 intents, idempotent dedup, multi-intent per owner ✅
match "Rust 后端":
  agent_rust: 0.7621 (全栈工程师，5年 Rust 经验)
  agent_rust: 0.7359 (喜欢开源，GitHub 上维护 Rust 项目)
  agent_security: 0.6266
  agent_design: 0.6154
match_owners: agent_rust 以 0.76 聚合排第一 ✅
remove / remove_owner: 正确维护计数 ✅
```

### V1 消费方影响

| 消费方 | 处理 |
|--------|------|
| server.py:195 `InMemoryField` | 更新为 V2 `MemoryField(pipeline)` |
| server.py:620 `field_router` | routes.py 已更新为 V2 接口 |
| tests/towow/test_field/ | V1 测试需要更新（pending） |

### 文件清单

```
backend/towow/field/
├── __init__.py        (39 行)   公开导出
├── types.py           (35 行)   Intent, FieldResult, OwnerMatch
├── protocols.py       (97 行)   IntentField, Encoder, Projector
├── encoder.py         (46 行)   MpnetEncoder
├── projector.py      (100 行)   SimHashProjector + bundle_binary
├── chunker.py         (52 行)   split_chunks
├── pipeline.py        (57 行)   EncodingPipeline
├── field.py          (175 行)   MemoryField
├── routes.py         (159 行)   V2 HTTP API
└── profile_loader.py (147 行)   保留（Profile 加载工具）
```

---

## 2026-02-15: Phase 3 实验（碎片级 deposit + Agent 聚合匹配）

> 脚本：`tests/field_poc/phase3_multi_intent_poc.py` | 数据：`phase3_results.json`
> Skills 调度：`towow-eng-test`（实验设计）+ `towow-dev`（代码实现）

### 实验设计

**验证 Genome v0.3 核心声明**："多 Intent per Agent"——每个 Agent 的 Profile fields 是独立的意图碎片。

三组对照（共享同一 EncodingPipeline）：

| 策略 | deposit 方式 | 查询方式 | Intent 数量 |
|------|-------------|---------|------------|
| C_baseline | `profile_to_text()` → 1 deposit/agent | `match()` + owner 聚合 | 447 |
| A_single | fields 分行 `\n` 拼接 → 1 deposit/agent | `match()` + owner 聚合 | 447 |
| B_multi | each field → separate deposit (same owner) | `match()` + manual 聚合 | 2,455 (avg 5.5/agent) |

B_multi 聚合策略子实验：max / top3_avg / weighted

测试集：20 条 TEST_QUERIES（L1-L4）+ 6 条 FORMULATION_TESTS = 26 条查询

### 结果

**Pass Rate (通过 / 总数)**

| 策略 | Total | L1 | L2 | L3 | L4 |
|------|-------|-----|-----|-----|-----|
| **C_baseline** | **18/26 (69%)** | **5/5** | 4/5 | 4/7 | 5/9 |
| A_single | 16/26 (62%) | 4/5 | 3/5 | 4/7 | 5/9 |
| B_multi_max | 14/26 (54%) | 3/5 | 4/5 | 4/7 | 3/9 |
| B_multi_top3_avg | 10/26 (38%) | 1/5 | 3/5 | 1/7 | 5/9 |
| B_multi_weighted | 12/26 (46%) | 2/5 | 3/5 | 2/7 | 5/9 |

**Hit Count (命中 / 期望命中)**

| 策略 | Total | L1 | L2 | L3 | L4 |
|------|-------|-----|-----|-----|-----|
| **C_baseline** | **49/126** | **17/24** | **12/26** | 12/34 | 8/42 |
| A_single | 46/126 | 15/24 | 11/26 | 12/34 | 8/42 |
| B_multi_max | 39/126 | 12/24 | 11/26 | 12/34 | 4/42 |
| B_multi_top3_avg | 28/126 | 8/24 | 8/26 | 6/34 | 6/42 |
| B_multi_weighted | 34/126 | 11/24 | 8/26 | 9/34 | 6/42 |

### 关键发现

1. **C_baseline 全面领先**：简单的 `profile_to_text` + pipeline 内部 chunking 是最佳策略。Pipeline 按句子边界切分保留了跨字段的上下文关系。

2. **A_single 略差**：用 `\n` 分隔字段（强制 field-level chunking）不比 C_baseline 的 sentence-level chunking 好。说明 chunker 的句子边界切分已经是合理的粒度。

3. **B_multi 显著退化，尤其 L1**：碎片化 deposit 导致短碎片（如 "skills: Python, Rust"）脱离上下文，直接匹配能力退化。447 agents × 5.5 fields = 2,455 intents 加剧了竞争噪音。

4. **聚合策略：max > weighted > top3_avg**：max 策略保留最强信号，top3_avg 稀释了强信号。但所有 B_multi 变体都不如 C_baseline。

5. **例外：L4 "用技术做点有意义的事"**：B_multi_top3_avg 和 weighted 找到了 `stack_overflow_soul`（其他策略未命中）。多 Intent 在极端模糊查询中偶尔能发现单 Intent 遗漏的关联——因为某个碎片字段恰好和查询有独立共振。

### 结论

**对于 Agent Profile 的 deposit 策略，C_baseline（profile_to_text → 单次 deposit）是当前最优方案。**

Genome v0.3 的"多 Intent per Agent"声明在 Agent Profile 场景下不成立——结构化的多字段数据更适合合并编码。但这不否定多 Intent 在其他场景的价值：
- **用户碎片**（时间轴上的生活记录）天然适合独立 deposit，因为每条碎片本身就是完整语境
- **Agent 行为反馈**（echo 数据）可以作为独立 Intent 追加，不需要重新编码整个 Profile
- **多粒度匹配**：单 Intent 做粗筛，多 Intent 做细粒度追问

**决策**：V2 Field 保留多 Intent per Agent 的能力（API 不变），但默认 deposit 策略用 profile_to_text 合并。match_owners 作为聚合工具保留。

---

## 2026-02-15: Phase 4 编码器对比实验

> 脚本：`tests/field_poc/encoder_comparison_poc.py`
> Skills 调度：`towow-eng-hdc`（编码器评估）+ `towow-dev`（代码实现）

### 实验设计

**决策目标**：当前锁定的 mpnet-768d (128 tokens) 是否应该换成更大的模型？

| 模型 | 维度 | max_seq | 候选原因 |
|------|------|---------|----------|
| paraphrase-multilingual-mpnet-base-v2 | 768d | 128 tokens | 当前默认 |
| intfloat/multilingual-e5-large | 1024d | 512 tokens | 更大窗口，可能保留更多张力结构 |
| BAAI/bge-m3 | 1024d | 8192 tokens | 超长窗口（因网络问题未完成） |

每个模型 × 4 种 chunk size (256, 512, 1024, full text) = 12 组配置。
全部使用 C_baseline 策略（Phase 3 winner）。20 条去重查询（L1-L4 各 5 条）。

### 结果（mpnet vs e5-large，8 组完成）

| Config | Pass | Hits | L1 | L2 | L3 | L4 | 编码时间 |
|--------|------|------|----|----|----|----|----|
| **mpnet-768d_chunk256** | **15/20** | 42/95 | **5/5** | 4/5 | 3/5 | 3/5 | 12s |
| mpnet-768d_chunk512 | 14/20 | 40/95 | 5/5 | 4/5 | 2/5 | 3/5 | 9s |
| mpnet-768d_chunk1024 | 14/20 | 40/95 | 5/5 | 4/5 | 2/5 | 3/5 | 9s |
| mpnet-768d_chunkfull | 14/20 | 40/95 | 5/5 | 4/5 | 2/5 | 3/5 | 10s |
| e5-large_chunk256 | 13/20 | **47/95** | 3/5 | 4/5 | 3/5 | 3/5 | 41s |
| e5-large_chunk512 | 13/20 | 46/95 | 3/5 | 4/5 | 3/5 | 3/5 | 44s |
| e5-large_chunk1024 | 13/20 | 46/95 | 3/5 | 4/5 | 3/5 | 3/5 | 44s |
| e5-large_chunkfull | 13/20 | 46/95 | 3/5 | 4/5 | 3/5 | 3/5 | 44s |

bge-m3 因网络问题（2.27GB 模型下载中断）未完成。

### 关键发现

1. **mpnet 通过率更高**（15/20 vs 13/20），e5-large **命中数更多**（47 vs 42）。差异仅 2 条查询，20 条样本下无统计显著性。

2. **chunk size 几乎无影响**：e5-large 4 种 chunk 结果一致；mpnet 仅 chunk256 略好 1 条。

3. **e5-large L1 退步**（3/5 vs 5/5）：更大模型在直接匹配上反而更差，可能原因：
   - 测试集偏差：expected_hits 在 Phase 0-2 基于 mpnet 系列模型标定
   - SimHash 投影瓶颈：1024d → 10,000d binary 的投影可能丢失了大模型的额外精度

4. **e5-large 慢 4 倍**（44s vs 10s 编码，0.7s vs 0.3s 查询），无精度优势。

5. **Hits vs Pass 矛盾**：e5-large 命中更多人但通过更少查询 → 命中更分散（每条多一点但不集中），mpnet 更集中（该找到的排名靠前）。

### 决策

**锁定 mpnet-768d + chunk256 作为 V2 默认编码配置。**

理由：
- 更大模型在当前 SimHash 投影 + 20 条测试集下无显著优势
- mpnet 速度快 4 倍，L1 满分
- 编码器是 Protocol 内部实现，通过 `Encoder` 接口随时可替换
- 下一步优先级是真人验证，不是编码器调优

---

## 2026-02-15: V2 Field 测试 + Lead 审查 + 修复

### 测试编写与执行

> Skills 调度：`towow-eng-test`（测试设计）+ `towow-dev`（代码实现）

**test_memory_field.py（25 测试）**：deposit、match、match_owners、remove、remove_owner、buffer 增长、Protocol 一致性。使用 HashPipeline（生产级测试管道，非 MagicMock）。

**test_chunker.py（10 测试）**：空字符串、空白、短文本、边界、长文本切分、中文句子边界、短句合并、无边界回退、内容保留、默认参数。

**test_projector.py（21 测试）**：SimHashProjector（16 条：shape、确定性、不同输入、batch vs single、自相似度=1、range、batch_similarity、packed_dim、不同 D、不同 seed）+ bundle_binary（5 条：单向量拷贝、相同向量、多数投票、空列表异常、偶数平局）。

**test_pipeline.py（12 测试）**：使用 StubEncoder（确定性归一化随机向量）+ 真实 SimHashProjector。shape、确定性、不同输入、空/空白异常、批量编码、相似度、packed_dim、长文本 chunking。

**全部 76 测试通过。**

### Lead 审查 #1：发现 6 个问题

| 编号 | 级别 | 问题 | 根因 |
|------|------|------|------|
| P0 | 阻塞 | field.py 硬编码 1250 | 维度耦合，换 D 值会静默错误 |
| P1 | 高 | MagicMock 测试管道 | 空壳 mock 无法发现接口违反 |
| P2 | 中 | remove_owner 锁竞态 | 循环中释放-重获锁，中间状态暴露 |
| P3 | 中 | remove O(N) 线性扫描 | 缺少反向索引 |
| P4 | 中 | 缺少 projector/chunker/pipeline 独立测试 | 只有集成级测试 |
| P5 | 低 | batch_project 未向量化 | Python for 循环逐行 packbits |

### 修复

**P0**：`packed_dim` 属性链 Projector Protocol → SimHashProjector → EncodingPipeline → MemoryField。消除所有硬编码 1250。

**P1**：MagicMock → HashPipeline（SHA-256 确定性 RNG + 真实 Hamming 相似度 + popcount LUT）。未定义方法调用会 AttributeError（而非 MagicMock 的静默接受）。

**P2**：提取 `_remove_locked()` 内部方法，`remove_owner` 单次 `async with self._lock` 包裹全部删除。

**P3**：新增 `_pos_index: dict[str, int]` 反向索引（intent_id → 行号），remove 从 O(N) 降为 O(1)。

**P4**：新增 test_chunker.py (10) + test_projector.py (21) + test_pipeline.py (12) = 43 新测试。

**P5**：`batch_project` 改为 `np.packbits(bits, axis=1)` 向量化。

### Lead 审查 #2：通过

二次审查无新的 P0/P1 问题。额外修复 2 个 P3 级一致性问题：
- `pipeline.py` bundle seed 从 `hashlib.md5` 统一为 `hashlib.sha256`
- `projector.py` docstring 中硬编码的 `1250` 改为泛化描述 `packed_dim`

**最终状态：76/76 Field 测试全绿，全套 332 测试通过。**

### 文件最终行数

```
backend/towow/field/
├── __init__.py        (39 行)   公开导出
├── types.py           (44 行)   Intent, FieldResult, OwnerMatch
├── protocols.py      (102 行)   IntentField, Encoder, Projector（含 packed_dim）
├── encoder.py         (45 行)   MpnetEncoder
├── projector.py      (106 行)   SimHashProjector + bundle_binary
├── chunker.py         (56 行)   split_chunks
├── pipeline.py        (71 行)   EncodingPipeline（含 packed_dim 代理）
├── field.py          (230 行)   MemoryField（反向索引 + 锁安全）
├── routes.py         (159 行)   V2 HTTP API
└── profile_loader.py (147 行)   保留（Profile 加载工具）

backend/tests/towow/test_field/
├── test_memory_field.py  (25 测试)  HashPipeline 驱动
├── test_chunker.py       (10 测试)  纯函数测试
├── test_projector.py     (21 测试)  SimHash + bundle_binary
├── test_pipeline.py      (12 测试)  StubEncoder + 真实 Projector
└── test_profile_loader.py (8 测试)  保留
```

---

## 待执行

- [x] Phase 3 实验：碎片级 deposit + Agent 聚合匹配
- [x] Phase 4 编码器对比实验（mpnet vs e5-large）
- [x] V2 Field 测试编写 + Lead 审查 + 修复（76 测试，332 全套）
- [ ] 真人验证：用真实感受判断匹配结果
