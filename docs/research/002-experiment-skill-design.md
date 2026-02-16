# 研究 002：实验技能设计

**日期**: 2026-02-16
**状态**: 完成（第一轮）
**关联**: Genome v0.3 §10, ADR-011, 研究 001

## 研究问题

如何设计一个实验技能（Experiment Skill），让 AI Agent 能科学地运行 Intent Field 的编码实验？

关键约束：
- 实验对象：text → vector → binary → match 管道
- 实验变量：编码模型、维度、量化方式、切分策略、匹配算法
- 评估难点：需同时评估共振/互补/干涉三种关系，不是单一准确率
- 当前数据：仅 20-26 条测试查询，pass/fail 判断

## AI 实验 Agent 框架调研

### AI Scientist v2 (Sakana AI, 2025.04)

- **核心创新**：最佳优先树搜索（BFTS），不是线性管道
- **三阶段**：初始代码生成 → 超参数调优 → 消融实验
- **失败处理**：buggy node 自动触发调试分支，并行探索使单分支失败不中断
- **已知限制**：成功率低于 v1（v1 依赖人工模板），成本 ~$15-20/run，难以产生真正新颖的假设
- **可借鉴**：树搜索架构适合编码实验（先定模型 → 再调参 → 再消融）
- **不需要**：论文生成管线（过重）

### AIDE (Weco AI, 2025.02) — 最直接可用

- **核心**：把 ML 实验建模为代码空间中的树搜索
- **MLE-Bench 上**：赢得奖牌数是线性 agent (OpenHands) 的 4 倍
- **50% 任务**超过人类中位参与者
- **可直接使用**：指定数据集 + 自然语言目标 + 评估指标，自动生成、运行、评估、迭代

### Agent Laboratory (EMNLP 2025)

- **三阶段**：Literature Review → Experimentation → Report Writing
- **Human-in-the-loop**：每阶段可提供反馈引导方向
- **关键数据**：纯自动 21% 成功率，人类辅助 64%
- **可借鉴**：human-in-the-loop 设计（三种关系需要人类定义评估标准）

### MLAgentBench (Stanford SNAP) — 失败模式手册

6 种已知失败模式（直接指导防护设计）：

| 失败模式 | 描述 | 防护措施 |
|----------|------|---------|
| 幻觉改进 | 声称性能提升但未执行代码 | 强制执行后才能报告 |
| 规格敏感 | 问题描述不明确 | 显式定义评估文件和指标 |
| 静默失败 | try-except 吞掉错误 | 禁用静默异常处理 |
| 资源耗尽 | 复制大文件导致失败 | 预设资源限制 |
| 选择保守 | ~50% 使用随机森林 | 明确要求探索多种方案 |
| 环境卡死 | 不必要的环境创建 | 预置好环境 |

### MLE-bench (OpenAI, ICLR 2025)

- 75 个 Kaggle ML 竞赛，pass@1 16.9%，pass@8 34.1%
- **关键启发**：多次尝试大幅提升成功率 → 实验 Skill 应内置"多次运行+选最优"

### AgentRxiv (2025.03)

- 多 Agent 通过共享预印本服务器协作
- 协作 vs 孤立：70.2% → 78.2%（MATH-500）
- **可借鉴**：实验 Skill 应维护实验档案，后续实验参考前序发现

## 评估方法研究

### MTEB 的局限（与我们相关的）

1. **cosine similarity 万能假设** — 所有任务统一使用余弦相似度，不适合互补关系
2. **无关系类型区分** — MTEB 不区分相似性的类型
3. **无通用最佳模型** — 没有单一方法在所有任务上最优

**结论**：MTEB 排名不能直接推导我们场景的最优模型。

### 不存在"互补关系匹配" benchmark

搜索确认：目前没有标准 benchmark 评估 need-capability matching。最接近的：
- **RelBERT** (2025) — 词汇关系 embedding
- **互补产品推荐** — PMSC, DecGCN（两个独立空间建模替代性和互补性）
- **语义匹配能量函数** — 多关系图嵌入到连续向量空间

**结论**：必须自建评估框架。

### 小样本统计方法

核心论文：**"When +1% Is Not Enough"** (2025.11)

针对 20-26 条查询的建议：
1. 始终报告 **delta（差异值）**，不是绝对值
2. 利用**配对设计**：基线和变体在相同种子和数据划分下运行
3. 使用 **BCa bootstrap 置信区间 + sign-flip 排列检验**
4. 每个配置运行 **3-5 个种子**
5. LLM **释义扩增**测试集到 100+ 条（保留原始 20-26 条作为金标准）

### 三种关系的评估设计

```
评估维度          评估方法                         指标
───────────────────────────────────────────────────
共振 (Resonance)  语义相似度 (STS 类)              Spearman@top-k
                  检索排序                          nDCG@10, MAP

互补 (Complement) 需求-能力匹配                    Precision@k
                  关系分类 (是否互补)               F1
                  对称性检验 (A需B ≠ B需A)         方向性准确率

干涉 (Interfere)  跨域关联检测                     Recall@threshold
                  深层语义桥接                      Bridge accuracy
───────────────────────────────────────────────────
聚合             Optuna 三目标 Pareto 前沿          Pareto front 大小
                 加权综合分                         Weighted score
```

## 工具栈推荐

### 推荐（轻量级组合）

| 工具 | 用途 | 优先级 |
|-----|------|--------|
| **Optuna** | 三目标超参搜索 + Pareto 可视化 | P0 |
| **Hydra + OmegaConf** | 实验配置管理 + 多运行扫描 | P0 |
| **配对 Bootstrap** | 小样本统计检验 | P0 |
| **JSON/SQLite** | 实验结果追踪 | P0 |
| **AIDE** | 代码空间树搜索（需更深探索时） | P1 |
| **W&B** | 嵌入空间交互可视化（需要时再接） | P2 |

### 不推荐

- AI Scientist v2 完整系统（过重）
- Agent Laboratory 完整系统（文献综述阶段不需要）
- Ray Tune（规模不需要分布式）
- MLflow / Neptune（过重，我们不需要完整 MLOps）

## 实验 Skill 概念架构

```
┌─────────────────────────────────────────────┐
│          Experiment Manager (编排层)           │
│  - 渐进式实验管理（参照 AI Scientist v2 树搜索）  │
│  - 实验档案维护（参照 AgentRxiv 累积知识）        │
│  - Human-in-the-loop 检查点（参照 Agent Lab）    │
├─────────────────────────────────────────────┤
│          Search Strategy (搜索层)              │
│  - Optuna 多目标优化（三维 Pareto 前沿）          │
│  - 树搜索探索（参照 AIDE）                       │
│  - 防幻觉：必须执行后才能报告（MLAgentBench 教训） │
├─────────────────────────────────────────────┤
│          Evaluation Framework (评估层)          │
│  - 三种关系类型独立评估器                         │
│  - 配对 bootstrap 统计检验                      │
│  - 查询释义扩增（PTEB 思路）                     │
├─────────────────────────────────────────────┤
│          Infrastructure (基础设施层)             │
│  - Hydra + OmegaConf 配置管理                   │
│  - JSON/SQLite 实验追踪                         │
│  - 可复现性保障（种子、环境、数据版本）              │
└─────────────────────────────────────────────┘
```

## 可复现性检查清单

| 实践 | 工具/方法 | 优先级 |
|-----|----------|--------|
| 固定所有随机种子 | random, numpy, torch seed | P0 |
| 配对实验设计 | 相同 seed + 相同数据划分 | P0 |
| 记录配置快照 | Hydra auto-save | P0 |
| 多种子运行 | 至少 3 个种子，报告均值+标准误 | P0 |
| 环境锁定 | requirements.txt 或 Docker | P1 |
| 数据版本控制 | DVC 或 Git LFS | P1 |
| 自动生成实验报告 | Jinja2 + Markdown | P2 |

## 参考文献

- [AI Scientist v2 (Sakana AI, 2025)](https://arxiv.org/abs/2504.08066)
- [AIDE (Weco AI, 2025)](https://arxiv.org/abs/2502.13138)
- [Agent Laboratory (EMNLP 2025)](https://aclanthology.org/2025.findings-emnlp.320/)
- [MLAgentBench (Stanford SNAP)](https://github.com/snap-stanford/MLAgentBench)
- [MLE-bench (OpenAI, ICLR 2025)](https://arxiv.org/abs/2410.07095)
- [AgentRxiv (2025)](https://arxiv.org/abs/2503.18102)
- [When +1% Is Not Enough (2025)](https://arxiv.org/html/2511.19794v1)
- [PTEB: Robust Embedding Evaluation (2025)](https://arxiv.org/html/2510.06730v2)
- [MMTEB (2025)](https://arxiv.org/abs/2502.13595)
- [Optuna Multi-objective](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/002_multi_objective.html)
- [Hydra Experiments](https://hydra.cc/docs/patterns/configuring_experiments/)
