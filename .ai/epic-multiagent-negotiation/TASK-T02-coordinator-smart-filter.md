# TASK-T02-coordinator-smart-filter

> **文档路径**: `.ai/epic-multiagent-negotiation/TASK-T02-coordinator-smart-filter.md`
>
> * TASK_ID: TASK-T02
> * BEADS_ID: towow-t91
> * 状态: DOING
> * 创建日期: 2026-01-22

---

## 关联 Story

- **STORY-02**: 智能筛选与候选人匹配

---

## 任务描述

激活 `Coordinator._smart_filter()` 中的 LLM 调用，实现基于提示词 2 的智能筛选功能。当前代码框架已存在，但实际 LLM 调用未启用。

### 当前问题

1. `_smart_filter()` 默认返回 Mock 候选人列表
2. `_build_filter_prompt()` 提示词需要优化
3. `_parse_filter_response()` 解析逻辑不够健壮

### 改造目标

1. 激活 LLM 调用，使用提示词 2 进行智能筛选
2. 优化提示词，提高筛选质量
3. 增强响应解析的鲁棒性
4. [v4] 筛选出 **最多 10 个** 高相关候选人（上限降低）
5. [v4] **MVP 不允许筛选失败**，保证至少返回 1 个候选人
6. [v4] 添加兜底机制：筛选失败时返回**随机 3 个活跃 Agent**

---

## 技术实现

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/coordinator.py` | 激活 `_smart_filter()` LLM 调用 |

### 关键代码改动

#### 1. 优化 _smart_filter()

```python
# towow/openagents/agents/coordinator.py

async def _smart_filter(
    self, demand_id: str, understanding: Dict
) -> List[Dict]:
    """
    智能筛选候选 Agent

    基于提示词 2：智能筛选
    从 Agent 池中筛选出 10-20 个高相关候选人
    """
    # 获取所有可用 Agent
    available_agents = await self._get_available_agents()

    if not available_agents:
        self._logger.warning("无可用 Agent，使用 Mock 数据")
        return self._mock_filter(understanding)

    # 检查 LLM 服务
    if not self.llm:
        self._logger.warning("LLM 服务不可用，使用 Mock 筛选")
        return self._mock_filter(understanding)

    # 构建提示词
    prompt = self._build_filter_prompt(understanding, available_agents)

    try:
        # 调用 LLM 进行智能筛选
        response = await self.llm.complete(
            prompt=prompt,
            system=self._get_filter_system_prompt(),
            fallback_key="smart_filter",
            max_tokens=4000,
            temperature=0.3  # 降低随机性，提高一致性
        )

        # 解析响应
        candidates = self._parse_filter_response(response, available_agents)

        if not candidates:
            self._logger.warning("LLM 筛选无结果，使用 Mock")
            return self._mock_filter(understanding)

        self._logger.info(f"智能筛选完成，找到 {len(candidates)} 个候选人")

        # 发布筛选结果事件
        await self._publish_event("towow.filter.completed", {
            "demand_id": demand_id,
            "candidates_count": len(candidates),
            "candidates": [c.get("agent_id") for c in candidates]
        })

        return candidates

    except Exception as e:
        self._logger.error(f"智能筛选失败: {e}")
        return self._mock_filter(understanding)

def _get_filter_system_prompt(self) -> str:
    """获取筛选系统提示词"""
    return """你是 ToWow 协作平台的智能筛选系统。

你的任务是根据用户需求，从候选 Agent 池中筛选出最适合参与协作的人选。

筛选原则：
1. 能力匹配优先：Agent 的 capabilities 应与需求的资源需求匹配
2. 地域相关性：考虑 Agent 的 location 与需求地点的兼容性
3. 多样性互补：选择能力互补的组合，避免过于同质化
4. 规模适配：根据需求规模控制候选人数（小规模 3-5 人，中等 5-8 人，大规模 8-12 人）
5. 关键角色优先：确保核心能力（如场地、技术、组织）有人覆盖

重要：
- 候选人数量应在 3-15 人之间
- 优先选择 relevance_score >= 70 的候选人
- 始终以有效的 JSON 格式输出"""
```

#### 2. 优化 _build_filter_prompt()

```python
def _build_filter_prompt(
    self, understanding: Dict, agents: List[Dict]
) -> str:
    """
    构建智能筛选提示词

    基于 PRD 中的提示词 2 设计
    """
    surface_demand = understanding.get('surface_demand', '')
    deep = understanding.get('deep_understanding', {})
    capability_tags = understanding.get('capability_tags', [])

    # 格式化 Agent 信息（限制每个 Agent 的信息量）
    agent_summaries = []
    for agent in agents[:50]:  # 最多处理 50 个 Agent
        summary = {
            "agent_id": agent.get("agent_id"),
            "display_name": agent.get("display_name", agent.get("agent_id")),
            "capabilities": agent.get("capabilities", [])[:5],  # 最多 5 个能力
            "location": agent.get("location", "未知"),
            "summary": agent.get("description", "")[:100]  # 限制描述长度
        }
        agent_summaries.append(summary)

    return f"""
# 智能筛选任务

## 需求信息

### 表面需求
{surface_demand}

### 深层理解
- **动机**: {deep.get('motivation', '未知')}
- **需求类型**: {deep.get('type', 'general')}
- **关键能力标签**: {', '.join(capability_tags) if capability_tags else '未指定'}
- **地点**: {deep.get('location', '未指定')}
- **规模**: {json.dumps(deep.get('scale', {}), ensure_ascii=False)}

### 不确定点
{json.dumps(understanding.get('uncertainties', []), ensure_ascii=False)}

## 候选 Agent 池（共 {len(agent_summaries)} 人）
```json
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}
```

## 输出要求

请以 JSON 格式输出筛选结果：

```json
{{
  "analysis": "简要分析筛选逻辑（50字以内）",
  "candidates": [
    {{
      "agent_id": "Agent 的 ID",
      "display_name": "Agent 显示名称",
      "reason": "选择该 Agent 的具体理由（30字以内）",
      "relevance_score": 85,
      "expected_role": "预期角色（如：场地提供者、技术顾问等）"
    }}
  ],
  "coverage": {{
    "covered": ["已覆盖的能力"],
    "uncovered": ["未覆盖的能力"]
  }}
}}
```
"""
```

#### 3. 增强 _parse_filter_response()

```python
def _parse_filter_response(
    self, response: str, agents: List[Dict]
) -> List[Dict]:
    """
    解析筛选响应

    增强解析鲁棒性，处理各种格式问题
    """
    try:
        # 尝试提取 JSON 块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接匹配 JSON 对象
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group()
            else:
                self._logger.warning("未找到有效 JSON")
                return []

        data = json.loads(json_str)
        candidates = data.get("candidates", [])

        # 验证候选人 ID 存在
        valid_ids = {a.get("agent_id") for a in agents}
        valid_candidates = []

        for candidate in candidates:
            agent_id = candidate.get("agent_id")
            if agent_id in valid_ids:
                # 补充显示名称（如果缺失）
                if not candidate.get("display_name"):
                    for agent in agents:
                        if agent.get("agent_id") == agent_id:
                            candidate["display_name"] = agent.get(
                                "display_name", agent_id
                            )
                            break
                valid_candidates.append(candidate)
            else:
                self._logger.warning(f"无效的 agent_id: {agent_id}")

        # 按 relevance_score 排序
        valid_candidates.sort(
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )

        # [v4] 最多返回 10 个
        return valid_candidates[:10]

    except json.JSONDecodeError as e:
        self._logger.error(f"JSON 解析错误: {e}")
        return []
    except Exception as e:
        self._logger.error(f"解析筛选响应错误: {e}")
        return []
```

---

## 接口契约

### 输入

```python
understanding: Dict = {
    "surface_demand": str,      # 表面需求
    "deep_understanding": {
        "motivation": str,
        "type": str,
        "location": str,
        "scale": dict
    },
    "capability_tags": List[str],
    "uncertainties": List[str]
}
```

### 输出

```python
candidates: List[Dict] = [
    {
        "agent_id": str,         # user_agent_bob
        "display_name": str,     # Bob
        "reason": str,           # 选择理由
        "relevance_score": int,  # 0-100
        "expected_role": str     # 预期角色
    }
]
```

---

## 依赖

### 硬依赖
- **T01**: demand.py 重构（需要 T01 提供的调用入口）

### 接口依赖
- 无

### 被依赖
- **T05**: 多轮协商逻辑

---

## 验收标准

- [x] **AC-1**: LLM 调用成功，返回有效的候选人列表
- [x] **AC-2**: [v4] 候选人数量在 **1-10 人之间**（最少 1 个，最多 10 个）
- [x] **AC-3**: 每个候选人都有 `relevance_score` 和 `reason`
- [x] **AC-4**: LLM 调用失败时，自动降级到 Mock 数据
- [x] **AC-5**: 筛选结果发布 `towow.filter.completed` 事件
- [x] **AC-6**: [v4] **筛选永不返回空列表**，失败时使用兜底候选（随机 3 个活跃 Agent）
- [x] **AC-7**: [v4] 兜底候选标记 `is_fallback: true`

### 测试用例

```python
@pytest.mark.asyncio
async def test_smart_filter_with_llm():
    """测试 LLM 智能筛选"""
    coordinator = CoordinatorAgent(llm=mock_llm_service)

    understanding = {
        "surface_demand": "办一场AI聚会",
        "capability_tags": ["场地提供", "技术分享"]
    }

    candidates = await coordinator._smart_filter("d-test", understanding)

    assert len(candidates) >= 3
    assert all("agent_id" in c for c in candidates)
    assert all("relevance_score" in c for c in candidates)

@pytest.mark.asyncio
async def test_smart_filter_fallback():
    """测试 LLM 不可用时降级"""
    coordinator = CoordinatorAgent(llm=None)

    candidates = await coordinator._smart_filter("d-test", {})

    # 应该返回 Mock 数据
    assert len(candidates) > 0
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
| LLM 输出格式不稳定 | 解析失败 | 增强解析鲁棒性，多种格式兼容 |
| Agent 数量过多 | 超出上下文限制 | 限制最多 50 个 Agent，压缩每个 Agent 信息 |
| 筛选质量不佳 | 候选人不匹配 | 提示词调优，降低温度参数 |

---

## 实现记录

### 完成日期
2026-01-23

### 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow/openagents/agents/coordinator.py` | 实现 v4 智能筛选功能 |
| `towow/tests/test_coordinator.py` | 添加 v4 测试用例 |

### 关键改动点

#### 1. `_get_filter_system_prompt()` - 更新系统提示词
- 候选人数量范围从 3-15 改为 1-10
- 增加"即使匹配度不高，也必须至少选择 1 个"的约束
- 明确要求每个候选人必须包含 reason 和 relevance_score 字段

#### 2. `_smart_filter()` - 添加兜底机制
- LLM 返回空结果时，调用 `_create_fallback_candidates()` 从数据库随机选择
- LLM 异常时，优先使用数据库兜底，其次使用 Mock 数据
- 确保永不返回空列表（AC-6）

#### 3. `_create_fallback_candidates()` - 新增方法
- 从可用 Agent 中随机选择最多 3 个作为兜底
- 所有兜底候选标记 `is_fallback: true`（AC-7）
- 设置 `relevance_score: 50`（中等分数）和 `reason: "兜底候选：系统自动选择"`

#### 4. `_parse_filter_response()` - 增强鲁棒性
- 最多返回 10 个候选人（从 15 改为 10，AC-2）
- 确保每个候选人有 reason、relevance_score、expected_role 字段（AC-3）
- 使用 agent_map 优化查找性能

#### 5. `_mock_filter()` - 支持 fallback 标记
- 新增 `is_fallback` 参数
- 当 `is_fallback=True` 时，为所有候选人添加 `is_fallback: true` 标记

### 调用链路

```
_smart_filter(demand_id, understanding)
    |
    +-- 无 LLM -> _mock_filter(understanding, is_fallback=False)
    |
    +-- 无数据库 Agent -> _mock_filter(understanding, is_fallback=False)
    |
    +-- LLM 调用成功
    |       |
    |       +-- 解析成功且有候选人 -> 返回 candidates[:10]
    |       |
    |       +-- 解析成功但无候选人 -> _create_fallback_candidates(available_agents)
    |
    +-- LLM 异常
            |
            +-- 有数据库 Agent -> _create_fallback_candidates(available_agents)
            |
            +-- 无数据库 Agent -> _mock_filter(understanding, is_fallback=True)
```

---

## 测试记录

### 测试命令
```bash
cd /Users/nature/个人项目/Towow/worktree-openagent/towow
python3 -m pytest tests/test_coordinator.py -v
```

### 测试结果
```
47 passed, 3 warnings in 0.11s
```

### 新增测试用例（TestSmartFilterV4）

| 测试用例 | 覆盖 AC | 说明 |
|---------|--------|------|
| `test_mock_filter_with_fallback_flag` | AC-7 | 验证 is_fallback 标记 |
| `test_create_fallback_candidates` | AC-6, AC-7 | 验证兜底候选生成 |
| `test_create_fallback_candidates_with_single_agent` | AC-6 | 验证单 Agent 兜底 |
| `test_smart_filter_uses_fallback_on_empty_llm_response` | AC-6, AC-7 | LLM 返回空时使用兜底 |
| `test_smart_filter_uses_fallback_on_llm_error` | AC-6, AC-7 | LLM 异常时使用兜底 |
| `test_smart_filter_max_10_candidates` | AC-2 | 验证最多 10 个候选人 |
| `test_parse_filter_response_ensures_required_fields` | AC-3 | 验证必填字段 |

### 更新的测试用例

| 测试用例 | 修改说明 |
|---------|----------|
| `test_get_filter_system_prompt` | 断言从 "3-15" 改为 "1-10" |
| `test_parse_limits_to_15` -> `test_parse_limits_to_10` | 限制从 15 改为 10 |
