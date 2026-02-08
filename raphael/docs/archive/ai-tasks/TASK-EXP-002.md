# TASK-EXP-002: 认证 Context 与 Hooks

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-002 |
| 状态 | TODO |
| 优先级 | P0 |
| 预估工时 | 4h |
| Beads ID | `towow-7b6` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

实现认证状态管理的 Context 和 useAuth Hook，提供登录、登出、Token 刷新等认证能力。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 4.1 节 OAuth2 接口契约
- TECH-PRODUCT-PAGE-v5.md 第 5.3.1 节 useAuth 设计
- 后端 OAuth2 API 文档

## 3. 输出

- `/context/ExperienceContext.tsx` - 体验页状态 Context
- `/hooks/useAuth.ts` - 认证 Hook
- `/lib/api/auth.ts` - 认证 API 封装
- `/types/experience.ts` - 类型定义

## 4. 验收标准

- [ ] useAuth Hook 提供 user, isLoading, isAuthenticated 状态
- [ ] login() 方法正确跳转到 SecondMe OAuth2 授权页
- [ ] logout() 方法正确清除认证状态
- [ ] Token 存储使用 httpOnly Cookie（后端设置）
- [ ] 页面刷新后认证状态保持
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：无

**接口依赖**：
- 后端 `/api/auth/login` 接口
- 后端 `/api/auth/callback` 接口
- 后端 `/api/auth/me` 接口
- 后端 `/api/auth/logout` 接口

## 6. 实现要点

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

export function useAuth(): UseAuthReturn {
  const context = useContext(ExperienceContext);
  // ...
}
```

```typescript
// lib/api/auth.ts
export async function getAuthUrl(): Promise<string> {
  const response = await fetch('/api/auth/login');
  const data = await response.json();
  return data.auth_url;
}

export async function getCurrentUser(): Promise<User | null> {
  const response = await fetch('/api/auth/me', {
    credentials: 'include',
  });
  if (!response.ok) return null;
  return response.json();
}
```

## 7. 测试要点

- 未登录状态测试
- 登录流程测试（跳转）
- 登录回调处理测试
- 登出流程测试
- Token 过期处理测试

---

## 实现记录

> 开发完成后填写

### 实现说明

（待填写）

### 测试结果

（待填写）

### 变更记录

| 时间 | 变更内容 | 变更人 |
|------|----------|--------|
| 2026-01-29 | 创建任务 | proj |
