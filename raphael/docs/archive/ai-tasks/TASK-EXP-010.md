# TASK-EXP-010: 错误处理与边界情况

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-010 |
| 状态 | TODO |
| 优先级 | P1 |
| 预估工时 | 3h |
| Beads ID | `towow-28t` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

完善错误处理机制，处理各种边界情况，提升用户体验。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 8.4 节错误处理策略
- TECH-PRODUCT-PAGE-v5.md 第 9 节风险与预案
- TASK-EXP-009 集成后的页面

## 3. 输出

- `/components/experience/ErrorBoundary.tsx` - 错误边界组件
- `/components/experience/ErrorFallback.tsx` - 错误回退组件
- 各组件错误处理增强

## 4. 验收标准

- [ ] API 错误统一格式处理
- [ ] 网络错误友好提示
- [ ] WebSocket 断线重连提示
- [ ] OAuth2 回调失败处理
- [ ] 协商超时处理
- [ ] ErrorBoundary 捕获渲染错误
- [ ] 重试机制实现
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：
- TASK-EXP-009（页面集成与状态管理）

**接口依赖**：无

## 6. 实现要点

```typescript
// 统一错误格式
interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// 错误处理工具
export function handleApiError(error: unknown): ApiError {
  if (error instanceof Response) {
    return {
      code: `HTTP_${error.status}`,
      message: getHttpErrorMessage(error.status),
    };
  }
  if (error instanceof Error) {
    return {
      code: 'UNKNOWN_ERROR',
      message: error.message,
    };
  }
  return {
    code: 'UNKNOWN_ERROR',
    message: '发生未知错误',
  };
}

// ErrorBoundary
class ErrorBoundary extends React.Component<Props, State> {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} onRetry={this.reset} />;
    }
    return this.props.children;
  }
}

// ErrorFallback
function ErrorFallback({ error, onRetry }: ErrorFallbackProps) {
  return (
    <ContentCard className={styles.errorFallback}>
      <h3>出错了</h3>
      <p>{error.message}</p>
      <Button variant="outline" onClick={onRetry}>
        重试
      </Button>
    </ContentCard>
  );
}
```

## 7. 测试要点

- API 错误处理测试
- 网络断开测试
- WebSocket 断线测试
- OAuth2 失败测试
- ErrorBoundary 测试
- 重试机制测试

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
