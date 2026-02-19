# Compact Instruction — 模块二结晶协议工作状态

**写于**: 2026-02-18
**用途**: 指导下一次会话的 compact summary，确保上下文连续
**优先加载**: `/towow-lab` skill（实验工作），`/arch` skill（协议讨论）

---

## 一、我们在做什么（一句话）

通爻协议分两个模块。模块一（意图场）解决"谁应该在同一个房间"，模块二（结晶协议）解决"这些人在一起之后怎么消除信息差、形成协作方案"。

模块一已完成（V2 Field 模块，332 个测试通过）。我们现在在做模块二的 **prompt 迭代实验**（EXP-009）。

---

## 二、模块二的核心设计（必须理解）

### 协议结构

```
触发事件
   ↓
端侧 Agent（参与者，每人基于自己的 Profile 发言）
   ↓
催化 Agent（主持人，看到所有人的发言，做跨语义翻译+信息差传输）
   ↓
循环 N 轮，直到"催化连续两轮没有新发现" = 收敛
   ↓
方案生成器（基于全部上下文，产出具体分工方案）
   ↓
（未来）WOWOK Machine JSON 智能合约
```

### 催化 Agent 的唯一任务

1. **跨语义翻译**（最重要）：发现不同人用不同语言说的同一件事。例："A 说的'把虚空编织成形'和 B 说的'从模糊需求构建架构'可能在描述同一种能力——把模糊的东西变成有结构的东西"
2. **信息差传输**：让还没到达接收方的信息到达。按优先级：未发现的匹配 > 隐藏的阻碍 > 缺失的角色 > 被忽略的信息 > 重复的供给

### 催化的绝对禁区

**绝不推荐行动**。催化只能描述关系、指出信息差，绝不能说"建议…""应该…""可以尝试…"。这是"协议止于可见性"原则的核心：主持人不越界，参与者的自主表达才有空间。

---

## 三、实验场景（当前使用）

### 触发事件

东南亚制造企业 CEO（年营收 2 亿，800 人，OEM 代工被抢），想做品牌转型，需要品牌叙事+组织转型+数字化三件事被串起来。

### 三个参与者

- **Lina**：纪录片导演，信奉"真实即内容力"，擅长把混乱的真实还原成叙事
- **赵维**：分布式系统架构师，擅长把模糊需求变成精确设计，看到"公司里的信息流动问题"
- **Maya**：组织发展顾问，自称"翻译专家"，诊断信息差是所有组织问题的根源

### Ground Truth（预设的 4 条隐藏连接，评分依据）

1. **Lina + Maya 的"翻译"共振**：两人都做跨语义空间翻译——Lina 翻真实→影像，Maya 翻不同部门语言→共同描述
2. **赵维 + Maya 的"隐形结构"共振**：赵维画数据流图，Maya 做社会网络分析，都在"让看不见的变可见"
3. **Lina + 赵维的"真实 vs 生成"张力**：工厂的隐性知识既是赵维要捕捉的数据，也是 Lina 要拍摄的内容。延伸：如果 Lina 的观察行为本身改变了被观察的真实，怎么办？
4. **三人交汇**：三人各自想把能力产品化，但各自缺对方的。组合后 > 部分之和

**文件**：`tests/crystallization_poc/simulations/sim001_3person/participants.md`（GT 详述），`tests/crystallization_poc/simulations/sim001_3person/trigger.md`（触发事件）

---

## 四、已完成的实验（EXP-009 SIM-001 + SIM-002）

### SIM-001（v0 baseline，已完成，2026-02-18）

- **配置**：3 人 × 6 轮，catalyst_v0，Sonnet 4.5，~22 分钟，~$2-3
- **结果**：

| 维度 | 数值 |
|------|------|
| Ground Truth 发现率 | 30%（6/20） |
| 跨语义翻译 | ~0 条（6 轮合计） |
| 约束违反（给行动建议） | ~36 次（每轮 6+ 次） |
| 收敛 | 未收敛（6 轮跑满） |
| 意外发现质量 | 极高（超出预设 GT 的洞察） |

- **诊断**：催化角色跑偏——当了战略顾问而不是主持人。擅长结构分析，不会做翻译，不尊重约束
- **文件**：`tests/crystallization_poc/simulations/sim001_3person/output/evaluation.md`

### v1 催化 Prompt（SIM-001 后设计）

三个修复：
1. **翻译提升为第一优先级** + 具体示例（纪录片导演 ↔ 系统架构师的翻译案例）
2. **强制三段输出格式**：`## 跨语义翻译` / `## 关系与信息差` / `## 收敛判断`
3. **禁止性约束 + 反面示例**：禁用词列表（建议/应该/可以尝试/不妨/如果你们能…）+ 3 个错误示例 + 3 个正确示例

**文件**：`tests/crystallization_poc/prompts/catalyst_v1.md`

### SIM-002（v1 验证，已完成，2026-02-18）

- **配置**：3 人 × 6 轮，catalyst_v1，相同场景和 Profiles，Sonnet 4.5，~23 分钟，~$2-3
- **对比结果**：

| 维度 | SIM-001 (v0) | SIM-002 (v1) | 变化 |
|------|-------------|-------------|------|
| 跨语义翻译 | ~0 条 | **24 条**（4/轮，每轮稳定） | 从无到有 |
| 约束违反 | ~36 次 | **3 次边界情况** | -92% |
| Ground Truth | 30% | **80%**（~16/20） | +50pp |
| 格式遵从 | 无格式 | **6/6 轮** | 完全遵从 |
| 意外发现 | 极高 | **极高** | 未退化 |
| 方案催化污染 | 大量 | **极少** | 端侧自主涌现占比大幅提升 |

- **假说验证**：H6（禁止性约束）强烈验证，H7（翻译优先级）极强验证，H5（强制格式）部分验证（格式有效但 token 截断），H8（质量退化）否定
- **遗留问题**：max_tokens=3000 导致 R3-R6 的 `## 收敛判断` section 被截断（纯工程问题，不是 prompt 问题）
- **精彩案例**：v1 不仅发现了 GT3（Lina+赵维张力），还深化为观测者效应层面："如果 Lina 在场会改变被观察的系统，真实还存在吗？"——超出预设 GT 质量
- **文件**：`tests/crystallization_poc/simulations/sim002_3person_v1/output/evaluation.md`

---

## 五、完整文件清单

```
docs/
├── decisions/ADR-014-module2-crystallization-implementation.md  ← 8 条实现决策
├── design-logs/DESIGN_LOG_006_CRYSTALLIZATION_PROTOCOL.md       ← 模块二设计文档（权威版）
├── research/
│   ├── 004-crystallization-experiment-plan.md   ← 实验 6 阶段计划
│   ├── 005-wowok-machine-reference.md           ← WOWOK Machine JSON 格式参考
│   └── 006-exp009-crystallization-poc-results.md ← EXP-009 完整结果
└── community/
    └── profile-contribution-guide.md            ← 社区 Profile 征集指南（自包含，可直接发给社区）

tests/crystallization_poc/
├── README.md
├── prompts/
│   ├── catalyst_v0.md          ← SIM-001 使用，baseline
│   ├── catalyst_v1.md          ← SIM-002 使用，当前最佳版本
│   ├── endpoint_v0.md          ← 端侧 prompt（尚未迭代）
│   └── plan_generator_v0.md    ← 方案生成器 prompt（尚未迭代）
└── simulations/
    ├── sim001_3person/          ← v0 baseline
    │   ├── run_sim.py, trigger.md, participants.md
    │   └── output/
    │       ├── round_1.md ~ round_6.md
    │       ├── transcript.md（~141K chars）
    │       ├── plan.md（4,257 chars，质量 3.5/5，受催化越界污染）
    │       ├── metadata.json
    │       └── evaluation.md
    └── sim002_3person_v1/       ← v1 验证（压倒性成功）
        ├── run_sim.py（比 sim001 多了 v1 prompt 加载逻辑）
        ├── participants.md → symlink to sim001
        ├── trigger.md → symlink to sim001
        └── output/
            ├── round_1.md ~ round_6.md
            ├── transcript.md（~141K chars）
            ├── plan.md（4,231 chars，质量更高，端侧自主涌现）
            ├── metadata.json（confirms: SIM-002, EXP-009, 6 rounds, not converged）
            └── evaluation.md

data/profiles/
├── profile-synthetic-lina.md    ← ~2500 字合成 Profile
├── profile-synthetic-zhaowei.md ← ~2800 字合成 Profile
└── profile-synthetic-maya.md   ← ~3000 字合成 Profile
```

---

## 六、重要技术细节（避免重踩坑）

### run_sim.py 的关键配置

```python
# SIM-001 / SIM-002 的 max_tokens 设置（问题根源）
ENDPOINT_MAX_TOKENS = 2048   # 端侧每人每轮，卡满（输出约 2050 chars）
CATALYST_MAX_TOKENS = 3000   # 催化，R3-R6 被截断（v1 输出密度更高，3000 不够）
PLAN_MAX_TOKENS = 4096       # 方案生成器，够用

# SIM-002 的 catalyst prompt 加载（已修复过一次 bug）
# extract_prompt_block() 从 catalyst_v1.md 中提取 ``` 之间的内容
# 关键：catalyst_v1.md 的"用法示例"部分必须用缩进格式（4 空格），不能用 ``` 包裹
# 否则 extract_prompt_block() 会误抓用法示例而不是真正的 prompt
```

### 收敛检测逻辑

代码检测催化输出中是否包含：
- `"新发现数量：0"` 或
- `"本轮没有新发现"`

由于 max_tokens 截断，R3-R6 的 `## 收敛判断` section 未出现，所以系统检测不到收敛，只能跑满 6 轮。

### SIM-002 的收敛信号（虽然系统没检测到，但数据显示已经在收敛）

- R1：9 个新发现
- R2：3 个新发现（明显下降，收敛趋势清晰）
- R3-R6：收敛判断被截断，无法获取数字

---

## 七、关键决策记录（ADR-014 摘要，8 条）

1. **模块一→二接口**：三视角并集 top-K，干涉视角权重不低于其他两个
2. **触发策略**：用户主动触发（初始），自动触发是后续方向
3. **参与者规模**：上限 ~8 人，超出截断
4. **方案交付**：结晶收敛后产出分工方案（谁做什么/得什么/付出什么）→ 未来变成 WOWOK Machine JSON 智能合约。"协议止于可见性"约束催化循环过程，不约束最终交付形态
5. **输出格式路径**：先自然语言调通 → 加 JSON 层 → 两种都保留
6. **收敛检测**：催化连续两轮没新发现 = 收敛，最大轮次作为硬保障
7. **代码保障边界**：最大轮次/超时/格式校验用代码，催化行为/翻译质量用 prompt
8. **代码复用**：模块二从零开始写，V1 只做参考，模块一（MemoryField）是上游依赖

---

## 八、当前实验进展（Phase 对应关系）

```
Phase 0：材料准备          ✅ 完成
  - 3 个合成 Profile（Lina/赵维/Maya，~2500-3000 字/人）
  - 触发事件（东南亚 CEO 品牌转型）
  - WOWOK Machine 格式调研

Phase 1：Prompt v0 + 首轮模拟  ✅ 完成（SIM-001）
  - 端侧/催化/方案生成器 prompt v0 设计
  - SIM-001 跑通，人工评估完成
  - 评估报告：sim001_3person/output/evaluation.md

Phase 2：Prompt 迭代           ✅ 部分完成（催化 v1 已验证）
  - 催化 prompt v1 设计 ✅
  - SIM-002 跑通，对比评估完成 ✅
  - 评估报告：sim002_3person_v1/output/evaluation.md
  - 端侧 prompt v1：❌ 未做
  - 催化 prompt v1.1（修收敛截断）：❌ 未做

Phase 3：方案生成 + 格式化      ❌ 未开始
Phase 4：评估自动化             ❌ 未开始
Phase 5：规模测试（5-8 人）     ❌ 未开始
```

---

## 九、明确的下一步（按优先级）

### 选项 A：v1.1 催化 Prompt + SIM-003（最自然的下一步）

修复唯一遗留的工程问题 + 快速验证收敛：

1. 修 `catalyst_v1.md` → `catalyst_v1_1.md`：调整输出顺序，**把 `## 收敛判断` 放第一段**（3 行，够了），翻译和关系分析放后面。这样即使 token 截断也不影响收敛检测
2. 同步把 SIM-003 的 `CATALYST_MAX_TOKENS` 提到 6000（彻底消除截断风险）
3. 跑 SIM-003，目标验证：收敛在 4-5 轮触发（不是 6 轮跑满）

### 选项 B：端侧 Prompt v1

改进端侧参与者的发言质量：
- 添加异议表达引导（"如果你不同意催化的观察，说出来"）
- Profile 风格差异化（有人写长文，有人写短句，有人用比喻）

### 选项 C：真实 Profile 测试

等社区提交真实 Profile 后替换合成数据重跑，验证催化在真实异质性数据上的表现。

### 选项 D：WOWOK Machine JSON 输出层

在方案生成器 prompt 里加 JSON 输出格式，对接 WOWOK Machine 智能合约。

---

## 十、用户核心要求（必须记住）

1. **实验标准**：不是验证"能不能"，是验证"怎么更好"——prompt 迭代实验
2. **记录方式**：所有实验结果必须完整记录，像汇报报告一样，为市场/投资人/学术界提供素材
3. **Skill 加载**：实验工作先调用 `/towow-lab`，每个领域操作必须显式加载对应 Skill
4. **Profile 要求**：每人几千字深度描述，高异质性，跨语义空间关联（表面看不出，需要催化翻译）
5. **用户语言偏好**：用户不是工程师，汇报时给决策点和结论，不要太多技术细节

---

## 十一、背景（通爻协议全貌）

这是一个双模块协议：

**模块一（V2 意图场）** — 已完成，生产可用
- BGE-M3 向量编码 + SimHash 投影
- 三视角匹配（共振/互补/干涉）
- 分层呈现：`POST /field/api/match-perspectives`
- 76 个测试

**模块二（结晶协议）** — 实验阶段（EXP-009）
- 两角色循环：端侧 Agent（参与者）+ 催化 Agent（主持人）
- 核心能力：跨语义翻译 + 信息差消除
- 交付：分工方案 → WOWOK Machine 智能合约
- 当前状态：催化 v1 prompt 验证成功，收敛机制待工程修复
