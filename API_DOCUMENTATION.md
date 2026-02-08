# Requirement Demo API 文档

## 概述

本服务提供用户注册、需求管理、实时消息推送等功能。

- **Base URL**: `http://localhost:8080`
- **API 文档 (Swagger UI)**: `http://localhost:8080/docs`
- **WebSocket**: `ws://localhost:8080/ws/{agent_id}`

---

## 认证 API

### 获取 OAuth2 登录 URL

获取 SecondMe OAuth2 授权页面 URL。

```
GET /api/auth/login
```

**响应示例**:
```json
{
  "authorization_url": "https://app.me.bot/oauth?client_id=xxx&redirect_uri=xxx&response_type=code&state=xxx",
  "state": "random_state_string"
}
```

**使用流程**:
1. 前端调用此接口获取 `authorization_url`
2. 重定向用户到 `authorization_url`
3. 用户授权后，SecondMe 重定向到 `redirect_uri?code=xxx&state=xxx`
4. 前端用 `code` 和 `state` 调用回调接口

---

### OAuth2 回调

处理 SecondMe OAuth2 授权回调。

```
GET /api/auth/callback?code={code}&state={state}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | SecondMe 返回的授权码 |
| state | string | 是 | CSRF 防护的 state 参数 |

**响应示例**:
```json
{
  "success": true,
  "message": "授权成功",
  "open_id": "user_email@example.com",
  "name": "用户名",
  "avatar": "https://example.com/avatar.jpg",
  "bio": "用户简介",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "needs_registration": true
}
```

---

### 完成注册

用户补填技能信息后完成注册，创建 Worker Agent。

```
POST /api/auth/complete-registration
Content-Type: application/json
```

**请求体**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "display_name": "张三",
  "skills": ["python", "react", "api-design"],
  "specialties": ["web-development", "backend"],
  "bio": "全栈开发者"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "注册成功",
  "agent_id": "user_d212ce7f",
  "display_name": "张三",
  "is_new": true
}
```

---

### 刷新 Token

```
POST /api/auth/refresh
Content-Type: application/json
```

**请求体**:
```json
{
  "refresh_token": "your_refresh_token"
}
```

**响应示例**:
```json
{
  "success": true,
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "expires_in": 3600,
  "open_id": "user_identifier"
}
```

---

## Agent 管理 API

### 获取 Agent 列表

```
GET /api/agents
```

**响应示例**:
```json
{
  "total": 2,
  "agents": [
    {
      "agent_id": "user_d212ce7f",
      "display_name": "Nature",
      "skills": ["Web3", "AI产品"],
      "specialties": ["blockchain", "ai"],
      "is_running": false,
      "created_at": "2026-01-29T10:00:00",
      "secondme_id": "nature@example.com",
      "bio": "AI 产品开发者"
    }
  ]
}
```

---

### 获取单个 Agent

```
GET /api/agents/{agent_id}
```

**响应示例**:
```json
{
  "agent_id": "user_d212ce7f",
  "display_name": "Nature",
  "skills": ["Web3", "AI产品"],
  "specialties": ["blockchain", "ai"],
  "is_running": true,
  "created_at": "2026-01-29T10:00:00",
  "secondme_id": "nature@example.com",
  "bio": "AI 产品开发者"
}
```

---

### Agent 操作 (启动/停止/重启)

```
POST /api/agents/{agent_id}/action
Content-Type: application/json
```

**请求体**:
```json
{
  "action": "start"  // 可选值: "start", "stop", "restart"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "Agent 已启动",
  "agent_id": "user_d212ce7f"
}
```

---

### 启动所有 Agent

```
POST /api/agents/start-all
```

**响应示例**:
```json
{
  "success": true,
  "message": "正在启动 2 个 Agent..."
}
```

---

### 停止所有 Agent

```
POST /api/agents/stop-all
```

**响应示例**:
```json
{
  "success": true,
  "message": "所有 Agent 已停止"
}
```

---

## 需求 API

### 提交需求

```
POST /api/requirements
Content-Type: application/json
```

**请求体**:
```json
{
  "title": "开发一个用户管理系统",
  "description": "需要实现用户注册、登录、权限管理等功能",
  "submitter_id": "user_d212ce7f",
  "metadata": {
    "priority": "high",
    "tags": ["backend", "auth"]
  }
}
```

**响应示例**:
```json
{
  "requirement_id": "req_abc123def456",
  "title": "开发一个用户管理系统",
  "description": "需要实现用户注册、登录、权限管理等功能",
  "submitter_id": "user_d212ce7f",
  "status": "pending",
  "channel_id": null,
  "metadata": {"priority": "high", "tags": ["backend", "auth"]},
  "created_at": "2026-01-29T10:00:00",
  "updated_at": "2026-01-29T10:00:00"
}
```

---

### 获取需求列表

```
GET /api/requirements?status={status}&submitter_id={submitter_id}&limit={limit}&offset={offset}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 按状态筛选 (pending/in_progress/completed) |
| submitter_id | string | 否 | 按提交者筛选 |
| limit | int | 否 | 返回数量限制 (默认 100) |
| offset | int | 否 | 偏移量 (默认 0) |

**响应示例**:
```json
{
  "total": 5,
  "requirements": [
    {
      "requirement_id": "req_abc123def456",
      "title": "开发一个用户管理系统",
      "description": "...",
      "submitter_id": "user_d212ce7f",
      "status": "pending",
      "channel_id": null,
      "metadata": {},
      "created_at": "2026-01-29T10:00:00",
      "updated_at": "2026-01-29T10:00:00"
    }
  ]
}
```

---

### 获取需求详情

```
GET /api/requirements/{requirement_id}
```

**响应示例**:
```json
{
  "requirement_id": "req_abc123def456",
  "title": "开发一个用户管理系统",
  "description": "需要实现用户注册、登录、权限管理等功能",
  "submitter_id": "user_d212ce7f",
  "status": "in_progress",
  "channel_id": "req_abc123def456",
  "metadata": {"priority": "high"},
  "created_at": "2026-01-29T10:00:00",
  "updated_at": "2026-01-29T10:05:00"
}
```

---

### 更新需求

```
PATCH /api/requirements/{requirement_id}?status={status}&channel_id={channel_id}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 新状态 |
| channel_id | string | 否 | 关联的 Channel ID |

**响应示例**:
```json
{
  "requirement_id": "req_abc123def456",
  "title": "开发一个用户管理系统",
  "status": "in_progress",
  "...": "..."
}
```

---

## Channel 消息 API

### 发送消息

```
POST /api/channels/{channel_id}/messages
Content-Type: application/json
```

**请求体**:
```json
{
  "sender_id": "user_d212ce7f",
  "content": "这是一条消息",
  "sender_name": "Nature",
  "message_type": "text",
  "metadata": {}
}
```

**响应示例**:
```json
{
  "message_id": "msg_xyz789",
  "channel_id": "req_abc123def456",
  "sender_id": "user_d212ce7f",
  "sender_name": "Nature",
  "content": "这是一条消息",
  "message_type": "text",
  "metadata": {},
  "created_at": "2026-01-29T10:10:00"
}
```

---

### 获取消息历史

```
GET /api/channels/{channel_id}/messages?limit={limit}&offset={offset}&after_id={after_id}
```

**参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | int | 否 | 返回数量限制 (默认 100) |
| offset | int | 否 | 偏移量 (默认 0) |
| after_id | string | 否 | 获取此消息之后的消息 |

**响应示例**:
```json
{
  "total": 10,
  "messages": [
    {
      "message_id": "msg_xyz789",
      "channel_id": "req_abc123def456",
      "sender_id": "user_d212ce7f",
      "sender_name": "Nature",
      "content": "这是一条消息",
      "message_type": "text",
      "metadata": {},
      "created_at": "2026-01-29T10:10:00"
    }
  ]
}
```

---

## WebSocket API

### 连接

```
WebSocket: ws://localhost:8080/ws/{agent_id}
```

连接后可以接收实时消息推送。

---

### 客户端发送消息格式

**Ping**:
```json
{"action": "ping"}
```
响应: `{"type": "pong"}`

**订阅 Channel**:
```json
{"action": "subscribe", "channel_id": "req_abc123def456"}
```
响应: `{"type": "subscribed", "channel_id": "req_abc123def456"}`

**取消订阅**:
```json
{"action": "unsubscribe", "channel_id": "req_abc123def456"}
```
响应: `{"type": "unsubscribed", "channel_id": "req_abc123def456"}`

---

### 服务端推送消息格式

**新需求**:
```json
{
  "type": "new_requirement",
  "data": {
    "requirement_id": "req_abc123def456",
    "title": "...",
    "description": "...",
    "...": "..."
  }
}
```

**需求更新**:
```json
{
  "type": "requirement_updated",
  "data": {
    "requirement_id": "req_abc123def456",
    "status": "in_progress",
    "...": "..."
  }
}
```

**Channel 消息**:
```json
{
  "type": "channel_message",
  "data": {
    "message_id": "msg_xyz789",
    "channel_id": "req_abc123def456",
    "sender_id": "user_d212ce7f",
    "content": "消息内容",
    "...": "..."
  }
}
```

---

## 统计 API

### 获取系统统计

```
GET /api/stats
```

**响应示例**:
```json
{
  "total_agents": 2,
  "running_agents": 1,
  "stopped_agents": 1,
  "skills": {
    "python": 2,
    "react": 1,
    "Web3": 1
  },
  "specialties": {
    "web-development": 1,
    "backend": 1
  }
}
```

---

### 获取 WebSocket 统计

```
GET /api/ws/stats
```

**响应示例**:
```json
{
  "total_connections": 5,
  "connections": ["user_d212ce7f", "user_abc123"],
  "channel_subscriptions": {
    "req_abc123def456": ["user_d212ce7f"]
  }
}
```

---

## 健康检查

```
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "total_agents": 2,
  "running_agents": 1
}
```

---

## 错误响应

所有 API 在出错时返回统一格式：

```json
{
  "detail": "错误描述信息"
}
```

**常见 HTTP 状态码**:
| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 / Token 无效 |
| 404 | 资源不存在 |
| 422 | 请求体验证失败 |
| 500 | 服务器内部错误 |

---

## cURL 示例

```bash
# 健康检查
curl http://localhost:8080/health

# 获取 Agent 列表
curl http://localhost:8080/api/agents

# 提交需求
curl -X POST http://localhost:8080/api/requirements \
  -H "Content-Type: application/json" \
  -d '{"title": "测试需求", "description": "这是一个测试"}'

# 获取需求列表
curl http://localhost:8080/api/requirements

# 更新需求状态
curl -X PATCH "http://localhost:8080/api/requirements/req_xxx?status=in_progress"

# 发送消息
curl -X POST http://localhost:8080/api/channels/req_xxx/messages \
  -H "Content-Type: application/json" \
  -d '{"sender_id": "test", "content": "Hello!"}'

# 获取消息
curl http://localhost:8080/api/channels/req_xxx/messages
```

---

## 前端集成示例

### JavaScript/TypeScript

```typescript
// API 客户端
const API_BASE = 'http://localhost:8080';

// 获取 Agent 列表
async function getAgents() {
  const res = await fetch(`${API_BASE}/api/agents`);
  return res.json();
}

// 提交需求
async function submitRequirement(title: string, description: string) {
  const res = await fetch(`${API_BASE}/api/requirements`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description })
  });
  return res.json();
}

// WebSocket 连接
function connectWebSocket(agentId: string) {
  const ws = new WebSocket(`ws://localhost:8080/ws/${agentId}`);

  ws.onopen = () => {
    console.log('Connected');
    ws.send(JSON.stringify({ action: 'ping' }));
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);

    if (data.type === 'new_requirement') {
      // 处理新需求
    } else if (data.type === 'channel_message') {
      // 处理 Channel 消息
    }
  };

  return ws;
}

// 订阅 Channel
function subscribeChannel(ws: WebSocket, channelId: string) {
  ws.send(JSON.stringify({
    action: 'subscribe',
    channel_id: channelId
  }));
}
```
