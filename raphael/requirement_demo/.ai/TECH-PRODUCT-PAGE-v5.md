# TECH-PRODUCT-PAGE-v5.md

## 文档元信息

| 字段 | 值 |
|------|-----|
| 文档ID | TECH-PRODUCT-PAGE-v5 |
| 状态 | DRAFT |
| 创建日期 | 2026-01-29 |
| 关联文档 | TECH-SERVICE-ENCAPSULATION.md, API_DOCUMENTATION.md |

---

## 1. 目标与范围

### 1.1 目标

为 ToWow 平台开发一个**产品体验页**，让用户能够：

1. **登录认证**：通过 SecondMe OAuth2 登录，获取用户身份
2. **提交需求**：填写并提交协作需求
3. **查看协商过程**：实时观看 Agent 之间的协商讨论
4. **体验 Agent 协作**：感受多 Agent 实时协作的能力

### 1.2 范围

**In Scope（本期范围）**：
- SecondMe OAuth2 登录集成
- 需求提交表单
- 协商过程实时展示（WebSocket）
- 协商结果展示

**Out of Scope（不在本期）**：
- 用户注册流程（依赖 SecondMe）
- 历史需求管理
- Agent 配置管理
- 多语言支持

### 1.3 技术约束

| 约束项 | 说明 |
|--------|------|
| 前端框架 | Next.js 14+ (App Router) |
| 样式方案 | CSS Modules + CSS Variables |
| 后端 API | FastAPI (已封装) |
| 实时通信 | WebSocket |
| 认证方式 | SecondMe OAuth2 |

---

## 2. 现状与约束

### 2.1 已有后端能力 [VERIFIED]

基于 `/Users/nature/个人项目/Towow/raphael/requirement_demo/web/` 代码验证：

#### 2.1.1 数据模型 (database.py:28-125)

```python
# User 模型 - 用户信息存储
class User(Base):
    agent_id: str          # 唯一标识
    display_name: str      # 显示名称
    skills: List[str]      # 技能列表
    specialties: List[str] # 专长列表
    secondme_id: str       # SecondMe 关联ID
    access_token: str      # OAuth2 Token
    refresh_token: str     # 刷新 Token
    token_expires_at: datetime  # Token 过期时间

# Requirement 模型 - 需求存储
class Requirement(Base):
    requirement_id: str    # 需求ID
    title: str             # 标题
    description: str       # 描述
    submitter_id: str      # 提交者 agent_id
    status: str            # pending/processing/completed/cancelled
    channel_id: str        # 关联的协商频道

# ChannelMessage 模型 - 消息存储
class ChannelMessage(Base):
    message_id: str        # 消息ID
    channel_id: str        # 频道ID
    sender_id: str         # 发送者ID
    content: str           # 消息内容
    message_type: str      # text/system/action
```

#### 2.1.2 WebSocket 管理器 (websocket_manager.py:31-248)

```python
class WebSocketManager:
    # 核心能力
    async def connect(websocket, agent_id) -> bool
    async def disconnect(agent_id)
    async def subscribe_channel(agent_id, channel_id)
    async def unsubscribe_channel(agent_id, channel_id)
    async def send_to_agent(agent_id, message) -> bool
    async def broadcast_to_channel(channel_id, message, exclude_agent) -> int
    async def broadcast_all(message, exclude_agent) -> int
```

#### 2.1.3 OAuth2 客户端 (oauth2_client.py) [VERIFIED]

- SecondMe OAuth2 授权流程
- Token 刷新机制
- 用户信息获取

### 2.2 已有前端组件 [VERIFIED]

基于 `/Users/nature/个人项目/Towow/raphael/requirement_demo/towow-website/` 验证：

| 组件 | 路径 | 用途 | 复用性 |
|------|------|------|--------|
| Button | components/ui/Button.tsx | 按钮（primary/outline） | 可复用 |
| ContentCard | components/ui/ContentCard.tsx | 内容卡片 | 可复用 |
| Shape | components/ui/Shape.tsx | 几何图形装饰 | 可复用 |
| LinkArrow | components/ui/LinkArrow.tsx | 链接箭头 | 可复用 |
| NodeItem | components/ui/NodeItem.tsx | 节点项 | 可复用 |
| QuoteBlock | components/ui/QuoteBlock.tsx | 引用块 | 可复用 |
| Divider | components/ui/Divider.tsx | 分隔线 | 可复用 |
| NoiseTexture | components/layout/NoiseTexture.tsx | 噪点纹理背景 | 可复用 |
| GridLines | components/layout/GridLines.tsx | 网格线背景 | 可复用 |

### 2.3 复用清单

**可直接复用**：
- Button 组件（登录按钮、提交按钮）
- ContentCard 组件（需求卡片、消息卡片）
- NoiseTexture + GridLines（页面背景）
- CSS Variables 系统

**需要扩展**：
- Button 组件：添加 loading 状态
- ContentCard 组件：添加实时更新动画

**需要新建**：
- LoginPanel 组件
- RequirementForm 组件
- NegotiationTimeline 组件
- MessageBubble 组件
- AgentAvatar 组件

---

## 3. 页面设计

### 3.1 页面结构

```
/experience                    # 产品体验页入口
├── 未登录状态
│   └── LoginPanel            # 登录面板
└── 已登录状态
    ├── Header                # 用户信息 + 退出
    ├── RequirementForm       # 需求提交表单
    ├── NegotiationPanel      # 协商过程面板
    │   ├── StatusIndicator   # 状态指示器
    │   ├── Timeline          # 时间线
    │   └── MessageList       # 消息列表
    └── ResultPanel           # 结果展示面板
```

### 3.2 用户流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  访问页面   │────▶│  SecondMe   │────▶│  登录成功   │
│  (未登录)   │     │  OAuth2     │     │  显示表单   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  查看结果   │◀────│  实时协商   │◀────│  提交需求   │
│  (完成)     │     │  (WebSocket)│     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 3.3 状态机

```
PageState:
  INIT          # 初始化，检查登录状态
  LOGIN         # 未登录，显示登录面板
  READY         # 已登录，可提交需求
  SUBMITTING    # 提交中
  NEGOTIATING   # 协商进行中
  COMPLETED     # 协商完成
  ERROR         # 错误状态
```

---

## 4. 前后端接口契约

### 4.1 REST API

#### 4.1.1 OAuth2 登录

```typescript
// 获取授权 URL
GET /api/auth/login
Response: { auth_url: string }

// OAuth2 回调
GET /api/auth/callback?code={code}&state={state}
Response: {
  success: boolean;
  user: {
    agent_id: string;
    display_name: string;
    avatar_url?: string;
  };
  token: string;  // JWT for subsequent requests
}

// 获取当前用户
GET /api/auth/me
Headers: { Authorization: "Bearer {token}" }
Response: {
  agent_id: string;
  display_name: string;
  avatar_url?: string;
  skills: string[];
  specialties: string[];
}

// 退出登录
POST /api/auth/logout
Headers: { Authorization: "Bearer {token}" }
Response: { success: boolean }
```

#### 4.1.2 需求管理

```typescript
// 提交需求
POST /api/requirements
Headers: { Authorization: "Bearer {token}" }
Body: {
  title: string;
  description: string;
  metadata?: Record<string, any>;
}
Response: {
  requirement_id: string;
  channel_id: string;
  status: "pending";
  created_at: string;
}

// 获取需求详情
GET /api/requirements/{requirement_id}
Headers: { Authorization: "Bearer {token}" }
Response: {
  requirement_id: string;
  title: string;
  description: string;
  status: "pending" | "processing" | "completed" | "cancelled";
  channel_id: string;
  created_at: string;
  updated_at: string;
}
```

### 4.2 WebSocket 消息协议

#### 4.2.1 连接建立

```typescript
// 连接 URL
ws://localhost:8000/ws/{agent_id}

// 连接成功响应
{
  type: "connected";
  agent_id: string;
  timestamp: string;
}
```

#### 4.2.2 订阅频道

```typescript
// 客户端发送
{
  action: "subscribe";
  channel_id: string;
}

// 服务端响应
{
  type: "subscribed";
  channel_id: string;
}
```

#### 4.2.3 消息类型

```typescript
// 协商消息
interface NegotiationMessage {
  type: "negotiation_message";
  message_id: string;
  channel_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  message_type: "text" | "system" | "action";
  timestamp: string;
}

// 状态更新
interface StatusUpdate {
  type: "status_update";
  channel_id: string;
  requirement_id: string;
  status: "pending" | "processing" | "completed" | "cancelled";
  timestamp: string;
}

// 协商完成
interface NegotiationComplete {
  type: "negotiation_complete";
  channel_id: string;
  requirement_id: string;
  result: {
    success: boolean;
    summary: string;
    participants: string[];
  };
  timestamp: string;
}
```

### 4.3 数据流图

```
┌──────────────┐                    ┌──────────────┐
│   Frontend   │                    │   Backend    │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       │  1. POST /api/requirements        │
       │──────────────────────────────────▶│
       │                                   │
       │  2. { requirement_id, channel_id }│
       │◀──────────────────────────────────│
       │                                   │
       │  3. WebSocket connect             │
       │──────────────────────────────────▶│
       │                                   │
       │  4. Subscribe channel             │
       │──────────────────────────────────▶│
       │                                   │
       │  5. Negotiation messages (stream) │
       │◀──────────────────────────────────│
       │                                   │
       │  6. Status updates (stream)       │
       │◀──────────────────────────────────│
       │                                   │
       │  7. Negotiation complete          │
       │◀──────────────────────────────────│
       │                                   │
```

---

## 5. 组件设计

### 5.1 新建组件

#### 5.1.1 LoginPanel

```typescript
// components/experience/LoginPanel.tsx
interface LoginPanelProps {
  onLoginClick: () => void;
  isLoading?: boolean;
}

// 功能：
// - 显示 SecondMe 登录按钮
// - 显示登录说明
// - 处理 loading 状态
```

#### 5.1.2 RequirementForm

```typescript
// components/experience/RequirementForm.tsx
interface RequirementFormProps {
  onSubmit: (data: RequirementInput) => Promise<void>;
  isSubmitting?: boolean;
  disabled?: boolean;
}

interface RequirementInput {
  title: string;
  description: string;
}

// 功能：
// - 标题输入（必填，最大 100 字符）
// - 描述输入（必填，最大 2000 字符）
// - 表单验证
// - 提交按钮（带 loading）
```

#### 5.1.3 NegotiationTimeline

```typescript
// components/experience/NegotiationTimeline.tsx
interface NegotiationTimelineProps {
  messages: NegotiationMessage[];
  status: NegotiationStatus;
  isLoading?: boolean;
}

type NegotiationStatus =
  | "waiting"      // 等待开始
  | "in_progress"  // 进行中
  | "completed"    // 已完成
  | "failed";      // 失败

// 功能：
// - 时间线展示消息
// - 自动滚动到最新
// - 状态指示器
// - 消息动画效果
```

#### 5.1.4 MessageBubble

```typescript
// components/experience/MessageBubble.tsx
interface MessageBubbleProps {
  message: NegotiationMessage;
  isCurrentUser?: boolean;
}

// 功能：
// - 消息气泡样式
// - 发送者头像和名称
// - 时间戳
// - 不同消息类型样式（text/system/action）
```

#### 5.1.5 AgentAvatar

```typescript
// components/experience/AgentAvatar.tsx
interface AgentAvatarProps {
  agentId: string;
  name: string;
  avatarUrl?: string;
  size?: "sm" | "md" | "lg";
  showName?: boolean;
}

// 功能：
// - 显示 Agent 头像
// - 无头像时显示首字母
// - 可选显示名称
```

### 5.2 扩展现有组件

#### 5.2.1 Button 扩展

```typescript
// 添加 loading 属性
interface ButtonProps {
  variant: 'primary' | 'outline';
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
  className?: string;
  isLoading?: boolean;  // 新增
  disabled?: boolean;   // 新增
}
```

### 5.3 Hooks 设计

#### 5.3.1 useAuth

```typescript
// hooks/useAuth.ts
interface UseAuthReturn {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}
```

#### 5.3.2 useWebSocket

```typescript
// hooks/useWebSocket.ts
interface UseWebSocketReturn {
  isConnected: boolean;
  subscribe: (channelId: string) => void;
  unsubscribe: (channelId: string) => void;
  messages: NegotiationMessage[];
  status: ConnectionStatus;
}
```

#### 5.3.3 useNegotiation

```typescript
// hooks/useNegotiation.ts
interface UseNegotiationReturn {
  submitRequirement: (data: RequirementInput) => Promise<string>;
  currentRequirement: Requirement | null;
  negotiationStatus: NegotiationStatus;
  messages: NegotiationMessage[];
  result: NegotiationResult | null;
  isLoading: boolean;
  error: Error | null;
}
```

---

## 6. 状态管理

### 6.1 状态结构

```typescript
// stores/experienceStore.ts
interface ExperienceState {
  // 认证状态
  auth: {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    error: string | null;
  };

  // 需求状态
  requirement: {
    current: Requirement | null;
    isSubmitting: boolean;
    error: string | null;
  };

  // 协商状态
  negotiation: {
    status: NegotiationStatus;
    messages: NegotiationMessage[];
    result: NegotiationResult | null;
  };

  // WebSocket 状态
  websocket: {
    isConnected: boolean;
    subscribedChannels: string[];
  };
}
```

### 6.2 状态管理方案

使用 React Context + useReducer 模式（轻量级，无需引入 Zustand）：

```typescript
// context/ExperienceContext.tsx
const ExperienceContext = createContext<ExperienceContextValue>(null);

export function ExperienceProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(experienceReducer, initialState);
  // ...
}
```

---

## 7. 任务拆解建议

### 7.1 任务列表

| TASK ID | 任务名称 | 优先级 | 依赖 | 预估工时 |
|---------|----------|--------|------|----------|
| TASK-EXP-001 | 页面路由与布局 | P0 | - | 2h |
| TASK-EXP-002 | 认证 Context 与 Hooks | P0 | - | 4h |
| TASK-EXP-003 | LoginPanel 组件 | P0 | TASK-EXP-002 | 3h |
| TASK-EXP-004 | RequirementForm 组件 | P0 | - | 4h |
| TASK-EXP-005 | WebSocket Hook | P0 | - | 4h |
| TASK-EXP-006 | MessageBubble 组件 | P1 | - | 2h |
| TASK-EXP-007 | AgentAvatar 组件 | P1 | - | 1h |
| TASK-EXP-008 | NegotiationTimeline 组件 | P0 | TASK-EXP-005, TASK-EXP-006 | 4h |
| TASK-EXP-009 | 页面集成与状态管理 | P0 | TASK-EXP-001~008 | 4h |
| TASK-EXP-010 | 错误处理与边界情况 | P1 | TASK-EXP-009 | 3h |
| TASK-EXP-011 | 动画与交互优化 | P2 | TASK-EXP-009 | 3h |

### 7.2 依赖关系图

```
TASK-EXP-001 (路由布局)
    │
    ├── TASK-EXP-002 (认证 Context) ──▶ TASK-EXP-003 (LoginPanel)
    │
    ├── TASK-EXP-004 (RequirementForm)
    │
    ├── TASK-EXP-005 (WebSocket Hook)
    │       │
    │       └── TASK-EXP-008 (NegotiationTimeline)
    │               │
    ├── TASK-EXP-006 (MessageBubble) ──┘
    │
    └── TASK-EXP-007 (AgentAvatar)

所有 ──▶ TASK-EXP-009 (页面集成)
              │
              ├── TASK-EXP-010 (错误处理)
              │
              └── TASK-EXP-011 (动画优化)
```

### 7.3 并行开发建议

**第一批（可并行）**：
- TASK-EXP-001: 页面路由与布局
- TASK-EXP-002: 认证 Context 与 Hooks
- TASK-EXP-004: RequirementForm 组件
- TASK-EXP-005: WebSocket Hook
- TASK-EXP-006: MessageBubble 组件
- TASK-EXP-007: AgentAvatar 组件

**第二批（依赖第一批）**：
- TASK-EXP-003: LoginPanel 组件（依赖 TASK-EXP-002）
- TASK-EXP-008: NegotiationTimeline 组件（依赖 TASK-EXP-005, TASK-EXP-006）

**第三批（集成）**：
- TASK-EXP-009: 页面集成与状态管理

**第四批（优化）**：
- TASK-EXP-010: 错误处理与边界情况
- TASK-EXP-011: 动画与交互优化

---

## 8. 技术决策

### 8.1 状态管理选型

**决策**：使用 React Context + useReducer

**理由**：
- 页面状态相对简单，不需要全局状态管理库
- 减少依赖，保持轻量
- 与 Next.js App Router 兼容性好

**替代方案**：Zustand
- 优点：API 简洁，性能好
- 缺点：增加依赖，对于单页面场景过重

### 8.2 实时通信方案

**决策**：原生 WebSocket + 自定义 Hook

**理由**：
- 后端已有 WebSocket 支持
- 消息协议简单，无需 Socket.IO
- 自定义 Hook 可以更好地控制重连逻辑

**重连策略**：
- 指数退避：1s, 2s, 4s, 8s, 16s, 最大 30s
- 最大重试次数：10 次
- 页面可见时自动重连

### 8.3 认证 Token 存储

**决策**：使用 httpOnly Cookie（由后端设置）

**理由**：
- 安全性更高，防止 XSS 攻击
- 自动随请求发送
- 后端已支持

**替代方案**：localStorage
- 优点：前端可控
- 缺点：XSS 风险

### 8.4 错误处理策略

**决策**：分层错误处理

```typescript
// 1. API 层：统一错误格式
interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// 2. Hook 层：错误状态管理
const { error, clearError } = useNegotiation();

// 3. UI 层：错误展示组件
<ErrorBoundary fallback={<ErrorFallback />}>
  <NegotiationTimeline />
</ErrorBoundary>
```

---

## 9. 风险与预案

### 9.1 风险列表

| 风险 | 影响 | 概率 | 预案 |
|------|------|------|------|
| SecondMe OAuth2 服务不稳定 | 用户无法登录 | 中 | 添加重试机制，显示友好错误提示 |
| WebSocket 连接不稳定 | 消息丢失 | 中 | 实现重连机制，消息去重 |
| 后端 API 响应慢 | 用户体验差 | 低 | 添加 loading 状态，超时处理 |
| 协商过程过长 | 用户等待焦虑 | 中 | 显示进度指示，预估时间 |

### 9.2 降级方案

**WebSocket 降级**：
- 如果 WebSocket 连接失败，降级为轮询模式
- 轮询间隔：3 秒

**认证降级**：
- 如果 OAuth2 回调失败，提供重试按钮
- 显示详细错误信息

---

## 10. 未决项

### 10.1 [OPEN] 消息历史加载

- 是否需要加载历史消息？
- 如果需要，分页策略是什么？

### 10.2 [OPEN] 协商超时处理

- 协商超时时间是多少？
- 超时后如何处理？

### 10.3 [TBD] 移动端适配

- 是否需要移动端适配？
- 如果需要，优先级如何？

---

## 附录 A：文件结构

```
towow-website/
├── app/
│   └── experience/
│       ├── page.tsx              # 体验页主页面
│       └── layout.tsx            # 体验页布局
├── components/
│   └── experience/
│       ├── LoginPanel.tsx
│       ├── LoginPanel.module.css
│       ├── RequirementForm.tsx
│       ├── RequirementForm.module.css
│       ├── NegotiationTimeline.tsx
│       ├── NegotiationTimeline.module.css
│       ├── MessageBubble.tsx
│       ├── MessageBubble.module.css
│       ├── AgentAvatar.tsx
│       ├── AgentAvatar.module.css
│       └── index.ts
├── hooks/
│   ├── useAuth.ts
│   ├── useWebSocket.ts
│   └── useNegotiation.ts
├── context/
│   └── ExperienceContext.tsx
├── types/
│   └── experience.ts
└── lib/
    └── api/
        ├── auth.ts
        └── requirements.ts
```

---

## 附录 B：CSS 变量扩展

```css
/* 体验页专用变量 */
:root {
  /* 消息气泡 */
  --bubble-user-bg: var(--color-primary-light);
  --bubble-agent-bg: var(--color-surface);
  --bubble-system-bg: var(--color-muted);

  /* 状态颜色 */
  --status-pending: var(--color-warning);
  --status-processing: var(--color-info);
  --status-completed: var(--color-success);
  --status-failed: var(--color-error);

  /* 动画 */
  --animation-message-in: slideInUp 0.3s ease-out;
  --animation-pulse: pulse 2s infinite;
}
```

---

*文档版本：v5*
*最后更新：2026-01-29*
