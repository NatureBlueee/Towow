# 研究文档 004：模块二结晶实验计划

**日期**: 2026-02-18
**状态**: 规划中
**前置**: ADR-014, DESIGN_LOG_006 (结晶协议设计)

---

## 实验目标

不是验证"能不能做到"（肯定能做到），是验证**"怎么更好做到"**。

具体要回答的问题：

0. **Formulation 能否从 Profile 中提取出原始意图没有说出的隐式需求？** （丰富化质量）
1. **催化 prompt 怎么写才能最有效地识别跨语义空间的等价表达？** （翻译质量）
2. **催化 prompt 怎么写才能优先传递对收敛影响最大的信息差？** （传输策略）
3. **端侧 prompt 怎么写才能让不同能力的 Agent 都产出高质量回复？** （参考模板质量）
4. **几轮能收敛？收敛信号是否可靠？** （收敛特性）
5. **方案生成的质量如何？每个人看到的分工是否合理？** （交付质量）

## 实验材料

### Profile 来源

社区共建 + 团队自写。参见 `docs/community/profile-contribution-guide.md`。

**要求**：
- 至少 3 个，目标 5-8 个
- 高异质性（不同领域、不同表达风格）
- 每人 2000-5000 字深度描述
- 跨语义空间关联——用各自领域语言描述时看不出关系，但底层互补

**存放位置**: `data/profiles/profile-{name}.md`

### 触发事件

一个具体的协作需求，产生的张力与多个参与者相关但关联方式不同。

触发事件要求：
- 真实可信（不是编的）
- 涉及多个维度的能力需求
- 不能一眼看出谁和谁匹配

## 实验序列

### Phase 0：材料准备

- [ ] 收集 3+ 个深度 Profile（社区共建 + 自写）
- [ ] 设计 1 个触发事件
- [ ] 探索 WOWOK Machine JSON 格式（为 Phase 3 准备）

### Phase 0.5：Formulation 观测

Formulation 是管道最上游——它做得不好，后面再怎么调催化都救不回来。

**观测策略**：
- 每次 RUN 先看 `formulated_demand.md`，判断：
  - 读起来像不像这个人在更完整地表达自己？
  - 有没有捕捉到 Profile 里的隐式需求？
  - 有没有编造 Profile 中不存在的信息？
  - 有没有丢掉原始意图中的关键信息？
- 如果有问题，先修 formulation prompt 再进后续迭代

**迭代策略**：
- Formulation 任务相对简单（读 Profile + 丰富化），预计 v0-v1 就能稳定
- 如果 Phase A 跑完催化已调好但端侧回复始终"偏"，回头检查 formulation
- 对比实验（如需要）：raw intent vs formulated intent，同配置跑两次

**评估维度**：
1. **信息保真** (pass/fail)：原始意图中的所有信息都保留了吗？
2. **隐式挖掘** (0-3)：从 Profile 中挖出了几个原话没提到但真实存在的需求？
3. **无编造** (pass/fail)：有没有编造 Profile 中不存在的信息？
4. **下游效果**：端侧 Agent 的回复是否与需求方的真实张力对齐？

### Phase 1：Prompt v0 + 首轮模拟

- [ ] 设计端侧参考 prompt v0
- [ ] 设计催化 prompt v0
- [ ] 手工模拟 3 人结晶（用 LLM 扮演端侧 Agent，催化 Agent 用最好的模型）
- [ ] 记录每轮：端侧回复、催化观察、人工评估笔记
- [ ] 人工评估维度：
  - 催化是否发现了跨语义连接？发现了几个？
  - 催化是否遗漏了明显的信息差？
  - 端侧回复是否有实质内容？还是空洞套话？
  - 几轮收敛？收敛时是否还有未发现的连接？
  - 过程中的"惊喜时刻"——催化指出了人都没想到的连接

### Phase 2：Prompt 迭代

- [ ] 根据 Phase 1 评估，识别 prompt 弱点
- [ ] 设计 prompt v1（针对性改进）
- [ ] 用相同的 Profile 和触发事件重跑
- [ ] 对比 v0 和 v1 的评估结果
- [ ] 继续迭代直到人工评估满意

### Phase 3：方案生成 + 格式化

- [ ] 设计方案生成 prompt（结晶收敛后，生成分工方案）
- [ ] 先自然语言版本
- [ ] 加 JSON 输出层（WOWOK Machine 格式）
- [ ] 评估方案质量：每个人的任务/收益/成本是否合理？

### Phase 4：评估自动化

- [ ] 从 Phase 1-2 的人工评估中沉淀评估原则
- [ ] 设计 LLM-as-Judge prompt
- [ ] 用人工评估结果校准 Judge
- [ ] 更大样本量验证

### Phase 5：规模测试

- [ ] 扩展到 5-8 人
- [ ] 测试催化 Agent 在更多参与者时的注意力质量
- [ ] 探索分组策略（如需要）

## 评估框架

### 人工评估（Phase 1-2）

每次 RUN 完成后，评估者回答：

0. **Formulation 质量**：formulated_demand.md 是否像这个人在完整表达自己？隐式需求挖掘了几个？有无编造？
1. **翻译质量** (1-5)：催化是否成功指出了跨语义空间的等价表达？
2. **传输完整性** (1-5)：催化是否遗漏了与张力消解相关的信息差？
3. **端侧质量** (1-5)：参与者的回复是否有实质性内容？
4. **收敛效率**：轮次数 + 收敛时是否还有未发现的重要连接
5. **方案质量** (1-5)：最终分工方案是否合理、可执行？
6. **惊喜度** (0-3)：是否有出乎意料的、有价值的发现？

### LLM-as-Judge（Phase 4+）

基于人工评估沉淀的原则设计。具体 prompt 在 Phase 4 时设计。

## 文件组织

```
tests/crystallization_poc/
  README.md                    # 实验说明
  prompts/
    formulation_v0.md          # 需求丰富化 prompt v0
    endpoint_v0.md             # 端侧 prompt v0
    catalyst_v0.md             # 催化 prompt v0
    plan_generator_v0.md       # 方案生成 prompt v0
  simulations/
    sim001_3person/            # 第一次 3 人模拟
      trigger.md               # 触发事件
      participants.md          # 参与者列表
      round_1.md               # 第一轮记录
      round_2.md               # ...
      evaluation.md            # 人工评估
      plan_output.md           # 方案输出
  results/
    summary.md                 # 实验结果汇总

data/profiles/
  profile-{name}.md            # 深度 Profile
```

## 与现有实验体系的关系

- EXP-005~008 是模块一（意向场）的实验，验证编码/压缩/多视角
- 本实验是模块二（结晶）的实验，验证催化对话机制
- 编号：从 EXP-009 开始
- 使用 towow-lab Skill 进行实验管理

## 工程探索（并行）

与实验并行推进的技术探索：

1. **WOWOK Machine JSON 格式**：了解智能合约的数据结构，为 Phase 3 的 JSON 输出做准备
2. **WOWOK SDK/MCP**：探索是否有可用的 SDK 或 MCP 服务器
3. **端侧 Agent 模拟**：用 LLM + Profile 作为 system prompt 模拟端侧 Agent
4. **催化 Agent 模型选择**：初始实验用 Claude Opus，验证模型能力上限
