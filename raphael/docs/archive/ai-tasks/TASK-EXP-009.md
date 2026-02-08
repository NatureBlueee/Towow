# TASK-EXP-009: 页面集成与状态管理

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-009 |
| 状态 | TODO |
| 优先级 | P0 |
| 预估工时 | 4h |
| Beads ID | `towow-wvq` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

将所有组件集成到体验页，实现完整的用户流程和状态管理。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 3 节页面设计
- TECH-PRODUCT-PAGE-v5.md 第 6 节状态管理
- TASK-EXP-001 ~ TASK-EXP-008 的所有组件

## 3. 输出

- `/app/experience/page.tsx` - 完整的体验页实现
- `/hooks/useNegotiation.ts` - 协商流程 Hook
- `/lib/api/requirements.ts` - 需求 API 封装

## 4. 验收标准

- [ ] 完整用户流程：登录 -> 提交需求 -> 查看协商 -> 查看结果
- [ ] 页面状态机正确实现（INIT/LOGIN/READY/SUBMITTING/NEGOTIATING/COMPLETED/ERROR）
- [ ] 状态切换流畅，无闪烁
- [ ] 错误状态正确处理
- [ ] 所有组件正确集成
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：
- TASK-EXP-001（页面路由与布局）
- TASK-EXP-002（认证 Context 与 Hooks）
- TASK-EXP-003（LoginPanel 组件）
- TASK-EXP-004（RequirementForm 组件）
- TASK-EXP-005（WebSocket Hook）
- TASK-EXP-006（MessageBubble 组件）
- TASK-EXP-007（AgentAvatar 组件）
- TASK-EXP-008（NegotiationTimeline 组件）

**接口依赖**：
- 后端 `/api/requirements` 接口

## 6. 实现要点

```typescript
// app/experience/page.tsx
type PageState =
  | 'INIT'
  | 'LOGIN'
  | 'READY'
  | 'SUBMITTING'
  | 'NEGOTIATING'
  | 'COMPLETED'
  | 'ERROR';

export default function ExperiencePage() {
  const { user, isLoading: authLoading, login } = useAuth();
  const {
    submitRequirement,
    currentRequirement,
    negotiationStatus,
    messages,
    result,
    isLoading,
    error,
  } = useNegotiation();

  const [pageState, setPageState] = useState<PageState>('INIT');

  // 状态机逻辑
  useEffect(() => {
    if (authLoading) {
      setPageState('INIT');
    } else if (!user) {
      setPageState('LOGIN');
    } else if (negotiationStatus === 'completed') {
      setPageState('COMPLETED');
    } else if (negotiationStatus === 'in_progress') {
      setPageState('NEGOTIATING');
    } else if (isLoading) {
      setPageState('SUBMITTING');
    } else if (error) {
      setPageState('ERROR');
    } else {
      setPageState('READY');
    }
  }, [authLoading, user, negotiationStatus, isLoading, error]);

  return (
    <div className={styles.page}>
      {pageState === 'INIT' && <LoadingScreen />}
      {pageState === 'LOGIN' && <LoginPanel onLoginClick={login} />}
      {pageState === 'READY' && (
        <RequirementForm onSubmit={submitRequirement} />
      )}
      {(pageState === 'SUBMITTING' || pageState === 'NEGOTIATING') && (
        <NegotiationTimeline
          messages={messages}
          status={negotiationStatus}
          isLoading={isLoading}
          currentUserId={user?.agent_id}
        />
      )}
      {pageState === 'COMPLETED' && <ResultPanel result={result} />}
      {pageState === 'ERROR' && <ErrorPanel error={error} />}
    </div>
  );
}
```

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

## 7. 测试要点

- 完整用户流程端到端测试
- 状态切换测试
- 错误处理测试
- 组件集成测试

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
