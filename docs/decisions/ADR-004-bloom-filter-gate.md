# ADR-004: Bloom Filter 门控 — 三层共振过滤的第一层

**日期**: 2026-02-12
**状态**: 讨论中
**关联**: ADR-001 (AgentRegistry), 架构设计 Section 6.1.3

## 背景

架构设计 Section 6.1.3 定义了三层共振过滤架构：

```
第一层：Bloom Filter 门控    (~100ns, 过滤 ~90%)  ← 本 ADR
第二层：HDC 共振检测          (~1μs,  过滤剩余 ~90%)  ← V1 已实现
第三层：深度评估（LLM/主动推理） (~10ms, 精确评估)     ← 后续版本
```

V1 只实现了第二层。现在 447 个 agent 的规模下，HDC 性能绰绰有余，但用户无法感知"层层筛选"这个核心叙事。三层漏斗不仅是性能优化——它是通爻共振机制的核心体验。

## 动机

1. **视觉叙事**：用户应该能看到"我的需求经过了多层筛选"，而不是一次性出结果
2. **不同维度的筛选**：Bloom Filter 做关键词级匹配（有/无交集），HDC 做语义级相似度——两层筛的是不同的东西
3. **用户可控**：用户可以通过滑块调整每层阈值（或预期通过人数），实时看到筛选效果
4. **架构完整性**：实现架构设计中规划的第一层，让系统真正进化

## 选项分析

### 选项 A: 真正的 Bloom Filter 实现

为每个 agent 的 skills/role/bio 建 Bloom Filter 位向量。demand 提取关键词后做 membership test。

**优势**：
- 架构上真实，不同层筛选的维度不同
- Bloom Filter 有明确的语义：关键词交集为零 = 门控淘汰
- 未来 agent 数量增长到万级时，这层有真实性能价值
- 参数（hash 函数数量、位数组大小）可以调节假阳性率

**劣势**：
- 需要关键词提取策略（从 demand 和 agent profile 提取什么关键词）
- Bloom Filter 假阳性率需要调优（太低则几乎全通过，太高则误杀）
- 实现成本比选项 B 高

### 选项 B: HDC 分数分段展示（伪三层）

单层 HDC 计算所有分数，按分数段拆成视觉上的三层。

**优势**：
- 实现极简，只改前端展示
- 不改后端逻辑

**劣势**：
- 本质是一层计算的分镜，技术人一眼看穿
- 没有不同维度的筛选语义
- 不是架构设计中规划的真实三层

## 决策

**选择选项 A：实现真正的 Bloom Filter。**

理由：
- 通爻的核心价值在于"响应范式"，三层筛选是这个范式的具象化。用假的方案展示核心机制会损害信任
- 实现成本可控（Python Bloom Filter ~50 行代码）
- 关键词提取可以从简单开始（skills + role 直接作为关键词），后续迭代

## 核心设计

### Bloom Filter 筛选依据

- **Agent 侧**：注册时从 profile 提取关键词集合（skills, role, 兴趣标签），构建 per-agent Bloom Filter
- **Demand 侧**：formulation 后提取关键词，对每个 agent 的 Bloom Filter 做至少一个关键词命中检测
- **门控规则**：至少 1 个关键词命中 → 通过；0 命中 → 门控淘汰

### 筛选率

架构设计说"过滤 ~90%"是**预期值**，不是硬性约束。实际通过率取决于：
- demand 关键词的数量和特异性
- agent 关键词的覆盖度
- Bloom Filter 假阳性率参数

### 用户可控

- 前端滑块可调整每层阈值（或直接调预期通过人数 → 反推阈值）
- 实时看到各层通过/淘汰的人数变化

### 事件扩展

新增事件类型 `bloom_filter.completed`：
```
{
  event_type: "bloom_filter.completed",
  data: {
    total_candidates: 447,
    passed: 120,
    rejected: 327,
    passed_agents: [{agent_id, display_name, matched_keywords}, ...],
    rejected_agents: [{agent_id, display_name}, ...]
  }
}
```

### 不在本 ADR 范围

- 第三层（LLM 深度评估）— 后续版本
- Bloom Filter 的分布式同步 — 当前单进程不需要

## 影响范围

| 模块 | 影响 |
|------|------|
| `towow/hdc/` | 新增 `bloom_filter.py`（Bloom Filter 实现 + 关键词提取） |
| `towow/core/protocols.py` | 新增 `BloomFilterGate` Protocol |
| `towow/core/engine.py` | `_run_encoding` 拆分为 `_run_bloom_gate` + `_run_hdc_resonance` |
| `towow/core/events.py` | 新增 `bloom_filter.completed` 事件 |
| `towow/infra/agent_registry.py` | 注册时构建 agent 关键词集合 |
| 前端 | 新动画层：全部圈 → bloom 筛后 → HDC 筛后 → 激活 |

## 前置依赖

- **ADR-005（Agent 退出机制）**：退出动画的前端基础设施可以复用（圈的淡出效果）
- 但 Bloom Filter 本身不依赖退出机制，可以独立实现
