# 模块二结晶实验 (Crystallization POC)

**状态**: Phase 0 — 材料准备中
**实验编号**: EXP-009 起
**前置**: EXP-005~008（模块一意向场实验）

---

## 目的

模块一（意向场）已验证。本实验验证**模块二：结晶**。

模块二解决的问题：场发现选出了参与者，但房间里的人如何发现彼此的价值？

实验目标不是验证"能不能做到"（肯定能），是验证**"怎么更好做到"**：

1. 催化 prompt 怎么写才能最有效地识别跨语义空间的等价表达？（翻译质量）
2. 催化 prompt 怎么写才能优先传递对收敛影响最大的信息差？（传输策略）
3. 端侧 prompt 怎么写才能让不同能力的 Agent 都产出高质量回复？（端侧质量）
4. 几轮能收敛？收敛信号是否可靠？（收敛特性）
5. 方案生成的质量如何？每个人看到的分工是否合理？（交付质量）

**参考文档**:
- `docs/research/004-crystallization-experiment-plan.md` — 完整实验计划
- `docs/design-logs/DESIGN_LOG_006_CRYSTALLIZATION_PROTOCOL.md` — 模块二协议设计

---

## 目录结构

```
tests/crystallization_poc/
  README.md                        # 本文件
  prompts/
    endpoint_v0.md                 # 端侧 prompt v0（待创建）
    catalyst_v0.md                 # 催化 prompt v0（待创建）
    plan_generator_v0.md           # 方案生成 prompt v0（待创建）
  simulations/
    sim001_3person/                # 第一次 3 人模拟
      participants.md              # 参与者列表（已创建，待填充）
      trigger.md                   # 触发事件（待创建）
      round_1.md                   # 第一轮记录（待创建）
      evaluation.md                # 人工评估（待创建）
      plan_output.md               # 方案输出（待创建）
  results/
    summary.md                     # 实验结果汇总
```

Profile 存放位置（与实验目录分离）：

```
data/profiles/
  profile-{name}.md               # 深度 Profile（每人 2000-5000 字）
```

---

## 如何运行实验

### Phase 0：材料准备

```bash
# 检查 Profile 是否就位
ls /Users/nature/个人项目/Towow/data/profiles/

# 手工编写触发事件
# 创建 simulations/sim001_3person/trigger.md
```

### Phase 1：首轮模拟

使用 LLM 扮演端侧 Agent（Claude Opus 扮演催化 Agent）：

1. 将 `prompts/catalyst_v0.md` 作为系统提示加载给催化 Agent
2. 将 `prompts/endpoint_v0.md` 作为参考模板发给端侧 Agent
3. 提供 `simulations/sim001_3person/trigger.md` 作为触发上下文
4. 手工逐轮记录，存入 `round_1.md`、`round_2.md`…
5. 完成后填写 `evaluation.md`

### Phase 2：Prompt 迭代

根据 Phase 1 评估，改写 prompt，重跑相同的 Profile + 触发事件，对比结果。

### Phase 3：方案生成

收敛后使用 `plan_generator_v0.md` 生成分工方案（自然语言版本优先，之后加 JSON 层）。

---

## 评估框架（6 维度）

每次模拟完成后，对照以下维度打分：

| 维度 | 描述 | 量表 |
|------|------|------|
| 翻译质量 | 催化是否成功指出了跨语义空间的等价表达 | 1–5 |
| 传输完整性 | 催化是否遗漏了与张力消解相关的信息差 | 1–5 |
| 端侧质量 | 参与者的回复是否有实质性内容（非空洞套话） | 1–5 |
| 收敛效率 | 总轮次数 + 收敛时是否还有未发现的重要连接 | 轮次数 |
| 方案质量 | 最终分工方案是否合理、可执行 | 1–5 |
| 惊喜度 | 是否出现出乎意料的、有价值的连接发现 | 0–3 |

**Phase 4+**：基于 Phase 1-2 的人工评估沉淀 LLM-as-Judge prompt，实现自动化评估。

---

## 与现有实验体系的关系

- EXP-005~008：模块一（意向场）实验，验证编码/压缩/多视角查询
- EXP-009+：模块二（结晶）实验，验证催化对话机制

模块一用数学（向量距离），模块二用对话（LLM 理解）。性质不同，工具不同。
