# 研究 001：Intent-to-Intent 多关系编码

**日期**: 2026-02-16
**状态**: 第二轮研究完成，待设计验证实验
**关联**: Genome v0.3 §10 开放问题 1, ADR-011

## 研究问题

> 当前向量编码（语义相似性）能否同时检测互补关系（缺口-填充）、共振关系（同向放大）和干涉关系（深层关联）？ — Genome v0.3 §10

### 关键修正（2026-02-16）

此前错误地将匹配理解为"异质匹配"（从 Agent 画像中找到响应需求的人）。
正确理解：**Intent-to-Intent 同质匹配** — 从意图中找到相关的意图。

三种"相关"：
1. **共振（Resonance）**：方向一致，互相增强
2. **互补（Complementary）**：缺口-填充，一方缺失恰好是另一方强项
3. **干涉（Interference）**：表面无关但深层相通

这改变了评估框架：不是 IR/检索排名（BEIR/MTEB nDCG），而是需要自定义的多关系评估。

## 第一轮研究发现（2026-02-16）

### 发现 1：单一对称 embedding 无法同时覆盖三种关系

学术共识。相似和互补在语义空间中方向不同，标准 cosine similarity 只能测一种。

关键论文：
- **AsymmeTrix** (Yohei Nakajima, 2025) — 不对称向量 embedding，方向性关系
- **MOEE** (ICLR 2025) — 混合专家 embedding，不同路由编码互补信息
- **Entity or Relation Embeddings** (2023/2024) — 实体 embedding 和关系 embedding 捕获互补信息，混合策略远超单独使用

### 发现 2：GHRR — HDC 领域关键突破

**GHRR（Generalized Holographic Reduced Representations, 2024）** 解决了经典 HDC 的根本限制：

- 经典 HDC binding 是交换律的（`bind(A,B) = bind(B,A)`），无法区分关系方向
- GHRR 引入**非交换 binding**：块对角酉矩阵乘法替代元素乘法
- 保持 HDC 核心性质（鲁棒性、分布式表示、bundling/binding 代数）
- 实验证明：组合结构解码准确率和记忆容量显著优于经典 FHRR

**PathHD (2025)** 验证了 GHRR 在知识图谱推理中的有效性：
- 每个关系映射为块对角酉矩阵
- 多跳路径通过非交换 binding 组合
- 在 WebQSP, CWQ, GrailQA 上匹配或超越神经网络基线
- 延迟降低 40-60%，GPU 内存减少 3-5x

**与我们的关联**：当前 SimHash 是 HDC 的最原始形式 — 只有投影，没有 binding。升级到 GHRR 意味着从"只测相似度"到"能编码关系结构"。

### 发现 3：MRL + BQL 是单关系场景最优紧凑方案

| 维度截断 + 二值化 | 精度保留 |
|------------------|---------|
| 1024→512 + binary | >93% |
| 1024→128 + binary | ~87-90% |
| 512 bits | 精度-存储最佳平衡点 |

原生支持 MRL 的模型（2025-2026）：
- Qwen3-Embedding (0.6B/4B/8B) — 32-1024 维
- EmbeddingGemma (308M) — 128-768 维
- mxbai-embed-large-v1 — 原生 binary MRL
- Gemini Embedding (API)

**局限**：MRL 训练目标是语义相似性，截断时保留的是"最重要的相似性信息"，不是互补信息。

### 发现 4：双曲空间可同时建模替代与互补

- **DHGAN** (CIKM 2022) — 替代关系和互补关系映射到不同双曲子空间
- **DHCF** (KBS 2023) — 双曲空间中解耦用户不同意图
- 双曲空间天然适合层次结构（负曲率空间体积指数增长）
- 但二值化在双曲空间中尚无成熟方案

### 发现 5：知识图谱 Embedding 的多关系建模

- **RotatE** — 关系=复数空间中的旋转，能建模对称/反对称/逆/组合关系
- **SectorE** (2025) — 关系=环形扇区区域（非点），允许同一关系下不同匹配程度
- **TransERR** (LREC 2024) — 四元数旋转，可建模 5 种关系模式
- 但 RotatE 直接二值化会丧失旋转语义

## 第二轮研究发现（2026-02-16）

### 方向 A：GHRR 深挖

#### A1. GHRR 数学细节

**块对角酉矩阵形式**：`H = [a_1, ..., a_D]^T`，每个 `a_j` 是 `m x m` 酉矩阵 `U(m)`

分解为 `phi(x)_j = Q^(j) * Lambda^(j)(x)`，Q 为随机酉矩阵，Lambda 为对角相位矩阵。

- **绑定操作**：`H_1 * H_2 = [a_j * b_j]` — 逐块矩阵乘法（非交换）
- **相似度**：`delta(H_1, H_2) = 1/(mD) * Re(tr(sum a_j * b_j†))` — Frobenius 内积归一化
- **有效维度**：`D * m^2`，m=1 退化为 FHRR（交换）
- **"对角度"参数**：连续调节交换性程度（1=FHRR, 0=最大非交换）
- **容量**：m=4, D=600 → ~400+ 绑定超向量（FHRR ~250）

#### A2. PathHD 实现细节

- 关系矩阵**随机初始化，不学习**
- 路径编码通过非交换绑定组合：`v_z = v_{r_1} * v_{r_2} * ... * v_{r_l}`
- 性能随维度 512→4k 上升后趋平，CWQ 偏好 6k
- WebQSP Hits@1: **86.2** vs 最强基线 85.7 (RoG)

#### A3. GHRR 在 NLP/文本匹配中的应用：空白

- 搜索 "non-commutative binding NLP" + "VSA relation encoding text"
- **所有 HDC+NLP 工作都用对称绑定（XOR/BSC）**，主要用于分类
- [VSA Open Source Info Discovery (2024)](https://arxiv.org/html/2408.10734)：768d → BSC 二进制，25x 压缩，tweet 分类 99%+
- [HyperSum (2024)](https://arxiv.org/html/2405.09765)：HDC 做文本摘要
- **没有人用 HDC 做过 STS（语义文本相似度）任务**

#### A4. 关键结论：GHRR 用于文本语义匹配是未探索方向

- **GHRR 在复数域操作，直接二值化会破坏酉矩阵结构 → GHRR 与 BSC 不兼容**
- 编码的是 KG 中固定关系类型，我们需要连续语义空间中的关系，难度更大
- 但非交换绑定的**思想**（不同关系 = 不同变换矩阵）是正确的

### 方向 B：指令感知 Embedding（最高优先级）

#### B1. INSTRUCTOR — 实验证据确凿

**[INSTRUCTOR (ACL 2023)](https://instructor-embedding.github.io/)**

- T-SNE 可视化证明：**无指令时不同情感文本因共享词汇聚集；加入情感指令后被分开**
- 不同指令确实产生**不同的相似度排序** — 同一组文本，指令不同则最近邻不同
- 330 个多样化任务 + 指令 + 对比损失训练，比无指令基线平均 +3.4%

#### B2. GSTransform — 空间变换机制

**[GSTransform (2025)](https://arxiv.org/html/2505.24754v1)**

- 两阶段：指令引导文本摘要聚类 → 轻量 encoder-decoder 投影到指令对齐空间
- **双目标损失**：对比损失（拉近同标签）+ 重建损失（保留原始结构）
- Case study 证明：同组文本以"国家"为指令按国家聚类，以"主题"为指令按主题聚类
- **几何结构确实发生根本性重组**

#### B3. Qwen3-Embedding

- 三阶段训练：对比预训练 → 监督训练 → 多候选模型合并
- 8B 版本 MTEB 多语言排名第一（70.58，2025.06）
- 使用指令通常 +1-5%

#### B4. 可行性判断

**优势**：零标注、零训练、一天出结果、已有成熟开源实现

**风险**：现有证据覆盖的是显式属性（情感/主题），"互补"这种隐式关系是否有效是未知的

**三条候选指令**：
```
共振: "找出具有相似技能和经验的人"
互补: "找出能满足这个需求的人"
干涉: "找出可能存在竞争或冲突的人"
```

### 方向 C：互补关系编码 SOTA

#### C1. Dual Embeddings IN-OUT 机制（最精准类比）

**[Dual Embeddings (2022)](https://arxiv.org/abs/2211.14982)**

SGNS 模型的一个常被忽略的特性：每个元素有两个表示 — 输入矩阵 `W_in` 和输出矩阵 `W_out`

- **同一矩阵内点积** → 衡量**相似性**（共振）
- **跨矩阵点积**（`v_in · v_out`）→ 衡量**互补性**

> **与通爻场景的类比极其精准**：相似性 ~ 共振，互补性 ~ 需求-能力匹配

#### C2. DecGCN — 双独立空间

**[DecGCN (CIKM 2020)](https://dl.acm.org/doi/10.1145/3340531.3412695)**

- 两个独立子 GCN，每个商品输出两个 embedding — 一个编码替代性，一个编码互补性
- Co-attention 机制整合两种局部邻域结构
- 前向迁移 + 循环迁移整合两种语义

#### C3. ConFit v2 — 简历匹配 SOTA

**[ConFit v2 (ACL Findings 2025)](https://arxiv.org/html/2502.12361v2)**

- **HyRe（Hypothetical Resume Embedding）**：用 LLM 生成假想简历，弥合需求-能力格式鸿沟
- **RUM（Runner-Up Hard-Negative Mining）**：取 3%-4% 百分位结果作困难负样本
- Recall 从 65.13% 提升到 **84.44%**（超过 OpenAI text-embedding-3-large）
- **关键启示**：互补匹配 SOTA 仍是 bi-encoder + 对比学习 + 数据增强，没人做 binary/compact representation

#### C4. AC3MH — 非对称互补流形哈希

**[AC3MH (2025)](https://www.sciencedirect.com/science/article/abs/pii/S0950705125017666)**

- 多视图 + 非对称 + 哈希的罕见结合
- 通过 autoencoder 探索特征语义和标签语义的互补关系

### 方向 D：紧凑多关系表示可行性

#### D1. Binary Quantization 精度数据

| 模型 | Float32 NDCG@10 | Binary | 保留率 |
|------|----------------|--------|--------|
| mxbai-embed-large (1024d) | 54.39 | 52.46 | **96.45%** |
| all-MiniLM-L6-v2 (384d) | 41.66 | 39.07 | **93.79%** |
| Cohere-embed-v3 (1024d) | 55.0 | 52.3 | **94.6%** |
| e5-base-v2 (768d) | 50.77 | 37.96 | **74.77%** |

**关键**：rescoring 从 92.53% 恢复到 96.45%。Binary 比 float32 节省 **32x 存储**，检索加速 **15-45x**。

#### D2. QAMA — 量化感知 Matryoshka

**[QAMA (CIKM 2025)](https://dl.acm.org/doi/10.1145/3746252.3761077)**

支持 0.5-bit 到 2-bit 量化，Hybrid Quantization 自适应分配精度给信息量大的维度。

#### D3. BSC 容量限制

**n_max ≈ 0.03 * d**：维度 10000 时最多 bundling ~250 项。BSC 噪声地板 0.5（随机二进制向量的期望 Hamming 相似度），限制有效容量。

#### D4. 200 bytes 预算方案

| 方案 | 分配 | 优缺点 |
|------|------|--------|
| 3 x 512 bits = 192B | 每种关系独立向量 | 最直接，需三次编码 |
| 1024 + 512 bits = 192B | 共振大，互补/干涉共享 | 非对称分配 |
| 1600 bits 单向量 + 关系矩阵 | GHRR 式变换 | 需 GHRR 兼容 BSC（目前不行）|

### 方向 E：最小可行实验设计

#### E1. 标注需求

| 方案 | 标注量 | 时间 |
|------|--------|------|
| 指令感知 baseline | **0** | 1 天 |
| Dual Embedding IN-OUT | **0**（需协商共现数据） | 1 天 |
| 二阶段检索 + 关系分类 | 150+ 对 | 3+ 天 |
| 稳定可靠的关系分类器 | 600-900 对 | 数周 |

#### E2. 推荐实验顺序

```
实验 1（0 标注，1 天）：指令感知 baseline
  - INSTRUCTOR 或 Qwen3-Embedding-0.6B
  - 三条指令分别编码相同文本对
  - 人工检查 top-10 结果是否对应不同关系类型

实验 2（0 标注，1 天）：Dual Embedding baseline
  - Word2Vec/FastText 在协商数据上训练
  - IN 距离 = 共振，IN-OUT 距离 = 互补

实验 3（150+ 标注，3+ 天）：二阶段 baseline
  - 粗筛: sentence-transformer + cosine
  - 分类: cross-encoder 做 3-way 关系分类
```

## 优先级排序（第二轮结论）

### 综合对比

| 方向 | 技术成熟度 | 标注需求 | 与通爻匹配度 | 紧凑表示可行性 |
|------|-----------|---------|-------------|---------------|
| A: GHRR | 低（仅KG验证，不兼容BSC） | 0 | 中 | 差 |
| **B: 指令感知** | **高（多模型成熟）** | **0** | **高** | 差（大浮点向量） |
| C: IN-OUT | 中（电商验证） | 需共现数据 | **高** | 中 |
| D: 紧凑多关系 | 低 | 0 | 中 | **高** |
| E: 实验设计 | **高** | 0-150 | **高** | — |

### 推荐路线

**第一步（验证核心假设）：方向 B — 指令感知 Embedding**

理由：
1. 零标注、零训练、一天出结果
2. **验证最高杠杆假设**："不同指令能否区分共振/互补/干涉"
3. INSTRUCTOR 已证明指令重组 embedding 几何，但仅在显式属性上
4. 结果直接指导后续路线：
   - 指令有效 → 指令 embedding + MRL + BQL → 512 bits x 3 = 192 bytes
   - 部分有效（共振好，互补差）→ 共振用指令 embedding，互补用 HyRe 思路
   - 指令无效 → 转向 IN-OUT Dual Embedding 或多空间方案

**第二步：方向 C — IN-OUT Dual Embedding**

IN-OUT 机制自然地在同一模型中产生两种度量（相似性 + 互补性），不需要多次编码。需要协商共现数据训练 SGNS。

**第三步：方向 D+A 结合**

BSC + 置换矩阵变换（替代 GHRR 的复数酉矩阵）。512-bit BSC 可 bundling ~15 组件，足够编码一个意图的多维度。

## 关键风险

1. GHRR 只在 KG 上验证，且与 BSC 不兼容 — **排除为短期方向**
2. 指令感知 embedding 对"互补"等隐式关系的引导效果未经验证
3. IN-OUT 需要充足的共现数据（我们的协商数据是否足够？）
4. 三种关系的清晰定义和标注一致性（人类标注者能否一致区分？）

## 参考文献

### GHRR & HDC
- [GHRR (2024)](https://arxiv.org/abs/2405.09689)
- [PathHD (2025)](https://arxiv.org/abs/2512.09369)
- [VSA Open Source Info Discovery (2024)](https://arxiv.org/html/2408.10734)
- [HDC Text Vectorization (ICNLSP 2025)](https://aclanthology.org/2025.icnlsp-1.4/)
- [HyperSum (2024)](https://arxiv.org/html/2405.09765)
- [BSC Capacity](https://twistient.github.io/HoloVec/models/bsc/)

### 指令感知 Embedding
- [INSTRUCTOR (ACL 2023)](https://instructor-embedding.github.io/)
- [GSTransform (2025)](https://arxiv.org/html/2505.24754v1)
- [Qwen3-Embedding (2025)](https://qwenlm.github.io/blog/qwen3-embedding/)
- [MOEE (ICLR 2025 Oral)](https://github.com/tianyi-lab/MoE-Embedding)

### 互补/替代关系
- [DecGCN (CIKM 2020)](https://dl.acm.org/doi/10.1145/3340531.3412695)
- [DHGAN (CIKM 2022)](https://dl.acm.org/doi/10.1145/3511808.3557281)
- [Dual Embeddings IN-OUT (2022)](https://arxiv.org/abs/2211.14982)
- [ConFit v2 (ACL Findings 2025)](https://arxiv.org/html/2502.12361v2)
- [AC3MH (2025)](https://www.sciencedirect.com/science/article/abs/pii/S0950705125017666)
- [AsymmeTrix (2025)](https://yoheinakajima.com/asymmetrix-asymmetric-vector-embeddings-for-directional-similarity-search/)

### 紧凑/量化表示
- [Embedding Quantization (HuggingFace 2024)](https://huggingface.co/blog/embedding-quantization)
- [QAMA (CIKM 2025)](https://dl.acm.org/doi/10.1145/3746252.3761077)
- [MatQuant (Google DeepMind 2025)](https://arxiv.org/abs/2502.06786)
- [Binarized KG Embeddings (2019)](https://arxiv.org/abs/1902.02970)
- [MRL (NeurIPS 2022)](https://arxiv.org/abs/2205.13147)
- [Binary MRL (mixedbread.ai)](https://www.mixedbread.com/blog/binary-mrl)
- [MRL+BQL (Vespa)](https://blog.vespa.ai/combining-matryoshka-with-binary-quantization-using-embedder/)

### 知识图谱多关系
- [RotatE](https://arxiv.org/abs/1902.10197)
- [SectorE (2025)](https://arxiv.org/abs/2506.11099)
- [TransERR (LREC 2024)](https://aclanthology.org/2024.lrec-main.1303/)

### 其他
- [Few-shot Relation Classification](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00392/106791)
- [DHCF (KBS 2023)](https://www.sciencedirect.com/science/article/pii/S0950705123001223)
