# ToWow MVP 设计文档与技术方案对齐检查报告

> 技术架构师审核报告 | 2026-01-21

---

## 一、概念对齐矩阵

### 1.1 设计文档10个MVP概念覆盖检查

| # | 概念 | 设计要求 | 技术方案覆盖 | 状态 | 差异说明 |
|---|------|----------|-------------|------|----------|
| 1 | **统一身份** | user_id + secondme_id 映射 | `agent_profiles.agent_id` + `user_name` | **[PARTIAL]** | 技术方案缺少明确的 `user_id` 与 `secondme_id` 字段，使用了 `agent_id` 代替 |
| 2 | **Agent Card** | PostgreSQL存简介 | `agent_profiles` 表 | **[OK]** | 覆盖完整 |
| 3 | **三类Agent角色** | 中心管理员 + Channel管理员 + 用户Agent | Coordinator + ChannelAdmin + UserAgent | **[OK]** | 覆盖完整 |
| 4 | **Channel即协作室** | OpenAgent原生Channel | `collaboration_channels` 表 + OpenAgent Channel | **[OK]** | 覆盖完整 |
| 5 | **需求广播** | OpenAgent事件 | `demand.broadcast` 事件 | **[OK]** | 覆盖完整 |
| 6 | **智能筛选** | 直接LLM一步到位 | `smart_filter` 方法 | **[OK]** | 覆盖完整 |
| 7 | **Offer机制** | 核心流程 | `offer_response` 消息类型 | **[PARTIAL]** | 缺少独立的 `offers` 表，设计文档有 offer_id/confidence 等字段 |
| 8 | **多轮协商** | 最多5轮 | `max_rounds = 5` | **[OK]** | 覆盖完整 |
| 9 | **三个Skills** | 方案聚合 + 缺口识别 + 递归判断 | supplement-04 完整实现 | **[OK]** | 覆盖完整 |
| 10 | **子网递归** | 最多2层 | `MAX_DEPTH = 2` | **[OK]** | 覆盖完整 |

### 1.2 概念覆盖总结

- **完全覆盖**: 8/10 (80%)
- **部分覆盖**: 2/10 (20%)
- **未覆盖**: 0/10 (0%)

**需要修复的概念**:
1. **概念1-统一身份**: 需要在数据模型中明确 `user_id` 与 `secondme_id` 字段
2. **概念7-Offer机制**: 需要创建独立的 `offers` 表

---

## 二、流程对齐表

### 2.1 设计文档21步流程覆盖检查

| 步骤 | 设计文档流程 | 技术方案实现位置 | 状态 | 说明 |
|------|-------------|-----------------|------|------|
| 1 | 需求发起 | UserAgent.submit_demand() | **[OK]** | |
| 2 | 需求标准化 | SecondMe API /understand | **[OK]** | |
| 3 | 需求广播 | demand.broadcast 事件 | **[OK]** | |
| 4 | 智能筛选 | Coordinator._smart_filter() | **[OK]** | |
| 5 | 创建Channel | Coordinator._create_collaboration_channel() | **[OK]** | |
| 6 | 邀请Agents | Coordinator._invite_candidates() | **[OK]** | |
| 7 | Agents响应邀请 | UserAgent._handle_invite() | **[OK]** | |
| 8 | 收集Offers | ChannelAdmin._handle_offer_response() | **[OK]** | |
| 9 | [Skill 1]方案聚合 | ChannelAdmin._llm_aggregate() | **[OK]** | |
| 10 | 选择性分发 | ChannelAdmin._distribute_proposal() | **[OK]** | |
| 11 | Agents决策(第1轮) | UserAgent._handle_proposal_review() | **[OK]** | |
| 12 | 方案调整 | ChannelAdmin._adjust_proposal() | **[OK]** | |
| 13 | Agents决策(后续轮) | _process_all_feedbacks() | **[OK]** | |
| 14 | [Skill 2]识别缺口 | GapIdentificationService.identify_gaps() | **[OK]** | |
| 15 | [Skill 3]判断是否递归 | GapIdentificationService.should_trigger_subnet() | **[OK]** | |
| 16 | 触发子网 | SubnetManager._create_subnet() | **[OK]** | |
| 17 | 子网执行 | Coordinator._handle_subnet_demand() | **[OK]** | |
| 18 | 整合子网结果 | ChannelAdmin._integrate_subnet_results() | **[OK]** | |
| 19 | 发布最终方案 | ChannelAdmin._finalize_proposal() | **[OK]** | |
| 20 | Agents认领任务 | proposal_finalized 消息 | **[PARTIAL]** | 缺少 notify_user 实现 |
| 21 | Channel归档 | _update_channel_status("completed") | **[PARTIAL]** | 缺少明确的归档到 collaboration_history 表 |

### 2.2 流程覆盖总结

- **完全覆盖**: 19/21 (90%)
- **部分覆盖**: 2/21 (10%)
- **未覆盖**: 0/21 (0%)

**需要修复的流程**:
1. **步骤20**: 需要实现 SecondMe notify_user 调用
2. **步骤21**: 需要实现 collaboration_history 表写入

---

## 三、数据结构差异

### 3.1 Agent Card 字段对比

| 字段 | 设计文档 | 技术方案 | 状态 |
|------|----------|----------|------|
| agent_id | `agent_id` | `agent_id` | **[OK]** |
| user_id | `user_id` | - | **[MISSING]** |
| secondme_id | `secondme_id` | - | **[MISSING]** |
| secondme_mcp_endpoint | `secondme_mcp_endpoint` | - | **[MISSING]** |
| profile | `profile` (TEXT) | `profile_summary` (TEXT) | **[RENAMED]** |
| location | `location` | `location` | **[OK]** |
| tags | `tags` (JSONB) | - | **[MISSING]** |
| active | `active` | `status` (VARCHAR) | **[DIFFERENT]** |
| created_at | `created_at` | `created_at` | **[OK]** |
| - | - | `capabilities` (JSONB) | **[EXTRA]** |
| - | - | `interests` (JSONB) | **[EXTRA]** |
| - | - | `recent_focus` (TEXT) | **[EXTRA]** |
| - | - | `availability` (VARCHAR) | **[EXTRA]** |
| - | - | `collaboration_style` (JSONB) | **[EXTRA]** |
| - | - | `past_collaborations` (JSONB) | **[EXTRA]** |

### 3.2 Demand 字段对比

| 字段 | 设计文档 | 技术方案 | 状态 |
|------|----------|----------|------|
| demand_id | `demand_id` | `demand_id` (UUID) | **[OK]** |
| requester_id | `requester_id` | `initiator_agent_id` | **[RENAMED]** |
| description | `description` | `raw_input` + `surface_demand` | **[SPLIT]** |
| capability_tags | `capability_tags` (JSONB) | - | **[MISSING]** |
| context | `context` (JSONB) | `deep_understanding` (JSONB) | **[RENAMED]** |
| status | `status` | `status` | **[OK]** |
| - | - | `channel_id` | **[EXTRA]** |
| - | - | `parent_demand_id` | **[EXTRA]** |
| - | - | `depth` | **[EXTRA]** |

### 3.3 Offer 字段对比

| 字段 | 设计文档 | 技术方案 | 状态 |
|------|----------|----------|------|
| offer_id | `offer_id` | - | **[MISSING]** |
| agent_id | `agent_id` | 消息中的 agent_id | **[NO TABLE]** |
| demand_id | `demand_id` | - | **[MISSING]** |
| content | `content` | 消息中的 contribution | **[NO TABLE]** |
| structured_data | `structured_data` (JSONB) | - | **[MISSING]** |
| confidence | `confidence` | - | **[MISSING]** |
| submitted_at | `submitted_at` | - | **[MISSING]** |

### 3.4 数据结构差异总结

**需要修复的问题**:

1. **agent_profiles 表需要增加字段**:
   - `user_id` VARCHAR(255) - ToWow全局用户ID
   - `secondme_id` VARCHAR(255) - SecondMe用户ID
   - `secondme_mcp_endpoint` TEXT - SecondMe MCP端点
   - `tags` JSONB - 能力标签

2. **demands 表需要增加字段**:
   - `capability_tags` JSONB - 能力标签

3. **需要新增 offers 表**:
   - `offer_id` UUID PRIMARY KEY
   - `agent_id` VARCHAR(64) REFERENCES agent_profiles
   - `demand_id` UUID REFERENCES demands
   - `channel_id` VARCHAR(100)
   - `content` TEXT
   - `structured_data` JSONB
   - `confidence` INTEGER
   - `decision` VARCHAR(20) - participate/decline/need_more_info
   - `conditions` JSONB
   - `submitted_at` TIMESTAMP

---

## 四、事件类型差异

### 4.1 设计文档8个事件与技术方案对比

| # | 设计文档事件 | 技术方案事件 | 状态 | 说明 |
|---|-------------|-------------|------|------|
| 1 | `demand.broadcast` | `towow.demand.broadcast` | **[OK]** | 命名规范不同但对应 |
| 2 | `filter.completed` | `towow.filter.completed` | **[OK]** | |
| 3 | `channel.created` | `towow.channel.created` | **[OK]** | |
| 4 | `offer.submitted` | `towow.offer.submitted` | **[OK]** | |
| 5 | `plan.distributed` | `towow.proposal.distributed` | **[RENAMED]** | plan -> proposal |
| 6 | `agent.response` | `towow.proposal.feedback` | **[RENAMED]** | 语义变化 |
| 7 | `subnet.triggered` | `towow.subnet.triggered` | **[OK]** | |
| 8 | `plan.finalized` | `towow.proposal.finalized` | **[RENAMED]** | plan -> proposal |

### 4.2 技术方案额外事件

技术方案在 supplement-02 中定义了更多事件类型:

```
额外事件 (设计文档未定义):
- towow.demand.submitted
- towow.demand.accepted
- towow.demand.rejected
- towow.filter.started
- towow.channel.invite_sent
- towow.channel.closed
- towow.offer.requested
- towow.offer.timeout
- towow.proposal.aggregating
- towow.proposal.adjusting
- towow.gap.identified
- towow.subnet.completed
- towow.agent.online
- towow.agent.offline
- towow.error.occurred
```

### 4.3 事件类型差异总结

- **命名规范差异**: 设计文档使用 `xxx.xxx` 格式，技术方案使用 `towow.xxx.xxx` 格式
- **术语差异**: 设计文档用 `plan`，技术方案用 `proposal`
- **覆盖度**: 技术方案覆盖了设计文档所有事件，并扩展了更多事件类型

**建议**: 统一命名规范，在文档中明确说明 `plan` 与 `proposal` 是同一概念

---

## 五、成功标准可实现性评估

### 5.1 设计文档成功标准

| 成功标准 | 技术支撑 | 可实现性 |
|---------|---------|---------|
| 100个真实用户发起或响应需求 | UserAgent + 需求提交页面 | **[HIGH]** |
| 观众实时看到协商过程（流式展示） | SSE实时推送 (supplement-03) | **[HIGH]** |
| 至少一个触发子网递归的案例 | SubnetManager (supplement-04) | **[MEDIUM]** - 需要预设触发条件 |
| 2000人同时在线不崩溃 | 限流中间件 (supplement-05) | **[MEDIUM]** - 需要压力测试验证 |

### 5.2 风险点与建议

1. **子网递归案例**: 建议在演示模式中预设一个必定触发子网的需求（如"需要场地+摄影师"）
2. **2000人并发**: 当前限流设置为100并发，可能需要调整或增加队列机制
3. **流式展示**: SSE实现已完成，但需要测试大量客户端同时连接的稳定性

---

## 六、缺口清单

### 6.1 Critical（必须修复）

| ID | 缺口描述 | 涉及文档 | 影响 |
|----|---------|---------|------|
| GAP-001 | `offers` 表缺失 | 主文档 3.1节 | 无法持久化Offer数据 |
| GAP-002 | `user_id` 和 `secondme_id` 字段缺失 | 主文档 3.1节 | 不符合统一身份设计 |
| GAP-003 | `capability_tags` 字段在 demands 表缺失 | 主文档 3.2节 | 无法按能力标签筛选 |
| GAP-004 | Channel归档到 `collaboration_history` 未实现 | 主文档 4.3节 | 无法记录协作历史 |

### 6.2 High（建议修复）

| ID | 缺口描述 | 涉及文档 | 影响 |
|----|---------|---------|------|
| GAP-005 | SecondMe notify_user 接口未实现 | 主文档 6.1节 | 用户无法收到最终通知 |
| GAP-006 | 事件命名不一致（plan vs proposal） | supplement-02 | 前端对接可能混淆 |
| GAP-007 | `agent_profiles.tags` 字段缺失 | 主文档 3.1节 | 与设计文档数据结构不一致 |

### 6.3 Medium（可选修复）

| ID | 缺口描述 | 涉及文档 | 影响 |
|----|---------|---------|------|
| GAP-008 | 设计文档中的 `secret` 字段未在技术方案体现 | 设计文档 4.2节 | 安全性相关 |
| GAP-009 | 设计文档提到的 Redis 在技术方案中被移除 | 主文档 2.2节 | 缓存能力受限 |

---

## 七、修复方案

### 7.1 数据库Schema修复

```sql
-- 修复 GAP-002: 增加 user_id 和 secondme_id
ALTER TABLE agent_profiles
ADD COLUMN user_id VARCHAR(255),
ADD COLUMN secondme_id VARCHAR(255) UNIQUE,
ADD COLUMN secondme_mcp_endpoint TEXT,
ADD COLUMN tags JSONB;

CREATE INDEX idx_agent_user_id ON agent_profiles(user_id);
CREATE INDEX idx_agent_secondme_id ON agent_profiles(secondme_id);
CREATE INDEX idx_agent_tags ON agent_profiles USING GIN(tags);

-- 修复 GAP-003: demands 表增加 capability_tags
ALTER TABLE demands ADD COLUMN capability_tags JSONB;
CREATE INDEX idx_demand_tags ON demands USING GIN(capability_tags);

-- 修复 GAP-001: 创建 offers 表
CREATE TABLE offers (
    offer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) REFERENCES agent_profiles(agent_id),
    demand_id UUID REFERENCES demands(demand_id),
    channel_id VARCHAR(100),

    -- Offer内容
    decision VARCHAR(20) NOT NULL, -- participate | decline | need_more_info
    content TEXT,
    structured_data JSONB,
    conditions JSONB,
    confidence INTEGER DEFAULT 50,
    reasoning TEXT,

    -- 时间
    submitted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_offer_demand ON offers(demand_id);
CREATE INDEX idx_offer_agent ON offers(agent_id);
CREATE INDEX idx_offer_channel ON offers(channel_id);

-- 修复 GAP-004: 确保 collaboration_history 表存在
CREATE TABLE IF NOT EXISTS collaboration_history (
    history_id SERIAL PRIMARY KEY,
    demand_id UUID REFERENCES demands(demand_id),
    channel_id VARCHAR(100),

    -- 参与者信息
    invited_agents JSONB,
    participants JSONB,

    -- 方案信息
    final_proposal JSONB,

    -- 统计
    negotiation_rounds INTEGER,
    subnets_count INTEGER,
    total_duration_seconds INTEGER,

    -- 状态
    status VARCHAR(20), -- completed | failed | timeout

    -- 时间
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### 7.2 事件命名统一建议

在 supplement-02 中增加事件别名映射：

```python
# 事件别名（兼容设计文档命名）
EVENT_ALIASES = {
    "demand.broadcast": "towow.demand.broadcast",
    "filter.completed": "towow.filter.completed",
    "channel.created": "towow.channel.created",
    "offer.submitted": "towow.offer.submitted",
    "plan.distributed": "towow.proposal.distributed",  # plan -> proposal
    "agent.response": "towow.proposal.feedback",       # 语义映射
    "subnet.triggered": "towow.subnet.triggered",
    "plan.finalized": "towow.proposal.finalized",      # plan -> proposal
}
```

### 7.3 ChannelAdmin 归档逻辑补充

```python
async def _archive_channel(self, channel_id: str):
    """归档Channel到历史表"""
    state = self.channel_states.get(channel_id)
    if not state:
        return

    async with self.db.session() as session:
        from database.models import CollaborationHistory

        history = CollaborationHistory(
            demand_id=state["demand"].get("demand_id"),
            channel_id=channel_id,
            invited_agents=state.get("invited_agents", []),
            participants=[a["agent_id"] for a in state["current_proposal"].get("assignments", [])],
            final_proposal=state["current_proposal"],
            negotiation_rounds=state.get("round", 0),
            subnets_count=len(state.get("subnet_results", {})),
            total_duration_seconds=int((datetime.utcnow() - state.get("created_at", datetime.utcnow())).total_seconds()),
            status="completed",
            completed_at=datetime.utcnow()
        )
        session.add(history)
```

---

## 八、对齐检查总结

### 8.1 整体对齐度

| 维度 | 对齐度 | 说明 |
|------|--------|------|
| 概念覆盖 | 80% | 2个概念需要补充实现 |
| 流程覆盖 | 90% | 2个步骤需要完善 |
| 数据结构 | 70% | 需要增加字段和表 |
| 事件类型 | 95% | 命名差异，功能完整 |
| 成功标准 | 85% | 技术上可实现，需要验证 |

### 8.2 修复优先级

**P0 - 必须在开发前修复**:
1. 创建 `offers` 表 (GAP-001)
2. 增加 `user_id`, `secondme_id` 字段 (GAP-002)
3. 增加 `capability_tags` 字段 (GAP-003)

**P1 - 开发中修复**:
1. 实现 Channel 归档逻辑 (GAP-004)
2. 实现 notify_user 接口 (GAP-005)

**P2 - 可选修复**:
1. 统一事件命名 (GAP-006)
2. 增加 tags 字段 (GAP-007)

### 8.3 结论

技术方案整体覆盖了设计文档的核心需求，主要差异在于：
1. **数据模型细节**：技术方案采用了更简化的数据结构，需要补充部分字段
2. **Offer持久化**：技术方案将Offer作为消息处理，需要增加独立表以支持数据分析
3. **命名规范**：存在 plan/proposal 术语差异，建议统一

**建议行动**：
1. 立即执行 7.1 节的数据库Schema修复
2. 更新主技术方案文档，反映这些变更
3. 在开发过程中同步实现归档和通知功能

---

**文档版本**: v1.0
**创建时间**: 2026-01-21
**审核人**: Tech Architect Agent
**状态**: 审核完成，待执行修复
