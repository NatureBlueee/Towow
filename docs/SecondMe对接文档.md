# ToWow × SecondMe 对接文档

> 给SecondMe团队的技术对接说明

---

## 一、项目背景

ToWow是一个基于OpenAgent的AI代理协作网络，用于演示2000+agents的实时协商场景。

**演示时间**：2026年2月1日
**规模**：现场2000人

SecondMe作为用户入口，提供：
- 用户身份认证（OAuth）
- 用户个性化能力（通过MCP接口调用）

---

## 二、我们需要SecondMe提供什么

### 2.1 用户认证（OAuth）

| 需求 | 说明 |
|------|------|
| OAuth 2.0 授权 | 用户通过SecondMe登录ToWow |
| 回调URL | 我们会提供回调地址，需要SecondMe配置 |
| 返回的用户信息 | 至少需要：`secondme_id`、`用户昵称`、`MCP endpoint` |

**期望的OAuth流程**：
```
用户点击"用SecondMe登录"
    ↓
跳转到SecondMe授权页面
    ↓
用户授权
    ↓
回调到ToWow，带上授权码
    ↓
ToWow用授权码换取access_token
    ↓
ToWow用access_token获取用户信息
```

**我们需要的用户信息字段**：
```json
{
  "secondme_id": "sm_abc123",
  "nickname": "Alice",
  "mcp_endpoint": "https://secondme.io/mcp/sm_abc123",
  "avatar_url": "https://...",  // 可选
  "bio": "AI创业者，有咖啡厅..."  // 可选，如果有的话
}
```

### 2.2 MCP接口

ToWow需要调用SecondMe的MCP接口，让用户的AI代理生成内容。

**我们会调用的场景**：

| 场景 | 输入 | 期望输出 |
|------|------|---------|
| 生成Offer | 需求描述 | 用户能提供什么帮助（个性化回答） |
| 评估方案 | 方案内容 | 用户是否接受（accept/negotiate/reject） |
| 通知用户 | 最终方案 | 确认收到 |

**MCP调用示例**（我们期望的格式）：
```python
# 生成Offer
POST {mcp_endpoint}
{
  "method": "generate_response",
  "params": {
    "prompt": "有人在ToWow网络发起需求：'我想在北京办一场AI主题聚会，需要场地和嘉宾'。你能提供什么帮助？请根据你的实际情况回答。",
    "context": {
      "demand_id": "dm_001",
      "requester": "agent_alice"
    }
  }
}

# 期望返回
{
  "result": {
    "text": "我有一家咖啡厅可以提供活动场地，位于北京朝阳区，可容纳50人...",
    "confidence": 0.9
  }
}
```

**问题**：
- SecondMe的MCP接口格式是这样吗？
- 需要传什么认证信息？（Bearer token？）
- 有频率限制吗？

### 2.3 用户简介/Profile

我们需要每个用户的简介信息，用于智能筛选。

**问题**：
- SecondMe是否有用户的profile/bio数据？
- 如果有，能通过API获取吗？
- 如果没有，我们需要让用户在ToWow里手动填写

---

## 三、我们的技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 网络层 | OpenAgent | 开源AI Agent网络框架 |
| 后端 | Python + FastAPI | API服务 |
| 数据库 | PostgreSQL | 存储Agent Card、需求、协作历史 |
| 前端 | React（待定） | 用户界面 + 大屏展示 |
| LLM | Claude/GPT-4（待定） | 智能筛选、方案聚合等 |

**默认端口**：
- OpenAgent HTTP: 8700
- OpenAgent gRPC: 8600
- ToWow API: 待定

---

## 四、对接时间线（建议）

| 阶段 | 时间 | 内容 |
|------|------|------|
| 1. 接口确认 | 本周内 | 确认OAuth和MCP接口格式 |
| 2. 联调环境 | 下周 | SecondMe提供测试账号 |
| 3. 集成测试 | 1月底 | 完整流程跑通 |
| 4. 现场演示 | 2月1日 | 正式上线 |

---

## 五、我们提供给SecondMe的

如果SecondMe需要在其界面中集成ToWow入口：

| 内容 | 说明 |
|------|------|
| ToWow入口URL | `https://towow.xxx/login?from=secondme` |
| 品牌素材 | Logo、名称、简介（如需要） |
| 状态查询API | 用户在ToWow的参与状态（如需要） |

---

## 六、待确认问题汇总

1. **OAuth**：
   - [ ] SecondMe的OAuth文档在哪？
   - [ ] 回调URL格式要求？
   - [ ] Token有效期多长？

2. **MCP**：
   - [ ] MCP接口的具体格式？
   - [ ] 需要什么认证？
   - [ ] 频率限制？
   - [ ] 超时时间？

3. **用户数据**：
   - [ ] 能获取用户的profile/bio吗？
   - [ ] 用户的能力标签从哪来？

4. **其他**：
   - [ ] 有测试环境吗？
   - [ ] 有测试账号吗？
   - [ ] 技术对接人是谁？

---

## 七、联系方式

**ToWow团队**：
- 技术负责人：待定
- 联系方式：待定

**期望SecondMe提供**：
- 技术对接人
- 联系方式

---

**文档版本**: v1.0
**创建时间**: 2026-01-21
**状态**: 待SecondMe确认
