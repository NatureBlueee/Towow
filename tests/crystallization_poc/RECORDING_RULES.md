# 结晶实验记录规则

> 本文件定义真人结晶实验的记录标准。所有 RUN 必须遵循这些规则。
> 参考实现: RUN-004 的 `run_log.md`

---

## 1. 版本命名

| 规则 | 示例 |
|------|------|
| 主改动跳整数 | endpoint v1 → v2（信息函数不变量是主改动） |
| 补丁用小数 | catalyst v2 → v2.1（逐对检查是最小补丁） |
| 文件名 = `{component}_{version}.md` | `catalyst_v2.1.md`, `formulation_v1.1.md` |
| **永不覆盖旧版本** | 新建文件，不修改已有 prompt 文件 |
| 版本号记录到 state.json | `prompt_versions` 列表和每个 run 的 `prompt_versions` 字段 |

---

## 2. state.json 更新规则

### RUN 状态流转

```
pending → running → completed → evaluated
```

- `pending`: config.json 写好，未开始执行
- `running`: 正在执行轮次
- `completed`: 所有轮次 + plan 生成完毕
- `evaluated`: 用户评估完毕，verdict 已写入

### 必须更新的字段

| 时机 | 更新内容 |
|------|---------|
| RUN 开始 | `status: "running"` |
| RUN 完成 | `status: "completed"`, `rounds`, `convergence`, `summary_200w`, `verification_results` |
| 用户评估后 | `status: "evaluated"`, `evaluation.user_verdict`, `evaluation.diagnosis`, `evaluation.modifications[]` |
| 迭代决策后 | `iteration_log[]` 追加条目（from_run, to_run, factor, change, result） |
| 新 prompt 版本 | `prompt_versions` 列表追加 |
| `next_action` | **每次状态变更都更新**，是跨 session 恢复的唯一入口 |

### summary_200w 要求

- 200 字以内
- 信息密度足够高——后续 session 只读此字段了解整个 run
- 必须包含：轮次数、收敛与否、关键发现（逐条）、方案质量一句话、最大问题
- 不允许空洞总结（"效果不错"不行，"3/3配对覆盖R1即达成"可以）

---

## 3. run_log.md 规则

**每个 RUN 必须有 `output/run_log.md`。** 这是实验过程的完整客观记录。

### 必须包含的章节

#### 3.1 头部信息
- Run ID、日期、描述、执行方式、模型、Lead 信息

#### 3.2 冻结条件
- 需求、参与者、模型、最大轮次
- 与上一 run 的对比表

#### 3.3 Prompt 版本变更表
- 每个组件的 from→to 版本 + 改动描述

#### 3.4 Agent Teams 成员注册表（如使用蜂群模式）

| 必须记录 | 示例 |
|----------|------|
| Name | endpoint-p07 |
| Agent ID | endpoint-p07@run-004 |
| Model | sonnet / opus |
| Backend | tmux / iterm2 |
| Prompt 来源 | endpoint_v2.md + chenxizhang.md |
| Spawn 状态 | 成功 / 首次失败→重试成功 |
| Spawn 失败原因（如有） | "[Tool result missing due to internal error]" |

#### 3.5 详细执行时间线

**每一轮必须记录：**

1. **Lead → Teammates 通信**:
   - 消息类型（初始 Prompt / SendMessage）
   - 核心指令概述
   - 特殊附加指令（相变检测、收敛后输出等）
   - 异常处理（指令重发、超时等）

2. **每个 Teammate 的活动**:
   - 读了哪些文件
   - 输出了什么文件
   - 核心产出概述（1-3 句话）
   - 收敛信号（如有）
   - Idle 通知 summary

3. **轮次质量评估**:
   - Prompt 机制是否生效（信息函数不变量、逐对检查、相变检测等）
   - 信息密度评估
   - 异常观察

#### 3.6 Phase Final（Plan 生成）
- 执行方式（Task subagent / teammate）
- 输入文件列表
- Token 消耗（如可获取）
- 质量评估

#### 3.7 Teammate 关闭序列
- 每个 teammate 的 shutdown 请求 ID、响应、关闭确认

#### 3.8 最终关系图谱
- 从催化收敛轮输出中完整复制

#### 3.9 验证目标达成表
- 每个指标的 baseline → actual → pass/fail

#### 3.10 技术观察
- 各 prompt 组件效果
- Agent Teams 蜂群行为观察
- 问题与建议

#### 3.11 Teammate 通信完整日志

三张汇总表：

1. **Lead → Endpoint 消息汇总**: 轮次 | 目标 | 消息类型 | 核心指令
2. **Lead → Catalyst 消息汇总**: 轮次 | 核心指令 | 特殊附加
3. **Teammate → Lead 消息汇总**: 来源 | 轮次 | Summary | 核心内容

#### 3.12 产出文件清单
- 完整文件树 + 总计

### 记录原则

- **客观 + 细节**: 记录实际发生的事，不做主观评价
- **展示原始内容**: 质量好坏让用户自己判断
- **异常必记**: 失败、重试、重发、超时等全部记录
- **可追溯**: 每个动作可追溯到具体的 SendMessage / Task / 文件写入

---

## 4. 文件组织

```
tests/crystallization_poc/
  state.json                           # 实验状态（单一真相源）
  RECORDING_RULES.md                   # 本文件
  prompts/
    {component}_{version}.md           # 永不覆盖，只新建
  simulations/real/
    run_NNN/
      config.json                      # 冻结配置
      output/
        formulated_demand.md           # Phase 0
        round_N_{participant_id}.md    # 每轮每人一个文件
        round_N_catalyst.md            # 每轮催化一个文件
        plan.md                        # 协作方案
        run_log.md                     # 运行日志（本规则定义的格式）
      evaluation.md                    # 用户评估（可选，人类可读副本）
    iteration_log.md                   # 跨 run 迭代记录（人类可读版）
```

---

## 5. 跨 Session 恢复规则

1. 新 session 第一步：读 `state.json`
2. 看 `next_action` 字段——这是"我该做什么"的唯一入口
3. 如果 `next_action.type = "user_evaluate"`：引导用户评估对应 run
4. 如果 `next_action.type = "run"`：准备执行下一个 run
5. **永远不依赖对话记忆**——所有状态在文件中

---

## 6. 增长管理

- 超过 10 个 run：旧 run 的 `summary_200w` 压缩为一行，详情归档到 `iteration_log.md`
- `run_log.md` 不压缩——它是完整记录，不受增长管理影响
- `state.json` 保持可读——单个 run 条目 ~30 行，10 个 run ~300 行，尚可管理
