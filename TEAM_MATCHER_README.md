# Team Matcher - 团队匹配功能

## 概述

Team Matcher 是基于 ToWow requirement_network 协议构建的团队组队匹配功能，用于黑客松、项目协作等场景。

**核心价值**：
- **自动组队**：从多个参与意向中自动生成最佳团队组合
- **智能匹配**：基于角色覆盖度、技能互补度的智能评分
- **意外发现**：识别跨领域组合，发现潜在协同机会

## 架构设计

### 本质理解

Team Matcher = 特殊的需求协商场景：
- 组队请求（Team Request）= 需求（Requirement）
- 参与意向（Match Offer）= Agent Offer
- 团队方案（Team Proposal）= 协商方案（Proposal）

### 核心组件

```
requirement_demo/web/
├── team_match_service.py       # 服务层：业务流程管理
├── team_composition_engine.py  # 算法层：团队组合引擎
└── test_team_match.py          # 测试：单元测试 + 集成测试
```

### 工作流程

```
1. 创建组队请求
   POST /api/team/request

2. 收集参与意向
   POST /api/team/offer (多次调用)

3. 生成团队方案
   POST /api/team/proposals/{request_id}

4. 查看方案详情
   GET /api/team/request/{request_id}/proposals
```

## API 端点

### 1. 创建组队请求

```http
POST /api/team/request
Content-Type: application/json

{
  "title": "寻找黑客松队友",
  "description": "参加 AI 黑客松，需要组建团队",
  "submitter_id": "user_alice",
  "required_roles": ["前端开发", "后端开发", "设计师"],
  "team_size": 3,
  "metadata": {
    "event": "AI Hackathon 2026"
  }
}
```

**响应**：
```json
{
  "request_id": "team_req_abc123",
  "title": "寻找黑客松队友",
  "status": "pending",
  "channel_id": "team_ch_xyz789",
  "created_at": "2026-02-07T12:00:00"
}
```

### 2. 提交参与意向

```http
POST /api/team/offer
Content-Type: application/json

{
  "request_id": "team_req_abc123",
  "agent_id": "user_bob",
  "agent_name": "Bob",
  "role": "前端开发",
  "skills": ["React", "TypeScript", "UI设计"],
  "specialties": ["web-development", "frontend"],
  "motivation": "想学习 AI 应用开发",
  "availability": "周末全天"
}
```

### 3. 生成团队方案

```http
POST /api/team/proposals/team_req_abc123?max_proposals=3
```

**响应**：返回 3 个不同的团队组合方案

```json
[
  {
    "proposal_id": "proposal_1",
    "title": "方案 1：前端开发 + 后端开发 + UI设计师",
    "members": [
      {
        "agent_id": "user_bob",
        "agent_name": "Bob",
        "role": "前端开发",
        "skills": ["React", "TypeScript"],
        "contribution": "前端开发方面的专业支持"
      },
      {
        "agent_id": "user_carol",
        "agent_name": "Carol",
        "role": "后端开发",
        "skills": ["Python", "FastAPI"],
        "contribution": "后端开发方面的专业支持"
      },
      {
        "agent_id": "user_dave",
        "agent_name": "Dave",
        "role": "UI设计师",
        "skills": ["Figma", "Sketch"],
        "contribution": "UI设计师方面的专业支持"
      }
    ],
    "coverage_score": 1.0,
    "synergy_score": 0.85,
    "unexpected_combinations": ["前端+后端 跨域组合", "设计+开发 互补"],
    "reasoning": "团队成员：Bob, Carol, Dave；角色覆盖度高（100%），满足需求；技能互补性强（85%），协作潜力大；意外发现：前端+后端 跨域组合, 设计+开发 互补；覆盖技能：React, TypeScript, Python, FastAPI, Figma, Sketch"
  }
]
```

### 4. 查询接口

```http
# 获取组队请求详情
GET /api/team/request/{request_id}

# 获取参与意向列表
GET /api/team/request/{request_id}/offers

# 获取团队方案列表
GET /api/team/request/{request_id}/proposals

# 获取统计信息
GET /api/team/stats
```

## WebSocket 实时通知

连接到 `/ws/{agent_id}` 或 `/ws/demo/{agent_id}` 后，会收到以下事件：

### 1. 组队请求创建
```json
{
  "type": "team_request_created",
  "payload": {
    "request_id": "team_req_abc123",
    "title": "寻找黑客松队友",
    "required_roles": ["前端", "后端"],
    "team_size": 3,
    "channel_id": "team_ch_xyz789"
  }
}
```

### 2. 收到参与意向
```json
{
  "type": "match_offer_received",
  "payload": {
    "offer_id": "offer_1",
    "request_id": "team_req_abc123",
    "agent_name": "Bob",
    "role": "前端开发",
    "skills": ["React", "TypeScript"]
  }
}
```

### 3. 方案生成完成
```json
{
  "type": "proposals_ready",
  "payload": {
    "request_id": "team_req_abc123",
    "proposal_count": 3
  }
}
```

## 核心算法

### 团队组合引擎（Team Composition Engine）

**输入**：N 个 MatchOffer
**输出**：K 个 TeamProposal（按评分排序）

**评分维度**：
1. **角色覆盖度**（50% 权重）
   - 计算：满足的必需角色数 / 总必需角色数
   - 阈值：< 0.5 的组合会被过滤掉

2. **技能互补度**（30% 权重）
   - 技能多样性：技能总数 / (成员数 × 3)
   - 专长互补性：不同专长领域数 / 成员数

3. **意外组合加分**（每个加 0.05）
   - 跨域组合：如 "设计+技术"、"前端+后端"
   - 互补技能：如 "设计+开发"

**算法流程**：
```python
1. 生成所有可能的团队组合（组合数学）
2. 评估每个组合（覆盖度、互补度、意外组合）
3. 过滤低分组合（覆盖度 < 0.5）
4. 排序并返回 top K 个方案
```

## 运行测试

```bash
cd requirement_demo

# 运行所有测试
python3 -m pytest web/test_team_match.py -v

# 运行特定测试
python3 -m pytest web/test_team_match.py::TestTeamMatchService -v

# 运行集成测试
python3 -m pytest web/test_team_match.py::TestTeamMatcherIntegration -v
```

**测试覆盖**：
- ✅ TeamMatchService 单元测试（7 个）
- ✅ TeamCompositionEngine 单元测试（8 个）
- ✅ 端到端集成测试（1 个）

## 使用示例

### Python 客户端示例

```python
import asyncio
import httpx

async def team_matcher_demo():
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # 1. 创建组队请求
        response = await client.post("/api/team/request", json={
            "title": "寻找黑客松队友",
            "description": "参加 AI 黑客松",
            "submitter_id": "user_alice",
            "required_roles": ["前端", "后端", "设计"],
            "team_size": 3,
        })
        request_data = response.json()
        request_id = request_data["request_id"]
        print(f"✓ 创建组队请求: {request_id}")

        # 2. 提交多个参与意向
        offers = [
            {"agent_id": "user_bob", "agent_name": "Bob", "role": "前端开发", "skills": ["React"]},
            {"agent_id": "user_carol", "agent_name": "Carol", "role": "后端开发", "skills": ["Python"]},
            {"agent_id": "user_dave", "agent_name": "Dave", "role": "设计师", "skills": ["Figma"]},
        ]

        for offer in offers:
            await client.post("/api/team/offer", json={
                **offer,
                "request_id": request_id,
                "specialties": [],
                "motivation": "想参加",
                "availability": "周末",
            })
            print(f"✓ {offer['agent_name']} 提交参与意向")

        # 3. 生成团队方案
        response = await client.post(f"/api/team/proposals/{request_id}?max_proposals=3")
        proposals = response.json()
        print(f"\n✓ 生成了 {len(proposals)} 个团队方案：")

        for i, proposal in enumerate(proposals, 1):
            print(f"\n方案 {i}: {proposal['title']}")
            print(f"  覆盖度: {proposal['coverage_score']:.0%}")
            print(f"  协同度: {proposal['synergy_score']:.0%}")
            if proposal['unexpected_combinations']:
                print(f"  意外发现: {', '.join(proposal['unexpected_combinations'])}")

asyncio.run(team_matcher_demo())
```

### JavaScript 客户端示例

```javascript
const BASE_URL = 'http://localhost:8080';

async function teamMatcherDemo() {
  // 1. 创建组队请求
  const requestResponse = await fetch(`${BASE_URL}/api/team/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: '寻找黑客松队友',
      description: '参加 AI 黑客松',
      submitter_id: 'user_alice',
      required_roles: ['前端', '后端', '设计'],
      team_size: 3,
    }),
  });
  const { request_id } = await requestResponse.json();
  console.log(`✓ 创建组队请求: ${request_id}`);

  // 2. 提交参与意向
  const offers = [
    { agent_id: 'user_bob', agent_name: 'Bob', role: '前端开发', skills: ['React'] },
    { agent_id: 'user_carol', agent_name: 'Carol', role: '后端开发', skills: ['Python'] },
    { agent_id: 'user_dave', agent_name: 'Dave', role: '设计师', skills: ['Figma'] },
  ];

  for (const offer of offers) {
    await fetch(`${BASE_URL}/api/team/offer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...offer,
        request_id,
        specialties: [],
        motivation: '想参加',
        availability: '周末',
      }),
    });
    console.log(`✓ ${offer.agent_name} 提交参与意向`);
  }

  // 3. 生成团队方案
  const proposalsResponse = await fetch(
    `${BASE_URL}/api/team/proposals/${request_id}?max_proposals=3`,
    { method: 'POST' }
  );
  const proposals = await proposalsResponse.json();
  console.log(`\n✓ 生成了 ${proposals.length} 个团队方案：`);

  proposals.forEach((proposal, i) => {
    console.log(`\n方案 ${i + 1}: ${proposal.title}`);
    console.log(`  覆盖度: ${(proposal.coverage_score * 100).toFixed(0)}%`);
    console.log(`  协同度: ${(proposal.synergy_score * 100).toFixed(0)}%`);
    if (proposal.unexpected_combinations.length > 0) {
      console.log(`  意外发现: ${proposal.unexpected_combinations.join(', ')}`);
    }
  });
}

teamMatcherDemo();
```

## 技术亮点

### 1. 工程实践（遵循 towow-dev 原则）

- **清晰度**：函数 < 50 行，职责单一，命名自解释
- **正确性**：参数验证、异常处理、边界检查
- **可测试性**：依赖注入、Mock 友好、16 个测试 100% 通过
- **可观测性**：关键操作有日志（INFO/DEBUG/ERROR）

### 2. 架构一致性（遵循通爻设计原则）

- **本质与实现分离**：接口稳定（API），实现可演化（算法）
- **代码保障 > Prompt 保障**：状态机控制流程，LLM 提供智能
- **复用协议**：基于 requirement_network，不重复造轮子

### 3. 算法设计

- **简单优先**：V1 使用启发式规则，不过度设计
- **可演化**：算法接口清晰，未来可替换为机器学习模型
- **有效性**：实测能识别跨域组合，覆盖度/协同度评分合理

## 下一步优化

### V1.1（性能优化）
- [ ] 添加组合数量限制（当 N 很大时，C(N, K) 组合爆炸）
- [ ] 使用缓存优化重复计算

### V1.2（算法优化）
- [ ] 更丰富的启发式规则（如时间冲突检测）
- [ ] 基于历史数据的协同度预测

### V2.0（机器学习）
- [ ] 使用协同过滤推荐团队组合
- [ ] 基于 LLM 生成团队方案推理说明

## 问题反馈

如有问题或建议，请联系项目维护者。

---

**实现时间**：2026-02-07
**测试状态**：✅ 16/16 通过
**代码行数**：约 800 行（含测试）
