# ToWow 产品全流程示例 - OpenAgent 迁移参考

> **目标读者**: OpenAgent 开发者
> **目的**: 展示 ToWow 多 Agent 协商平台的完整业务流程，便于迁移到 OpenAgent 框架

---

## 一、业务场景

### 场景描述

用户小明想找人帮他开发一个电商网站，他在 ToWow 平台提交需求：

```
"我想做一个电商网站，预算 5 万，2 个月内上线，需要支持微信支付"
```

系统需要：
1. 理解用户需求
2. 从候选人库中筛选合适的服务商
3. 让多个服务商 Agent 进行协商竞争
4. 聚合最优方案呈现给用户
5. 收集用户反馈，多轮协商直到达成一致

---

## 二、Agent 角色定义

### 2.1 系统级 Agent

| Agent | 职责 | OpenAgent 映射 |
|-------|------|----------------|
| **Coordinator** | 需求理解、候选人筛选、创建协商频道 | WorkerAgent + 自定义 Tool |
| **ChannelAdmin** | 管理协商频道、聚合方案、分发反馈、识别缺口 | WorkerAgent + State Machine |

### 2.2 动态 Agent（每个候选人一个）

| Agent | 职责 | OpenAgent 映射 |
|-------|------|----------------|
| **UserAgent** | 代表候选人生成报价、评估方案、提交反馈 | WorkerAgent（动态创建） |

### 2.3 Agent 数量

```
一次协商涉及的 Agent:
- 1 x Coordinator
- 1 x ChannelAdmin
- N x UserAgent (N = 筛选出的候选人数量，通常 5-10 个)
```

---

## 三、完整流程示例

### Step 0: 用户提交需求

**用户输入:**
```json
{
  "content": "我想做一个电商网站，预算 5 万，2 个月内上线，需要支持微信支付",
  "user_id": "user-xiaoming"
}
```

**系统响应:**
```json
{
  "demand_id": "d-abc123",
  "status": "processing",
  "message": "需求已提交，正在为您匹配服务商..."
}
```

---

### Step 1: Coordinator 理解需求

**Coordinator 调用 LLM 分析需求:**

```
Input: "我想做一个电商网站，预算 5 万，2 个月内上线，需要支持微信支付"

LLM Output:
{
  "demand_type": "software_development",
  "keywords": ["电商", "网站", "微信支付"],
  "constraints": {
    "budget": 50000,
    "deadline": "2 months",
    "payment": "wechat_pay"
  },
  "required_skills": ["web_development", "ecommerce", "payment_integration"]
}
```

**发出事件:** `towow.demand.understood`

---

### Step 2: Coordinator 筛选候选人

**Coordinator 查询候选人库:**

```sql
SELECT * FROM candidates
WHERE skills CONTAINS ('web_development', 'ecommerce')
AND available = true
ORDER BY rating DESC
LIMIT 10
```

**筛选结果:** 10 个候选人

| ID | 名称 | 技能 | 评分 |
|----|------|------|------|
| c-001 | 张工作室 | web, ecommerce, payment | 4.8 |
| c-002 | 李开发 | web, ecommerce | 4.6 |
| c-003 | 王团队 | fullstack, ecommerce | 4.5 |
| ... | ... | ... | ... |

**发出事件:** `towow.filter.completed`

```json
{
  "event_type": "towow.filter.completed",
  "payload": {
    "demand_id": "d-abc123",
    "candidate_count": 10,
    "candidates": ["c-001", "c-002", "c-003", ...]
  }
}
```

---

### Step 3: Coordinator 创建协商频道

**创建频道:**
```json
{
  "channel_id": "collab-abc123",
  "demand_id": "d-abc123",
  "participants": ["c-001", "c-002", ..., "c-010"],
  "status": "collecting_responses"
}
```

**为每个候选人创建 UserAgent:**

```python
for candidate in candidates:
    user_agent = UserAgent(
        agent_id=f"ua-{candidate.id}",
        candidate=candidate,
        channel_id="collab-abc123"
    )
    # 注册到 OpenAgent 网络
    network.register(user_agent)
```

**发出事件:** `towow.channel.created`

---

### Step 4: ChannelAdmin 广播需求

**ChannelAdmin 向所有 UserAgent 发送需求:**

```json
{
  "message_type": "demand_broadcast",
  "channel_id": "collab-abc123",
  "demand": {
    "content": "我想做一个电商网站...",
    "constraints": {
      "budget": 50000,
      "deadline": "2 months"
    }
  }
}
```

**发出事件:** `towow.demand.broadcast`

---

### Step 5: 每个 UserAgent 生成 Offer（综合性回应）

**重要：Offer 不是简单的"报价"，是基于 Agent 个人能力、记忆、偏好的综合性回应！**

**UserAgent (张工作室) 调用 SecondMe MCP 生成 Offer:**

```
SecondMe 基于用户的 HMM 记忆生成个性化 offer：
- 张工作室有 10 年电商开发经验
- 最近刚完成一个类似项目
- 对微信支付特别熟悉
- 最近时间比较充裕
```

**Offer 数据结构（综合性回应）:**
```json
{
  "offer_id": "offer_001",
  "agent_id": "c-001",
  "demand_id": "d-abc123",
  "content": "我有10年电商开发经验，刚完成一个类似的服装电商项目。微信支付我特别熟，还做过退款和对账功能。最近时间充裕，可以全职投入。如果项目有意思，价格可以商量。",
  "structured_data": {
    "resource_type": "技术开发",
    "experience": "10年电商",
    "recent_project": "服装电商，2个月前完成",
    "specialty": ["微信支付", "退款对账", "会员系统"],
    "availability": "全职投入",
    "cost_flexibility": "可商量"
  },
  "confidence": 95,
  "personal_note": "这个项目和我之前做的很像，很有信心能做好"
}
```

**UserAgent (李开发) 的 Offer - 不同的视角:**
```json
{
  "offer_id": "offer_002",
  "agent_id": "c-002",
  "content": "我是独立开发者，擅长快速交付。虽然经验没那么久，但我用的技术栈很新，可以更快上手。我可以做前后端，但支付部分可能需要学习一下。",
  "structured_data": {
    "resource_type": "全栈开发",
    "experience": "3年",
    "tech_stack": ["React", "Node.js", "最新框架"],
    "strength": "快速交付",
    "weakness": "支付经验少",
    "availability": "兼职，每天6小时"
  },
  "confidence": 75,
  "personal_note": "想通过这个项目学习支付集成"
}
```

**UserAgent (王团队) 的 Offer - 团队视角:**
```json
{
  "offer_id": "offer_003",
  "agent_id": "c-003",
  "content": "我们是5人团队，可以分工协作。有专门的UI设计师、前端、后端、测试。我们做过很多电商项目，流程很成熟。缺点是沟通成本高一些，需要明确的需求文档。",
  "structured_data": {
    "resource_type": "团队开发",
    "team_size": 5,
    "roles": ["UI设计", "前端", "后端", "测试", "项目经理"],
    "strength": "分工明确，流程成熟",
    "requirement": "需要详细需求文档",
    "availability": "可以立即开始"
  },
  "confidence": 90,
  "personal_note": "团队正好有空档期，可以优先处理这个项目"
}
```

**每个 Agent 的 Offer 都是独特的、个性化的，反映了他们自己的能力、偏好、限制。**

**发出事件:** `towow.offer.submitted` (每个 Agent 一个，并行)

---

### Step 6: ChannelAdmin 聚合方案（Skill 1: 方案聚合）

**收集到 10 个 Offers 后，ChannelAdmin 调用 LLM 进行方案聚合：**

```
LLM Prompt:
原始需求：电商网站，预算5万，2个月，需要微信支付

收到的 Offers：
1. c-001 (张工作室): 10年电商经验，微信支付专精，全职投入，价格可商量
2. c-002 (李开发): 3年经验，技术栈新，支付经验少，兼职
3. c-003 (王团队): 5人团队，流程成熟，需要需求文档
4. c-004 (赵设计): 专业UI设计，不做开发
5. c-005 (孙测试): 专业测试，可兼职
...
10. c-010 (周运维): 服务器部署和运维

请完成以下任务：
1. 分析哪些 Offers 对满足需求是必要的
2. 选出最相关的 5-8 个
3. 为每个被选中的 Agent 分配具体任务
4. 考虑 Agent 之间的协作关系
```

**LLM 聚合结果（不是简单分配预算，而是任务和角色）:**
```json
{
  "selected_agents": ["c-001", "c-003", "c-004", "c-005"],
  "plan": {
    "c-001": {
      "role": "技术负责人 + 核心开发",
      "specific_task": "负责架构设计、后端开发、微信支付集成",
      "why_selected": "微信支付专精，经验丰富",
      "dependencies": ["需要 c-004 提供UI设计稿"]
    },
    "c-003": {
      "role": "前端开发",
      "specific_task": "团队出一人负责前端实现",
      "why_selected": "团队有前端专人，可以和 c-001 配合",
      "dependencies": ["依赖 c-004 的设计", "依赖 c-001 的接口"]
    },
    "c-004": {
      "role": "UI/UX 设计",
      "specific_task": "设计电商网站整体界面和交互",
      "why_selected": "专业设计师，可以保证视觉质量",
      "dependencies": []
    },
    "c-005": {
      "role": "测试",
      "specific_task": "负责功能测试和支付流程测试",
      "why_selected": "专业测试，确保支付安全",
      "dependencies": ["在开发完成后介入"]
    }
  },
  "not_selected": {
    "c-002": "支付经验不足，且只能兼职",
    "c-010": "当前阶段不需要运维，可能后期需要"
  },
  "rationale": "选择了一个经验丰富的技术负责人（c-001）+ 团队前端支持（c-003）+ 专业设计（c-004）+ 专业测试（c-005）的组合，可以保证质量和进度"
}
```

**发出事件:** `towow.aggregation.completed`

---

### Step 7: ChannelAdmin 选择性分发方案给被选中的 Agent

**重要：方案只发给被选中的 Agent，不是发给用户！**

**方案内容（给每个 Agent 看的是他们的具体任务和整体协作关系）:**

```json
{
  "event_type": "towow.proposal.distributed",
  "payload": {
    "channel_id": "collab-abc123",
    "round": 1,
    "recipients": ["c-001", "c-003", "c-004", "c-005"],
    "overall_goal": "电商网站，预算5万，2个月",
    "tasks": {
      "c-001": {
        "role": "技术负责人 + 核心开发",
        "specific_task": "架构设计、后端开发、微信支付集成",
        "collaborators": ["c-003 负责前端", "c-004 负责设计"],
        "dependencies": ["等待 c-004 的设计稿"]
      },
      "c-003": {
        "role": "前端开发",
        "specific_task": "前端页面实现",
        "collaborators": ["配合 c-001 的接口"],
        "dependencies": ["等待 c-004 的设计", "等待 c-001 的API"]
      },
      "c-004": {
        "role": "UI/UX 设计",
        "specific_task": "整体界面和交互设计",
        "collaborators": ["设计稿给 c-001 和 c-003"],
        "dependencies": []
      },
      "c-005": {
        "role": "测试",
        "specific_task": "功能和支付流程测试",
        "collaborators": ["验收各方产出"],
        "dependencies": ["在开发完成后介入"]
      }
    },
    "timeline": "总工期2个月，设计2周→开发5周→测试1周",
    "next_steps": "请各位确认是否接受安排，或提出调整建议"
  }
}
```

**未被选中的 Agent 不会收到方案（隐式知道"我这次没被需要"）**

---

### Step 8: 每个 Agent 评估方案并给出反馈

**这是 Agent 之间的协商，不是用户参与！**

**每个被选中的 Agent 基于自己的情况评估方案，给出三种响应之一：**

**Agent c-001 (张工作室) - Accept:**
```json
{
  "agent_id": "c-001",
  "response_type": "accept",
  "message": "我接受技术负责人的角色。架构设计和微信支付都是我擅长的，没问题。",
  "additional_thoughts": "建议 c-004 的设计稿最好在第一周出来，这样我可以尽早开始后端设计"
}
```

**Agent c-003 (王团队) - Negotiate:**
```json
{
  "agent_id": "c-003",
  "response_type": "negotiate",
  "message": "前端开发可以，但我们团队习惯整体接项目。只出一个人做前端，我们内部资源浪费了。建议让我们团队也参与部分后端工作，可以加快进度。",
  "proposed_changes": {
    "expand_scope": "前端 + 部分后端模块（如商品管理）",
    "reason": "团队协作效率更高，可以缩短工期"
  }
}
```

**Agent c-004 (赵设计) - Accept with condition:**
```json
{
  "agent_id": "c-004",
  "response_type": "accept",
  "message": "设计没问题，但需要先明确几个问题：网站风格是什么？有参考网站吗？目标用户是谁？",
  "conditions": ["需要需求方提供风格参考", "需要明确目标用户群"],
  "commitment": "明确后可以在2周内出设计稿"
}
```

**Agent c-005 (孙测试) - Accept:**
```json
{
  "agent_id": "c-005",
  "response_type": "accept",
  "message": "测试工作没问题。我建议在开发过程中就介入，做一些冒烟测试，不用等到最后。",
  "additional_thoughts": "可以提前准备测试用例和自动化脚本"
}
```

**发出事件:** `towow.feedback.submitted` (每个 Agent 一个)

---

### Step 9: ChannelAdmin 根据 Agent 反馈调整方案

**ChannelAdmin 分析所有 Agent 的反馈，调用 LLM 调整方案：**

```
第1轮反馈汇总:
- c-001: accept，建议设计稿第一周出
- c-003: negotiate，希望扩大范围（前端+部分后端）
- c-004: accept with condition，需要风格参考和用户画像
- c-005: accept，建议提前介入测试

分析:
- c-003 的建议有道理，团队整体参与效率更高
- c-004 的条件合理，需要补充信息
- c-005 的建议很好，可以提高质量

调整方案:
1. c-003 范围扩大：前端 + 商品管理模块
2. c-001 范围调整：架构设计 + 订单系统 + 支付集成
3. 补充 c-004 需要的信息（从原始需求中提取或标记为待确认）
4. c-005 提前介入，从第3周开始
```

**发出事件:** `towow.proposal.distributed` (Round 2)

---

### Step 10: 第2轮 Agent 协商

**ChannelAdmin 发送调整后的方案：**
```json
{
  "round": 2,
  "changes_summary": "根据大家反馈调整了分工",
  "updated_tasks": {
    "c-001": {
      "role": "技术架构 + 核心系统",
      "scope_change": "移除商品管理（给c-003），专注订单和支付"
    },
    "c-003": {
      "role": "前端 + 商品管理",
      "scope_change": "扩大范围，团队可以整体参与"
    },
    "c-004": {
      "additional_info": "风格参考：简约现代，目标用户：25-40岁白领",
      "note": "如需更多信息，可以直接问需求方"
    },
    "c-005": {
      "timeline_change": "从第3周开始介入，边开发边测试"
    }
  }
}
```

**第2轮各 Agent 评估...**

---

### Step 11: 第3轮协商达成一致

**经过调整，所有 Agent 接受：** 4个 accept

```json
{
  "event_type": "towow.negotiation.round_completed",
  "payload": {
    "channel_id": "collab-abc123",
    "round": 3,
    "result": "all_accepted",
    "final_allocation": {
      "c-001": "技术架构 + 订单系统 + 支付集成",
      "c-003": "前端开发 + 商品管理模块",
      "c-004": "UI/UX 设计",
      "c-005": "测试（第3周起介入）"
    },
    "collaboration_notes": [
      "c-004 第1周出设计稿",
      "c-001 和 c-003 并行开发",
      "c-005 从第3周开始做冒烟测试"
    ]
  }
}
```

---

### Step 12: ChannelAdmin 识别缺口

**协商达成一致后，ChannelAdmin 调用 Skill 2 识别缺口：**

```
当前方案:
- 主开发: c-001
- 支付集成: c-003
- UI设计: c-005

原始需求分析:
- 需要: 电商网站、微信支付、2个月上线
- 当前: 有开发、有支付、有UI
- 缺口: 无（方案完整）

或者如果有缺口:
- 缺口: 服务器运维（无人负责部署和运维）
- 重要性: 70%
```

**发出事件:** `towow.gap.identified`

---

### Step 13: 智能递归判断（如果有缺口）

**如果识别到缺口，ChannelAdmin 调用 Skill 3 判断是否触发子网：**

```
缺口: 服务器运维
三重条件判断:
1. 需求满足度: 当前80% → 递归后95% ✓
2. 利益相关方: c-001表示"如果有运维支持，我可以更专注开发" ✓
3. 成本效益: 递归成本5000 tokens，收益显著 ✓

决定: 触发子网递归
```

**发出事件:** `towow.subnet.triggered`

---

### Step 14: 子网执行（如果触发）

```
创建子 Channel: collab-abc123-sub-1
子需求: "寻找服务器运维，负责电商网站部署"
子网协商...
子网结果: c-012 负责运维，预算 5000元
```

**子结果返回父 Channel，整合进最终方案**

---

### Step 15: 协商完成，通知用户

**所有协商完成后（Agent 们达成一致 + 缺口处理完毕），ChannelAdmin 生成最终方案并通知用户：**

```json
{
  "event_type": "towow.negotiation.finalized",
  "payload": {
    "channel_id": "collab-abc123",
    "total_rounds": 3,
    "final_result": {
      "participants": [
        {"agent_id": "c-001", "role": "主开发", "budget": 33000},
        {"agent_id": "c-003", "role": "支付集成", "budget": 10000},
        {"agent_id": "c-005", "role": "UI设计", "budget": 7000}
      ],
      "total_budget": 50000,
      "timeline": "45天",
      "scope": "电商网站（商品管理、订单系统、微信支付，不含会员系统）",
      "agreement": "各方已达成一致"
    }
  }
}
```

**用户最终看到的是已协商好的完整方案，而非需要用户参与协商！**

---

## 四、事件流总览（修正版）

```
Timeline:

T+0s    [USER]        提交需求
        [SYSTEM]      → towow.demand.submitted

T+2s    [COORDINATOR] LLM 理解需求
        [COORDINATOR] → towow.demand.understood

T+3s    [COORDINATOR] 查询数据库筛选候选人
        [COORDINATOR] → towow.filter.completed (10 candidates)

T+4s    [COORDINATOR] 创建频道，注册 UserAgent
        [COORDINATOR] → towow.channel.created

T+5s    [CHANNEL_ADMIN] 广播需求
        [CHANNEL_ADMIN] → towow.demand.broadcast

T+7s~T+20s  [USER_AGENT_*] 各 Agent LLM 生成报价（并行）
            [USER_AGENT_*] → towow.offer.submitted (x10)

T+22s   [CHANNEL_ADMIN] LLM 聚合方案，选出5个Agent
        [CHANNEL_ADMIN] → towow.aggregation.completed

T+23s   [CHANNEL_ADMIN] 选择性分发方案给5个被选中的Agent
        [CHANNEL_ADMIN] → towow.proposal.distributed (Round 1)

--- 第1轮 Agent 协商 ---

T+25s~T+35s  [USER_AGENT_*] 各 Agent LLM 评估方案
             [USER_AGENT_*] → towow.feedback.submitted (accept/negotiate)

T+36s   [CHANNEL_ADMIN] 分析反馈，调整方案
        [CHANNEL_ADMIN] → towow.proposal.distributed (Round 2)

--- 第2轮 Agent 协商 ---

T+38s~T+48s  [USER_AGENT_*] 各 Agent 再次评估
             [USER_AGENT_*] → towow.feedback.submitted

T+49s   [CHANNEL_ADMIN] 再次调整
        [CHANNEL_ADMIN] → towow.proposal.distributed (Round 3)

--- 第3轮 Agent 协商 ---

T+51s~T+60s  [USER_AGENT_*] 所有 Agent accept
             [CHANNEL_ADMIN] → towow.negotiation.round_completed

T+62s   [CHANNEL_ADMIN] 识别缺口
        [CHANNEL_ADMIN] → towow.gap.identified (无缺口/有缺口)

T+63s   [CHANNEL_ADMIN] 判断是否递归
        (如有缺口) → towow.subnet.triggered

T+90s   [CHANNEL_ADMIN] 子网结果返回，整合最终方案
        [CHANNEL_ADMIN] → towow.negotiation.finalized

T+91s   [USER_AGENT_*] 通知各参与方的人类用户
        [SYSTEM]      → 用户看到最终方案
```

---

## 五、核心设计点（修正版）

### 5.1 用户只参与开始和结束

```
用户的参与点：
1. 开始：提交需求（自然语言描述）
2. 结束：查看最终协商结果

用户不参与的部分：
- 候选人筛选（Coordinator 自动完成）
- 方案聚合（ChannelAdmin 自动完成）
- 多轮协商（Agent 之间自动完成）
- 缺口识别和子网递归（ChannelAdmin 自动完成）

这就是"AI 代理协商"的核心价值：
用户只需要说"我要什么"，Agent 们自己去谈判、协调、达成一致。
```

### 5.2 Agent 的三种响应模式

```
当 Agent 收到方案时，必须给出三种响应之一：

1. Accept（接受）
   - "我接受这个安排"
   - 无需进一步协商

2. Negotiate（协商）
   - "我有意见，建议调整..."
   - 提供具体的修改建议
   - ChannelAdmin 会尝试调整方案

3. Reject（拒绝并退出）
   - Agent 直接退出 Channel
   - 不需要解释原因
   - ChannelAdmin 会重新分配任务或标记需求失败
```

### 5.3 多轮协商的终止条件

```
成功终止：
- 所有被选中的 Agent 都回复 "accept"
- 进入缺口识别阶段

达到上限终止（最多5轮）：
- 如果大部分 Agent 已 accept → 继续，标记未 accept 的为"可选参与者"
- 如果核心 Agent 未 accept → 标记需求为"协商失败"

异常终止：
- 核心 Agent 退出（如唯一的主开发退出）
- ChannelAdmin 重新筛选或通知需求无法满足
```

### 5.1 网络配置 (network.yaml)

```yaml
name: towow-negotiation
description: ToWow Multi-Agent Negotiation Network

agents:
  - name: coordinator
    type: worker
    config:
      system_prompt: "你是需求协调者..."
      tools:
        - query_candidates
        - create_channel

  - name: channel_admin
    type: worker
    config:
      system_prompt: "你是协商频道管理员..."
      tools:
        - aggregate_proposals
        - identify_gaps

# UserAgent 动态创建，不在配置中定义

events:
  - towow.demand.submitted
  - towow.demand.understood
  - towow.filter.completed
  - towow.channel.created
  - towow.demand.broadcast
  - towow.offer.submitted
  - towow.aggregation.completed
  - towow.proposal.distributed
  - towow.feedback.submitted
  - towow.gap.identified
  - towow.offer.updated
  - towow.negotiation.finalized
```

### 5.2 Coordinator Agent (coordinator.py)

```python
from openagents import WorkerAgent, on_event

class Coordinator(WorkerAgent):

    @on_event("towow.demand.submitted")
    async def handle_demand(self, event):
        # 1. LLM 理解需求
        understanding = await self.llm.analyze(event.content)
        await self.publish("towow.demand.understood", understanding)

        # 2. 筛选候选人
        candidates = await self.tools.query_candidates(understanding.keywords)
        await self.publish("towow.filter.completed", {"candidates": candidates})

        # 3. 创建频道
        channel = await self.tools.create_channel(event.demand_id, candidates)
        await self.publish("towow.channel.created", channel)
```

### 5.3 ChannelAdmin Agent (channel_admin.py)

```python
from openagents import WorkerAgent, on_event

class ChannelAdmin(WorkerAgent):

    def __init__(self):
        self.channels = {}  # channel_id -> ChannelState

    @on_event("towow.channel.created")
    async def handle_channel_created(self, event):
        # 初始化频道状态
        self.channels[event.channel_id] = ChannelState(
            participants=event.participants,
            status="collecting_responses"
        )
        # 广播需求
        await self.broadcast_demand(event.channel_id, event.demand)

    @on_event("towow.offer.submitted")
    async def handle_offer(self, event):
        state = self.channels[event.channel_id]
        state.offers[event.candidate_id] = event.offer

        # 检查是否收集完成
        if len(state.offers) == len(state.participants):
            await self.aggregate_proposals(event.channel_id)

    async def aggregate_proposals(self, channel_id):
        state = self.channels[channel_id]
        # LLM 聚合
        proposal = await self.llm.aggregate(state.offers)
        await self.publish("towow.proposal.distributed", proposal)
```

### 5.4 UserAgent (user_agent.py)

```python
from openagents import WorkerAgent, on_message

class UserAgent(WorkerAgent):

    def __init__(self, candidate):
        self.candidate = candidate
        self.system_prompt = f"你是{candidate.name}的代理，专长：{candidate.skills}"

    @on_message("demand_broadcast")
    async def handle_demand(self, message):
        # LLM 生成报价
        offer = await self.llm.generate_offer(
            demand=message.demand,
            candidate=self.candidate
        )
        await self.publish("towow.offer.submitted", {
            "candidate_id": self.candidate.id,
            "offer": offer
        })

    @on_message("proposal_review")
    async def handle_feedback(self, message):
        # LLM 评估是否更新报价
        evaluation = await self.llm.evaluate_feedback(
            feedback=message.feedback,
            current_offer=self.current_offer
        )
        if evaluation.should_update:
            await self.publish("towow.offer.updated", evaluation.new_offer)
```

---

## 六、关键设计点

### 6.1 真实 LLM 调用（非 Mock）

```
重要：每个步骤都是真实的 LLM 调用，不是模拟！

- Coordinator.analyze() → 真实 LLM
- UserAgent.generate_offer() → 真实 LLM
- ChannelAdmin.aggregate() → 真实 LLM

LLM 调用本身需要时间（2-5秒），这就是自然的"阶段感"，不需要人为延迟。
```

### 6.2 事件驱动依赖

```
依赖关系通过事件自然表达：

demand.submitted
  → (Coordinator 处理)
  → filter.completed
  → (Coordinator 处理)
  → channel.created
  → (ChannelAdmin 处理)
  → demand.broadcast
  → (UserAgent 处理)
  → offer.submitted (多个)
  → (ChannelAdmin 等待全部)
  → aggregation.completed
  → ...

前一步完成自然触发后一步，不需要延迟或轮询。
```

### 6.3 动态 Agent 创建

```python
# 候选人数量不固定，UserAgent 需要动态创建
for candidate in filtered_candidates:
    agent = UserAgent(candidate)
    network.register(agent, lifetime="channel")  # 频道结束后自动注销
```

---

## 七、与现有代码的映射

| 现有代码 | OpenAgent 迁移 |
|----------|----------------|
| `towow/openagents/agents/coordinator.py` | `openagents/agents/coordinator.py` (继承 WorkerAgent) |
| `towow/openagents/agents/channel_admin.py` | `openagents/agents/channel_admin.py` (继承 WorkerAgent) |
| `towow/openagents/agents/user_agent.py` | `openagents/agents/user_agent.py` (继承 WorkerAgent) |
| `towow/openagents/agents/router.py` | **删除** (使用 OpenAgent 内置路由) |
| `towow/events/event_bus.py` | **删除** (使用 OpenAgent 内置事件系统) |
| `towow/config.py` 中的延迟配置 | **删除** (不需要延迟) |

---

## 八、总结

这个示例展示了 ToWow 产品的完整业务流程：

1. **3 类 Agent**: Coordinator, ChannelAdmin, UserAgent
2. **12 种事件**: 从 demand.submitted 到 negotiation.finalized
3. **多轮协商**: 支持用户反馈和多轮优化
4. **真实 LLM 调用**: 每个决策点都是真实的 LLM 调用
5. **事件驱动**: 依赖关系通过事件自然表达

迁移到 OpenAgent 后，可以利用框架内置的：
- Agent 生命周期管理
- 消息路由
- 事件系统
- Studio UI 监控
- 多协议支持

**下一步**: 参考 `openagents/llm.txt` 和 `openagents/demos/` 开始实现。
