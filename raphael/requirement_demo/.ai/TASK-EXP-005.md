# TASK-EXP-005: WebSocket Hook

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-005 |
| 状态 | TODO |
| 优先级 | P0 |
| 预估工时 | 4h |
| Beads ID | `towow-32d` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

实现 WebSocket 连接管理 Hook，支持频道订阅、消息接收、自动重连。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 4.2 节 WebSocket 消息协议
- TECH-PRODUCT-PAGE-v5.md 第 5.3.2 节 useWebSocket 设计
- 后端 WebSocket 接口文档

## 3. 输出

- `/hooks/useWebSocket.ts` - WebSocket Hook
- `/types/experience.ts` - 消息类型定义（扩展）

## 4. 验收标准

- [ ] 支持 WebSocket 连接建立
- [ ] 支持频道订阅/取消订阅
- [ ] 支持消息接收和解析
- [ ] 实现指数退避重连（1s, 2s, 4s, 8s, 16s, 最大 30s）
- [ ] 最大重试次数 10 次
- [ ] 页面可见时自动重连
- [ ] 连接状态暴露（isConnected）
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：无

**接口依赖**：
- 后端 WebSocket 端点 `ws://localhost:8000/ws/{agent_id}`

## 6. 实现要点

```typescript
// hooks/useWebSocket.ts
interface UseWebSocketReturn {
  isConnected: boolean;
  subscribe: (channelId: string) => void;
  unsubscribe: (channelId: string) => void;
  messages: NegotiationMessage[];
  status: ConnectionStatus;
}

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export function useWebSocket(agentId: string | null): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<NegotiationMessage[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);

  // 指数退避重连
  const getRetryDelay = () => {
    const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
    return delay;
  };

  // 连接逻辑
  const connect = useCallback(() => {
    if (!agentId) return;
    // ...
  }, [agentId]);

  // 订阅频道
  const subscribe = useCallback((channelId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        channel_id: channelId,
      }));
    }
  }, []);

  return { isConnected, subscribe, unsubscribe, messages, status };
}
```

## 7. 测试要点

- 连接建立测试
- 消息接收测试
- 频道订阅测试
- 断线重连测试
- 重连次数限制测试

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
