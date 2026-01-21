# TASK-018：实时推送服务（后端SSE）

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-018 |
| 所属Phase | Phase 5：前端开发 |
| 硬依赖 | TASK-002 |
| 接口依赖 | - |
| 可并行 | TASK-015~017（前端可基于接口契约并行开发） |
| 预估工作量 | 1天 |
| 状态 | 待开始 |
| 关键路径 | YES |

---

## 任务描述

实现后端SSE（Server-Sent Events）实时推送服务，将协商事件推送给前端。这是前后端实时通信的核心组件。

---

## 技术方案

### 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Agent     │────>│ EventBus    │────>│ SSE Router  │
│   事件      │     │ 事件总线    │     │ 推送服务    │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               v
                                        ┌─────────────┐
                                        │   前端      │
                                        │   客户端    │
                                        └─────────────┘
```

---

## 具体工作

### 1. 事件记录器

`towow/events/recorder.py`:

```python
"""
事件记录器
记录所有事件并支持订阅
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class EventRecord:
    """事件记录"""
    event_id: str
    event_type: str
    timestamp: str
    channel_id: Optional[str]
    demand_id: Optional[str]
    payload: Dict


class EventRecorder:
    """
    事件记录器

    功能：
    1. 记录所有事件（内存中保留最近1000条）
    2. 支持按channel/demand查询历史事件
    3. 支持订阅新事件
    """

    MAX_EVENTS = 1000

    def __init__(self):
        self.events: deque = deque(maxlen=self.MAX_EVENTS)
        self.subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def record(self, event: Dict):
        """记录事件"""
        async with self._lock:
            record = EventRecord(
                event_id=event.get("event_id", ""),
                event_type=event.get("event_type", ""),
                timestamp=event.get("timestamp", datetime.utcnow().isoformat()),
                channel_id=event.get("payload", {}).get("channel_id"),
                demand_id=event.get("payload", {}).get("demand_id"),
                payload=event.get("payload", {})
            )
            self.events.append(record)

            # 通知所有订阅者
            for queue in self.subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Subscriber queue full, dropping event")

    def subscribe(self) -> asyncio.Queue:
        """订阅事件流"""
        queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        logger.debug(f"New subscriber, total: {len(self.subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """取消订阅"""
        self.subscribers.discard(queue)
        logger.debug(f"Subscriber removed, total: {len(self.subscribers)}")

    def get_by_channel(self, channel_id: str, limit: int = 50) -> List[Dict]:
        """获取指定channel的历史事件"""
        result = []
        for record in reversed(self.events):
            if record.channel_id and channel_id in record.channel_id:
                result.append({
                    "event_id": record.event_id,
                    "event_type": record.event_type,
                    "timestamp": record.timestamp,
                    "payload": record.payload
                })
                if len(result) >= limit:
                    break
        return list(reversed(result))

    def get_by_demand(self, demand_id: str, limit: int = 50) -> List[Dict]:
        """获取指定demand的历史事件"""
        result = []
        for record in reversed(self.events):
            if record.demand_id == demand_id:
                result.append({
                    "event_id": record.event_id,
                    "event_type": record.event_type,
                    "timestamp": record.timestamp,
                    "payload": record.payload
                })
                if len(result) >= limit:
                    break
        return list(reversed(result))

    def get_after(self, event_id: str, limit: int = 50) -> List[Dict]:
        """获取指定事件ID之后的事件"""
        result = []
        found = False
        for record in self.events:
            if found:
                result.append({
                    "event_id": record.event_id,
                    "event_type": record.event_type,
                    "timestamp": record.timestamp,
                    "payload": record.payload
                })
                if len(result) >= limit:
                    break
            elif record.event_id == event_id:
                found = True
        return result


# 全局事件记录器
event_recorder = EventRecorder()
```

### 2. SSE事件推送路由

`towow/api/routers/events.py`:

```python
"""
SSE事件推送路由
"""
from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional
import asyncio
import json
from events.recorder import event_recorder

router = APIRouter(prefix="/api/events", tags=["events"])


async def event_generator(
    demand_id: str,
    request: Request,
    last_event_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    SSE事件生成器

    为特定demand_id生成事件流
    """
    # 订阅事件
    queue = event_recorder.subscribe()

    try:
        # 首先发送历史事件
        channel_id = f"collab-{demand_id[:8]}"

        if last_event_id:
            # 断点续传：从指定事件ID之后开始
            history = event_recorder.get_after(last_event_id)
        else:
            # 全量历史
            history = event_recorder.get_by_channel(channel_id)

        for event in history:
            yield f"data: {json.dumps(event)}\n\n"

        # 持续发送新事件
        while True:
            # 检查客户端是否断开
            if await request.is_disconnected():
                break

            try:
                # 等待新事件（超时5秒发送心跳）
                event = await asyncio.wait_for(queue.get(), timeout=5.0)

                # 过滤只发送相关事件
                payload = event.get("payload", {})
                event_channel = payload.get("channel_id") or payload.get("channel")
                event_demand = payload.get("demand_id")

                if (event_channel and demand_id[:8] in event_channel) or \
                   (event_demand and event_demand == demand_id):
                    yield f"data: {json.dumps(event)}\n\n"

            except asyncio.TimeoutError:
                # 发送心跳
                yield f": heartbeat\n\n"

    finally:
        event_recorder.unsubscribe(queue)


@router.get("/stream/{demand_id}")
async def stream_events(
    demand_id: str,
    request: Request,
    last_event_id: Optional[str] = Query(None, description="断点续传的事件ID")
):
    """
    SSE事件流端点

    GET /api/events/stream/{demand_id}

    支持断点续传：添加 ?last_event_id=xxx 参数
    """
    return StreamingResponse(
        event_generator(demand_id, request, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
            "Access-Control-Allow-Origin": "*",  # CORS
        }
    )


@router.get("/recent/{demand_id}")
async def get_recent_events(
    demand_id: str,
    count: int = Query(50, ge=1, le=200, description="返回事件数量"),
    after: Optional[str] = Query(None, description="指定事件ID之后的事件")
):
    """
    获取最近事件（轮询备用）

    GET /api/events/recent/{demand_id}?count=50&after=event_id
    """
    channel_id = f"collab-{demand_id[:8]}"

    if after:
        events = event_recorder.get_after(after, count)
    else:
        events = event_recorder.get_by_channel(channel_id, count)

    return {
        "events": events,
        "count": len(events),
        "has_more": len(events) == count
    }


@router.get("/health")
async def events_health():
    """
    事件服务健康检查
    """
    return {
        "status": "healthy",
        "subscribers": len(event_recorder.subscribers),
        "events_in_memory": len(event_recorder.events)
    }
```

### 3. 需求API路由

`towow/api/routers/demand.py`:

```python
"""
需求API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
from uuid import uuid4
from datetime import datetime
from events.recorder import event_recorder

router = APIRouter(prefix="/api/demand", tags=["demand"])


class DemandSubmitRequest(BaseModel):
    raw_input: str
    user_id: Optional[str] = "anonymous"


class DemandSubmitResponse(BaseModel):
    demand_id: str
    channel_id: str
    status: str
    understanding: Dict[str, Any]


@router.post("/submit", response_model=DemandSubmitResponse)
async def submit_demand(request: DemandSubmitRequest):
    """
    提交需求

    POST /api/demand/submit
    """
    try:
        # 生成demand_id
        demand_id = f"d-{uuid4().hex[:8]}"
        channel_id = f"collab-{demand_id[2:]}"

        # 调用SecondMe理解需求（TODO: 实际调用）
        understanding = {
            "surface_demand": request.raw_input,
            "confidence": "high"
        }

        # 记录需求理解事件
        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.demand.understood",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "demand_id": demand_id,
                "channel_id": channel_id,
                "surface_demand": understanding["surface_demand"],
                "confidence": understanding["confidence"]
            }
        })

        # 异步触发筛选流程
        asyncio.create_task(
            trigger_filtering(demand_id, channel_id, request.raw_input)
        )

        return DemandSubmitResponse(
            demand_id=demand_id,
            channel_id=channel_id,
            status="processing",
            understanding=understanding
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def trigger_filtering(demand_id: str, channel_id: str, raw_input: str):
    """
    触发筛选流程（异步）

    这里应该调用Coordinator的筛选逻辑
    """
    # 模拟延迟
    await asyncio.sleep(2)

    # 记录筛选完成事件
    await event_recorder.record({
        "event_id": f"evt-{uuid4().hex[:8]}",
        "event_type": "towow.filter.completed",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "demand_id": demand_id,
            "channel_id": channel_id,
            "candidates": [
                {"agent_id": "user_agent_bob", "reason": "场地资源"},
                {"agent_id": "user_agent_alice", "reason": "技术分享"},
                {"agent_id": "user_agent_charlie", "reason": "活动策划"}
            ]
        }
    })


@router.get("/{demand_id}")
async def get_demand(demand_id: str):
    """
    获取需求详情

    GET /api/demand/{demand_id}
    """
    # TODO: 从数据库查询
    return {
        "demand_id": demand_id,
        "status": "processing",
        "created_at": datetime.utcnow().isoformat()
    }


@router.get("/{demand_id}/status")
async def get_demand_status(demand_id: str):
    """
    获取需求状态

    GET /api/demand/{demand_id}/status
    """
    # TODO: 从数据库查询
    return {
        "demand_id": demand_id,
        "status": "processing",
        "current_round": 1
    }
```

### 4. 事件记录集成

`towow/events/integration.py`:

```python
"""
事件记录集成
在Agent事件发生时自动记录
"""
from events.recorder import event_recorder
from events.bus import event_bus


async def record_towow_event(event: dict):
    """记录ToWow事件到recorder"""
    await event_recorder.record(event)


def setup_event_recording():
    """
    设置事件记录

    订阅所有towow.*事件并记录
    """
    # 订阅所有towow事件
    event_bus.subscribe("towow.*", record_towow_event)

    # 也可以单独订阅特定事件
    event_types = [
        "towow.demand.broadcast",
        "towow.demand.understood",
        "towow.filter.completed",
        "towow.offer.submitted",
        "towow.proposal.distributed",
        "towow.proposal.feedback",
        "towow.proposal.finalized",
        "towow.negotiation.failed",
        "towow.subnet.triggered",
        "towow.subnet.completed",
        "towow.gap.identified"
    ]

    for event_type in event_types:
        event_bus.subscribe(event_type, record_towow_event)
```

### 5. FastAPI应用集成

`towow/api/main.py`:

```python
"""
FastAPI应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import demand, events, health

# 创建应用
app = FastAPI(
    title="ToWow API",
    description="ToWow协作网络后端API",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(demand.router)
app.include_router(events.router)
app.include_router(health.router)


@app.on_event("startup")
async def startup():
    """应用启动时初始化"""
    from events.integration import setup_event_recording
    setup_event_recording()
    print("ToWow API started")


@app.on_event("shutdown")
async def shutdown():
    """应用关闭时清理"""
    print("ToWow API shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 接口契约

### SSE事件格式

```typescript
interface SSEEvent {
  event_id: string;       // 唯一事件ID
  event_type: string;     // 事件类型
  timestamp: string;      // ISO8601时间戳
  payload: {
    demand_id?: string;
    channel_id?: string;
    [key: string]: any;
  };
}
```

### SSE端点

**GET /api/events/stream/{demand_id}**

- 返回：`text/event-stream`
- 支持断点续传：`?last_event_id=xxx`
- 心跳间隔：5秒

### 轮询端点（降级方案）

**GET /api/events/recent/{demand_id}**

- Query参数：`count` (1-200), `after` (event_id)
- 返回：`{ events: [], count: number, has_more: boolean }`

---

## 验收标准

- [ ] SSE端点可以正常连接
- [ ] 事件可以实时推送到前端
- [ ] 心跳机制正常工作（每5秒）
- [ ] 客户端断开后资源正确释放
- [ ] 断点续传功能正常
- [ ] 历史事件可以正确获取
- [ ] CORS配置正确，前端可以连接
- [ ] 轮询端点作为降级方案可用

---

## 产出物

- `towow/events/recorder.py`
- `towow/events/integration.py`
- `towow/api/routers/events.py`
- `towow/api/routers/demand.py`
- `towow/api/main.py`

---

**创建时间**: 2026-01-21
**来源**: supplement-03-frontend.md
**关键路径**: YES - 前后端实时通信核心

> Beads 任务ID：`towow-kdy`
