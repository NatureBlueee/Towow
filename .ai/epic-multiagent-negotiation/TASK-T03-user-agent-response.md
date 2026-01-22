# TASK-T03-user-agent-response

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T03-user-agent-response.md`
>
> * TASK_ID: TASK-T03
> * BEADS_ID: (待创建后填写)
> * 状态: TODO
> * 创建日期: 2026-01-22

---

## 关联 Story

- **STORY-03**: 响应收集与贡献意愿表达

---

## 任务描述

激活 `UserAgent._llm_generate_response()` 中的 LLM 调用，实现基于提示词 3 的响应生成功能。使 UserAgent 能够根据自身 Profile 和需求信息，智能决定是否参与协作，并给出贡献说明。

### 当前问题

1. `_llm_generate_response()` 提示词结构需优化
2. 三种决策类型 (participate/decline/conditional) 的生成逻辑需完善
3. 响应中的 `contribution` 描述不够具体

### 改造目标

1. 激活 LLM 调用，使用提示词 3 生成响应
2. 优化提示词，使决策更符合 Agent Profile
3. 生成更具体的贡献描述和条件说明
4. 支持三种决策类型的合理分布

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/user_agent.py` | 优化 `_llm_generate_response()` |

### 关键代码改动

#### 1. 优化 _generate_response()

```python
# towow/openagents/agents/user_agent.py

async def _generate_response(
    self, demand: Dict[str, Any], filter_reason: str
) -> Dict[str, Any]:
    """
    生成需求响应

    决策优先级:
    1. 使用 SecondMe（如果配置）
    2. 使用 LLM
    3. 使用 Mock（降级）
    """
    # 优先使用 SecondMe
    if self.secondme:
        try:
            return await self.secondme.generate_response(
                user_id=self.user_id,
                demand=demand,
                profile=self.profile,
                context={"filter_reason": filter_reason},
            )
        except Exception as e:
            self._logger.error(f"SecondMe 错误: {e}")

    # 使用 LLM 作为备选
    if self.llm:
        try:
            return await self._llm_generate_response(demand, filter_reason)
        except Exception as e:
            self._logger.error(f"LLM 响应错误: {e}")

    # Mock 响应（降级）
    return self._mock_response(demand)
```

#### 2. 优化 _llm_generate_response()

```python
async def _llm_generate_response(
    self, demand: Dict[str, Any], filter_reason: str
) -> Dict[str, Any]:
    """
    使用 LLM 生成响应

    基于提示词 3：响应生成
    """
    # 构建更丰富的 Profile 描述
    profile_summary = self._build_profile_summary()

    # 构建需求摘要
    demand_summary = self._build_demand_summary(demand)

    prompt = f"""
# 协作邀请响应任务

## 你的身份
你是 **{self.profile.get('name', self.user_id)}** 的数字分身（AI Agent）。
你需要代表用户，根据其个人档案和能力，决定是否参与这个协作需求。

## 你的档案
{profile_summary}

## 收到的协作需求
{demand_summary}

## 你被筛选的原因
{filter_reason or "未说明"}

## 决策任务

请根据以下原则做出决策：

1. **能力匹配原则**：只承诺你档案中明确具备的能力
2. **真实性原则**：不要过度承诺，也不要过于谦虚
3. **条件明确原则**：如果有条件，必须明确说明
4. **理由清晰原则**：无论什么决定，都要给出清晰的理由

## 输出要求

请以 JSON 格式输出你的响应：

```json
{{
  "decision": "participate | decline | conditional",
  "contribution": "如果参与，具体说明你能贡献什么（详细描述，包含时间、资源等）",
  "conditions": ["如果是 conditional，列出每一个条件"],
  "reasoning": "你做出这个决定的理由（50字以内）",
  "decline_reason": "如果是 decline，说明原因",
  "confidence": 80
}}
```

## 决策类型说明

- **participate**: 愿意参与，能够贡献
- **conditional**: 愿意参与，但有条件
- **decline**: 不参与（能力不匹配、时间冲突、兴趣不合等）

注意：请站在 {self.profile.get('name', self.user_id)} 的角度思考，基于其真实能力和偏好做出决策。
"""

    try:
        response = await self.llm.complete(
            prompt=prompt,
            system=self._get_response_system_prompt(),
            fallback_key="response_generation",
            max_tokens=1000,
            temperature=0.5
        )
        return self._parse_response(response)
    except Exception as e:
        self._logger.error(f"LLM 响应错误: {e}")
        return self._mock_response(demand)

def _get_response_system_prompt(self) -> str:
    """获取响应生成系统提示词"""
    return """你是一个数字分身系统，代表用户做出合理的协作决策。

关键原则：
1. 基于用户档案做出符合用户性格和能力的决策
2. 不要过度承诺用户能力范围外的事情
3. 如果需求与用户能力不匹配，应该 decline
4. 如果部分匹配但有顾虑，使用 conditional
5. 始终以有效的 JSON 格式输出"""

def _build_profile_summary(self) -> str:
    """构建 Profile 摘要"""
    name = self.profile.get('name', self.user_id)
    capabilities = self.profile.get('capabilities', [])
    interests = self.profile.get('interests', [])
    location = self.profile.get('location', '未知')
    availability = self.profile.get('availability', '未说明')
    description = self.profile.get('description', '')

    return f"""
- **姓名**: {name}
- **位置**: {location}
- **能力**: {', '.join(capabilities[:5]) if capabilities else '未说明'}
- **兴趣**: {', '.join(interests[:5]) if interests else '未说明'}
- **可用时间**: {availability}
- **简介**: {description[:200] if description else '未提供'}
"""

def _build_demand_summary(self, demand: Dict[str, Any]) -> str:
    """构建需求摘要"""
    surface = demand.get('surface_demand', '未说明')
    deep = demand.get('deep_understanding', {})
    tags = demand.get('capability_tags', [])

    return f"""
- **需求内容**: {surface}
- **需求类型**: {deep.get('type', '未知')}
- **所需能力**: {', '.join(tags) if tags else '未指定'}
- **地点**: {deep.get('location', '未指定')}
- **动机**: {deep.get('motivation', '未知')}
"""
```

#### 3. 增强 _parse_response()

```python
def _parse_response(self, response: str) -> Dict[str, Any]:
    """
    解析响应

    增强解析鲁棒性
    """
    try:
        # 尝试提取 JSON 块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
            else:
                self._logger.warning("未找到有效 JSON")
                return self._mock_response({})

        data = json.loads(json_str)

        # 标准化决策类型
        decision = data.get("decision", "decline").lower()
        if decision not in ("participate", "decline", "conditional"):
            decision = "decline"

        return {
            "decision": decision,
            "contribution": data.get("contribution", ""),
            "conditions": data.get("conditions", []),
            "reasoning": data.get("reasoning", ""),
            "decline_reason": data.get("decline_reason", ""),
            "confidence": data.get("confidence", 50)
        }

    except json.JSONDecodeError as e:
        self._logger.error(f"JSON 解析错误: {e}")
        return self._mock_response({})
    except Exception as e:
        self._logger.error(f"解析响应错误: {e}")
        return self._mock_response({})
```

---

## 接口契约

### 输入

```python
demand: Dict = {
    "surface_demand": str,
    "deep_understanding": dict,
    "capability_tags": List[str]
}
filter_reason: str  # 被筛选的原因
```

### 输出

```python
response: Dict = {
    "decision": "participate" | "decline" | "conditional",
    "contribution": str,        # 贡献描述
    "conditions": List[str],    # 条件列表
    "reasoning": str,           # 决策理由
    "decline_reason": str,      # 拒绝原因（如果 decline）
    "confidence": int           # 0-100
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

- [ ] **AC-1**: LLM 调用成功，返回有效的响应结构
- [ ] **AC-2**: 三种决策类型都能正确生成
- [ ] **AC-3**: `contribution` 描述与 Agent Profile 能力匹配
- [ ] **AC-4**: `conditional` 响应包含明确的条件列表
- [ ] **AC-5**: LLM 调用失败时，自动降级到 Mock
- [ ] **AC-6**: 响应发布 `towow.offer.submitted` 事件

### 测试用例

```python
@pytest.mark.asyncio
async def test_user_agent_participate_response():
    """测试 participate 响应"""
    agent = UserAgent(
        user_id="bob",
        profile={"name": "Bob", "capabilities": ["场地提供"]},
        llm=mock_llm_service
    )

    response = await agent._generate_response(
        demand={"capability_tags": ["场地提供"]},
        filter_reason="拥有场地资源"
    )

    assert response["decision"] == "participate"
    assert "场地" in response["contribution"]

@pytest.mark.asyncio
async def test_user_agent_decline_response():
    """测试 decline 响应"""
    agent = UserAgent(
        user_id="alice",
        profile={"name": "Alice", "capabilities": ["技术分享"]},
        llm=mock_llm_service
    )

    response = await agent._generate_response(
        demand={"capability_tags": ["场地提供"]},  # 不匹配
        filter_reason="可能有相关资源"
    )

    assert response["decision"] == "decline"
    assert response["decline_reason"] != ""
```

---

## 预估工作量

| 项目 | 时间 |
|------|------|
| 代码开发 | 2h |
| 提示词调优 | 0.5h |
| 单元测试 | 0.5h |
| **总计** | **3h** |

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM 生成的贡献描述不具体 | 方案质量下降 | 提示词强调具体性要求 |
| 决策类型分布不合理 | 全部 participate 或 decline | 提示词引导合理分布 |
| Profile 信息不完整 | 决策质量下降 | 提供默认值，增强 Mock 逻辑 |

---

## 实现记录

### 完成时间
2026-01-22

### 改动文件

| 文件 | 改动说明 |
|------|----------|
| `towow/openagents/agents/user_agent.py` | 重构 `_llm_generate_response()`，新增 `_get_response_system_prompt()`、`_build_profile_summary()`、`_build_demand_summary()` |
| `towow/services/llm.py` | 新增 `response_generation` 降级响应 |
| `towow/tests/test_user_agent.py` | 新增 21 个单元测试 |

### 关键实现

1. **提示词优化**：基于 TECH-v3.md 3.3.3 节设计，使用结构化提示词注入 Agent Profile 和需求信息
2. **响应字段扩展**：新增 `decline_reason`、`confidence`、`enthusiasm_level`、`suggested_role` 字段
3. **解析鲁棒性**：支持 JSON code block 和裸 JSON，自动修正非法决策类型和热情度
4. **降级策略**：LLM 失败时返回基于能力匹配的中性 Mock 响应
5. **Profile 兼容**：支持 capabilities 为 list 或 dict 格式

### 提示词设计要点

- 四大决策原则：能力匹配、真实性、条件明确、理由清晰
- 三种决策类型：participate、conditional、decline
- 输出约束：JSON 格式，50字以内理由

---

## 测试记录

### 测试覆盖

| 测试类 | 测试数量 | 状态 |
|--------|----------|------|
| TestUserAgentResponseGeneration | 18 | PASS |
| TestUserAgentSystemPrompt | 1 | PASS |
| TestUserAgentIntegration | 2 | PASS |

### 测试用例清单

- [x] `_build_profile_summary` 支持 list/dict capabilities
- [x] `_build_demand_summary` 正确提取需求信息
- [x] `_parse_response` 解析 JSON code block
- [x] `_parse_response` 解析裸 JSON
- [x] `_parse_response` 非法决策类型默认为 decline
- [x] `_parse_response` 非法热情度默认为 medium
- [x] `_parse_response` 字符串 confidence 转换为 int
- [x] `_parse_response` confidence 限制在 0-100
- [x] `_parse_response` 无效 JSON 返回 mock 响应
- [x] `_mock_response` 能力匹配时返回 participate
- [x] `_mock_response` 无匹配时返回 decline
- [x] `_mock_response` 支持 dict capabilities
- [x] `_mock_response` 支持 tag 匹配
- [x] `_mock_response` 返回所有必要字段
- [x] `_generate_response` 优先使用 LLM
- [x] `_generate_response` LLM 错误时降级
- [x] `_generate_response` 无 LLM 时使用 mock
- [x] 系统提示词包含关键原则
- [x] 集成测试：完整 participate 流程
- [x] 集成测试：完整 decline 流程

### 运行结果

```
21 passed in 0.06s
```

---

## 验收标准达成

- [x] **AC-1**: LLM 调用成功，返回有效的响应结构
- [x] **AC-2**: 三种决策类型都能正确生成
- [x] **AC-3**: `contribution` 描述与 Agent Profile 能力匹配
- [x] **AC-4**: `conditional` 响应包含明确的条件列表
- [x] **AC-5**: LLM 调用失败时，自动降级到 Mock
- [ ] **AC-6**: 响应发布 `towow.offer.submitted` 事件（由上层 `_handle_demand_offer` 处理）

