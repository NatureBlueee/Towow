# TASK-T05-multi-round-logic

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T05-multi-round-logic.md`
>
> * TASK_ID: TASK-T05
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-22

---

## 关联 Story

- **STORY-05**: 多轮协商与共识达成

---

## 任务描述

实现完整的多轮协商逻辑，包括：
1. UserAgent 方案反馈生成（提示词 5）
2. ChannelAdmin 方案调整（提示词 6）
3. 协商状态机流转
4. [v4] **最多 5 轮协商限制**（原为 3 轮）
5. [v4] **第 5 轮强制终结**，区分已确认/可选参与者
6. [v4] **三档阈值判定**：>=80% → finalize，50-80% → 继续协商，<50% → fail

### 当前问题

1. `ChannelAdmin._adjust_proposal()` 提示词需优化
2. `UserAgent._llm_evaluate_proposal()` 反馈生成不够丰富
3. [v4] 协商轮次从 3 轮改为 **5 轮**
4. [v4] 需要实现**三档阈值判断**（>=80%/50-80%/<50%）
5. [v4] 需要实现**强制终结**逻辑（第 5 轮后）

### 改造目标

1. [v4] 实现 **5 轮协商** 完整流程
2. 优化方案调整提示词，能够根据反馈有效调整
3. [v4] 实现**三档阈值判定**：
   - **>=80% 接受** → FINALIZED
   - **50-80% 接受** → 继续协商（若 round < 5）
   - **<50% 接受** → FAILED
4. [v4] 实现**强制终结**：第 5 轮后，区分 confirmed_participants 和 optional_participants
5. 支持 withdraw（退出）和 negotiate（协商）反馈类型

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/channel_admin.py` | 优化多轮协商逻辑、`_adjust_proposal()` |
| `towow/openagents/agents/user_agent.py` | 优化 `_llm_evaluate_proposal()` |

### 关键代码改动

#### 1. 修改协商轮次限制

```python
# towow/openagents/agents/channel_admin.py

class ChannelAdminAgent(TowowBaseAgent):
    # [v4] 修改最大轮次为 5
    MAX_NEGOTIATION_ROUNDS = 5
    # [v4] 三档阈值
    ACCEPT_THRESHOLD_HIGH = 0.8   # >= 80% 直接通过
    ACCEPT_THRESHOLD_LOW = 0.5    # < 50% 失败
```

#### 2. 优化 _evaluate_feedback()

```python
async def _evaluate_feedback(self, state: ChannelState):
    """
    评估反馈，决定下一步

    [v4] 三档阈值决策逻辑：
    - >= 80% 接受 → FINALIZED
    - 50-80% 接受 → 继续协商（若 round < 5）
    - < 50% 接受 → FAILED
    - round >= 5 → FORCE_FINALIZED
    """
    if state.status != ChannelStatus.NEGOTIATING:
        self._logger.debug(f"跳过评估，Channel 状态: {state.status.value}")
        return

    # 统计反馈
    total = len(state.proposal_feedback)
    if total == 0:
        if state.current_round < state.max_rounds:
            await self._next_round(state)
        else:
            await self._fail_channel(state, "no_feedback")
        return

    accepts = sum(
        1 for f in state.proposal_feedback.values()
        if f.get("feedback_type") == "accept"
    )
    rejects = sum(
        1 for f in state.proposal_feedback.values()
        if f.get("feedback_type") in ("reject", "withdraw")
    )
    negotiates = sum(
        1 for f in state.proposal_feedback.values()
        if f.get("feedback_type") == "negotiate"
    )

    accept_rate = accepts / total
    reject_rate = rejects / total

    self._logger.info(
        f"Channel {state.channel_id} 反馈评估: "
        f"{accepts} 接受 ({accept_rate:.0%}), "
        f"{rejects} 拒绝/退出 ({reject_rate:.0%}), "
        f"{negotiates} 协商 (共: {total})"
    )

    # 发布评估事件
    await self._publish_event("towow.feedback.evaluated", {
        "channel_id": state.channel_id,
        "accepts": accepts,
        "rejects": rejects,
        "negotiates": negotiates,
        "accept_rate": accept_rate,
        "round": state.current_round
    })

    # [v4] 三档阈值决策逻辑
    # 1. >= 80% 接受 → 完成
    if accept_rate >= 0.8:
        await self._finalize_channel(state)
        return

    # 2. < 50% 接受 → 失败
    if accept_rate < 0.5:
        await self._fail_channel(state, "low_acceptance")
        return

    # 3. 50-80% 接受：检查轮次
    if state.current_round >= state.max_rounds:
        # [v4] 达到第 5 轮，强制终结
        await self._force_finalize_channel(state)
        return

    # 4. 50-80% 接受且轮次 < 5 → 下一轮
    await self._next_round(state)
```

#### 3. 优化 _adjust_proposal()

```python
async def _adjust_proposal(
    self,
    state: ChannelState,
    feedback: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    根据反馈调整方案

    基于提示词 6：方案调整
    """
    if not self.llm:
        # 没有 LLM，简单标记轮次
        adjusted = dict(state.current_proposal or {})
        adjusted["round"] = state.current_round
        adjusted["adjusted"] = True
        return adjusted

    current_proposal = state.current_proposal or {}

    # 分析反馈
    accept_feedbacks = []
    negotiate_feedbacks = []
    reject_feedbacks = []

    for agent_id, fb in feedback.items():
        fb_type = fb.get("feedback_type")
        fb_data = {
            "agent_id": agent_id,
            "adjustment_request": fb.get("adjustment_request", ""),
            "concerns": fb.get("concerns", []),
            "reasoning": fb.get("reasoning", "")
        }
        if fb_type == "accept":
            accept_feedbacks.append(fb_data)
        elif fb_type == "negotiate":
            negotiate_feedbacks.append(fb_data)
        else:
            reject_feedbacks.append(fb_data)

    prompt = f"""
# 方案调整任务

## 原始需求
{state.demand.get('surface_demand', '未说明')}

## 当前方案（第 {state.current_round - 1} 轮）
```json
{json.dumps(current_proposal, ensure_ascii=False, indent=2)}
```

## 反馈汇总
- 接受: {len(accept_feedbacks)} 人
- 希望调整: {len(negotiate_feedbacks)} 人
- 拒绝/退出: {len(reject_feedbacks)} 人

## 调整请求详情

### 希望调整的反馈
```json
{json.dumps(negotiate_feedbacks, ensure_ascii=False, indent=2)}
```

### 拒绝/退出的反馈
```json
{json.dumps(reject_feedbacks, ensure_ascii=False, indent=2)}
```

## 调整原则

1. **优先解决共性问题**：多人提出的问题优先处理
2. **平衡各方利益**：调整不应损害已接受方的利益
3. **保持方案可行**：调整后的方案仍应可执行
4. **透明说明变更**：清晰说明做了什么调整及原因

## 输出要求

请输出调整后的完整方案（保持原方案 JSON 结构），并添加调整说明：

```json
{{
  "summary": "调整后的方案摘要",
  "objective": "方案目标",
  "assignments": [...],
  "timeline": {{...}},
  "success_criteria": [...],
  "risks": [...],
  "gaps": [...],
  "confidence": "high/medium/low",
  "adjustment_summary": {{
    "round": {state.current_round},
    "changes_made": [
      {{"aspect": "调整方面", "before": "调整前", "after": "调整后", "reason": "原因"}}
    ],
    "requests_addressed": ["已处理的请求"],
    "requests_declined": [
      {{"request": "未处理的请求", "reason": "原因"}}
    ]
  }}
}}
```
"""

    try:
        response = await self.llm.complete(
            prompt=prompt,
            system="你是 ToWow 的方案调整系统。根据参与者反馈优化协作方案，以有效 JSON 格式输出。",
            fallback_key="proposal_adjustment",
            max_tokens=4000,
            temperature=0.4
        )
        adjusted = self._parse_proposal(response)
        adjusted["round"] = state.current_round
        return adjusted
    except Exception as e:
        self._logger.error(f"方案调整错误: {e}")
        adjusted = dict(current_proposal)
        adjusted["adjustment_failed"] = True
        adjusted["round"] = state.current_round
        return adjusted
```

#### 4. 优化 UserAgent._llm_evaluate_proposal()

```python
# towow/openagents/agents/user_agent.py

async def _llm_evaluate_proposal(
    self, proposal: Dict[str, Any]
) -> Dict[str, Any]:
    """
    使用 LLM 评估方案

    基于提示词 5：方案反馈
    """
    # 找到自己在方案中的角色
    my_assignment = None
    for assignment in proposal.get("assignments", []):
        if assignment.get("agent_id") == self.agent_id:
            my_assignment = assignment
            break

    # 构建 Profile 摘要
    profile_summary = self._build_profile_summary()

    prompt = f"""
# 方案评审任务

## 你的身份
你是 **{self.profile.get('name', self.user_id)}** 的数字分身。
你需要代表用户评估这个协作方案。

## 你的档案
{profile_summary}

## 协作方案
```json
{json.dumps(proposal, ensure_ascii=False, indent=2)}
```

## 你在方案中的角色分配
```json
{json.dumps(my_assignment, ensure_ascii=False) if my_assignment else "未分配具体角色"}
```

## 评审任务

请评估这个方案是否可以接受，考虑：
1. 你的角色分配是否合理？
2. 职责是否在你的能力范围内？
3. 时间安排是否可行？
4. 是否有任何顾虑或条件？

## 输出要求

请以 JSON 格式输出你的反馈：

```json
{{
  "feedback_type": "accept | negotiate | withdraw",
  "reasoning": "你做出这个评估的理由（50字以内）",
  "adjustment_request": "如果是 negotiate，说明希望如何调整",
  "concerns": ["如果有顾虑，列出每一个"],
  "confidence": 80
}}
```

## 反馈类型说明

- **accept**: 接受方案，愿意按分配的角色参与
- **negotiate**: 基本同意，但希望调整某些方面
- **withdraw**: 退出协作（角色不合适、时间冲突等）

注意：请站在 {self.profile.get('name', self.user_id)} 的角度评估。
"""

    try:
        response = await self.llm.complete(
            prompt=prompt,
            system="你是数字分身系统，代表用户评估协作方案。以有效 JSON 格式输出。",
            fallback_key="proposal_feedback",
            max_tokens=800,
            temperature=0.5
        )
        return self._parse_feedback(response)
    except Exception as e:
        self._logger.error(f"LLM 评估错误: {e}")
        return self._mock_feedback(proposal)
```

---

## 接口契约

### 方案反馈（UserAgent 输出）

```python
feedback: Dict = {
    "feedback_type": "accept" | "negotiate" | "withdraw",
    "reasoning": str,
    "adjustment_request": str,  # 仅 negotiate 时有值
    "concerns": List[str],
    "confidence": int
}
```

### 调整后方案（ChannelAdmin 输出）

```python
adjusted_proposal: Dict = {
    # 原方案所有字段
    ...
    "adjustment_summary": {
        "round": int,
        "changes_made": List[dict],
        "requests_addressed": List[str],
        "requests_declined": List[dict]
    }
}
```

---

## 依赖

### 硬依赖
- **T02**: Coordinator 智能筛选
- **T03**: UserAgent 响应生成
- **T04**: ChannelAdmin 方案聚合

### 接口依赖
- 无

### 被依赖
- **T06**: 缺口识别与子网
- **T07**: 状态检查与恢复机制
- **T08**: 前端修复（接口依赖）
- **T09**: 熔断器测试
- **T10**: E2E 测试

---

## 验收标准

- [ ] **AC-1**: [v4] 完整的 **5 轮协商** 流程可运行
- [ ] **AC-2**: [v4] **>=80% 接受** 时正确触发 FINALIZED
- [ ] **AC-3**: [v4] **<50% 接受** 时正确触发 FAILED
- [ ] **AC-4**: [v4] **50-80% 接受且 round < 5** 时触发下一轮
- [ ] **AC-5**: [v4] **第 5 轮后强制终结**，状态为 FORCE_FINALIZED
- [ ] **AC-6**: [v4] 强制终结时区分 `confirmed_participants` 和 `optional_participants`
- [ ] **AC-7**: `negotiate` 反馈触发方案调整
- [ ] **AC-8**: `withdraw` 反馈正确处理
- [ ] **AC-9**: 每轮发布 `towow.negotiation.round_started` 事件
- [ ] **AC-10**: [v4] 发布 `towow.feedback.evaluated` 事件（含 accept_rate 和 decision）
- [ ] **AC-11**: [v4] 发布 `towow.negotiation.force_finalized` 事件（第 5 轮后）

### 测试用例

```python
@pytest.mark.asyncio
async def test_multi_round_negotiation():
    """测试多轮协商流程"""
    admin = ChannelAdminAgent(llm=mock_llm_service)

    # 模拟第一轮：50% 接受，50% negotiate
    state = create_test_state(round=1)
    state.proposal_feedback = {
        "bob": {"feedback_type": "accept"},
        "alice": {"feedback_type": "negotiate", "adjustment_request": "调整时间"}
    }

    await admin._evaluate_feedback(state)

    # 应该进入第二轮
    assert state.current_round == 2
    assert state.status == ChannelStatus.PROPOSAL_SENT

@pytest.mark.asyncio
async def test_finalize_on_80_percent_accept():
    """测试 80% 接受时完成"""
    admin = ChannelAdminAgent(llm=mock_llm_service)

    state = create_test_state(round=2)
    state.proposal_feedback = {
        "bob": {"feedback_type": "accept"},
        "alice": {"feedback_type": "accept"},
        "charlie": {"feedback_type": "accept"},
        "dave": {"feedback_type": "accept"},
        "eve": {"feedback_type": "negotiate"}
    }  # 80% 接受

    await admin._evaluate_feedback(state)

    assert state.status == ChannelStatus.FINALIZED

@pytest.mark.asyncio
async def test_fail_on_majority_reject():
    """测试多数拒绝时失败"""
    admin = ChannelAdminAgent(llm=mock_llm_service)

    state = create_test_state(round=1)
    state.proposal_feedback = {
        "bob": {"feedback_type": "reject"},
        "alice": {"feedback_type": "withdraw"},
        "charlie": {"feedback_type": "accept"}
    }  # 67% 拒绝/退出

    await admin._evaluate_feedback(state)

    assert state.status == ChannelStatus.FAILED
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 代码开发 | 2.5h |
| 提示词调优 | 1h |
| 单元测试 | 0.5h |
| **总计** | **4h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 方案调整效果不佳 | 多轮无进展 | 提示词强调变更要求，限制轮次 |
| 反馈类型判断错误 | 流程异常 | 增强解析逻辑，标准化类型 |
| 3 轮后仍有分歧 | 用户体验差 | 生成妥协方案，给出建议 |

---

## 实现记录

*(开发完成后填写)*

---

## 测试记录

*(测试完成后填写)*
