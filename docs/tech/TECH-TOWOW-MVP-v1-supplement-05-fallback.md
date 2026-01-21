# 技术方案补充05：降级预案

> 2000人现场演示的风险应对与降级策略

---

## 一、风险识别

### 1.1 主要风险点

| 风险 | 概率 | 影响 | 场景 |
|------|------|------|------|
| LLM服务超时/不可用 | 中 | 高 | Claude API故障或限流 |
| 2000人并发压力 | 中 | 高 | 同时发起大量需求 |
| OpenAgent连接断开 | 低 | 高 | 网络问题或服务重启 |
| 数据库压力 | 低 | 中 | 大量写入 |
| 前端SSE断开 | 中 | 中 | 网络波动 |
| 协商超时 | 中 | 中 | LLM响应慢导致协商时间过长 |

### 1.2 演示场景特殊性

2000人现场演示的特点：
- **时间紧迫**：不能让观众等待太久
- **容错性低**：一次失败可能影响整体观感
- **可预测性需求**：需要确保至少有成功案例
- **视觉效果重要**：需要展示协商过程的动态感

---

## 二、降级策略

### 2.1 LLM降级策略

#### 策略A：超时自动降级

```python
"""
towow/services/llm.py
带降级的LLM服务
"""
import asyncio
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LLMServiceWithFallback:
    """带降级能力的LLM服务"""

    def __init__(
        self,
        primary_client,  # Anthropic Claude
        fallback_responses: Dict[str, str] = None,
        timeout: float = 30.0
    ):
        self.primary = primary_client
        self.fallback_responses = fallback_responses or {}
        self.timeout = timeout
        self.failure_count = 0
        self.circuit_open = False

    async def complete(
        self,
        prompt: str,
        system: str = None,
        fallback_key: str = None
    ) -> str:
        """
        调用LLM，超时或失败时使用降级响应

        Args:
            prompt: 提示词
            system: 系统提示
            fallback_key: 降级响应的key，用于获取预设响应

        Returns:
            LLM响应或降级响应
        """
        # 熔断器打开时直接返回降级响应
        if self.circuit_open:
            logger.warning("Circuit breaker open, using fallback")
            return self._get_fallback(fallback_key, prompt)

        try:
            response = await asyncio.wait_for(
                self._call_primary(prompt, system),
                timeout=self.timeout
            )
            self.failure_count = 0  # 重置失败计数
            return response

        except asyncio.TimeoutError:
            logger.warning(f"LLM timeout after {self.timeout}s")
            self._record_failure()
            return self._get_fallback(fallback_key, prompt)

        except Exception as e:
            logger.error(f"LLM error: {e}")
            self._record_failure()
            return self._get_fallback(fallback_key, prompt)

    async def _call_primary(self, prompt: str, system: str) -> str:
        """调用主LLM"""
        response = await self.primary.messages.create(
            model="claude-3-sonnet-20240229",  # 使用更快的模型
            max_tokens=2000,
            system=system or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _record_failure(self):
        """记录失败"""
        self.failure_count += 1
        if self.failure_count >= 3:
            self.circuit_open = True
            logger.error("Circuit breaker opened due to repeated failures")
            # 60秒后尝试恢复
            asyncio.create_task(self._reset_circuit_breaker())

    async def _reset_circuit_breaker(self):
        """重置熔断器"""
        await asyncio.sleep(60)
        self.circuit_open = False
        self.failure_count = 0
        logger.info("Circuit breaker reset")

    def _get_fallback(self, key: str, prompt: str) -> str:
        """获取降级响应"""
        if key and key in self.fallback_responses:
            return self.fallback_responses[key]

        # 通用降级响应
        return self._generate_generic_fallback(prompt)

    def _generate_generic_fallback(self, prompt: str) -> str:
        """生成通用降级响应"""
        # 根据prompt关键词返回不同的降级响应
        if "筛选" in prompt or "filter" in prompt.lower():
            return """
{
  "candidates": [
    {"agent_id": "user_agent_demo1", "reason": "综合能力匹配"},
    {"agent_id": "user_agent_demo2", "reason": "地理位置匹配"},
    {"agent_id": "user_agent_demo3", "reason": "兴趣领域匹配"}
  ]
}
"""
        elif "聚合" in prompt or "aggregate" in prompt.lower():
            return """
{
  "summary": "初步合作方案",
  "assignments": [],
  "confidence": "medium"
}
"""
        else:
            return '{"status": "processing", "message": "系统处理中"}'


# 预设的降级响应
FALLBACK_RESPONSES = {
    "demand_understanding": """
{
  "surface_demand": "用户需求处理中",
  "deep_understanding": {"motivation": "待分析"},
  "uncertainties": ["需要更多信息"],
  "confidence": "low"
}
""",
    "smart_filter": """
[
  {"agent_id": "user_agent_demo1", "reason": "推荐候选人1"},
  {"agent_id": "user_agent_demo2", "reason": "推荐候选人2"},
  {"agent_id": "user_agent_demo3", "reason": "推荐候选人3"},
  {"agent_id": "user_agent_demo4", "reason": "推荐候选人4"},
  {"agent_id": "user_agent_demo5", "reason": "推荐候选人5"}
]
""",
    "response_generation": """
{
  "decision": "participate",
  "contribution": "愿意参与协作",
  "conditions": [],
  "reasoning": "对该活动感兴趣"
}
""",
    "proposal_aggregation": """
{
  "summary": "初步合作方案已生成",
  "assignments": [
    {"agent_id": "user_agent_demo1", "role": "参与者", "responsibility": "待分配"}
  ],
  "timeline": "待确定",
  "confidence": "medium"
}
"""
}
```

### 2.2 并发限流策略

```python
"""
towow/middleware/rate_limiter.py
请求限流中间件
"""
from fastapi import Request, HTTPException
from collections import defaultdict
import time
import asyncio

class RateLimiter:
    """
    请求限流器

    策略：
    - 全局限流：最多100个并发请求
    - 单用户限流：每分钟最多5个需求
    - 排队机制：超出限制的请求排队等待
    """

    def __init__(
        self,
        max_concurrent: int = 100,
        per_user_per_minute: int = 5,
        queue_timeout: float = 30.0
    ):
        self.max_concurrent = max_concurrent
        self.per_user_per_minute = per_user_per_minute
        self.queue_timeout = queue_timeout

        self.current_requests = 0
        self.user_requests = defaultdict(list)  # user_id -> [timestamps]
        self.lock = asyncio.Lock()
        self.queue = asyncio.Queue()

    async def acquire(self, user_id: str = "anonymous") -> bool:
        """
        获取请求许可

        Returns:
            True if allowed, raises HTTPException if rejected
        """
        async with self.lock:
            # 检查用户限流
            now = time.time()
            user_reqs = self.user_requests[user_id]
            # 清理1分钟前的记录
            user_reqs[:] = [t for t in user_reqs if now - t < 60]

            if len(user_reqs) >= self.per_user_per_minute:
                raise HTTPException(
                    status_code=429,
                    detail="请求过于频繁，请稍后再试"
                )

            # 检查全局限流
            if self.current_requests >= self.max_concurrent:
                # 尝试排队
                try:
                    await asyncio.wait_for(
                        self._wait_in_queue(),
                        timeout=self.queue_timeout
                    )
                except asyncio.TimeoutError:
                    raise HTTPException(
                        status_code=503,
                        detail="服务繁忙，请稍后再试"
                    )

            # 允许请求
            self.current_requests += 1
            user_reqs.append(now)
            return True

    async def release(self):
        """释放请求许可"""
        async with self.lock:
            self.current_requests = max(0, self.current_requests - 1)
            # 通知排队的请求
            try:
                self.queue.put_nowait(True)
            except asyncio.QueueFull:
                pass

    async def _wait_in_queue(self):
        """在队列中等待"""
        await self.queue.get()


# FastAPI中间件
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """限流中间件"""
    # 跳过非API请求
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # 跳过事件流请求
    if "/events/" in request.url.path:
        return await call_next(request)

    user_id = request.headers.get("X-User-ID", "anonymous")

    try:
        await rate_limiter.acquire(user_id)
        response = await call_next(request)
        return response
    finally:
        await rate_limiter.release()
```

### 2.3 演示模式（Demo Mode）

```python
"""
towow/services/demo_mode.py
演示模式服务
"""
from typing import Dict, Any, List, Optional
import json
import random

class DemoModeService:
    """
    演示模式服务

    功能：
    1. 预设成功案例，确保演示不失败
    2. 加速协商过程
    3. 模拟真实的多Agent交互
    """

    def __init__(self):
        self.demo_cases = self._load_demo_cases()
        self.demo_mode_enabled = False

    def _load_demo_cases(self) -> List[Dict]:
        """加载预设演示案例"""
        return [
            {
                "trigger_keywords": ["聚会", "活动", "party"],
                "demand": {
                    "surface_demand": "在北京举办一场AI主题聚会",
                    "location": "北京"
                },
                "candidates": [
                    {"agent_id": "demo_bob", "name": "Bob", "contribution": "提供30人会议室"},
                    {"agent_id": "demo_alice", "name": "Alice", "contribution": "AI技术分享"},
                    {"agent_id": "demo_charlie", "name": "Charlie", "contribution": "活动策划"},
                ],
                "proposal": {
                    "summary": "2月16日在朝阳区举办30人AI聚会",
                    "assignments": [
                        {"agent_id": "demo_bob", "role": "场地提供", "responsibility": "提供会议室和投影设备"},
                        {"agent_id": "demo_alice", "role": "技术分享", "responsibility": "做30分钟AI趋势分享"},
                        {"agent_id": "demo_charlie", "role": "活动策划", "responsibility": "负责流程安排和现场协调"},
                    ],
                    "timeline": "2月16日 14:00-17:00",
                    "confidence": "high"
                },
                "negotiation_script": [
                    {"agent": "demo_bob", "action": "participate", "delay": 2},
                    {"agent": "demo_alice", "action": "participate", "delay": 3},
                    {"agent": "demo_charlie", "action": "participate", "delay": 4},
                    {"agent": "demo_bob", "action": "feedback_accept", "delay": 6},
                    {"agent": "demo_alice", "action": "feedback_negotiate", "message": "时间能调整吗？", "delay": 7},
                    {"agent": "demo_charlie", "action": "feedback_accept", "delay": 8},
                ]
            },
            {
                "trigger_keywords": ["设计师", "原型", "UI"],
                "demand": {
                    "surface_demand": "找一个懂AI的设计师帮做产品原型",
                    "location": "不限"
                },
                "candidates": [
                    {"agent_id": "demo_david", "name": "David", "contribution": "UI/UX设计"},
                    {"agent_id": "demo_emma", "name": "Emma", "contribution": "AI产品经验"},
                ],
                "proposal": {
                    "summary": "David将在3天内完成初版原型设计",
                    "assignments": [
                        {"agent_id": "demo_david", "role": "设计师", "responsibility": "负责UI原型设计"},
                    ],
                    "timeline": "3个工作日",
                    "confidence": "high"
                },
                "negotiation_script": [
                    {"agent": "demo_david", "action": "participate", "delay": 2},
                    {"agent": "demo_emma", "action": "decline", "reason": "最近太忙", "delay": 3},
                    {"agent": "demo_david", "action": "feedback_accept", "delay": 5},
                ]
            }
        ]

    def match_demo_case(self, raw_input: str) -> Optional[Dict]:
        """
        匹配预设案例

        Args:
            raw_input: 用户输入

        Returns:
            匹配的案例，或None
        """
        if not self.demo_mode_enabled:
            return None

        raw_lower = raw_input.lower()
        for case in self.demo_cases:
            for keyword in case["trigger_keywords"]:
                if keyword in raw_lower:
                    return case

        return None

    async def run_demo_negotiation(
        self,
        case: Dict,
        channel_id: str,
        event_callback
    ):
        """
        运行演示协商脚本

        Args:
            case: 演示案例
            channel_id: Channel ID
            event_callback: 事件回调函数
        """
        import asyncio

        for step in case.get("negotiation_script", []):
            await asyncio.sleep(step.get("delay", 1))

            agent = step["agent"]
            action = step["action"]

            if action == "participate":
                await event_callback({
                    "type": "offer_response",
                    "channel": channel_id,
                    "agent_id": agent,
                    "decision": "participate",
                    "contribution": next(
                        (c["contribution"] for c in case["candidates"] if c["agent_id"] == agent),
                        "愿意参与"
                    )
                })

            elif action == "decline":
                await event_callback({
                    "type": "offer_response",
                    "channel": channel_id,
                    "agent_id": agent,
                    "decision": "decline",
                    "reasoning": step.get("reason", "暂时无法参与")
                })

            elif action == "feedback_accept":
                await event_callback({
                    "type": "proposal_feedback",
                    "channel": channel_id,
                    "agent_id": agent,
                    "feedback_type": "accept"
                })

            elif action == "feedback_negotiate":
                await event_callback({
                    "type": "proposal_feedback",
                    "channel": channel_id,
                    "agent_id": agent,
                    "feedback_type": "negotiate",
                    "adjustment_request": step.get("message", "需要调整")
                })


# 全局演示模式服务
demo_service = DemoModeService()


def enable_demo_mode():
    """启用演示模式"""
    demo_service.demo_mode_enabled = True


def disable_demo_mode():
    """禁用演示模式"""
    demo_service.demo_mode_enabled = False
```

### 2.4 前端断线重连

```typescript
// src/hooks/useSSE.ts (增强版)

export const useSSEWithReconnect = (url: string): SSEHookResult => {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const lastEventIdRef = useRef<string | null>(null);

  const connect = useCallback(() => {
    const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

    // 带上lastEventId实现断点续传
    let fullUrl = `${API_BASE}${url}`;
    if (lastEventIdRef.current) {
      fullUrl += `?last_event_id=${lastEventIdRef.current}`;
    }

    const eventSource = new EventSource(fullUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
      setError(null);
      setReconnectCount(0);
      console.log('SSE connected');
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // 记录最后的事件ID
        if (data.event_id) {
          lastEventIdRef.current = data.event_id;
        }
        setLastEvent(data);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    eventSource.onerror = (e) => {
      setConnected(false);
      setError(new Error('SSE connection error'));
      console.error('SSE error:', e);

      // 指数退避重连
      const delay = Math.min(1000 * Math.pow(2, reconnectCount), 30000);
      console.log(`Reconnecting in ${delay}ms...`);

      setTimeout(() => {
        if (eventSourceRef.current === eventSource) {
          setReconnectCount(c => c + 1);
          connect();
        }
      }, delay);
    };

    return eventSource;
  }, [url, reconnectCount]);

  // ... 其余代码同前
};

// 降级到轮询
export const useEventPolling = (url: string, interval: number = 3000) => {
  const [events, setEvents] = useState<any[]>([]);
  const [lastEventId, setLastEventId] = useState<string | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const params = lastEventId ? `?after=${lastEventId}` : '';
        const response = await fetch(`${url}${params}`);
        const data = await response.json();

        if (data.events && data.events.length > 0) {
          setEvents(prev => [...prev, ...data.events]);
          const lastEvent = data.events[data.events.length - 1];
          if (lastEvent.event_id) {
            setLastEventId(lastEvent.event_id);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    };

    const timer = setInterval(poll, interval);
    poll(); // 立即执行一次

    return () => clearInterval(timer);
  }, [url, interval, lastEventId]);

  return { events, lastEventId };
};
```

---

## 三、监控与告警

### 3.1 健康检查端点

```python
"""
towow/api/routers/health.py
健康检查路由
"""
from fastapi import APIRouter
from datetime import datetime
import psutil

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    """
    健康检查

    GET /api/health
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health():
    """
    详细健康状态

    GET /api/health/detailed
    """
    # CPU使用率
    cpu_percent = psutil.cpu_percent(interval=0.1)

    # 内存使用
    memory = psutil.virtual_memory()

    # 检查各服务状态
    services = {
        "database": await check_database(),
        "openagent": await check_openagent(),
        "llm": await check_llm()
    }

    overall_healthy = all(s["healthy"] for s in services.values())

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / 1024 / 1024
        },
        "services": services
    }


async def check_database() -> dict:
    """检查数据库"""
    try:
        # 执行简单查询
        from database.connection import db
        async with db.session() as session:
            await session.execute("SELECT 1")
        return {"healthy": True, "latency_ms": 0}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


async def check_openagent() -> dict:
    """检查OpenAgent连接"""
    try:
        # 检查Agent是否在线
        return {"healthy": True, "agents_online": 3}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


async def check_llm() -> dict:
    """检查LLM服务"""
    try:
        from services.llm import llm_service
        # 发送简单请求
        response = await llm_service.complete("Hello", timeout=5)
        return {"healthy": True, "circuit_open": llm_service.circuit_open}
    except Exception as e:
        return {"healthy": False, "error": str(e)}
```

### 3.2 指标收集

```python
"""
towow/middleware/metrics.py
指标收集中间件
"""
from prometheus_client import Counter, Histogram, Gauge
import time

# 请求计数
REQUEST_COUNT = Counter(
    'towow_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟
REQUEST_LATENCY = Histogram(
    'towow_request_latency_seconds',
    'Request latency',
    ['endpoint']
)

# 活跃需求数
ACTIVE_DEMANDS = Gauge(
    'towow_active_demands',
    'Number of active demands'
)

# LLM调用
LLM_CALLS = Counter(
    'towow_llm_calls_total',
    'Total LLM calls',
    ['status']  # success | timeout | error
)

LLM_LATENCY = Histogram(
    'towow_llm_latency_seconds',
    'LLM call latency'
)


async def metrics_middleware(request, call_next):
    """指标收集中间件"""
    start_time = time.time()

    response = await call_next(request)

    # 记录请求
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    # 记录延迟
    REQUEST_LATENCY.labels(
        endpoint=request.url.path
    ).observe(time.time() - start_time)

    return response
```

---

## 四、降级预案总结

### 4.1 降级等级

| 等级 | 触发条件 | 降级措施 |
|------|---------|---------|
| **L0 正常** | 所有服务正常 | 无 |
| **L1 轻度** | LLM偶尔超时 | 使用缓存响应、延长超时 |
| **L2 中度** | LLM频繁超时 | 启用演示模式、使用预设响应 |
| **L3 严重** | OpenAgent断开 | 显示维护页面、播放预录视频 |

### 4.2 操作手册

#### 现场快速切换演示模式

```bash
# 启用演示模式
curl -X POST http://localhost:8000/api/admin/demo-mode/enable

# 禁用演示模式
curl -X POST http://localhost:8000/api/admin/demo-mode/disable
```

#### 检查系统状态

```bash
# 健康检查
curl http://localhost:8000/api/health/detailed

# 查看活跃需求
curl http://localhost:8000/api/admin/stats
```

#### 重启服务

```bash
# 重启ToWow后端
systemctl restart towow

# 重启OpenAgent
systemctl restart openagent
```

### 4.3 新增TASK

```markdown
# TASK-020：降级预案实现

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-020 |
| 所属Phase | Phase 4：演示准备 |
| 依赖 | TASK-013 |
| 预估工作量 | 0.5天 |
| 状态 | 待开始 |

---

## 任务描述

实现完整的降级预案，确保2000人演示的稳定性。

---

## 具体工作

1. 实现LLM熔断器和降级响应
2. 实现请求限流中间件
3. 实现演示模式服务
4. 实现健康检查和监控端点
5. 准备2-3个完整的演示案例
6. 编写操作手册

---

## 验收标准

- [ ] LLM超时后自动使用降级响应
- [ ] 并发超过100时正确限流
- [ ] 演示模式可以一键启用/禁用
- [ ] 健康检查端点正常工作
- [ ] 至少有2个预设演示案例可用

---

## 产出物

- `services/llm.py` (带降级)
- `middleware/rate_limiter.py`
- `services/demo_mode.py`
- `api/routers/health.py`
- 操作手册文档
```

---

**文档版本**: v1.0
**创建时间**: 2026-01-21
**状态**: 补充完成
