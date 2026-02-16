# V2 Intent Field 实验全景回顾

**日期**: 2026-02-16
**状态**: 探索阶段完成，待设计验证实验
**关联**: Genome v0.3, ADR-011, 研究 001/002

## 一、工程产出

### V2 Field 模块 — 10 文件，~1000 LOC，76 测试

```
backend/towow/field/
├── protocols.py    — 3 Protocol（IntentField / Encoder / Projector）
├── types.py        — Intent, FieldResult, OwnerMatch
├── encoder.py      — MpnetEncoder (768d)
├── projector.py    — SimHashProjector (10000d → packed uint8[1250])
├── chunker.py      — split_chunks (max 256 chars, 句子边界)
├── pipeline.py     — EncodingPipeline (chunk → encode → project → bundle)
├── field.py        — MemoryField (内存持久场, O(1) 删除, 去重)
├── profile_loader.py — 447 Agent JSON → text
├── routes.py       — 5 HTTP 端点
└── __init__.py
```

编码管道：`text → split_chunks(256) → encode_batch(mpnet-768d) → batch_project(SimHash 10000d) → bundle_binary(majority vote) → packed uint8[1250]`

### Lead 审计修复（6 项，已提交）

| ID | 问题 | 修复 |
|----|------|------|
| P0 | 硬编码 1250 | packed_dim 属性链 |
| P1 | MagicMock 测试管道 | HashPipeline 生产级 |
| P2 | remove_owner 锁竞争 | _remove_locked() |
| P3 | remove O(N) | _pos_index 逆向索引 O(1) |
| P4 | 缺独立模块测试 | +43 新测试 |
| P5 | batch_project 未向量化 | np.packbits(bits, axis=1) |

## 二、实验全记录

### Phase 0：基线

- **模型**：MiniLM-L12-v2 (384d)
- **结果**：14/20 通过，L4 仅 1/5
- **结论**：基线可用但 L4 惨败

### Phase 1：编码策略对比（4策略 × 2相似度 = 8组）

| 策略 | 通过 | Hits |
|------|------|------|
| mpnet-chunk-dense | **16/20** | **45/95** |
| mpnet-chunk-binary | **16/20** | **45/95** |
| mpnet-flat-dense | 15/20 | 41/95 |
| MiniLM 各组 | 14/20 | 37-38/95 |

**锁定**：mpnet-768d, chunked bundle, SimHash binary 几乎无损

### Phase 2：Formulation 能否改善匹配？

| 策略 | 通过 |
|------|------|
| A_raw（直接编码） | **3/6** |
| B_llm_only（LLM 扩展） | 1/6 |
| C_llm_profile（LLM + Profile） | 2/6 |
| D_raw_bundle（纯向量 bundle） | 1/6 |

**锁定**：零 LLM 匹配管道。Formulation 价值在 UX 不在匹配。

### Phase 3：碎片级 deposit + Owner 聚合

- C_baseline（整段 profile）胜出
- 碎片化 deposit 不如整段 deposit
- 原因：碎片太短，独立编码后语义不完整

### Phase 4：编码器 × chunk_size 对比

- 3 模型 (mpnet/e5-large/bge-m3) × 4 chunk_size = 12 组
- mpnet-768d + chunk_size=256 仍然最优
- 但模型覆盖仍局限于 sentence-transformers 系列

## 三、"端侧 Agent 写透镜"设计

### 透镜的定义（Genome §1）

> **丰富 → 透镜 → 聚焦**

V1 五步是同一操作在五个尺度上的实例，每步透镜可独立替换。

### 两种透镜

**编码透镜**（全网统一）：
- Encoder Protocol + Projector Protocol
- 当前实现：MpnetEncoder + SimHashProjector
- 所有意图用同一透镜编码 → 同一空间可匹配

**Formulation 透镜**（§6 不对称设计）：
- 用户侧：adapter + LLM → 主动、即时
- Agent 侧：Profile 编码 = 注册时完成的 formulation → 被动、累积
- Phase 2 验证：formulation 价值在 UX，不在匹配管道

### 元逻辑 vs 透镜

- **元逻辑**（不可替换）：意图必须编码才能进场 → 场内匹配 → 可见性 → 行为
- **透镜**（可替换）：编码方式、匹配算法、formulation 实现
- V2 Protocol 设计已体现：Encoder/Projector 是可替换接口

## 四、关键修正：Intent-to-Intent

### 旧理解（错误）

"从一群 Agents 的画像中找到某个能响应你需求的人" — 异质匹配

### 新理解（正确）

"从意图里面找到相关的意图" — 同质匹配

三种"相关"：共振、互补、干涉

### 对实验的影响

| 方面 | 旧框架 | 新框架 |
|------|--------|--------|
| 评估基准 | BEIR/MTEB nDCG | 自定义多关系评估 |
| 测试查询设计 | demand → agent 匹配 | intent → intent 关系 |
| L3 难度定义 | "互补"是附加挑战 | "互补"是核心关系类型之一 |
| 模型选择依据 | MTEB 排名 | 三种关系的综合表现 |

## 五、已验证结论 vs 待验证假设

### 高置信度（已验证）

1. 零 LLM 匹配管道可行 — 协议层决策
2. Formulation 价值在 UX 不在匹配 — Phase 2
3. 整段 profile 优于碎片化 deposit — Phase 3
4. SimHash binary ≈ 原始浮点 — Phase 1
5. Chunked bundle ≥ flat encode — Phase 1
6. 三个 Protocol 接口的可替换架构正确

### 待验证（探索阶段结论）

1. mpnet 是否最佳编码器 — Phase 4 只 3 个模型
2. SimHash 是否最佳二值化 — MRL+BQL 是直接竞争者
3. 向量编码能否同时捕获三种关系 — §10 开放问题
4. 20 条查询的统计效力 — 置信区间过宽
5. GHRR 非交换 binding 在意图匹配场景的有效性

## 六、下一步

详见研究 001/002。核心方向：
1. 设计三种关系的评估框架（自建，不依赖 MTEB）
2. 验证 GHRR / 指令感知 embedding / MRL+BQL 在我们场景的表现
3. 用 Optuna 三目标搜索 + 配对 bootstrap 做严谨的统计验证
