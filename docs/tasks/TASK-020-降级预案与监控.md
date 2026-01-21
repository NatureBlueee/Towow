# TASK-020：降级预案与监控

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-020 |
| 所属Phase | Phase 7：降级与监控 |
| 硬依赖 | TASK-013 |
| 接口依赖 | - |
| 可并行 | - |
| 预估工作量 | 0.5天 |
| 状态 | 待开始 |
| 优先级 | P1（2000人演示稳定性保障） |

---

## 任务描述

实现完整的降级预案，确保2000人现场演示的稳定性。包括：
- LLM服务降级（熔断器）
- 请求限流
- 演示模式（预设案例）
- 健康检查与监控

---

## 风险识别

### 主要风险点

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|---------|
| LLM服务超时/不可用 | 中 | 高 | 熔断器 + 预设响应 |
| 2000人并发压力 | 中 | 高 | 限流 + 排队 |
| OpenAgent连接断开 | 低 | 高 | 演示模式兜底 |
| 前端SSE断开 | 中 | 中 | 断线重连 + 轮询降级 |

### 演示场景特殊性

- **时间紧迫**：不能让观众等待太久
- **容错性低**：一次失败可能影响整体观感
- **可预测性需求**：需要确保至少有成功案例

---

## 具体工作

### 1. LLM降级服务

`towow/services/llm.py`:

```python
"""
带降级能力的LLM服务
"""
import asyncio
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


# 预设的降级响应
FALLBACK_RESPONSES = {
    "demand_understanding": {
        "surface_demand": "用户需求处理中",
        "deep_understanding": {"motivation": "待分析"},
        "uncertainties": ["需要更多信息"],
        "confidence": "low"
    },
    "smart_filter": [
        {"agent_id": "user_agent_demo1", "reason": "推荐候选人1"},
        {"agent_id": "user_agent_demo2", "reason": "推荐候选人2"},
        {"agent_id": "user_agent_demo3", "reason": "推荐候选人3"},
    ],
    "response_generation": {
        "decision": "participate",
        "contribution": "愿意参与协作",
        "conditions": [],
        "reasoning": "对该活动感兴趣"
    },
    "proposal_aggregation": {
        "summary": "初步合作方案已生成",
        "assignments": [
            {"agent_id": "user_agent_demo1", "role": "参与者", "responsibility": "待分配"}
        ],
        "timeline": "待确定",
        "confidence": "medium"
    }
}


class LLMServiceWithFallback:
    """带降级能力的LLM服务"""

    def __init__(
        self,
        primary_client,
        fallback_responses: Dict = None,
        timeout: float = 30.0,
        failure_threshold: int = 3
    ):
        self.primary = primary_client
        self.fallback_responses = fallback_responses or FALLBACK_RESPONSES
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.circuit_open = False
        self._reset_task = None

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
            fallback_key: 降级响应的key

        Returns:
            LLM响应或降级响应（JSON字符串）
        """
        import json

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
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            system=system or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _record_failure(self):
        """记录失败"""
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            logger.error("Circuit breaker opened due to repeated failures")
            # 60秒后尝试恢复
            self._reset_task = asyncio.create_task(self._reset_circuit_breaker())

    async def _reset_circuit_breaker(self):
        """重置熔断器"""
        await asyncio.sleep(60)
        self.circuit_open = False
        self.failure_count = 0
        logger.info("Circuit breaker reset")

    def _get_fallback(self, key: str, prompt: str) -> str:
        """获取降级响应"""
        import json

        if key and key in self.fallback_responses:
            return json.dumps(self.fallback_responses[key], ensure_ascii=False)

        return self._generate_generic_fallback(prompt)

    def _generate_generic_fallback(self, prompt: str) -> str:
        """生成通用降级响应"""
        import json

        if "筛选" in prompt or "filter" in prompt.lower():
            return json.dumps(self.fallback_responses.get("smart_filter", []))
        elif "聚合" in prompt or "aggregate" in prompt.lower():
            return json.dumps(self.fallback_responses.get("proposal_aggregation", {}))
        else:
            return json.dumps({"status": "processing", "message": "系统处理中"})

    def get_status(self) -> Dict:
        """获取服务状态"""
        return {
            "circuit_open": self.circuit_open,
            "failure_count": self.failure_count,
            "threshold": self.failure_threshold
        }
```

### 2. 请求限流中间件

`towow/middleware/rate_limiter.py`:

```python
"""
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
        """获取请求许可"""
        async with self.lock:
            now = time.time()

            # 清理1分钟前的记录
            user_reqs = self.user_requests[user_id]
            user_reqs[:] = [t for t in user_reqs if now - t < 60]

            # 检查用户限流
            if len(user_reqs) >= self.per_user_per_minute:
                raise HTTPException(
                    status_code=429,
                    detail="请求过于频繁，请稍后再试"
                )

            # 检查全局限流
            if self.current_requests >= self.max_concurrent:
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
            try:
                self.queue.put_nowait(True)
            except asyncio.QueueFull:
                pass

    async def _wait_in_queue(self):
        """在队列中等待"""
        await self.queue.get()

    def get_status(self) -> dict:
        """获取限流器状态"""
        return {
            "current_requests": self.current_requests,
            "max_concurrent": self.max_concurrent,
            "queue_size": self.queue.qsize()
        }


# 全局限流器实例
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """限流中间件"""
    # 跳过非API请求
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    # 跳过事件流请求和健康检查
    if "/events/" in request.url.path or "/health" in request.url.path:
        return await call_next(request)

    user_id = request.headers.get("X-User-ID", "anonymous")

    try:
        await rate_limiter.acquire(user_id)
        response = await call_next(request)
        return response
    finally:
        await rate_limiter.release()
```

### 3. 演示模式服务

`towow/services/demo_mode.py`:

```python
"""
演示模式服务
"""
from typing import Dict, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


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
                "id": "demo_meetup",
                "trigger_keywords": ["聚会", "活动", "party", "meetup"],
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
                    {"agent": "demo_alice", "action": "feedback_negotiate", "message": "时间能调到下午3点吗？", "delay": 7},
                    {"agent": "demo_charlie", "action": "feedback_accept", "delay": 8},
                    {"agent": "demo_alice", "action": "feedback_accept", "delay": 10},
                ]
            },
            {
                "id": "demo_designer",
                "trigger_keywords": ["设计师", "原型", "UI", "设计"],
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
                    {"agent": "demo_emma", "action": "decline", "reason": "最近项目太多", "delay": 3},
                    {"agent": "demo_david", "action": "feedback_accept", "delay": 5},
                ]
            }
        ]

    def match_demo_case(self, raw_input: str) -> Optional[Dict]:
        """匹配预设案例"""
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
        """运行演示协商脚本"""
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

    def enable(self):
        """启用演示模式"""
        self.demo_mode_enabled = True
        logger.info("Demo mode enabled")

    def disable(self):
        """禁用演示模式"""
        self.demo_mode_enabled = False
        logger.info("Demo mode disabled")

    def get_status(self) -> Dict:
        """获取演示模式状态"""
        return {
            "enabled": self.demo_mode_enabled,
            "available_cases": [c["id"] for c in self.demo_cases]
        }


# 全局演示模式服务
demo_service = DemoModeService()
```

### 4. 健康检查路由

`towow/api/routers/health.py`:

```python
"""
健康检查路由
"""
from fastapi import APIRouter
from datetime import datetime
import psutil

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    """基础健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health():
    """详细健康状态"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    services = {
        "database": await check_database(),
        "llm": await check_llm(),
        "rate_limiter": check_rate_limiter()
    }

    overall_healthy = all(s.get("healthy", False) for s in services.values())

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": round(memory.available / 1024 / 1024, 2)
        },
        "services": services
    }


async def check_database() -> dict:
    """检查数据库"""
    try:
        # TODO: 实际数据库检查
        return {"healthy": True, "latency_ms": 5}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


async def check_llm() -> dict:
    """检查LLM服务"""
    try:
        from services.llm import llm_service
        status = llm_service.get_status()
        return {
            "healthy": not status.get("circuit_open", False),
            "circuit_open": status.get("circuit_open", False),
            "failure_count": status.get("failure_count", 0)
        }
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_rate_limiter() -> dict:
    """检查限流器"""
    from middleware.rate_limiter import rate_limiter
    status = rate_limiter.get_status()
    return {
        "healthy": True,
        **status
    }
```

### 5. 管理员API

`towow/api/routers/admin.py`:

```python
"""
管理员API
"""
from fastapi import APIRouter, HTTPException
from services.demo_mode import demo_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/demo-mode/enable")
async def enable_demo_mode():
    """启用演示模式"""
    demo_service.enable()
    return {"status": "enabled", "message": "演示模式已启用"}


@router.post("/demo-mode/disable")
async def disable_demo_mode():
    """禁用演示模式"""
    demo_service.disable()
    return {"status": "disabled", "message": "演示模式已禁用"}


@router.get("/demo-mode/status")
async def get_demo_mode_status():
    """获取演示模式状态"""
    return demo_service.get_status()


@router.get("/stats")
async def get_system_stats():
    """获取系统统计"""
    from events.recorder import event_recorder
    from middleware.rate_limiter import rate_limiter

    return {
        "events_in_memory": len(event_recorder.events),
        "active_subscribers": len(event_recorder.subscribers),
        "rate_limiter": rate_limiter.get_status(),
        "demo_mode": demo_service.get_status()
    }
```

---

## 降级等级

| 等级 | 触发条件 | 降级措施 |
|------|---------|---------|
| **L0 正常** | 所有服务正常 | 无 |
| **L1 轻度** | LLM偶尔超时 | 使用缓存响应、延长超时 |
| **L2 中度** | LLM频繁超时（熔断器打开） | 启用演示模式、使用预设响应 |
| **L3 严重** | 系统不可用 | 显示维护页面 |

---

## 现场操作手册

### 快速切换演示模式

```bash
# 启用演示模式
curl -X POST http://localhost:8000/api/admin/demo-mode/enable

# 禁用演示模式
curl -X POST http://localhost:8000/api/admin/demo-mode/disable
```

### 检查系统状态

```bash
# 健康检查
curl http://localhost:8000/api/health/detailed

# 查看系统统计
curl http://localhost:8000/api/admin/stats
```

---

## 验收标准

- [ ] LLM超时后自动使用降级响应
- [ ] 熔断器在连续3次失败后打开
- [ ] 熔断器60秒后自动尝试恢复
- [ ] 并发超过100时正确限流
- [ ] 演示模式可以一键启用/禁用
- [ ] 演示脚本运行流畅
- [ ] 健康检查端点正常工作
- [ ] 至少有2个预设演示案例可用

---

## 产出物

- `towow/services/llm.py`（带降级）
- `towow/middleware/rate_limiter.py`
- `towow/services/demo_mode.py`
- `towow/api/routers/health.py`
- `towow/api/routers/admin.py`
- 操作手册（本文档）

---

**创建时间**: 2026-01-21
**来源**: supplement-05-fallback.md
**优先级**: P1（2000人演示稳定性保障）
