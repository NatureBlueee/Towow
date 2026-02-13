# PLAN-010: 统一入口选择器

**关联**: ADR-010 (已批准)
**阶段**: ④ 实现方案
**修订**: v2 — 审查后修复 isAuthenticated 语义混淆盲区

---

## 变更总览

| # | 文件 | 类型 | 说明 |
|---|------|------|------|
| 1 | `website/app/enter/page.tsx` | **新建** | 入口选择器页面 |
| 2 | `website/app/page.tsx` | 修改 | CTA href 从 SecondMe OAuth → `/enter` |
| 3 | `website/hooks/useStoreAuth.ts` | 修改 | localStorage fallback + authSource + login/logout 修复 |
| 4 | `website/components/store/DemandInput.tsx` | 修改 | assist 按钮 gate 改用 authSource |
| 5 | `website/components/store/HistoryPanel.tsx` | 修改 | 历史 gate 改用 authSource |

后端**零改动**。quick-register API 已有（ADR-009），SecondMe OAuth 已有。
Store 页面（`store/page.tsx`、`store/[scene]/page.tsx`）**无需改动**——全部通过 hook 返回值间接适配。

---

## 变更 1: `/enter` 入口页

**新建** `website/app/enter/page.tsx`

### 页面结构

```
┌─────────────────────────────────────┐
│           通爻 (logo/link)           │
├─────────────────────────────────────┤
│                                     │
│        选择你的进入方式               │
│        不同方式，不同起点             │
│                                     │
│  ┌─────────┐  ┌─────────┐          │
│  │SecondMe │  │ Google  │          │
│  │AI 分身   │  │即将开放  │          │
│  └─────────┘  └─────────┘          │
│                                     │
│  ── 或者直接加入 ──                  │
│                                     │
│  [邮箱注册表单 / 手机号注册表单]      │
│  (tab 切换)                         │
│                                     │
│  ── 开发者？──                       │
│                                     │
│  ┌─────────────────────┐            │
│  │ MCP · 在你的 IDE 中  │            │
│  │ 连接通爻网络         │            │
│  └─────────────────────┘            │
│                                     │
└─────────────────────────────────────┘
```

### 五个入口的行为

| 入口 | 点击行为 |
|------|---------|
| SecondMe | `window.location.href = '/api/auth/secondme/start?return_to=/store/'` |
| Google | Toast "Google 登录即将开放，请先使用其他方式" |
| 邮箱 | 展开邮箱表单（email + name + raw_text），提交 quick-register，成功后跳转 /store |
| 手机号 | 展开手机号表单（phone + name + raw_text），提交 quick-register，成功后跳转 /store |
| MCP | 外部链接（暂指向 GitHub README 或 MCP 安装文档） |

### 邮箱/手机号表单

复用 `quickRegister()` API（`website/lib/store-api.ts`），与 Playground 同一后端。

注册成功后：
1. `localStorage.setItem('playground_agent_id', result.agent_id)`
2. `localStorage.setItem('playground_display_name', result.display_name)`
3. `router.push('/store')`

### Skill 调度

| 子任务 | Skill |
|--------|-------|
| 页面设计与布局 | `ui-ux-pro-max` |
| 组件实现 | `towow-eng-frontend` |

---

## 变更 2: 首页 CTA

**修改** `website/app/page.tsx` line 31

```
# Before
primaryButtonHref="/api/auth/secondme/start?return_to=/store/"

# After
primaryButtonHref="/enter"
```

**契约变更分析**：
- 这是一个 URL 路径变更（契约）
- 消费方：仅 `page.tsx` 中的 `<Hero>` 组件
- 无其他消费方（首页 CTA 是单一入口点）

---

## 变更 3: useStoreAuth 扩展（核心变更）

**修改** `website/hooks/useStoreAuth.ts`

### 审查发现的盲区

原计划只加 localStorage fallback 给 `isAuthenticated`。但 `isAuthenticated` 在系统中被两种语义消费：
- **有身份**（能发协商）→ SecondMe + localStorage 用户都满足
- **有 SecondMe cookie**（能用分身辅助、能看历史）→ 只有 SecondMe 用户满足

**教训**: 扩展标志语义 ≠ 增加判断条件。当 boolean 从"唯一条件 A"扩展为"A 或 B"时，所有下游必须验证它依赖的是"标志为 true"还是"条件 A 为 true"。

### 返回值扩展

```typescript
interface UseStoreAuthReturn {
  user: StoreUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;    // 有任何身份（SecondMe 或 localStorage）
  authSource: 'secondme' | 'local' | null;  // 新增：身份来源
  login: () => void;           // 改为跳转 /enter（不再直接跳 SecondMe）
  logout: () => Promise<void>; // 改为同时清理 cookie + localStorage
  error: ApiError | null;
  clearError: () => void;
}
```

### checkAuth 逻辑

```typescript
// 1. GET /api/auth/me → 有 cookie → authSource='secondme', isAuthenticated=true
// 2. 如果 step 1 失败 → 检查 localStorage playground_agent_id
//    → 有 → authSource='local', isAuthenticated=true, user={agent_id, display_name}
//    → 无 → authSource=null, isAuthenticated=false
```

### login() 修改

```typescript
// Before: window.location.href = getAuthUrl('/store/')  → 直接跳 SecondMe
// After:  window.location.href = '/enter'  → 统一入口选择器
```

### logout() 修改

```typescript
// Before: 只调 logoutApi()（清 cookie）
// After:  logoutApi() + localStorage.removeItem('playground_agent_id') + localStorage.removeItem('playground_display_name')
```

这确保两种身份都能正确登出。

---

## 变更 4: DemandInput assist 按钮 gate

**修改** `website/components/store/DemandInput.tsx`

### 问题

当前 line 150: `if (!isAuthenticated) { onLoginRequest?.(); return; }`

localStorage 用户 `isAuthenticated=true` → 通过 gate → 调 assist-demand → 后端需要 cookie → 401。

### 修复

DemandInput 需要接收新 prop `authSource`，assist 按钮的 gate 改为：

```typescript
// Before: if (!isAuthenticated) { onLoginRequest?.(); return; }
// After:  if (authSource !== 'secondme') { 显示提示 "此功能需要 SecondMe 账号"; return; }
```

对于非 SecondMe 用户，assist 按钮仍然可见但点击后提示需要 SecondMe。
submit（发起协商）按钮不受影响——所有用户都能提交需求。

### 接口变更

```typescript
// DemandInput props 新增:
authSource?: 'secondme' | 'local' | null;
```

Store 页面传递: `<DemandInput authSource={auth.authSource} ... />`

---

## 变更 5: HistoryPanel gate

**修改** `website/components/store/HistoryPanel.tsx`

### 问题

HistoryPanel 接收 `isAuthenticated` prop，当为 true 时 fetch `GET /store/api/history`。
后端要求 cookie session → localStorage 用户会 401。

### 修复

HistoryPanel 新增 `authSource` prop，只在 `authSource === 'secondme'` 时 fetch。

```typescript
// Before: isAuthenticated && fetch history
// After:  authSource === 'secondme' && fetch history
```

---

## 端到端验证

### 链路 A: SecondMe 用户
```
首页 CTA → /enter → 点 SecondMe → OAuth → cookie 设置 → /store
→ useStoreAuth: cookie 检测成功 → authSource='secondme', isAuthenticated=true
→ DemandInput: assist 可用 ✓, submit 可用 ✓
→ HistoryPanel: 可看历史 ✓
→ StoreHeader: 显示头像+名字+退出 ✓
```

### 链路 B: 邮箱用户
```
首页 CTA → /enter → 填邮箱表单 → quick-register → localStorage 设置 → /store
→ useStoreAuth: cookie 失败 → localStorage 成功 → authSource='local', isAuthenticated=true
→ DemandInput: assist 显示提示需 SecondMe ✓, submit 可用（传 localStorage agent_id）✓
→ HistoryPanel: 不 fetch（authSource!='secondme'）✓
→ StoreHeader: 显示首字母头像+名字+退出 ✓, 退出清 localStorage ✓
```

### 链路 C: 手机号用户
```
同链路 B（quick-register API 同时支持 email 和 phone）
```

### 链路 D: 未登录用户直接访问 /store
```
→ useStoreAuth: cookie 失败 → localStorage 无 → authSource=null, isAuthenticated=false
→ DemandInput: submit 仍可用（userId 默认 'app_store_user'）✓
→ StoreHeader: 显示"连接你的 Agent" → 点击 → /enter ✓
```

### 链路 E: Google 用户
```
首页 CTA → /enter → 点 Google → Toast "即将开放" → 选其他方式
```

### 链路 F: MCP 用户
```
首页 CTA → /enter → 点 MCP → 新窗口打开 MCP 文档
```

---

## 消费方验证（审查后更新）

| 消费方 | 依赖的是什么 | 处理 |
|--------|------------|------|
| `store/page.tsx` | `auth.user?.agent_id` → submit | 不变，hook 返回正确 user |
| `store/[scene]/page.tsx` | 同上 | 不变 |
| `DemandInput` assist | **需要 SecondMe cookie** | 变更 4: gate 改用 `authSource` |
| `DemandInput` submit | 需要 `isAuthenticated`（或匿名） | 不变 |
| `StoreHeader` login | **应跳 /enter** | 变更 3: `login()` → `/enter` |
| `StoreHeader` logout | **需清 localStorage** | 变更 3: `logout()` 清两者 |
| `StoreHeader` user display | `user.display_name` | 不变（localStorage user 有此字段）|
| `HistoryPanel` | **需要 SecondMe cookie** | 变更 5: gate 改用 `authSource` |
| `useStoreNegotiation` | `submit(intent, scope, userId)` | 不变，userId 从 `auth.user?.agent_id` 传入 |

---

## Skill 调度

| 子任务 | Skill |
|--------|-------|
| `/enter` 页面设计 | `ui-ux-pro-max` |
| `/enter` 页面实现 | `towow-eng-frontend` |
| `useStoreAuth` 扩展 | `towow-dev` |
| `DemandInput` + `HistoryPanel` 适配 | `towow-dev` |
| 首页 CTA 改一行 | `towow-dev` |

---

## 不做

- 不做 Google OAuth 后端（按钮只 Toast）
- 不做 Playground 页面重构（`/playground` 保留，`/enter` 是新页面）
- 不合并两套身份机制（暂时并行）
- 不给 localStorage 用户做 assist-demand（需要 SecondMe）
- 不给 localStorage 用户做历史（需要 cookie session）
