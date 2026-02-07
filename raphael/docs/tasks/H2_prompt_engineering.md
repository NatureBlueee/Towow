# H2 -- Prompt 工程研究

> 创建日期：2026-02-07
> 状态：PRD 已细化
> 优先级：Tier 1（产品线）
> 依赖：无硬依赖，可立即启动
> 阻塞：LLM 调用质量提升（独立路径）

---

## 为什么做这件事

通爻网络的协商流程中有 6 个 LLM 调用点（Skill），它们直接决定了用户感知到的系统质量。一个 Offer 写得好不好、方案聚合得合不合理、发现性对话能不能真正激发隐藏价值——这些全由 Prompt 的设计水平决定。

当前的 Prompt 是"先写着用"的 V1 草案（见架构文档 Section 9.4-9.9），存在以下问题：

1. **指令笼统**：比如"想想意想不到的价值"——LLM 不知道怎么"想"，需要更具体的引导结构（chain-of-thought、元认知提示）。
2. **缺乏评估基准**：不知道什么是"好的 Offer"、什么是"好的方案"，无法系统地比较和改进。
3. **第一提案偏见未在 Prompt 层缓解**：架构设计原则 0.5 指出代码层通过等待屏障和观察遮蔽结构性消除偏见，但 Prompt 层还可以进一步配合（如反锚定提示、随机化呈现顺序指令）。
4. **场景适配缺失**：同一套 Prompt 对"找技术合伙人"和"组黑客松团队"的效果可能截然不同，缺乏场景化适配策略。

**核心约束**：Prompt 改进不能替代代码保障。如果一个行为可以用状态机、屏障、遮蔽等代码机制保障，就不应该依赖 Prompt 保障。Prompt 的职责是"提供智能"——让 LLM 更好地理解角色、生成更丰富的内容、做出更有洞察力的判断。

---

## 你要回答什么问题

**总问题**：如何系统地设计和优化通爻 6 个 Skill 的 Prompt，使每个 LLM 调用点产出质量最大化，同时严守"代码保障 > Prompt 保障"的原则？

具体子问题：

1. 当前 6 个 Skill 的 V1 Prompt 各有什么优点和不足？哪些不足属于 Prompt 层可以改进的，哪些应该交给代码层？
2. 怎么定义"好的 Offer"、"好的方案"、"好的发现性对话"？能否建立可量化或可对比的评估基准？
3. 什么 Prompt 设计模式（CoT、元认知、persona、few-shot、结构化输出）在什么场景下效果最好？
4. 如何在 Prompt 层配合代码层，进一步缓解第一提案偏见？
5. 不同场景（招技术合伙人 vs 组黑客松团队 vs 其他）是否需要不同的 Prompt 变体？差异有多大？
6. 优化后的 Prompt 是否真的比 V1 更好？改进幅度有多大？

---

## 我们提供什么

### 设计原则

| # | 原则 | 与 H2 的关系 |
|---|------|-------------|
| 0.5 | 代码保障 > Prompt 保障 | **核心约束**：确定性逻辑交给代码（等待屏障、轮次计数、观察遮蔽、状态机），Prompt 只负责需要智能的部分 |
| 0.6 | 需求 != 要求 | DemandFormulationSkill 的核心指导：区分张力（真正需要什么）和假设性解法（以为怎么满足） |
| 0.8 | 投影是基本操作 | 每个 Skill 本质上都是一次投影：丰富的输入通过 Prompt 透镜变成聚焦的输出 |

### 6 个 Skill 的接口定义（架构文档 Section 9.3-9.9）

每个 Skill 都有稳定的接口层（角色、职责、输入、输出、原则、约束、调用时机）和可进化的实现层（具体 Prompt）。以下是摘要：

| Skill | 类型 | 角色定位 | 输入 | 输出 | 核心原则 |
|-------|------|---------|------|------|---------|
| **DemandFormulationSkill** | 可定制 | 用户真实需求的理解者和表达者 | 用户原始意图 + Profile Data | 丰富化后的需求文本 | 理解"要求"背后的"需求"；补充而非替换；丰富化程度由用户控制 |
| **ReflectionSelectorSkill** | 可定制 | Agent 画像的投影执行者 | ProfileDataSource + 透镜参数 | HDC 超向量画像 | 反映真实能力，不美化；投影是无状态函数 |
| **OfferGenerationSkill** | 可定制 | Agent 在协商中的发言人 | 需求文本 + Agent Profile Data | Offer（能贡献什么、相关经历） | 只描述 Profile 中记录的；说清相关性；元认知：意想不到的价值 |
| **CenterCoordinatorSkill** | 统一 | 多方资源综合规划者 | 需求文本 + 所有 Offer + 历史（遮蔽格式） | 结构化决策（plan/contract/need_more_info/trigger_p2p/has_gap） | 满足需求 > 通过率 > 效率；考虑互补性和意外组合；反锚定 |
| **SubNegotiationSkill** | 统一 | 双方隐藏价值的发现者 | 触发原因 + A的Offer和Profile + B的Offer和Profile | 发现报告（新关联、协调方案、额外贡献） | 发现未说出的价值，不裁决对错；关注 Profile 中 Offer 未涉及的部分 |
| **GapRecursionSkill** | 统一 | 缺口到子需求的转换器 | 缺口描述 + 父需求 context | 子需求文本（进入递归） | 子需求比父需求更具体；自包含；保留足够上下文 |

**注意**：ReflectionSelectorSkill 的核心逻辑是 HDC 编码（计算密集型），不涉及 LLM 调用。H2 聚焦的是其他 5 个需要 LLM 的 Skill，但可以分析 ReflectionSelectorSkill 中"特征文本提取"是否需要 LLM 辅助。

### 已有 Prompt 草案

每个 Skill 的 V1 Prompt 见架构文档 Section 9.4-9.9 的"V1 Prompt 草案"部分。此外：

- **Team Matcher 的 Prompt**（`requirement_demo/web/team_prompts.py`）：已投入使用的团队组合 Prompt，可作为"真实场景下 Prompt 如何运作"的参考。它定义了团队组合顾问角色、三种方案理念（快速验证/技术深度/跨域创新）、结构化 JSON 输出格式。
- **团队组合引擎**（`requirement_demo/web/team_composition_engine.py`）：展示了"代码保障 + LLM 创造性"的协作模式——算法做评分和组合，LLM 做创意方案生成。

### 演示场景数据

- **"找技术合伙人"场景**（`requirement_demo/web/demo_scenario.json`）：完整的 7 Agent 协商脚本，展示认知转变（"技术合伙人" -> "快速验证能力"）、意外发现（Notion 模板用户的真实需求）、协商创造（方案在协商前不存在）。
- 这个场景可作为 Prompt 评估的"黄金标准用例"——好的 Prompt 应该能引导 LLM 产出类似质量的协商过程。

### 研究支撑（架构文档 Section 9.2）

| 研究发现 | 来源 | 对 Prompt 设计的启示 |
|---------|------|---------------------|
| LLM 有严重的第一提案偏见（10-30x） | Microsoft Magentic Marketplace, 2025 | 代码层用等待屏障消除；Prompt 层用反锚定提示配合 |
| 多轮迭代平均效果 -3.5%，错误放大 4.4x | Google DeepMind, 2025 | 限制协商轮次为最多 2 轮（代码控制），Prompt 中不鼓励"继续讨论" |
| Proposer -> Aggregator 是最优架构 | Mixture-of-Agents, 2024 | OfferGeneration = Proposer，CenterCoordinator = Aggregator |
| persona + metacognition 产生集体智能 | Emergent Coordination, 2025 | 每个 Skill 的 Prompt 需要明确 persona 和元认知提示 |
| 观察遮蔽比摘要更好，成本低 50% | JetBrains Research, 2025 | CenterCoordinator 第 2 轮用遮蔽而非摘要 |

### SkillPolisher 机制（架构文档 Section 9.10）

架构已定义了 Skill 优化的工作流程和约束：

- SkillPolisher 只能优化实现层（Prompt），不能改变接口层（角色、职责、输入、输出）
- 优化维度：prompt 用词和结构、CoT 引导、模型适配、边界条件、few-shot 示例、场景模板
- 验证方式：A/B 测试

---

## 子任务分解

### H2.1 -- 现状梳理与边界划定

**描述**：系统分析 6 个 Skill 的 V1 Prompt，评估每个 Prompt 的优点、不足和改进空间。关键产出是**边界划定**：哪些问题属于 Prompt 层可以改进的，哪些应该交给代码层（严守原则 0.5）。

**依赖**：无

**交付物**：
- 6 个 Skill 的 Prompt 分析卡（每个包含：当前 Prompt 原文、角色清晰度评分、指令具体性评分、元认知引导评分、结构化输出评分、已发现的问题清单）
- 边界划定表：每个已发现问题标注"Prompt 层解决"或"代码层解决"或"双层配合"
- Team Matcher 现有 Prompt 的对比分析（它已在实际使用中，有什么经验可以复用？）

### H2.2 -- 评估基准设计

**描述**：为 Prompt 优化建立可对比的评估基准。没有评估基准，优化就是"感觉更好了"，不是"证明更好了"。

**依赖**：H2.1（需要知道评估什么维度）

**交付物**：
- **评估维度定义**：每个 Skill 的"好"意味着什么（可量化或可对比的标准）
  - DemandFormulation：丰富化程度（补充了多少有用上下文）、保留度（是否保留了用户原始意图）、区分度（是否区分了需求和要求）
  - OfferGeneration：事实准确性（是否只描述 Profile 中的内容）、相关性覆盖（是否涵盖了相关能力）、元认知深度（是否发现了意想不到的价值）
  - CenterCoordinator：方案质量（是否满足需求、各方通过率、效率）、组合创意（是否发现了互补和意外组合）、结构化输出合规率
  - SubNegotiation：发现密度（是否发现了 Offer 未涉及的关联）、可操作性（发现是否可落地）
  - GapRecursion：子需求质量（是否比父需求更具体）、自包含性（是否可独立理解）
- **测试用例集**：至少 5 个不同场景的输入（含"找技术合伙人"黄金标准），用于 A/B 对比
- **评估方法**：人工评估模板 + 可选的 LLM 辅助评估方案

### H2.3 -- 用户侧 Skill 优化（DemandFormulation + OfferGeneration）

**描述**：优先优化用户直接感知的两个 Skill。DemandFormulation 决定了需求的质量（影响后续所有环节），OfferGeneration 决定了每个 Agent 响应的质量（影响方案聚合）。

**依赖**：H2.1 + H2.2（需要知道改什么、怎么判断更好）

**交付物**：
- DemandFormulationSkill 优化后的 Prompt（V2）
  - 重点：如何引导 LLM 区分"需求"和"要求"（原则 0.6）
  - 重点：丰富化的深度控制（保守 vs 开放的平衡点）
  - 重点：不同类型需求（技术/情感/资源）的不同丰富化策略
- OfferGenerationSkill 优化后的 Prompt（V2）
  - 重点：元认知提示的具体化（不是"想想意想不到的价值"，而是具体的思考步骤）
  - 重点：防止捏造的 Prompt 层保障（配合代码层的信息源限制）
  - 重点：不同类型 Agent（人 vs Bot vs 工具）的 Prompt 差异
- 两个 Skill 的 V1 vs V2 对比测试结果（使用 H2.2 的评估基准）

### H2.4 -- CenterCoordinator 优化

**描述**：CenterCoordinator 是聚合逻辑最复杂的 Skill——它需要综合所有 Offer、考虑互补性、做出结构化决策（5 种输出类型）、处理历史遮蔽。这个 Skill 的 Prompt 质量直接决定最终方案的质量。

**依赖**：H2.1 + H2.2 + H2.3（需要有优质的 Offer 输入才能测试 Center 的聚合质量）

**交付物**：
- CenterCoordinatorSkill 优化后的 Prompt（V2）
  - 重点：决策原则的具体化（"满足需求 > 通过率 > 效率"如何具体引导推理？）
  - 重点：5 种输出类型（plan/contract/need_more_info/trigger_p2p/has_gap）的判断标准在 Prompt 中如何清晰表达
  - 重点：元认知提示——如何让 LLM 真正考虑"互补性"和"意外组合"，而不是只做表面匹配
  - 重点：观察遮蔽格式的 Prompt 适配（第 2 轮如何让 LLM 正确理解遮蔽后的输入）
  - 重点：反锚定——如何在 Prompt 层配合代码层消除第一提案偏见
- V1 vs V2 对比测试结果
- 边界条件测试：空 Offer、单一 Offer、大量 Offer（10+）时的表现

### H2.5 -- SubNegotiation + GapRecursion 优化

**描述**：优化剩余两个统一 Skill。SubNegotiation 是发现性对话的核心，GapRecursion 是递归机制的触发器。两者使用频率低于 DemandFormulation/OfferGeneration/CenterCoordinator，但对系统的"发现未知价值"能力至关重要。

**依赖**：H2.1 + H2.2

**交付物**：
- SubNegotiationSkill 优化后的 Prompt（V2）
  - 重点：如何引导 LLM 发现 Profile 和 Offer 之间的"差异"（未说出的部分）
  - 重点：冲突解决 vs 互补发现的不同引导策略
  - 重点：确保输出是"发现报告"而非"裁决书"
- GapRecursionSkill 优化后的 Prompt（V2）
  - 重点：子需求的抽象程度控制（太具体限制响应范围，太抽象失去精准度）
  - 重点：自包含性和上下文保留的平衡
- V1 vs V2 对比测试结果

### H2.6 -- 第一提案偏见缓解策略

**描述**：第一提案偏见（first-proposal bias）是通爻系统需要对抗的结构性问题。架构设计已在代码层做了三重保障（等待屏障、观察遮蔽、轮次限制），本子任务研究 Prompt 层的配合策略，以及验证代码层 + Prompt 层组合方案的实际效果。

**依赖**：H2.4（需要 CenterCoordinator 的优化 Prompt 作为基础）

**交付物**：
- **偏见分析报告**：在通爻的具体场景中，第一提案偏见如何表现？（用测试用例复现）
- **代码层保障清单**（梳理已有的）：
  - 等待屏障：所有 Offer 到齐后才调用 Center（消除时序偏见）
  - 观察遮蔽：第 2 轮遮蔽原始 Offer，只保留推理和决策（消除锚定效应）
  - 轮次限制：最多 2 轮（避免错误放大）
- **Prompt 层配合策略**（新增的）：
  - 反锚定提示：在 CenterCoordinator 的 Prompt 中加入"不要因为某个 Offer 排在前面就给予更高权重"
  - 随机化顺序指令：是否在 Prompt 中告知 LLM "以下 Offer 的顺序是随机的"能有效缓解偏见？
  - 强制对比：是否要求 LLM "先分别评价每个 Offer，再综合比较"比直接"综合所有 Offer"效果更好？
  - 其他可能的 Prompt 层策略
- **组合方案验证**：代码层保障 + Prompt 层策略的联合效果（A/B 测试）

### H2.7 -- Prompt 设计模式总结

**描述**：从 H2.1-H2.6 的实践中提炼 Prompt 设计模式，形成可复用的知识。这个产出的架构韧性极高——即使具体 Prompt 随场景变化，模式本身是永久资产。

**依赖**：H2.3 + H2.4 + H2.5 + H2.6（需要足够多的实践经验）

**交付物**：
- **Prompt 设计模式手册**（3000-5000 字），至少包含：
  - 模式 1：角色定义模式（什么样的 persona 描述最有效？）
  - 模式 2：元认知引导模式（如何让 LLM "思考自己的思考"？）
  - 模式 3：结构化输出模式（如何让 LLM 稳定输出特定格式？）
  - 模式 4：事实约束模式（如何限制 LLM 只使用给定信息？）
  - 模式 5：发现性提示模式（如何引导 LLM 发现非显然关联？）
  - 模式 6：反偏见模式（如何在 Prompt 层对抗 LLM 的结构性偏见？）
  - 每个模式包含：适用场景、Prompt 模板、正例/反例、在通爻中的具体应用
- **"代码保障 vs Prompt 保障"决策树**：给未来的 Skill 设计者一个清晰的判断工具——这个行为应该用代码保障还是 Prompt 保障？

---

## 做完了是什么样

1. **6 个 Skill 都有 V2 Prompt**，每个 V2 都经过 A/B 测试验证优于 V1
2. **有可复用的评估基准**，未来的 Prompt 迭代可以客观对比
3. **有 Prompt 设计模式手册**，未来新增 Skill 或新场景时可以直接参考
4. **第一提案偏见有代码层 + Prompt 层的双重缓解方案**，且经过验证
5. **明确了"代码保障 vs Prompt 保障"的边界**，避免把确定性逻辑交给 Prompt

**产出格式**：
- 分析报告和模式手册：Markdown 文档
- 测试用例和对比数据：Jupyter Notebook 或 Markdown 表格
- 优化后的 Prompt：直接在报告中给出完整文本，可以直接复制使用
- 所有产出提交到 `raphael/research/H2_prompt_engineering/` 目录

**产出规模**：
- 每个子任务（H2.1-H2.7）各一份文档
- 总计约 15,000-25,000 字（含 Prompt 原文、分析、测试结果）
- 测试用例集至少覆盖 5 个不同场景

---

## 你必须遵守的

### 硬性约束

1. **代码保障 > Prompt 保障**（原则 0.5）：如果一个行为可以用状态机、屏障、遮蔽等代码机制保障，就不应该用 Prompt 保障。在分析中必须明确标注哪些问题属于代码层、哪些属于 Prompt 层。

2. **不改变 Skill 的接口定义**（SkillPolisher 约束）：你只能优化 Prompt 实现，不能改变 Skill 的角色、职责、输入、输出定义。如果你认为接口需要调整，请在报告中标注为"架构建议"，由架构师决定。

3. **所有优化必须有对比数据**：不接受"我觉得更好了"的结论。每个 V2 Prompt 必须与 V1 在相同测试用例上对比，给出可观察的差异。

4. **中文优先**：测试用例和 Prompt 模板以中文为主。通爻是中文优先的系统。

5. **遵守架构研究结论**：
   - 多轮迭代效果为负（DeepMind 2025）→ 不要设计鼓励多轮的 Prompt
   - 等待屏障消除时序偏见（代码层）→ Prompt 层不需要重复这个保障
   - 观察遮蔽优于摘要（JetBrains 2025）→ CenterCoordinator 第 2 轮的历史格式已确定为遮蔽，Prompt 需要适配这个格式

### 与通爻设计原则的对齐

- DemandFormulationSkill 必须体现"需求 != 要求"（原则 0.6）
- OfferGenerationSkill 必须防止 LLM 捏造 Profile 中不存在的能力
- CenterCoordinatorSkill 必须考虑互补性和意外组合（协商的核心价值是 context 多样性）
- SubNegotiationSkill 是"发现性对话"，不是辩论——必须区分这两者
- GapRecursionSkill 的子需求必须自包含（分形结构的要求）

---

## 你可以自己决定的

### 方法选择
- 用什么 Prompt 工程框架或方法论（CoT、ReAct、few-shot、zero-shot、等等）
- 用什么 LLM 做测试（Claude、GPT、开源模型均可，但请记录模型版本）
- 评估基准的具体量化方式（评分制、排名制、通过/不通过、等等）

### 范围调整
- 如果发现某个 Skill 的 V1 Prompt 已经足够好，可以跳过其 V2 优化，在报告中说明原因
- 如果发现某个 Skill 的问题本质上是接口层的（不是 Prompt 层能解决的），可以标注为"架构建议"而不是强行用 Prompt 修补
- 子任务的顺序可以根据实际发现调整（但 H2.1/H2.2 必须在 H2.3-H2.6 之前）

### 工具使用
- 可以使用任何 Prompt 测试工具或框架
- 可以构造自己的测试数据（不限于演示场景）
- 可以参考外部 Prompt 工程最佳实践（请标注来源）

### 额外发现
- 如果在优化过程中发现了新的设计问题（如某个 Skill 的接口定义不合理），请记录为"附录：发现与建议"
- 如果发现了架构文档中未提及的 LLM 偏见或问题，同样记录

---

## 对接方式

### 提交位置
`raphael/research/H2_prompt_engineering/`

建议目录结构：
```
H2_prompt_engineering/
  H2.1_current_analysis.md        -- 现状梳理与边界划定
  H2.2_evaluation_framework.md    -- 评估基准设计
  H2.3_user_skills_optimization.md -- 用户侧 Skill 优化
  H2.4_center_coordinator.md      -- CenterCoordinator 优化
  H2.5_sub_gap_optimization.md    -- SubNegotiation + GapRecursion 优化
  H2.6_first_proposal_bias.md     -- 第一提案偏见缓解
  H2.7_design_patterns.md         -- Prompt 设计模式总结
  test_cases/                     -- 测试用例集
  appendix/                       -- 附录（额外发现、架构建议等）
```

### 有问题找谁
- Prompt 设计方向：自行判断，参考架构文档 Section 9 的接口定义和优化方向提示
- 架构约束和设计原则：创始人 / Arch Skill
- 代码层实现细节：Dev Skill

### 建议节奏
- H2.1 + H2.2：第 1 周（打基础，建评估体系）
- H2.3 + H2.4：第 2 周（核心 Skill 优化）
- H2.5 + H2.6：第 3 周（剩余 Skill + 偏见缓解）
- H2.7：第 3 周末（总结提炼）
- 总计：约 3 周

### 后续依赖
- H2 的产出（V2 Prompt + 设计模式）直接用于 SkillPolisher 的持续优化流程
- 评估基准可被 H4（最小验证实验设计）复用
- 第一提案偏见的发现可能影响代码层设计（反馈给架构师）

---

*本文档由 Task Arch Skill 生成。*
*关联文档：`docs/ARCHITECTURE_DESIGN.md` Section 9、`docs/CONTRIBUTION_TASK_CATALOG.md` H2 条目、`.claude/skills/task-arch/SKILL.md`*
