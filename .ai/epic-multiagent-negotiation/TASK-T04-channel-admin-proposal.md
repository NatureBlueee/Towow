# TASK-T04-channel-admin-proposal

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T04-channel-admin-proposal.md`
>
> * TASK_ID: TASK-T04
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-22

---

## 关联 Story

- **STORY-04**: 方案聚合与角色分配

---

## 任务描述

激活 `ChannelAdminAgent._generate_proposal()` 中的 LLM 调用，实现基于提示词 4 的方案聚合功能。使 ChannelAdmin 能够整合多个 UserAgent 的贡献意愿，生成结构化的协作方案。

### 当前问题

1. `_generate_proposal()` 提示词结构需优化
2. 方案结构中角色分配 (`assignments`) 不够明确
3. 时间线 (`timeline`) 和成功标准 (`success_criteria`) 生成不够具体

### 改造目标

1. 激活 LLM 调用，使用提示词 4 生成方案
2. 优化提示词，生成更完整的方案结构
3. 确保每个参与者都有明确的角色和职责
4. 生成可衡量的成功标准

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/channel_admin.py` | 优化 `_generate_proposal()` |

### 关键代码改动

#### 1. 优化 _generate_proposal()

```python
# towow/openagents/agents/channel_admin.py

async def _generate_proposal(
    self,
    state: ChannelState,
    participants: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    生成协作方案

    基于提示词 4：方案聚合
    整合多方贡献，形成结构化的协作方案
    """
    if not self.llm:
        self._logger.debug("未配置 LLM 服务，使用模拟方案")
        return self._mock_proposal(state, participants)

    # 构建提示词
    prompt = self._build_proposal_prompt(state, participants)

    try:
        response = await self.llm.complete(
            prompt=prompt,
            system=self._get_proposal_system_prompt(),
            fallback_key="proposal_aggregation",
            max_tokens=4000,
            temperature=0.4
        )

        proposal = self._parse_proposal(response)

        # 验证方案完整性
        proposal = self._validate_and_enhance_proposal(proposal, participants)

        self._logger.info(
            f"方案生成完成，包含 {len(proposal.get('assignments', []))} 个角色分配"
        )

        return proposal

    except Exception as e:
        self._logger.error(f"方案生成错误: {e}")
        return self._mock_proposal(state, participants)

def _get_proposal_system_prompt(self) -> str:
    """获取方案生成系统提示词"""
    return """你是 ToWow 协作平台的方案聚合系统。

你的任务是整合各参与者的贡献和条件，生成一个可执行的协作方案。

方案设计原则：
1. 角色明确：每个参与者都应有明确的角色和职责
2. 条件兼顾：尽可能满足各参与者提出的条件
3. 时间合理：考虑各方可用时间，给出合理的时间安排
4. 风险可控：识别潜在风险并提供应对建议
5. 成功可衡量：定义清晰的成功标准

始终以有效的 JSON 格式输出。"""
```

#### 2. 优化 _build_proposal_prompt()

```python
def _build_proposal_prompt(
    self,
    state: ChannelState,
    participants: List[Dict[str, Any]]
) -> str:
    """构建方案生成提示词"""
    demand = state.demand
    surface_demand = demand.get('surface_demand', '未说明')
    deep = demand.get('deep_understanding', {})

    # 格式化参与者信息
    participant_details = []
    for p in participants:
        detail = {
            "agent_id": p.get("agent_id"),
            "display_name": p.get("display_name", p.get("agent_id")),
            "decision": p.get("decision"),
            "contribution": p.get("contribution", "未说明"),
            "conditions": p.get("conditions", []),
            "capabilities": p.get("capabilities", [])
        }
        participant_details.append(detail)

    return f"""
# 协作方案生成任务

## 需求背景

### 原始需求
{surface_demand}

### 需求分析
- **类型**: {deep.get('type', 'general')}
- **动机**: {deep.get('motivation', '未知')}
- **规模**: {json.dumps(deep.get('scale', {}), ensure_ascii=False)}
- **时间线**: {json.dumps(deep.get('timeline', {}), ensure_ascii=False)}
- **资源需求**: {json.dumps(deep.get('resource_requirements', []), ensure_ascii=False)}

## 参与者及其贡献

共 {len(participants)} 位参与者：

```json
{json.dumps(participant_details, ensure_ascii=False, indent=2)}
```

## 当前协商状态
- 当前轮次: 第 {state.current_round} 轮（最多 {state.max_rounds} 轮）

## 输出要求

请生成一个结构化的协作方案（JSON 格式）：

```json
{{
  "summary": "方案核心摘要（一句话描述这个方案做什么）",
  "objective": "方案目标（要达成的具体成果）",
  "assignments": [
    {{
      "agent_id": "参与者 ID",
      "display_name": "参与者名称",
      "role": "角色名称",
      "responsibility": "具体职责描述（包含要做什么、产出什么）",
      "conditions_addressed": ["已满足的条件列表"],
      "estimated_effort": "预估投入（如：2小时/周、1天等）"
    }}
  ],
  "timeline": {{
    "start_date": "建议开始时间",
    "end_date": "预计完成时间",
    "milestones": [
      {{"name": "里程碑名称", "date": "时间点", "deliverable": "交付物"}}
    ]
  }},
  "collaboration_model": {{
    "communication_channel": "主要沟通方式",
    "meeting_frequency": "会议频率",
    "decision_mechanism": "决策机制"
  }},
  "success_criteria": [
    "成功标准1（可衡量的）",
    "成功标准2"
  ],
  "risks": [
    {{
      "risk": "风险描述",
      "probability": "high/medium/low",
      "mitigation": "应对措施"
    }}
  ],
  "gaps": ["方案中可能存在的缺口"],
  "confidence": "high/medium/low",
  "notes": "其他备注说明"
}}
```

## 注意事项
- 确保每个参与者都有明确分工
- 时间安排要考虑各方提出的时间约束
- 方案应该是可执行的，而非泛泛而谈
- 如果某些条件无法满足，在 notes 中说明原因和替代方案
"""
```

#### 3. 添加方案验证方法

```python
def _validate_and_enhance_proposal(
    self,
    proposal: Dict[str, Any],
    participants: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    验证并增强方案

    确保方案结构完整，补充缺失字段
    """
    # 确保 assignments 包含所有参与者
    assigned_ids = {a.get("agent_id") for a in proposal.get("assignments", [])}
    participant_ids = {p.get("agent_id") for p in participants}

    # 补充未分配的参与者
    for p in participants:
        if p.get("agent_id") not in assigned_ids:
            proposal.setdefault("assignments", []).append({
                "agent_id": p.get("agent_id"),
                "display_name": p.get("display_name", p.get("agent_id")),
                "role": "待分配",
                "responsibility": p.get("contribution", "待确定"),
                "conditions_addressed": p.get("conditions", []),
                "estimated_effort": "待评估"
            })

    # 确保必要字段存在
    proposal.setdefault("summary", "协作方案")
    proposal.setdefault("objective", "完成协作需求")
    proposal.setdefault("timeline", {"start_date": "待定", "milestones": []})
    proposal.setdefault("success_criteria", ["需求被满足"])
    proposal.setdefault("risks", [])
    proposal.setdefault("gaps", [])
    proposal.setdefault("confidence", "medium")

    return proposal
```

---

## 接口契约

### 输入

```python
state: ChannelState  # 包含 demand, candidates, current_round 等
participants: List[Dict] = [
    {
        "agent_id": str,
        "display_name": str,
        "decision": str,
        "contribution": str,
        "conditions": List[str],
        "capabilities": List[str]
    }
]
```

### 输出

```python
proposal: Dict = {
    "summary": str,
    "objective": str,
    "assignments": List[Assignment],
    "timeline": Timeline,
    "collaboration_model": dict,
    "success_criteria": List[str],
    "risks": List[Risk],
    "gaps": List[str],
    "confidence": str,
    "notes": str
}
```

---

## 依赖

### 硬依赖
- **T01**: demand.py 重构

### 接口依赖
- 无

### 被依赖
- **T05**: 多轮协商逻辑

---

## 验收标准

- [ ] **AC-1**: LLM 调用成功，返回完整的方案结构
- [ ] **AC-2**: 每个参与者都有明确的 `role` 和 `responsibility`
- [ ] **AC-3**: `timeline` 包含至少一个 `milestone`
- [ ] **AC-4**: `success_criteria` 至少包含 2 个可衡量的标准
- [ ] **AC-5**: 方案发布 `towow.proposal.distributed` 事件
- [ ] **AC-6**: LLM 调用失败时，自动降级到 Mock 方案

### 测试用例

```python
@pytest.mark.asyncio
async def test_generate_proposal_complete():
    """测试生成完整方案"""
    admin = ChannelAdminAgent(llm=mock_llm_service)

    state = ChannelState(
        channel_id="ch-test",
        demand_id="d-test",
        demand={"surface_demand": "办一场AI聚会"},
        candidates=[]
    )

    participants = [
        {"agent_id": "bob", "contribution": "提供场地"},
        {"agent_id": "alice", "contribution": "技术分享"}
    ]

    proposal = await admin._generate_proposal(state, participants)

    assert "summary" in proposal
    assert len(proposal["assignments"]) >= 2
    assert all("role" in a for a in proposal["assignments"])

@pytest.mark.asyncio
async def test_validate_proposal_fills_gaps():
    """测试方案验证补充缺失字段"""
    admin = ChannelAdminAgent(llm=None)

    proposal = {"summary": "测试方案"}
    participants = [{"agent_id": "bob", "contribution": "场地"}]

    enhanced = admin._validate_and_enhance_proposal(proposal, participants)

    assert "assignments" in enhanced
    assert "timeline" in enhanced
    assert "success_criteria" in enhanced
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
| 方案结构不完整 | 前端展示异常 | 验证方法补充缺失字段 |
| 角色分配不合理 | 参与者不满意 | 提示词强调合理性，多轮调整 |
| LLM 生成时间过长 | 用户等待过久 | 设置超时，降级到 Mock |

---

## 实现记录

*(开发完成后填写)*

---

## 测试记录

*(测试完成后填写)*
