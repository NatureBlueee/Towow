ToWow MVP 设计文档（完整版）
基于OpenAgent的AI代理协作网络

---
## MVP概念总览（2026-01-21确认）

### MVP必须实现的概念
| 概念 | 简化程度 | 说明 |
|------|---------|------|
| 概念1：统一身份 | 简化 | 只做 user_id + secondme_id 映射 |
| 概念2：Agent Card | **大幅简化** | PostgreSQL存简介，不做断线重连/A2A |
| 概念3：三类Agent角色 | 保持 | 中心管理员 + Channel管理员 + 用户Agent |
| 概念4：Channel即协作室 | 直接用 | OpenAgent原生Channel |
| 概念5：需求广播 | 简化 | 就是一个OpenAgent事件 |
| 概念6：智能筛选 | **大幅简化** | 直接LLM一步到位，不做规则层 |
| 概念7：Offer机制 | 保持 | 核心流程 |
| 概念8：多轮协商 | 保持 | 最多5轮 |
| 概念9：三个Skills | 保持 | 方案聚合 + 缺口识别 + 递归判断 |
| 概念10：子网递归 | 简化 | 最多2层 |
| 概念11：Agent多实例 | 不用管 | OpenAgent原生支持 |
| 概念12：统一接口 | 简化 | 只做SecondMe适配器 |

### 未来实现的概念（MVP不做）
| 概念 | 优先级 | 什么时候做 |
|------|--------|-----------|
| 概念13：Context作为Agent | V2 | 有成功案例后 |
| A2A协议 | V2 | 需要跨网络时 |
| 断线重连token | V2 | 用户量大后 |
| 端侧筛选 | V3 | 去中心化演进 |
| Offer缓存/知识沉淀 | V2 | 有数据积累后 |
| 静音机制 | V2 | 网络规模扩大后 |
| 等候室 | V3 | 做零工市场时 |
| Agent验证/信誉系统 | V3 | Web3集成时 |

### 并发架构确认
```
┌──────────────────────────────────────────────────────────┐
│                   中心管理员Agent（1个，常驻）              │
│  - 监听 demand.broadcast，异步处理多个筛选请求              │
└──────────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Channel管理员   │ │ Channel管理员   │ │ Channel管理员   │
│ (需求1)        │ │ (需求2)        │ │ (需求3)        │
│ 独立协商       │ │ 独立协商       │ │ 独立协商       │
└────────────────┘ └────────────────┘ └────────────────┘
                           │
┌──────────────────────────────────────────────────────────┐
│  用户Agents池（每用户1个，可同时在多个Channel）             │
│  agent_alice: 在Channel1(发起者) + Channel2(响应者)       │
│  agent_bob: 在Channel1(响应者) + Channel3(响应者)         │
└──────────────────────────────────────────────────────────┘
```

---
目录
1. 设计背景与目标
2. 当前MVP核心概念
3. 总体流程设计
4. 基于OpenAgent的技术架构
5. MVP实现范围与优先级
6. 未来演进方向
7. 关键风险与应对

---
第一部分：设计背景与目标
1.1 为什么做这个MVP（设计原因）
核心验证假设： 上千个agent的网络是可以通信并产生涌现协商效果的。
具体验证目标：
1. 让2000人现场看到AI agents真的在协商，而不是在表演
2. 展示SecondMe自己的孤立网络做不到的跨agent协作能力
3. 积累用户数据，且数据结构能适配未来任何入口
4. 展示ToWow协议的核心机制：主体筛选、主动响应、协商方案、子网递归
成功标准：
- 现场至少100个真实用户发起或响应需求
- 观众能够实时看到协商过程（流式展示）
- 至少出现一个触发子网递归的案例
- 系统在2000人同时在线时不崩溃

---
1.2 我们要实现什么（设计要求）
必须体现的核心能力：
1. 主体筛选：网络中的agents根据规则/算法自主判断是否响应需求
2. 主动响应：agents看到需求后主动提交offer，而非被动等待分配
3. 协商方案：多个agents的offers被中心agent聚合成可执行方案
4. 多轮协商：agents可以对方案提出异议、补充，经过迭代达成共识
5. 子网递归：复杂需求自动触发下层子网（至少2层）
必须展示的涌现效果：
- 方案的细节足够丰富和真实（体现SecondMe的个性化记忆）
- 协商过程是实时可见的，观众能看到"AI在思考和讨论"
- 不同用户的相同需求会产生不同的响应组合（体现网络的动态性）
必须积累的数据资产：
- 用户身份（与具体入口解耦，支持未来多入口）
- Agent能力画像（capabilities、availability）
- 成功的协作案例（为未来的offer缓存奠定基础）

---
1.3 我们拥有的条件（设计条件）
OpenAgent提供的能力：
- 网络运行与稳定连接：维护海量agents的在线状态
- 事件分发机制：标准化的事件订阅/发布系统
- Channel管理：创建、成员管理、消息路由、权限控制
- Agent连接管理：注册、心跳、断线重连
- Agent Groups：分组与权限管理
SecondMe提供的能力：
- 深度个性化的用户理解（HMM记忆系统）
- 训练好的大模型（理解和生成个性化内容）
- MCP协议支持（可以被外部系统调用）
- OAuth登录（用户无需管理API key）
时间和资源条件：
- 开发时间：约8天（2月1日前）
- 预算：成本不是问题（LLM调用、服务器都可以）
- 人力：你+平静（两人协作开发）
- 现场环境：2000人规模分享会，需要大屏展示

---
1.4 我们面临的限制（设计限制）
架构限制：
- SecondMe只是一个可插拔的入口，我们做的是协议层，不是为SecondMe定制
- 用户在网络中只能有一个身份，无论从什么入口进来
- MVP不做offer缓存机制（每次都实时协商）
- MVP采用邀请制，agents不能主动加入channel
简化限制（MVP范围控制）：
- 中心agent的能力通过独立的skills实现，不做复杂的"智能"
- 子网递归最多2层
- 多轮协商最多5轮
- 不做需求的"标准/非标"分类，统一处理
技术限制：
- 现场2000人同时在线，必须考虑性能
- 需要做限流，但不能影响演示效果
- 前端必须流式输出，不能等所有结果出来再显示
- OpenAgent Python版本稳定性有待验证（Go版本未发布）

---
第二部分：当前MVP核心概念
概念1：统一身份（Unified Identity）
定义： 用户在ToWow网络中的全局唯一标识，与具体接入平台（SecondMe、未来的其他agent平台）解耦。
设计原因：
- SecondMe只是我们预设的一个接口，我们做的是协议层产品
- 用户可能未来通过其他入口使用ToWow，但应该能识别为同一个人
- 数据结构要支持简单迁移和适配
设计思路： 用户在网络中只有一个user_id（ToWow全局ID），可以关联多个平台账号（如secondme_id、未来的platform_x_id）。首次登录时创建user_id，后续从其他入口登录时可以绑定到同一个user_id。
数据结构：
{
  "user_id": "towow_user_001",
  "secondme_id": "sm_abc123",
  "platform_x_id": null,  // 未来扩展
  "created_at": "2026-01-21T10:00:00Z"
}

---
概念2：Agent Card（Agent Card）
定义： 每个agent在网络中的"身份证"，包含能力描述、简介信息。持久化存储在PostgreSQL。

**MVP简化设计（2026-01-21确认）**：
- ✅ 只做PostgreSQL存储Agent简介
- ❌ 不做断线重连token机制（MVP只用一天，掉线重新登录即可）
- ❌ 不做A2A协议（单一网络，用OpenAgent原生gRPC/HTTP连接）

设计原因：
- MVP是演示场景，只运行几小时，断线重连不是核心需求
- 简化开发复杂度，聚焦核心协商流程

Agent Card数据结构（MVP简化版）：
{
  "agent_id": "agent_alice",
  "user_id": "towow_user_001",
  "secondme_id": "sm_abc123",
  "secondme_mcp_endpoint": "https://secondme.io/mcp/sm_abc123",
  "profile": "AI创业者，有一家咖啡厅可以提供活动场地，位于北京朝阳区，可容纳50人。周末和工作日晚上都有空。对AI应用和创业话题感兴趣。",
  "location": "北京",
  "tags": ["场地", "创业", "AI"],  // 可选，辅助筛选
  "created_at": "2026-01-21T10:00:00Z",
  "active": true
}

MVP流程：
1. 用户通过SecondMe OAuth登录
2. 创建Agent Card，存入PostgreSQL
3. 连接OpenAgent网络（gRPC 8600）
4. 如果掉线？重新登录，重新连接

**未来演进方向（V2+）**：
- 断线重连token机制
- A2A跨网络通信协议
- 端侧筛选，agents自主判断是否响应

---
概念3：三类Agent角色（Three Agent Roles）
定义： 在OpenAgent网络中，agents按功能分为三类角色，每类有不同的权限和职责。
角色1：中心管理员Agent（Central Admin Agent）
职责：
- 维护全局Agent Card注册表
- 处理用户筛选请求
- 返回候选agent_id列表
权限：
- 可以查询所有注册agents的信息
- 可以执行智能筛选算法
实现：
- 单例agent，网络启动时创建
- 持续在线，监听"需求广播"事件
对应关系： 原设计中"Agent注册表"的查询接口
角色2：Channel管理员Agent（Channel Admin Agent）
职责：
- 协调单个需求的协商过程
- 邀请agents加入channel
- 收集offers，聚合方案
- 进行多轮协商
- 判断是否触发子网递归
- 生成最终方案
权限：
- 可以邀请agents加入channel
- 可以向选定的agents发送消息
- 可以创建子channel（触发递归）
实现：
- 每个需求创建时自动生成
- channel_id与demand_id一一对应
- 需求完成后归档
对应关系： 原设计中的"中心协调Agent"
角色3：用户Agent（User Agent）
职责：
- 代表人类用户或服务
- 响应需求，提交offer
- 参与多轮协商
- 接收最终方案，通知用户
权限：
- 只有在channel内的聊天权限
- 不能主动加入channel（MVP阶段，只能被邀请）
- 可以退出channel
实现：
- 与SecondMe实例一一对应
- 长期在线（或待命状态）
- 可以同时参与多个channels
对应关系： 原设计中的"端侧Agent"

---
概念4：Channel即协作室（Channel as Collaboration Room）
定义： OpenAgent的Channel机制天然对应ToWow的"临时协作室"。每个需求创建一个专属channel，邀请相关agents加入协商。
设计原因：
- OpenAgent已经实现了channel的生命周期管理
- 不需要自己实现协作室的底层通信逻辑
- Channel的权限系统可以直接用于控制agent参与
Channel配置：
channel_id: "dm_001"  # 与demand_id相同
channel_type: "private"  # MVP只用private
created_by: "coordinator_dm_001"  # Channel管理员agent
members:
  - "agent_alice"  # 需求发起者
  - "agent_bob"    # 被邀请的响应者
  - "agent_charlie"
  - ...
与原设计的映射：
- 原"临时协作室" → OpenAgent的private channel
- 原"Redis存储协作室状态" → OpenAgent内置的channel状态管理
- 原"WebSocket推送" → OpenAgent的事件系统

---
概念5：需求广播（Demand Broadcasting）
定义： 用户通过自己的agent向整个网络发送需求信息的过程。需求以标准化格式表达，包含描述、能力标签、上下文等。
设计原因：
- 用户不知道网络中谁能帮忙，所以需要"广播"而非"点对点"
- 这是去中心化市场发现的起点
- 广播触发整个协作流程
需求对象数据结构：
{
  "demand_id": "dm_001",
  "requester_id": "agent_alice",
  "description": "我想在北京办一场AI主题聚会，需要场地和愿意分享的嘉宾",
  "capability_tags": ["场地提供", "演讲嘉宾", "活动策划"],
  "context": {
    "location": "北京",
    "expected_attendees": 50,
    "date": "2026-02-15",
    "budget": "5000元以内"
  },
  "status": "broadcasting",
  "created_at": "2026-01-22T10:00:00Z"
}
广播流程：
1. 用户通过SecondMe agent输入自然语言需求
2. 系统调用LLM提取能力标签和上下文
3. 创建Demand对象，存入PostgreSQL
4. 向OpenAgent网络发送"demand.broadcast"事件
5. 中心管理员agent监听到事件，触发智能筛选
MVP不做的事情：
- 不判断"标准需求"vs"非标需求"（统一按广播处理）
- 不做需求去重或聚合
- 不做需求的复杂性预判

---
概念6：智能筛选（Intelligent Filtering）
定义： 从网络的agents中，识别出与当前需求相关的10-20个候选agents。

**MVP简化设计（2026-01-21确认）**：
- ✅ 直接把所有Agent简介丢给LLM，一步到位输出候选列表
- ❌ 不做两层筛选（规则SQL + LLM语义）
- ❌ 不做能力标签体系设计

设计原因：
- 现代LLM上下文足够大（Claude 200K tokens），100个agent简介约50K tokens，完全够用
- 简化开发，不需要设计复杂的能力标签和SQL查询
- LLM理解自然语言比规则匹配更灵活

**MVP筛选流程**：
```
需求来了
    ↓
中心管理员Agent读取所有Agent简介（从PostgreSQL）
    ↓
把需求 + 所有简介一起丢给LLM
    ↓
LLM直接输出：应该邀请哪些agent_id
    ↓
中心管理员Agent把列表交给Channel管理员
    ↓
Channel管理员直接拉人进Channel
```

**筛选提示词**：
```
你是ToWow网络的中心调度Agent。

有一个新需求：
{demand_description}

需求上下文：
{demand_context}

以下是网络中所有在线agents的简介：
---
{all_agent_profiles}
---

请分析这个需求需要什么能力，然后从上面的agents中选出最合适的10-20个人。

输出JSON格式：
{
  "analysis": "这个需求需要...",
  "selected_agents": ["agent_id_1", "agent_id_2", ...],
  "reasons": {
    "agent_id_1": "选择原因",
    "agent_id_2": "选择原因"
  }
}
```

**性能考虑**：
- 假设100个agent，每人简介500字 = 5万字 ≈ 25K tokens
- 一次筛选调用约3-5秒，可接受
- 如果agent数量超过200，可以考虑先按location过滤

**未来演进方向（V2+）**：
- 两层筛选：规则快速过滤 + LLM精细判断（当agent数量>500时）
- 端侧筛选：需求广播给所有agent，各自判断是否响应

---
概念7：Offer机制（Offer Mechanism）
定义： Agent响应需求时提交的结构化方案内容，描述"我能提供什么帮助"。Offer是agents参与协作的基本单位。
设计原因：
- 需要一个标准格式让agents表达自己的贡献
- Channel管理员agent需要可解析的结构化数据
- Offer是未来"知识沉淀"的基础（MVP不做）
Offer数据结构：
{
  "offer_id": "offer_001",
  "agent_id": "agent_bob",
  "demand_id": "dm_001",
  "content": "我有一家咖啡厅可以提供活动场地，位于北京朝阳区，可容纳50人。周末和工作日晚上都可以。场地费可以商量，如果活动有价值可以免费提供。",
  "structured_data": {
    "resource_type": "场地",
    "location": "北京朝阳区",
    "capacity": 50,
    "availability": ["周末", "工作日晚上"],
    "cost": "可协商"
  },
  "confidence": 90,
  "submitted_at": "2026-01-22T10:05:00Z"
}
生成流程：
1. Agent收到协作邀请
2. 调用SecondMe的MCP接口：generate_offer(demand_description)
3. SecondMe基于用户的HMM记忆生成个性化offer
4. Agent提交offer到channel
MVP限制：
- 每个agent只能提交一次offer（不允许修改）
- Offer内容由SecondMe自由生成，系统不强制结构
- 不做offer质量评分（所有offer同等对待）

---
概念8：选择性分发与多轮协商（Selective Distribution & Multi-Round Negotiation）
定义： Channel管理员agent在收集所有offers后，只向被选中的agents分发初步方案，并允许最多5轮的反馈-调整循环，直到所有相关agents接受方案。
设计原因：
- 避免无关agents参与不必要的讨论
- 允许agents对方案提出异议和补充
- 确保最终方案是所有参与者都接受的
- 体现"真实协商"而非"单向分配"
选择性分发逻辑
为什么不分发给所有agents？
- 避免无关agents看到不需要他们的方案（减少困惑）
- 只让真正参与协作的agents进行后续讨论（提高效率）
- 未被选中的agents自然知道"我这次没被需要"（隐式反馈）
方案内容示例：
{
  "plan_version": 1,
  "demand_id": "dm_001",
  "recipients": ["agent_bob", "agent_charlie", "agent_diana"],
  "tasks": {
    "agent_bob": {
      "role": "场地提供方",
      "specific_task": "提供咖啡厅场地，容纳50人，2月15日下午2-5点",
      "dependencies": ["需要agent_diana确认活动流程"],
      "notes": "场地费可协商"
    },
    "agent_charlie": {
      "role": "演讲嘉宾",
      "specific_task": "分享AI应用案例，时长30分钟",
      "dependencies": [],
      "notes": "可提供技术demo"
    },
    "agent_diana": {
      "role": "活动策划",
      "specific_task": "设计活动流程，协调各方",
      "dependencies": [],
      "notes": "有类似活动经验"
    }
  },
  "overall_timeline": "2月15日 14:00-17:00",
  "next_steps": "请各位确认是否接受安排，或提出调整建议"
}
Agents的三种响应模式
模式A：接受（Accept）
{
  "agent_id": "agent_bob",
  "response_type": "accept",
  "message": "我接受这个安排，咖啡厅场地没问题，可以免费提供"
}
模式B：协商（Negotiate）
{
  "agent_id": "agent_charlie",
  "response_type": "negotiate",
  "message": "我可以做演讲嘉宾，但希望时长调整为45分钟，因为案例比较复杂，需要充分讲解",
  "proposed_changes": {
    "duration": "45分钟",
    "reason": "案例复杂，需要demo演示"
  }
}
模式C：拒绝并退出（Reject）
- Agent直接退出channel（调用OpenAgent的leave_channel）
- 不需要解释原因（简化流程）
- Channel管理员检测到member.left事件
多轮协商流程
第1轮：
- 管理员发送初步方案给5个agents
- 3个accept，2个negotiate

第2轮：
- 管理员根据negotiate的反馈调整方案
- 重新发送给5个agents
- 4个accept，1个negotiate

第3轮：
- 管理员再次调整
- 5个全部accept

→ 协商成功，进入下一步
终止条件：
成功终止：
- 所有被选中的agents都回复"accept"
- 进入识别缺口阶段
达到上限终止：
- 已经进行了5轮协商，仍有agents未accept
- Channel管理员判断： 
  - 如果大部分agents已accept，继续（标记未accept的为"可选参与者"）
  - 如果核心agents未accept，标记需求为"协商失败"，通知发起者
异常终止：
- 核心agent退出（如唯一的场地提供方退出）
- Channel管理员重新筛选或通知需求无法满足

---
概念9：Channel管理员的三个Skills（Three Skills of Coordinator）
定义： Channel管理员agent通过三个独立的LLM skills来完成协调工作，每个skill负责特定任务。
Skill 1：方案聚合（Plan Aggregation）
输入：
- 原始需求描述
- 所有agents提交的offers（如10个）
任务：
1. 分析每个offer的内容和价值
2. 判断哪些offers是真正需要的（如选出5个）
3. 将选中的offers整合成结构化方案
4. 明确每个被选中agent的具体任务和依赖关系
输出：
- 初步方案（JSON格式）
- 被选中的agent_id列表
LLM Prompt示例：
原始需求：{demand.description}

收到的offers：
1. agent_bob: {offer_content}
2. agent_charlie: {offer_content}
...
10. agent_kevin: {offer_content}

请完成以下任务：
1. 判断哪些offers对满足需求是必要的
2. 选出5-8个最相关的offers
3. 为每个被选中的agent分配具体任务
4. 标注任务之间的依赖关系

返回JSON格式：
{
  "selected_agents": ["agent_bob", "agent_charlie", ...],
  "tasks": {
    "agent_bob": {
      "role": "...",
      "specific_task": "...",
      "dependencies": [...]
    },
    ...
  },
  "rationale": "为什么选择这些agents"
}
Skill 2：缺口识别（Gap Identification）
输入：
- 原始需求描述
- 多轮协商后的最终接受方案
- 所有参与agents的反馈
任务：
1. 判断当前方案是否完整满足需求
2. 识别缺失的资源或能力
3. 评估缺口的严重程度
输出：
- 缺口列表（如：["摄影师", "茶歇服务"]）
- 每个缺口的重要性评分
LLM Prompt示例：
原始需求：{demand.description}

当前方案：
- 场地：agent_bob提供咖啡厅（50人）
- 嘉宾：agent_charlie分享AI案例（45分钟）
- 策划：agent_diana协调流程

请判断：
1. 这个方案是否完整满足需求？
2. 还缺少哪些资源或能力？
3. 缺口的重要性如何？

返回JSON：
{
  "is_complete": false,
  "gaps": [
    {
      "type": "摄影师",
      "importance": 70,
      "reason": "需要记录活动内容，用于后续传播"
    },
    {
      "type": "茶歇服务",
      "importance": 40,
      "reason": "提升参与体验，但非必需"
    }
  ]
}
Skill 3：智能递归判断（Intelligent Recursion Decision）
输入：
- 原始需求描述
- 识别出的缺口列表
- 当前方案和agents反馈
- 预估的递归成本（Token、时间）
任务： 基于三重条件判断是否触发子网递归
三重条件：
1. 需求满足度提升：递归能显著提升需求的完成度（如从70%→90%）
2. 利益相关方满意度：现有参与agents认为递归有价值
3. 成本效益比：递归的Token成本与收益成正比
输出：
- 是否递归（true/false）
- 如果递归，生成子需求列表
LLM Prompt示例：
原始需求：{demand.description}
当前方案：{aggregated_plan}
Agents反馈：{agent_responses}
识别的缺口：{gaps}

请判断触发递归是否满足以下三个条件：

条件1：能更好满足原始需求
- 当前需求满足度：估计70%（有场地和嘉宾，但无记录）
- 递归后满足度：预计90%（增加摄影师）
- 提升幅度：20%

条件2：能让所有利益相关方更满意
- 场地方agent_bob说："如果有摄影记录，我愿意免费提供场地"
- 嘉宾agent_charlie说："有摄影的话，我可以分享更深入内容"

条件3：Token使用效率最大化
- 预估递归成本：5000 tokens（创建子网、筛选摄影师、协商）
- 预估收益：需求满足度提升20%，现有参与者满意度提升
- 成本效益比：收益/成本 > 1.5（阈值）

请返回JSON：
{
  "should_recurse": true,
  "condition_1_met": true,
  "condition_1_analysis": "满足度从70%提升到90%，提升20%，超过15%阈值",
  "condition_2_met": true,
  "condition_2_analysis": "场地方和嘉宾都明确表示递归后会提供更多价值",
  "condition_3_met": true,
  "condition_3_analysis": "成本5000 tokens，收益显著，比值约2.0",
  "sub_demands": [
    {
      "description": "寻找摄影师，拍摄AI主题聚会（2月15日，北京）",
      "capability_tags": ["摄影", "活动拍摄"],
      "priority": "high"
    }
  ]
}

---
概念10：子网递归（Recursive Subnet）
定义： 当单层协作网络无法满足需求时，自动创建下层子协作网络的机制。子网使用相同的协作流程，最终将结果返回给父网络。
设计原因：
- 复杂需求需要多层级供应链
- 递归是ToWow"最小完备性"的体现（同一个机制，无限扩展）
- 展示"道生一，一生二，二生三，三生万物"的理念
递归触发流程：
父Channel（dm_001）：
- Skill 2识别缺口："需要摄影师"
- Skill 3判断：满足三重条件，决定递归
- 生成子需求："寻找摄影师..."
    ↓
创建子Channel（dm_001_sub_1）：
- 子需求广播
- 智能筛选：找到3个摄影师agents
- 邀请、收集offers、协商
- 生成子方案："agent_kevin提供摄影服务"
    ↓
子结果返回父Channel：
- 父管理员收到："摄影师已找到，agent_kevin"
- 整合进最终方案
数据关联：
{
  "parent_demand_id": "dm_001",
  "parent_channel_id": "dm_001",
  "sub_demand_id": "dm_001_sub_1",
  "sub_channel_id": "dm_001_sub_1",
  "depth": 1,
  "sub_result": {
    "摄影师": {
      "提供者": "agent_kevin",
      "详情": "专业活动摄影，提供照片和视频"
    }
  }
}
MVP限制：
- 最多2层递归（depth <= 2）
- 不做循环检测（假设2层内不会出现循环依赖）
- 子网与父网是独立的channels，不共享参与者

---
概念11：Agent多实例模型（Multi-Instance Agent Model）
定义： 单个agent可以同时参与多个channels，每个channel对应一个独立的"实例"，实例之间不互相影响。
设计原因：
- 用户可能同时发起需求（作为需求方）和响应需求（作为提供方）
- 一个agent可能被多个需求邀请参与
- 需要支持并发场景
实现思路： Agent在逻辑上是单一的（对应一个user_id），但在运行时可以有多个"会话"。每个会话绑定到一个channel，会话之间独立：
- 独立的上下文（不同需求的历史）
- 独立的状态（有的在等待响应，有的在提交offer）
- 独立的通信通道
示例场景：
agent_alice同时处于：
- Channel_A（dm_001）：作为需求发起者，发起"办AI聚会"的需求
- Channel_B（dm_002）：作为响应者，提供"场地"的offer
- Channel_C（dm_003）：作为响应者，提供"活动策划"的offer

每个channel的交互互不影响
技术实现：
- 通过异步任务（asyncio）或消息队列实现
- 每个channel的消息推送到独立的处理函数
MVP限制：
- 不做实例数量限制（假设每个agent最多参与5个channels）
- 不做智能的"精力分配"（所有实例同等优先级）
- 实例之间不共享状态（如"我在另一个channel已经承诺提供场地了"）

---
概念12：统一接口/可插拔接口（Pluggable Interface）
定义： ToWow协议层定义标准化的agent接入接口，任何符合接口规范的agent系统（SecondMe、未来的其他平台）都可以接入网络。
设计原因：
- 我们做的是协议层，不是为某个特定平台定制
- 要实现"无敌的商业"（其他团队做类似网络时，我们可以互联）
- SecondMe只是第一个接入者，不应该是唯一的接入者
标准化接口定义：
class AgentInterface:
    """ToWow协议的标准Agent接口"""
    
    async def get_capabilities(self) -> dict:
        """获取agent的能力描述"""
        pass
    
    async def judge_relevance(self, demand: dict) -> bool:
        """判断是否响应需求"""
        pass
    
    async def generate_offer(self, demand: dict) -> dict:
        """生成offer"""
        pass
    
    async def evaluate_plan(self, plan: dict) -> str:
        """评估方案，返回accept/negotiate/reject"""
        pass
    
    async def notify_user(self, message: dict):
        """通知用户"""
        pass
SecondMe适配器实现：
class SecondMeAdapter(AgentInterface):
    """SecondMe的ToWow适配器"""
    
    def __init__(self, secondme_mcp_endpoint: str):
        self.mcp_endpoint = secondme_mcp_endpoint
    
    async def generate_offer(self, demand: dict) -> dict:
        # 调用SecondMe的MCP接口
        response = await call_mcp(
            self.mcp_endpoint,
            prompt=f"有人需要：{demand['description']}。你能提供什么帮助？"
        )
        return {
            "content": response.text,
            "confidence": response.confidence
        }
MVP限制：
- 只实现SecondMe适配器
- 接口规范在MVP阶段可能不够完善，需要迭代
- 不做复杂的"协议翻译"

---
概念13：Context作为Agent（Context as Agent）
定义： 不仅人类用户的SecondMe可以作为agent接入网络，任何"上下文"（服务、资源、知识库、工作流）都可以包装为agent，使用相同的通信协议。
设计原因：
- 避免为"用户agent"和"服务agent"设计两套不同的架构
- 保持系统的最小完备性（统一抽象）
- 让系统更容易扩展（任何东西都可以成为agent）
设计思路： 无论是人类用户（通过SecondMe）还是一个服务（如"某咖啡厅的场地预订服务"），在ToWow网络中都是一个agent。区别仅在于：
- User Agent：背后是人的SecondMe记忆
- Service Agent：背后是服务的context描述
两者使用相同的接口、相同的注册流程、相同的协作流程。
示例：Service Agent
{
  "agent_id": "service_coffee_house",
  "type": "service",
  "capabilities": ["场地提供"],
  "context": {
    "service_name": "某某咖啡厅",
    "location": "北京朝阳区",
    "capacity": 50,
    "available_times": ["周末", "工作日晚上"],
    "pricing": "按小时收费，500元/小时"
  },
  "response_logic": "rule-based"  // 可以是规则引擎，不一定需要LLM
}
MVP限制：
- 主要focus在User Agent（SecondMe）
- Service Agent作为概念验证（可以手工创建1-2个）
- 不做复杂的"context → agent"自动转换工具

---
第三部分：总体流程设计
3.1 主流程：单层协作（完整版）
步骤1：需求发起
用户通过SecondMe输入："我想在北京办一场AI主题聚会，需要场地和嘉宾"
    ↓
步骤2：需求标准化
- 调用LLM提取能力标签：["场地提供", "演讲嘉宾", "活动策划"]
- 提取上下文：{location: "北京", attendees: 50, ...}
- 创建Demand对象（demand_id = "dm_001"）
- 存入PostgreSQL
    ↓
步骤3：需求广播
用户agent（agent_alice）向OpenAgent网络发送事件：
{
  "event_type": "demand.broadcast",
  "payload": {demand对象}
}
    ↓
步骤4：智能筛选
中心管理员agent监听到事件：
- 读取Agent Card注册表
- 执行两层筛选（规则+LLM）
- 获得候选列表：["agent_bob", "agent_charlie", ..., "agent_kevin"]（共20个）
    ↓
步骤5：创建Channel
中心管理员agent调用OpenAgent API：
- create_channel(channel_id="dm_001", type="private")
- 自动生成Channel管理员agent（coordinator_dm_001）
    ↓
步骤6：邀请Agents
Channel管理员agent逐一邀请20个候选agents：
- invite_to_channel(channel_id="dm_001", agent_id="agent_bob")
- invite_to_channel(channel_id="dm_001", agent_id="agent_charlie")
- ...
    ↓
步骤7：Agents响应邀请
每个被邀请的agent：
- 收到邀请通知（OpenAgent事件）
- 调用SecondMe MCP：judge_relevance(demand)
- 如果愿意响应：
  - 加入channel
  - 调用SecondMe MCP：generate_offer(demand)
  - 提交offer到channel
    ↓
步骤8：收集Offers
Channel管理员agent收集所有offers（假设收到10个）
    ↓
步骤9：[Skill 1] 方案聚合
- 分析10个offers
- 判断只需要5个（agent_bob, charlie, diana, eric, frank）
- 为每个被选中的agent分配具体任务
- 生成初步方案（plan_version_1）
    ↓
步骤10：选择性分发
Channel管理员只向5个被选中的agents发送方案
未被选中的5个agents不会收到
    ↓
步骤11：Agents决策（第1轮）
- agent_bob: "accept"
- agent_charlie: "negotiate"（希望时长45分钟）
- agent_diana: "accept"
- agent_eric: "negotiate"（需要确认茶歇预算）
- agent_frank: "accept"
    ↓
步骤12：方案调整（第2轮）
Channel管理员根据negotiate反馈调整方案：
- 时长改为45分钟
- 茶歇预算明确为500元
- 生成plan_version_2
- 重新发送给5个agents
    ↓
步骤13：Agents决策（第2轮）
- 所有5个agents: "accept"
    ↓
步骤14：[Skill 2] 识别缺口
分析最终接受的方案：
- 有场地、嘉宾、策划、茶歇
- 缺少：摄影师、宣传渠道
    ↓
步骤15：[Skill 3] 判断是否递归
评估三重条件：
- 条件1：✓ 增加摄影师，满足度从75%→90%
- 条件2：✓ 场地方表示"有摄影记录愿意降价"
- 条件3：✓ 递归成本5000 tokens，收益显著
决定：触发递归（寻找摄影师），不递归（宣传渠道优先级低）
    ↓
步骤16：触发子网
Channel管理员发送事件：
{
  "event_type": "subnet.trigger",
  "payload": {
    "parent_demand_id": "dm_001",
    "sub_demand": {
      "description": "寻找摄影师，拍摄AI主题聚会（2月15日，北京）",
      "capability_tags": ["摄影", "活动拍摄"]
    }
  }
}
    ↓
步骤17：子网执行
重复步骤2-13（递归调用，depth=1）：
- 创建子Channel（dm_001_sub_1）
- 筛选摄影师agents
- 协商
- 返回结果："agent_kevin提供摄影服务"
    ↓
步骤18：整合子网结果
父Channel管理员收到子网结果：
- 将agent_kevin加入最终方案
- 更新方案：plan_final
    ↓
步骤19：发布最终方案
Channel管理员将完整方案发送到channel：
{
  "final_plan": {
    "场地": {agent_bob, 详情},
    "嘉宾": {agent_charlie, 详情},
    "策划": {agent_diana, 详情},
    "茶歇": {agent_eric, 详情},
    "布置": {agent_frank, 详情},
    "摄影": {agent_kevin, 详情}
  },
  "status": "finalized"
}
    ↓
步骤20：Agents认领任务
每个参与的agent看到最终方案：
- 识别自己的任务部分
- 调用SecondMe MCP：notify_user(plan)
- SecondMe向人类用户发送通知
    ↓
步骤21：Channel归档
Channel管理员：
- 标记channel状态为"completed"
- OpenAgent归档channel历史
- 数据写入PostgreSQL（供未来分析）

---
3.2 事件流示例
事件1：需求广播
{
  "event_type": "demand.broadcast",
  "timestamp": "2026-01-22T10:00:00Z",
  "payload": {
    "demand_id": "dm_001",
    "requester_id": "agent_alice",
    "description": "我想在北京办一场AI主题聚会，需要场地和愿意分享的嘉宾",
    "capability_tags": ["场地提供", "演讲嘉宾", "活动策划"],
    "context": {
      "location": "北京",
      "expected_attendees": 50,
      "date": "2026-02-15"
    }
  }
}
事件2：筛选完成
{
  "event_type": "filter.completed",
  "timestamp": "2026-01-22T10:01:00Z",
  "payload": {
    "demand_id": "dm_001",
    "candidates": [
      "agent_bob",
      "agent_charlie",
      "agent_diana",
      // ... 共20个
    ],
    "filter_method": "rule+llm",
    "duration_ms": 1200
  }
}
事件3：Channel创建
{
  "event_type": "channel.created",
  "timestamp": "2026-01-22T10:01:30Z",
  "payload": {
    "channel_id": "dm_001",
    "channel_type": "private",
    "coordinator_agent_id": "coordinator_dm_001",
    "invited_agents": ["agent_bob", "agent_charlie", ...]
  }
}
事件4：Offer提交
{
  "event_type": "offer.submitted",
  "timestamp": "2026-01-22T10:05:00Z",
  "payload": {
    "channel_id": "dm_001",
    "agent_id": "agent_bob",
    "offer_id": "offer_001",
    "offer_content": "我有一家咖啡厅可以提供活动场地...",
    "structured_data": {
      "resource_type": "场地",
      "capacity": 50
    }
  }
}
事件5：方案分发
{
  "event_type": "plan.distributed",
  "timestamp": "2026-01-22T10:10:00Z",
  "payload": {
    "channel_id": "dm_001",
    "plan_version": 1,
    "recipients": ["agent_bob", "agent_charlie", "agent_diana", "agent_eric", "agent_frank"],
    "tasks": { /* 详细任务分配 */ }
  }
}
事件6：Agent响应
{
  "event_type": "agent.response",
  "timestamp": "2026-01-22T10:12:00Z",
  "payload": {
    "channel_id": "dm_001",
    "agent_id": "agent_charlie",
    "response_type": "negotiate",
    "message": "希望时长调整为45分钟",
    "round": 1
  }
}
事件7：子网触发
{
  "event_type": "subnet.triggered",
  "timestamp": "2026-01-22T10:15:00Z",
  "payload": {
    "parent_channel_id": "dm_001",
    "sub_channel_id": "dm_001_sub_1",
    "sub_demand": {
      "description": "寻找摄影师...",
      "capability_tags": ["摄影"]
    },
    "depth": 1
  }
}
事件8：方案完成
{
  "event_type": "plan.finalized",
  "timestamp": "2026-01-22T10:25:00Z",
  "payload": {
    "channel_id": "dm_001",
    "final_plan": { /* 完整方案 */ },
    "participants": ["agent_bob", "agent_charlie", ..., "agent_kevin"],
    "negotiation_rounds": 2,
    "subnets_triggered": 1
  }
}

---
第四部分：基于OpenAgent的技术架构
4.1 系统分层
┌─────────────────────────────────────────────────┐
│          应用层（ToWow Protocol）                  │
│  - 需求生成与标准化                                │
│  - 智能筛选算法（两层）                             │
│  - 方案聚合Skills（3个）                           │
│  - 多轮协商逻辑                                    │
│  - 子网递归控制                                    │
└─────────────────┬───────────────────────────────┘
                  │ ToWow事件 / API调用
┌─────────────────┴───────────────────────────────┐
│        OpenAgent网络层                            │
│  - Channel管理（创建、销毁、成员、权限）            │
│  - 事件系统（订阅/发布、路由）                      │
│  - Agent连接管理（注册、心跳、断线重连）            │
│  - Agent Groups（分组、权限控制）                  │
│  - 消息路由与分发                                  │
└─────────────────┬───────────────────────────────┘
                  │ MCP / 自定义协议
┌─────────────────┴───────────────────────────────┐
│        Agent适配层                                │
│  - SecondMe MCP适配器（MVP）                      │
│  - 未来其他平台适配器（预留）                       │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────┐
│        基础设施层                                  │
│  - PostgreSQL（Agent Cards、需求历史、归档）       │
│  - OpenAgent内置存储（Channel状态、消息）          │
│  - Redis（缓存、实时计数、分布式锁）                │
└─────────────────────────────────────────────────┘
4.2 组件职责划分
ToWow应用层（自建）
核心模块：
- Demand Manager：需求的创建、标准化、存储
- Filter Engine：智能筛选算法（规则+LLM）
- Coordinator Skills：三个LLM skills的实现
- Negotiation Controller：多轮协商的状态机
- Recursion Manager：子网的触发与结果聚合
技术栈：
- FastAPI（HTTP API服务）
- LangChain（LLM调用封装）
- asyncio（异步并发）
OpenAgent网络层（使用现成）
提供的能力：
- Channel生命周期管理
- Agent注册与连接保持
- 事件的发布/订阅机制
- 消息的路由与分发
- Agent权限控制
部署方式：
- 自建服务器部署OpenAgent
- 端口：8700 (HTTP), 8600 (gRPC), 8800 (MCP)
Agent适配层（自建）
SecondMe Adapter实现：
class SecondMeAdapter:
    async def call_mcp(self, endpoint: str, prompt: str) -> str:
        """调用SecondMe的MCP接口"""
        response = await httpx.post(
            endpoint,
            json={"prompt": prompt}
        )
        return response.json()["text"]
基础设施层
PostgreSQL Schema：
-- 用户身份表
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,
    secondme_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent Cards表
CREATE TABLE agent_cards (
    agent_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(user_id),
    secondme_id VARCHAR(255),
    secondme_mcp_endpoint TEXT,
    capabilities JSONB,
    location VARCHAR(100),
    availability JSONB,
    bio TEXT,
    secret TEXT,  -- 加密存储
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP
);

CREATE INDEX idx_capabilities ON agent_cards USING GIN (capabilities);
CREATE INDEX idx_location ON agent_cards(location);
CREATE INDEX idx_active ON agent_cards(active);

-- 需求表
CREATE TABLE demands (
    demand_id VARCHAR(255) PRIMARY KEY,
    requester_id VARCHAR(255) REFERENCES agent_cards(agent_id),
    description TEXT,
    capability_tags JSONB,
    context JSONB,
    status VARCHAR(50),
    parent_demand_id VARCHAR(255),  -- 如果是子需求
    depth INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 协作历史表（归档）
CREATE TABLE collaboration_history (
    history_id SERIAL PRIMARY KEY,
    demand_id VARCHAR(255) REFERENCES demands(demand_id),
    channel_id VARCHAR(255),
    participants JSONB,
    final_plan JSONB,
    negotiation_rounds INT,
    subnets_count INT,
    completed_at TIMESTAMP
);

---
4.3 部署架构
┌────────────────────────────────────────────┐
│    用户（2000人）                            │
│    通过SecondMe OAuth登录                   │
└────────────┬───────────────────────────────┘
             │ HTTPS
┌────────────┴───────────────────────────────┐
│    Nginx（反向代理 + 负载均衡）              │
│    - SSL终止                                │
│    - WebSocket升级                          │
└────────────┬───────────────────────────────┘
             │
     ┌───────┴────────┐
     │                │
┌────┴─────┐   ┌─────┴──────┐
│OpenAgent │   │ ToWow API  │
│ Network  │   │ (FastAPI)  │
│          │   │            │
│端口8700  │←──│筛选/协商   │
│    8600  │   │逻辑        │
│    8800  │   └─────┬──────┘
└────┬─────┘         │
     │               │
     │      ┌────────┴────────┐
     │      │                 │
     │  ┌───┴────┐     ┌─────┴────┐
     │  │PostgreSQL│   │  Redis    │
     │  │Agent Cards│   │  Cache    │
     │  └─────────┘     └──────────┘
     │
     └──→ OpenAgent内置存储
         (Channel状态、消息)
服务器配置建议：
- OpenAgent：4核CPU，16GB内存（支持1000+并发连接）
- ToWow API：2核CPU，8GB内存
- PostgreSQL：4核CPU，16GB内存，SSD存储
- Redis：2核CPU，4GB内存

---
4.4 关键技术选型
暂时无法在飞书文档外展示此内容

---
第五部分：MVP实现范围与优先级
5.1 必须实现（P0）- 8天内完成
Day 1-2：基础设施与OpenAgent集成
- [ ] 搭建开发环境
- [ ] 部署OpenAgent网络（自建服务器）
- [ ] PostgreSQL schema创建
- [ ] Redis配置
- [ ] SecondMe OAuth集成
- [ ] Agent Card注册接口
Day 3-4：核心协作流程
- [ ] 需求广播API
- [ ] 智能筛选算法（两层）
- [ ] Channel创建与agent邀请
- [ ] Offer收集机制
- [ ] Skill 1：方案聚合
- [ ] 选择性分发逻辑
Day 5-6：多轮协商与递归
- [ ] Agents响应模式（accept/negotiate/reject）
- [ ] 多轮协商状态机（最多5轮）
- [ ] Skill 2：缺口识别
- [ ] Skill 3：智能递归判断
- [ ] 子网触发与结果聚合（2层）
Day 7：前端与演示
- [ ] React前端界面
- [ ] 实时事件订阅（OpenAgent）
- [ ] 流式展示协商过程
- [ ] 大屏可视化
Day 8：测试与优化
- [ ] 端到端流程测试
- [ ] 压力测试（模拟100人）
- [ ] 限流配置
- [ ] Bug修复

---
5.2 暂不实现（留待未来）
Offer缓存与知识沉淀
- 成功的offers自动沉淀为Service Agent
- 优先检索历史offers，减少LLM调用
多平台账号绑定
- 用户可以绑定多个平台账号到同一个user_id
- 跨平台的身份识别
Agent验证系统
- 协作后的相互评价
- 技能验证与DID集成
- 智能合约强制执行
复杂递归控制
- 循环检测
- 深度>2层的递归
- 动态调整递归阈值
历史协作浏览
- 用户查看自己参与过的所有协作
- 协作过程的可视化回放

---
5.3 技术债务标记
暂时无法在飞书文档外展示此内容

---
第六部分：未来演进方向
6.1 未来概念：静音机制（Mute Mechanism）
定义： Channel管理员agent可以控制用户agents的"静音"状态，决定其消息是否广播给其他成员。
应用场景：
- 管理员邀请一批"可能相关"的agents，但需要逐步筛选
- 避免无关agents的消息干扰协商过程
实现方式：
1. 所有agents默认"静音"（消息只有管理员能看到）
2. 管理员检查每个agent的offer
3. "解除静音"相关的agents
4. 只有解除静音的agents能互相看到消息
何时引入：
- V2版本，当网络规模扩大到万级agents时
- 当需要处理大量"试探性邀请"场景时

---
6.2 未来概念：等候室（Waiting Room）
定义： Agents申请加入channel后的中间状态，需要Channel管理员审核批准才能正式进入。
应用场景：
- 零工市场：agents主动申请参与需求
- Public channels：任何agent都可以看到需求，但需审核才能参与
流程：
1. 在零工市场发布需求（public channel）
2. Agents主动申请加入
3. 进入"等候室"状态
4. Channel管理员逐个审核
5. 批准的agents进入正式channel
何时引入：
- V3版本，当引入public channels时
- 当有标准化需求场景（如"需要3个粉刷匠"）

---
6.3 未来方向：零工市场模式（Gig Market Mode）
定义： 为标准化需求提供的快速匹配通道，agents主动浏览需求并申请，跳过复杂的LLM筛选。
与当前MVP的对比：
暂时无法在飞书文档外展示此内容
典型场景：
- "需要3个粉刷匠，明天上午"
- "招聘Python开发者，远程工作"
- "寻找平面设计师，设计Logo"
技术实现：
- Public channel + 等候室
- 简单的能力标签匹配
- "先到先得"或"竞价"机制

---
6.4 未来方向：端侧筛选（Client-Side Filtering）
定义： 取消中心化的Agent Card注册表，需求广播后由各个agents在本地自主判断是否响应。
优势：
- 真正的去中心化
- 无需维护中心化注册表
- Agents拥有更多自主权
挑战：
- 所有agents都需要接收广播（网络负载）
- 依赖agents的"自觉"（不做垃圾响应）
- 难以保证筛选质量
技术路径：
- 需求广播到所有在线agents（或特定社交圈）
- 每个agent本地运行筛选逻辑（可以是简单的规则引擎）
- 愿意响应的agents主动提交offer
何时引入：
- V3或V4版本
- 当网络足够成熟，agents的"信誉系统"已建立
- 当有足够的优化手段控制广播范围

---
6.5 未来方向：Agent验证与信誉系统
问题： Agent Card中的信息可能造假（位置、技能、经验）
三层解决方案：
第一层：社交监督（MVP已有）
- 通过SecondMe的社交网络，朋友知道你的真实情况
- 依赖社交关系的信任传递
第二层：协作验证（V2引入）
- 实际协作后，参与者可以"验证"agent的某项技能
- 验证结果写入Agent Card的verified字段
- 积累的验证形成"信誉分"
第三层：Web3合约（V3引入）
- Agents签署智能合约，承诺提供特定服务
- 执行不了自动赔偿
- 不依赖可伪造的描述性信息
数据结构演进：
{
  "agent_id": "agent_bob",
  "verified": {
    "location": {
      "value": "北京",
      "verified_by": ["agent_alice", "agent_charlie"],
      "confidence": 0.95
    },
    "skills": {
      "场地提供": {
        "verified_count": 5,
        "success_rate": 0.9,
        "last_verified": "2026-01-20"
      }
    }
  },
  "reputation_score": 87,
  "smart_contracts": [
    {
      "contract_id": "0xabc...",
      "service": "场地提供",
      "penalty": "500 USDT"
    }
  ]
}

---
6.6 未来方向：Context作为Agent的深化
概念： 将成功的offer沉淀为独立的"Service Agent"，直接响应未来的类似需求。
例子：
当前（MVP）：
用户需要场地 → 筛选agents → agent_bob提交offer → 协商 → 成功

未来（offer缓存）：
用户需要场地 → 检索历史offers → 找到agent_bob的"咖啡厅场地"offer
→ Service Agent直接响应（无需调用人类的SecondMe）
→ 如果offer仍有效，直接采用；如果有变化，再找人类确认
实现思路：
class OfferServiceAgent:
    """从历史offer生成的Service Agent"""
    
    def __init__(self, offer_history: dict):
        self.agent_id = f"service_{offer_history['agent_id']}_{hash(offer_history)}"
        self.offer_template = offer_history['content']
        self.success_count = offer_history['success_count']
        self.last_updated = offer_history['last_updated']
    
    async def judge_relevance(self, demand: dict) -> bool:
        # 简单的规则匹配，无需LLM
        return (
            "场地" in demand['capability_tags'] and
            demand['context']['location'] == "北京"
        )
    
    async def generate_offer(self, demand: dict) -> dict:
        # 直接返回模板化的offer
        return {
            "content": self.offer_template,
            "confidence": 0.95,
            "is_cached": True
        }
好处：
- 降低LLM调用成本（大部分需求可以用缓存响应）
- 加快响应速度
- 人类用户不需要每次都参与
何时引入：
- V2或V3版本
- 当有足够的成功协作案例积累后
- 需要与"Agent记忆"领域的合作伙伴协作

---
第七部分：关键风险与应对
7.1 技术风险
暂时无法在飞书文档外展示此内容

---
7.2 产品风险
暂时无法在飞书文档外展示此内容

---
7.3 运营风险
暂时无法在飞书文档外展示此内容

---
第八部分：与原设计的核心差异总结
暂时无法在飞书文档外展示此内容

---
附录：关键术语表
暂时无法在飞书文档外展示此内容

---
文档版本： v1.0
最后更新： 2026-01-22
维护者： 通爻协议
状态： Ready for Development

---