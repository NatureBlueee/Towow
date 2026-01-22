# STORY-01: 需求理解

> **文档路径**: `.ai/epic-multiagent-negotiation/STORY-01-demand-understanding.md`
>
> * EPIC_ID: E-001
> * STORY_ID: STORY-01
> * 优先级: P0
> * 状态: 可开发
> * 创建日期: 2026-01-22

---

## 用户故事

**作为**一个有协作需求的用户
**我希望**输入自然语言描述我的需求，AI 能理解其深层含义
**以便**系统能更精准地匹配合适的协作者，而不只是关键词匹配

---

## 背景与动机

### 为什么需要"理解"而不是"解析"

用户的 Agent（SecondMe）已经深度了解用户，有用户的个性化记忆。我们的提示词不是让 AI "解析"用户说的话，而是让 AI "理解"用户真正想要什么。

**错误示范**：提取关键词、打标签、结构化解析
**正确思路**：你怎么理解这个需求？用户没说出口的是什么？

### 当前问题

现有 `demand.py` 中的需求理解是简单的透传：
```python
understanding = {
    "surface_demand": request.raw_input,
    "confidence": "high"
}
```
没有任何 LLM 调用，无法理解用户的深层需求。

---

## 验收标准

### AC-1: 表面需求提取
**Given** 用户输入 "我想在北京办一场AI主题聚会，需要场地和嘉宾"
**When** 系统调用需求理解提示词
**Then** 能提取出表面需求 "想在北京办一场AI主题聚会"

### AC-2: 深层需求推断
**Given** 用户输入包含上下文信息（如用户历史、偏好）
**When** 系统调用需求理解提示词
**Then** 能推断出：
- 用户为什么想办这个活动
- 用户可能的偏好（轻松氛围 vs 正式分享）
- 用户在意什么（质量 vs 规模）

### AC-3: 能力标签识别
**Given** 用户输入包含隐含的能力需求
**When** 系统调用需求理解提示词
**Then** 能识别出所需能力标签，如 `["场地提供", "演讲嘉宾", "活动策划"]`

### AC-4: 上下文提取
**Given** 用户输入包含约束条件
**When** 系统调用需求理解提示词
**Then** 能提取出：
- 地理位置
- 时间要求
- 预算范围
- 人数规模

### AC-5: 边界处理
**Given** 用户输入模糊或信息不足
**When** 系统调用需求理解提示词
**Then**
- 能标注不确定的字段为 `[TBD]`
- 不编造用户没说过的偏好
- 能给出合理的默认假设并标注

---

## 技术要点

### LLM 调用
- **提示词**: 提示词 1 - 需求理解
- **调用位置**: `services/llm.py` 或 `services/secondme.py`
- **模型**: Claude API

### 依赖模块
- `services/llm.py`: LLM 调用封装
- `api/routers/demand.py`: 需求提交入口

### 接口定义

**输入**:
```python
class DemandUnderstandRequest(BaseModel):
    raw_input: str          # 用户原始输入
    user_id: str            # 用户 ID
    user_context: dict = {} # 可选：用户上下文（历史、偏好）
```

**输出**:
```python
class DemandUnderstanding(BaseModel):
    surface_demand: str                    # 表面需求
    deep_understanding: dict               # 深层理解
    capability_tags: list[str]             # 能力标签
    context: dict                          # 提取的上下文
    uncertainties: list[str] = []          # 不确定的点
    confidence: str = "medium"             # 整体置信度
```

### 提示词模板

```
你是{用户名}的数字分身。

今天你听到了一个需求：
"{user_input}"

请帮我理解这个需求：

1. 表面需求：我字面上说的是什么？

2. 深层理解：基于你对我的了解，你觉得我真正想要的是什么？
   - 我为什么会提出这个需求？
   - 我之前有类似的经历吗？

3. 我的偏好：在这个需求里，我可能会更在意什么？
   - 什么样的方案会让我更满意？
   - 有什么是我没说出口但其实很在意的？

4. 边界：有什么是我可能不太能接受的？
   （如果不确定，可以说不确定，不要编造）

5. 能力标签：这个需求需要哪些能力来满足？

6. 上下文信息：提取出的时间、地点、人数、预算等约束

请基于用户记忆来回答，不要凭空想象。
输出 JSON 格式。
```

---

## 测试场景

| 场景 | 输入 | 预期输出 |
|------|------|----------|
| 正常场景 | "我想在北京办一场AI主题聚会，需要场地和嘉宾" | surface_demand: "想在北京办一场AI主题聚会", capability_tags: ["场地提供", "演讲嘉宾", "活动策划"], context: {location: "北京"} |
| 模糊输入 | "想找人一起搞点事情" | surface_demand: "想找人合作某个项目", uncertainties: ["具体想做什么不明确", "时间地点未知"], confidence: "low" |
| 复杂需求 | "下个月想在上海办一个50人的技术分享会，预算5000以内，需要场地、3个嘉宾、还要有茶歇" | context: {location: "上海", attendees: 50, budget: "5000", date: "下个月"}, capability_tags: ["场地提供", "演讲嘉宾", "茶歇服务"] |
| 边界场景 | "" (空输入) | 返回错误提示，要求用户提供更多信息 |

---

## UI 证据要求

- [ ] 需求输入框截图
- [ ] 理解结果展示截图（显示 surface_demand 和 capability_tags）
- [ ] 模糊输入时的提示 UI

---

## OPEN 事项

| 编号 | 问题 | 状态 |
|------|------|------|
| OPEN-1.1 | 用户上下文（历史记忆）在 MVP 阶段是否传入 | 待确认：MVP 先不传，用默认假设 |
| OPEN-1.2 | 能力标签是否需要预定义词表 | 待确认：MVP 先用 LLM 自由生成 |

---

## 关联文档

- PRD: `./PRD-multiagent-negotiation-v3.md` (F1 章节)
- 提示词: `/docs/提示词清单.md` (提示词 1)
- 技术方案: `/docs/tech/TECH-TOWOW-MVP-v1.md` (6.1 章节)
