# OpenAgent Framework Migration Analysis

> **Document Version**: v1.0
> **Created**: 2026-01-22
> **Status**: DRAFT
> **Author**: Tech Agent B

---

## 1. OpenAgent Framework Capability Summary

### 1.1 Framework Overview

**OpenAgents** is an open-source framework for creating AI Agent Networks - autonomous agents that connect and collaborate seamlessly. Key characteristics:

- **Version**: 0.7.x (latest 0.8.5)
- **Python Version**: 3.10+ (3.12 recommended)
- **Architecture**: Event-driven, multi-protocol support
- **License**: Apache 2.0

### 1.2 Core Capabilities

| Capability | Description | ToWow Relevance |
|------------|-------------|-----------------|
| **Event System** | All communication via events with pattern matching (`@on_event`) | HIGH - Maps to ToWow's event bus |
| **Multi-Protocol** | HTTP (8700), gRPC (8600), MCP (8800), WebSocket | MEDIUM - ToWow uses simple HTTP API |
| **Workspace API** | High-level API for channels, agents, direct messages | HIGH - Maps to ToWow's channel system |
| **Mods System** | Plugin architecture for extending functionality | HIGH - Can implement ToWow business logic |
| **Task Delegation** | Built-in mod for agent task assignment | HIGH - Maps to ToWow's negotiation flow |
| **Project Mod** | Template-based project workflows | MEDIUM - Potential for demand lifecycle |
| **LLM Integration** | Multi-provider support (OpenAI, Anthropic, etc.) | HIGH - ToWow uses LLM for proposals |

### 1.3 Agent Types in OpenAgents

```
CollaboratorAgent
      |
      v
  WorkerAgent  <-- Recommended base class
      |
      +-- on_startup() / on_shutdown()
      +-- on_direct(context)
      +-- on_channel_post(context)
      +-- on_channel_mention(context)
      +-- on_channel_reply(context)
      +-- @on_event(pattern) decorator
```

### 1.4 Key Patterns from Demos

**Demo 08 (Alternative Service Project)** - Most relevant pattern:

```python
class CoordinatorAgent(WorkerAgent):
    default_agent_id = "coordinator"

    async def on_startup(self):
        # Bind adapters after client is ready
        self.delegation_adapter.bind_client(self.client)
        self.project_adapter.bind_client(self.client)

    @on_event("project.notification.started")
    async def handle_project_start(self, context: EventContext):
        # Delegate tasks to other agents
        task_id = await self.delegation_adapter.delegate_task(...)
        result = await self._wait_for_task_completion(task_id)
```

---

## 2. Architecture Mapping Analysis

### 2.1 Current ToWow Architecture

```
                    ToWow Current Architecture

    +-------------------+
    |   API Layer       |  FastAPI endpoints
    |   (main.py)       |  - POST /api/demand
    +-------------------+  - GET /api/events
            |
            v
    +-------------------+
    | AgentFactory      |  Creates/manages agents
    | (factory.py)      |  - get_coordinator()
    +-------------------+  - get_channel_admin()
            |              - get_user_agent()
            v
    +-------------------+
    | TowowBaseAgent    |  Base class (independent)
    | (base.py)         |  - Mock workspace
    +-------------------+  - send_to_agent()
            |
    +-------+-------+
    |       |       |
    v       v       v
+-------+ +-------+ +-------+
|Coord- | |Channel| |User   |
|inator | |Admin  | |Agent  |
+-------+ +-------+ +-------+
    |         |         |
    v         v         v
+-------------------+
| AgentRouter       |  Routes messages between agents
| (router.py)       |  - Message deduplication
+-------------------+  - Agent lookup via factory
```

### 2.2 OpenAgent Target Architecture

```
                    OpenAgent Target Architecture

    +-------------------+
    | Network           |  OpenAgents Network
    | (network.yaml)    |  - HTTP/gRPC transport
    +-------------------+  - Mods configuration
            |
            v
    +-------------------+
    | Mods              |
    | - messaging       |  Thread messaging
    | - task_delegation |  Task assignment
    | - towow_business  |  Custom business logic (NEW)
    +-------------------+
            |
            v
    +-------------------+
    | WorkerAgent       |  OpenAgents base class
    | (worker_agent.py) |  - Built-in event routing
    +-------------------+  - Workspace API
            |
    +-------+-------+
    |       |       |
    v       v       v
+-------+ +-------+ +-------+
|Towow  | |Towow  | |Towow  |
|Coord  | |Channel| |User   |
|Agent  | |Admin  | |Agent  |
+-------+ +-------+ +-------+
         (extends WorkerAgent)
```

### 2.3 Component Mapping Table

| ToWow Component | OpenAgent Equivalent | Migration Strategy |
|-----------------|---------------------|-------------------|
| `TowowBaseAgent` | `WorkerAgent` | Replace base class |
| `EventContext` | `EventContext` from models | Direct mapping |
| `ChannelMessageContext` | `ChannelMessageContext` | Direct mapping |
| `AgentRouter.route_message()` | `workspace().agent().send()` | Built-in routing |
| `send_to_agent()` | `workspace().agent().send()` | API compatible |
| `post_to_channel()` | `workspace().channel().post()` | API compatible |
| `event_bus.publish()` | Client event system | Adapt to OpenAgent events |
| `AgentFactory` | Network agent management | Configuration-based |

### 2.4 Event Mapping

| ToWow Event | OpenAgent Event Pattern |
|-------------|------------------------|
| `towow.demand.understood` | `towow.demand.understood` (custom) |
| `towow.filter.completed` | `towow.filter.completed` (custom) |
| `towow.proposal.generated` | `towow.proposal.generated` (custom) |
| `towow.negotiation.finalized` | `towow.negotiation.finalized` (custom) |
| Direct message | `agent.message` |
| Channel message | `thread.channel_message.notification` |

---

## 3. Migration Feasibility Assessment

### 3.1 Compatibility Analysis

#### HIGH Compatibility (Easy Migration)

| Feature | ToWow | OpenAgent | Notes |
|---------|-------|-----------|-------|
| Agent lifecycle | `on_startup()` | `on_startup()` | Identical API |
| Direct messaging | `send_to_agent()` | `workspace().agent().send()` | Similar pattern |
| Channel posting | `post_to_channel()` | `workspace().channel().post()` | Similar pattern |
| Event handling | Manual routing | `@on_event()` decorator | More elegant |
| Async patterns | `async/await` | `async/await` | Identical |

#### MEDIUM Compatibility (Adaptation Needed)

| Feature | ToWow | OpenAgent | Migration Effort |
|---------|-------|-----------|------------------|
| Agent Factory | Custom `AgentFactory` class | Network config + adapters | Refactor to config |
| Message routing | Custom `AgentRouter` | Built-in via connector | Remove custom code |
| State management | In-memory `Dict` | Shared cache mod | Use mod adapter |
| LLM integration | Custom `LLMService` | OpenAgent LLM providers | Adapt interface |

#### LOW Compatibility (Significant Rework)

| Feature | ToWow | OpenAgent | Migration Effort |
|---------|-------|-----------|------------------|
| Negotiation state machine | `ChannelStatus` enum | No equivalent | Custom mod needed |
| Gap identification | Custom `GapIdentifier` | No equivalent | Custom mod needed |
| Subnet management | Custom `SubnetManager` | Task delegation mod | Partial mapping |

### 3.2 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **API Breaking Changes** | HIGH | Wrapper layer for backward compat |
| **Event System Differences** | MEDIUM | Custom event types registration |
| **State Persistence** | MEDIUM | Use shared cache mod |
| **LLM Provider Lock-in** | LOW | OpenAgent supports multiple providers |
| **Performance Overhead** | LOW | gRPC transport for high performance |

### 3.3 Benefits of Migration

1. **Reduced Code Complexity**
   - Remove custom `AgentRouter` (225 lines)
   - Remove mock `_MockWorkspace` (90 lines)
   - Use built-in event routing

2. **Enhanced Features**
   - Multi-protocol support (HTTP, gRPC, MCP)
   - Built-in task delegation mod
   - Studio UI for monitoring/debugging
   - Network discovery and publishing

3. **Better Maintainability**
   - Active open-source community
   - Regular updates and bug fixes
   - Standardized patterns

4. **Scalability**
   - Decentralized network topology options
   - Agent group management
   - Built-in connection management

---

## 4. Migration Implementation Plan

### 4.1 Phase Overview

```
Phase 1: Foundation (Week 1-2)
    |
    v
Phase 2: Core Agents (Week 3-4)
    |
    v
Phase 3: Business Logic (Week 5-6)
    |
    v
Phase 4: Integration & Testing (Week 7-8)
```

### 4.2 Phase 1: Foundation Setup

**Goal**: Set up OpenAgent network and create base infrastructure

**Tasks**:

1. **T1.1: Network Configuration**
   ```yaml
   # network.yaml
   network:
     name: ToWowNegotiation
     mode: centralized
     transports:
       - type: http
         config:
           port: 8700
           serve_studio: true
       - type: grpc
         config:
           port: 8600
     mods:
       - name: openagents.mods.workspace.messaging
         enabled: true
       - name: openagents.mods.coordination.task_delegation
         enabled: true
   ```

2. **T1.2: Base Agent Wrapper**
   ```python
   # towow/agents/base.py
   from openagents.agents.worker_agent import WorkerAgent, on_event

   class TowowWorkerAgent(WorkerAgent):
       """ToWow-specific WorkerAgent base class."""

       def __init__(self, db=None, llm_service=None, **kwargs):
           super().__init__(**kwargs)
           self.db = db
           self.llm = llm_service

       # Backward compatibility methods
       async def send_to_agent(self, agent_id: str, data: dict):
           return await self.workspace().agent(agent_id).send(data)
   ```

3. **T1.3: Custom Mod for ToWow Events**
   ```python
   # towow/mods/towow_events/mod.py
   from openagents.core.base_mod import BaseMod

   class TowowEventsMod(BaseMod):
       """Custom mod for ToWow-specific events."""

       async def initialize(self):
           # Register custom event types
           self.register_event_type("towow.demand.*")
           self.register_event_type("towow.proposal.*")
           self.register_event_type("towow.negotiation.*")
   ```

**Deliverables**:
- [ ] `network.yaml` configuration
- [ ] `TowowWorkerAgent` base class
- [ ] Custom events mod skeleton

### 4.3 Phase 2: Core Agent Migration

**Goal**: Migrate Coordinator, ChannelAdmin, UserAgent

**Tasks**:

1. **T2.1: CoordinatorAgent Migration**

   **Current** (`towow/openagents/agents/coordinator.py`):
   - 657 lines
   - Handles `new_demand`, `subnet_demand`, `channel_completed`
   - Uses `_smart_filter()` with LLM

   **Target**:
   ```python
   class TowowCoordinatorAgent(TowowWorkerAgent):
       default_agent_id = "coordinator"

       @on_event("towow.demand.new")
       async def handle_new_demand(self, context: EventContext):
           # Migrate _handle_new_demand logic
           pass

       @on_event("towow.subnet.request")
       async def handle_subnet_demand(self, context: EventContext):
           # Migrate _handle_subnet_demand logic
           pass
   ```

2. **T2.2: ChannelAdminAgent Migration**

   **Current** (`towow/openagents/agents/channel_admin.py`):
   - 2200 lines
   - Complex state machine (`ChannelStatus`)
   - Manages negotiation lifecycle

   **Target**:
   ```python
   class TowowChannelAdminAgent(TowowWorkerAgent):
       default_agent_id = "channel_admin"

       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.channels: Dict[str, ChannelState] = {}
           # Use shared cache mod for persistence
           self.cache_adapter = SharedCacheAdapter()

       @on_event("towow.channel.create")
       async def handle_create_channel(self, context: EventContext):
           # Migrate start_managing logic
           pass

       @on_event("towow.response.received")
       async def handle_response(self, context: EventContext):
           # Migrate response handling logic
           pass
   ```

3. **T2.3: UserAgent Migration**

   **Current** (`towow/openagents/agents/user_agent.py`):
   - 1099 lines
   - Handles proposals, bargaining, withdrawal

   **Target**:
   ```python
   class TowowUserAgent(TowowWorkerAgent):

       def __init__(self, user_id: str, profile: dict, **kwargs):
           agent_id = f"user_agent_{user_id}"
           super().__init__(agent_id=agent_id, **kwargs)
           self.user_id = user_id
           self.profile = profile

       @on_event("towow.invite.received")
       async def handle_invite(self, context: EventContext):
           pass

       @on_event("towow.proposal.received")
       async def handle_proposal(self, context: EventContext):
           pass
   ```

**Deliverables**:
- [ ] Migrated `TowowCoordinatorAgent`
- [ ] Migrated `TowowChannelAdminAgent`
- [ ] Migrated `TowowUserAgent`

### 4.4 Phase 3: Business Logic Migration

**Goal**: Migrate negotiation state machine and gap identification

**Tasks**:

1. **T3.1: State Machine Mod**
   ```python
   # towow/mods/negotiation/state_machine.py

   class NegotiationStateMachine:
       """Manages channel state transitions."""

       TRANSITIONS = {
           ChannelStatus.CREATED: [ChannelStatus.BROADCASTING],
           ChannelStatus.BROADCASTING: [ChannelStatus.COLLECTING],
           ChannelStatus.COLLECTING: [ChannelStatus.AGGREGATING],
           ChannelStatus.AGGREGATING: [ChannelStatus.PROPOSAL_SENT],
           ChannelStatus.PROPOSAL_SENT: [ChannelStatus.NEGOTIATING],
           ChannelStatus.NEGOTIATING: [
               ChannelStatus.FINALIZED,
               ChannelStatus.FAILED
           ],
       }
   ```

2. **T3.2: Gap Identification Service**
   ```python
   # towow/services/gap_identification.py
   # Keep existing implementation, adapt interface for OpenAgent
   ```

3. **T3.3: Subnet Manager Adaptation**
   ```python
   # Use TaskDelegationAdapter for subnet spawning
   class SubnetManager:
       def __init__(self, delegation_adapter: TaskDelegationAdapter):
           self.delegation = delegation_adapter

       async def spawn_subnet(self, gap: Gap, parent_channel_id: str):
           # Use task delegation for subnet coordination
           await self.delegation.delegate_task(
               assignee_id="coordinator",
               description=f"Handle gap: {gap.description}",
               payload={"gap": gap, "parent": parent_channel_id}
           )
   ```

**Deliverables**:
- [ ] Negotiation state machine mod
- [ ] Adapted gap identification service
- [ ] Subnet management via task delegation

### 4.5 Phase 4: Integration & Testing

**Goal**: Full system integration and testing

**Tasks**:

1. **T4.1: API Layer Integration**
   ```python
   # towow/api/main.py

   @app.post("/api/demand")
   async def submit_demand(request: DemandRequest):
       # Send event to coordinator via network
       await network_client.send_event(
           event_type="towow.demand.new",
           payload=request.dict()
       )
   ```

2. **T4.2: Event Bridge** (if needed for backward compatibility)
   ```python
   # Bridge ToWow event bus to OpenAgent events
   class EventBridge:
       def __init__(self, old_bus, openagent_client):
           self.old_bus = old_bus
           self.client = openagent_client

       async def forward(self, event):
           # Convert and forward events
           pass
   ```

3. **T4.3: End-to-End Testing**
   - Migrate existing tests
   - Add integration tests for OpenAgent network
   - Performance benchmarks

**Deliverables**:
- [ ] Updated API layer
- [ ] Event bridge (if needed)
- [ ] Test suite migration
- [ ] Performance benchmarks

### 4.6 File-Level Migration Map

| Current File | Target File | Status |
|--------------|-------------|--------|
| `towow/openagents/agents/base.py` | `towow/agents/base.py` (extends WorkerAgent) | TODO |
| `towow/openagents/agents/coordinator.py` | `towow/agents/coordinator.py` | TODO |
| `towow/openagents/agents/channel_admin.py` | `towow/agents/channel_admin.py` | TODO |
| `towow/openagents/agents/user_agent.py` | `towow/agents/user_agent.py` | TODO |
| `towow/openagents/agents/router.py` | REMOVE (use built-in) | TODO |
| `towow/openagents/agents/factory.py` | `towow/agents/factory.py` (simplified) | TODO |
| N/A | `network.yaml` (new) | TODO |
| N/A | `towow/mods/negotiation/` (new) | TODO |

---

## 5. Recommendations

### 5.1 Immediate Actions

1. **Create feature branch**: `feature/openagent-migration`
2. **Set up OpenAgent network locally** for testing
3. **Create `TowowWorkerAgent` base class** as compatibility layer

### 5.2 Key Decisions Needed

1. **State Persistence Strategy**
   - Option A: Use OpenAgent's shared cache mod
   - Option B: Keep existing database approach
   - **Recommendation**: Option A for simpler architecture

2. **Event System**
   - Option A: Full migration to OpenAgent events
   - Option B: Bridge layer for gradual migration
   - **Recommendation**: Option A for clean architecture

3. **LLM Integration**
   - Option A: Use OpenAgent's LLM providers
   - Option B: Keep custom LLMService
   - **Recommendation**: Option B initially, migrate later

### 5.3 Success Criteria

- [ ] All existing tests pass
- [ ] Negotiation flow works end-to-end
- [ ] No regression in API response times
- [ ] Studio can monitor agents
- [ ] Code reduction > 20%

---

## Appendix A: Code References

### Current Implementation Files

| File | Lines | Purpose |
|------|-------|---------|
| `/towow/openagents/agents/base.py` | 280 | Base agent class |
| `/towow/openagents/agents/coordinator.py` | 657 | Demand coordination |
| `/towow/openagents/agents/channel_admin.py` | 2200 | Negotiation management |
| `/towow/openagents/agents/user_agent.py` | 1099 | User digital avatar |
| `/towow/openagents/agents/router.py` | 225 | Message routing |
| `/towow/openagents/agents/factory.py` | ~200 | Agent factory |
| **Total** | **~4661** | |

### OpenAgent Reference Files

| File | Purpose |
|------|---------|
| `/openagents/src/openagents/agents/worker_agent.py` | Base WorkerAgent class |
| `/openagents/src/openagents/core/workspace.py` | Workspace API |
| `/openagents/src/openagents/mods/coordination/task_delegation/` | Task delegation mod |
| `/openagents/demos/08_alternative_service_project/` | Coordinator pattern example |

---

## Appendix B: OpenAgent Event Patterns

```python
# Built-in events
"agent.message"                        # Direct agent messages
"thread.channel_message.notification"  # Channel messages
"thread.reply.notification"            # Reply messages
"thread.reaction.notification"         # Reactions
"task.notification.completed"          # Task completion
"project.notification.started"         # Project start

# Custom ToWow events (to register)
"towow.demand.new"                     # New demand submitted
"towow.demand.understood"              # Demand analyzed
"towow.filter.completed"               # Filtering done
"towow.channel.create"                 # Create negotiation channel
"towow.invite.sent"                    # Invite sent to agent
"towow.response.received"              # Agent response
"towow.proposal.generated"             # Proposal ready
"towow.proposal.distributed"           # Proposal sent
"towow.feedback.received"              # Feedback from agent
"towow.gap.identified"                 # Gap found
"towow.subnet.request"                 # Subnet needed
"towow.negotiation.finalized"          # Negotiation complete
"towow.negotiation.failed"             # Negotiation failed
```

---

## 6. Gap Analysis: Migration Strategy Details (G-01 to G-04)

### G-01: Circuit Breaker Migration Strategy

#### Current Implementation Analysis

ToWow's circuit breaker implementation is located in `/towow/services/llm.py` and provides:

**CircuitState Enum**:
```python
class CircuitState(Enum):
    CLOSED = "closed"      # Normal state, allow requests
    OPEN = "open"          # Tripped state, reject requests
    HALF_OPEN = "half_open"  # Testing state, allow limited requests
```

**CircuitBreaker Configuration**:
| Parameter | Default | Purpose |
|-----------|---------|---------|
| `failure_threshold` | 3 | Consecutive failures to trip |
| `recovery_timeout` | 30.0s | Time before testing recovery |
| `half_open_max_calls` | 1 | Calls allowed in half-open state |

**LLMServiceWithFallback Features**:
- Timeout control (default 10s)
- Circuit breaker integration
- Pre-defined fallback responses by `fallback_key`
- Statistics tracking (total/success/failure/timeout/circuit_open counts)

#### Migration Strategy

**Option A: Adapter Pattern (Recommended)**
```python
# towow/adapters/circuit_breaker_adapter.py

from openagents.core.base_adapter import BaseAdapter
from services.llm import CircuitBreaker, CircuitState

class CircuitBreakerAdapter(BaseAdapter):
    """Adapt ToWow CircuitBreaker for OpenAgent framework."""

    def __init__(self, **config):
        super().__init__()
        self.breaker = CircuitBreaker(
            failure_threshold=config.get("failure_threshold", 3),
            recovery_timeout=config.get("recovery_timeout", 30.0),
            half_open_max_calls=config.get("half_open_max_calls", 1)
        )

    async def wrap_call(self, coro, fallback_key: str = None):
        """Wrap async call with circuit breaker protection."""
        if not self.breaker.can_execute():
            return self._get_fallback(fallback_key)

        try:
            result = await coro
            self.breaker.record_success()
            return result
        except Exception as e:
            self.breaker.record_failure()
            return self._get_fallback(fallback_key)
```

**Option B: OpenAgent Mod**
```python
# towow/mods/resilience/circuit_breaker_mod.py

class CircuitBreakerMod(BaseMod):
    """Circuit breaker as OpenAgent mod."""

    async def on_llm_call_start(self, context):
        # Check circuit state before LLM call
        pass

    async def on_llm_call_complete(self, context, success: bool):
        # Record result for circuit state update
        pass
```

**Migration Steps**:
1. Keep existing `CircuitBreaker` class unchanged
2. Create `CircuitBreakerAdapter` wrapping the existing implementation
3. Inject adapter into OpenAgent agents via `TowowWorkerAgent` base class
4. Register circuit breaker events for monitoring via OpenAgent event system

**Fallback Response Migration**:
- Keep `FALLBACK_RESPONSES` dictionary in services/llm.py
- Access via adapter pattern: `self.circuit_adapter.get_fallback(key)`

---

### G-02: State Machine and Event Flow Integration

#### Current ChannelStatus State Machine

```
ChannelStatus Enum (8 states):

CREATED ──────> BROADCASTING ──────> COLLECTING ──────> AGGREGATING
    │                                     │                  │
    │                                     │                  v
    │                                     │          PROPOSAL_SENT
    │                                     │                  │
    │                                     │                  v
    │                                     │           NEGOTIATING
    │                                     │              /    \
    v                                     v             v      v
FAILED <──────────────────────────────────────────  FINALIZED  FAILED
```

**State Transition Table**:

| From State | To State | Trigger | Event Published |
|------------|----------|---------|-----------------|
| CREATED | BROADCASTING | `start_managing()` called | `towow.channel.created` |
| BROADCASTING | COLLECTING | Demand broadcast complete | `towow.demand.broadcast` |
| COLLECTING | AGGREGATING | All responses received or timeout | - |
| AGGREGATING | PROPOSAL_SENT | Proposal generated | `towow.aggregation.started` |
| PROPOSAL_SENT | NEGOTIATING | Proposal distributed | `towow.proposal.distributed` |
| NEGOTIATING | FINALIZED | >= 80% accept OR all accept | `towow.proposal.finalized` |
| NEGOTIATING | FAILED | > 50% reject OR max rounds | `towow.negotiation.failed` |
| NEGOTIATING | NEGOTIATING | Has negotiates, round < max | `towow.negotiation.round_started` |
| * | FAILED | No participants | `towow.negotiation.failed` |

#### OpenAgent Event Mapping

**State Transition to Event Bridge**:
```python
# towow/mods/negotiation/state_event_bridge.py

class StateEventBridge:
    """Maps ChannelStatus transitions to OpenAgent events."""

    TRANSITION_EVENTS = {
        (ChannelStatus.CREATED, ChannelStatus.BROADCASTING): "towow.channel.broadcasting",
        (ChannelStatus.BROADCASTING, ChannelStatus.COLLECTING): "towow.channel.collecting",
        (ChannelStatus.COLLECTING, ChannelStatus.AGGREGATING): "towow.channel.aggregating",
        (ChannelStatus.AGGREGATING, ChannelStatus.PROPOSAL_SENT): "towow.proposal.sent",
        (ChannelStatus.PROPOSAL_SENT, ChannelStatus.NEGOTIATING): "towow.negotiation.started",
        (ChannelStatus.NEGOTIATING, ChannelStatus.FINALIZED): "towow.negotiation.finalized",
        (ChannelStatus.NEGOTIATING, ChannelStatus.FAILED): "towow.negotiation.failed",
    }

    async def on_state_change(self, channel_id: str, from_state: ChannelStatus, to_state: ChannelStatus, context: dict):
        """Emit OpenAgent event on state transition."""
        event_type = self.TRANSITION_EVENTS.get((from_state, to_state))
        if event_type:
            await self.client.publish_event(
                event_type=event_type,
                payload={
                    "channel_id": channel_id,
                    "from_state": from_state.value,
                    "to_state": to_state.value,
                    **context
                }
            )
```

**Integration with ChannelAdminAgent**:
```python
class TowowChannelAdminAgent(TowowWorkerAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state_bridge = StateEventBridge()

    async def _change_state(self, state: ChannelState, new_status: ChannelStatus, context: dict = None):
        old_status = state.status
        state.status = new_status
        await self.state_bridge.on_state_change(
            channel_id=state.channel_id,
            from_state=old_status,
            to_state=new_status,
            context=context or {}
        )
```

---

### G-03: SSE Event Bridging

#### Current SSE Architecture

ToWow uses FastAPI + Server-Sent Events for real-time frontend updates:

**Components**:
1. `EventRecorder` (`/towow/events/recorder.py`) - Stores events in memory, supports pub/sub
2. `EventBus` (`/towow/events/bus.py`) - Internal event routing with wildcard subscriptions
3. SSE Router (`/towow/api/routers/events.py`) - HTTP endpoint for event streaming

**Event Flow**:
```
Agent Action
    │
    v
EventBus.publish()  ──> EventRecorder.record()
                              │
                              v
                        SSE Generator
                              │
                              v
                        Frontend (EventSource)
```

**SSE Event Format**:
```json
{
  "event_id": "evt-abc123",
  "event_type": "towow.proposal.finalized",
  "timestamp": "2026-01-22T10:30:00Z",
  "payload": {
    "channel_id": "collab-xyz",
    "demand_id": "d-12345678",
    ...
  }
}
```

#### OpenAgent Event Bridge Design

**Bridge Architecture**:
```
OpenAgent Event System
        │
        v
┌───────────────────┐
│  TowowEventBridge │
│  - Subscribe to   │
│    OpenAgent      │
│  - Convert format │
│  - Forward to SSE │
└───────────────────┘
        │
        v
EventRecorder (existing)
        │
        v
SSE Generator (existing)
        │
        v
Frontend (unchanged)
```

**Implementation**:
```python
# towow/bridges/sse_event_bridge.py

from typing import Dict, Any
from events.recorder import event_recorder
from openagents.agents.worker_agent import on_event

class SSEEventBridge:
    """Bridges OpenAgent events to ToWow SSE system."""

    # OpenAgent event patterns to SSE event types
    EVENT_MAPPING = {
        "towow.demand.*": True,
        "towow.channel.*": True,
        "towow.proposal.*": True,
        "towow.negotiation.*": True,
        "towow.offer.*": True,
        "towow.feedback.*": True,
        "towow.gap.*": True,
        "towow.subnet.*": True,
        "towow.agent.*": True,
    }

    def __init__(self, openagent_client):
        self.client = openagent_client
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        """Subscribe to all ToWow event patterns."""
        for pattern in self.EVENT_MAPPING.keys():
            self.client.subscribe(pattern, self._handle_event)

    async def _handle_event(self, event):
        """Convert and forward OpenAgent event to SSE."""
        sse_event = self._convert_to_sse_format(event)
        await event_recorder.record(sse_event)

    def _convert_to_sse_format(self, openagent_event) -> Dict[str, Any]:
        """Convert OpenAgent event to ToWow SSE format."""
        return {
            "event_id": openagent_event.id or f"evt-{uuid4().hex[:8]}",
            "event_type": openagent_event.type,
            "timestamp": openagent_event.timestamp or datetime.utcnow().isoformat(),
            "payload": openagent_event.payload or {}
        }
```

**Integration in Main App**:
```python
# towow/api/main.py

async def lifespan(app: FastAPI):
    # Startup
    openagent_client = await connect_to_network()
    sse_bridge = SSEEventBridge(openagent_client)
    app.state.sse_bridge = sse_bridge

    yield

    # Shutdown
    await openagent_client.disconnect()
```

**Zero Frontend Changes**: The SSE endpoint (`/api/v1/events/negotiations/{demand_id}/stream`) remains unchanged. Frontend continues to receive events in the same format.

---

### G-04: Subnet Recursive Implementation

#### Current Subnet Architecture

**SubnetManager** (`/towow/services/subnet_manager.py`) handles recursive sub-negotiations:

**Data Flow**:
```
Parent Channel (FINALIZED)
         │
         v
   Gap Identification
         │ (identifies missing capabilities)
         v
   SubnetManager.process_gaps()
         │
         v
   Create Sub-Demand
         │
         v
   Coordinator handles "subnet_demand"
         │
         v
   Create Child Channel
         │
         v
   Child Negotiation (recursive)
         │
         v
   SubnetManager.integrate_results()
         │
         v
   Updated Parent Proposal
```

**Key Data Structures**:

```python
@dataclass
class SubnetInfo:
    subnet_id: str
    parent_channel_id: str      # Links to parent
    parent_demand_id: str
    gap_id: str                 # Which gap this solves
    sub_demand: Dict[str, Any]
    recursion_depth: int        # Depth limit control
    status: SubnetStatus
    channel_id: Optional[str]   # Child channel ID when created
    result: Optional[Dict]
    timeout_seconds: int = 180
```

**Parent-Child Relationship**:
```
Parent Channel (ch-parent-001)
    │
    ├── Subnet 1 (subnet-abc123)
    │   └── Child Channel (ch-child-001)
    │
    └── Subnet 2 (subnet-def456)
        └── Child Channel (ch-child-002)
```

**Configuration**:
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `MAX_RECURSION_DEPTH` | 1 | MVP limit to 1 level |
| `MAX_SUBNETS_PER_LAYER` | 3 | Prevent explosion |
| `DEFAULT_TIMEOUT` | 180s | Per-subnet timeout |

#### OpenAgent Task Delegation Mapping

**Current Flow vs Task Delegation**:

| Current ToWow | OpenAgent Equivalent |
|---------------|---------------------|
| `SubnetManager.process_gaps()` | `TaskDelegationAdapter.delegate_task()` |
| `SubnetInfo` | `TaskContext` with metadata |
| Channel completion callback | `@on_event("task.notification.completed")` |
| Timeout monitoring | Built-in task timeout |

**Implementation Strategy**:

```python
# towow/services/subnet_manager_openagent.py

class SubnetManagerOpenAgent:
    """SubnetManager adapted for OpenAgent task delegation."""

    def __init__(self, delegation_adapter: TaskDelegationAdapter):
        self.delegation = delegation_adapter
        self._parent_children: Dict[str, List[str]] = {}

    async def process_gaps(
        self,
        analysis_result: GapAnalysisResult,
        recursion_depth: int = 0
    ) -> List[str]:
        """Process gaps using task delegation."""

        if recursion_depth >= self.max_depth:
            return []

        created_task_ids = []
        subnet_triggers = analysis_result.get_subnet_triggers()

        for gap in subnet_triggers[:self.max_subnets]:
            # Create task for subnet handling
            task_id = await self.delegation.delegate_task(
                assignee_id="coordinator",
                description=f"Handle gap: {gap.description}",
                payload={
                    "type": "subnet_demand",
                    "gap": gap.to_dict(),
                    "parent_channel_id": analysis_result.channel_id,
                    "parent_demand_id": analysis_result.demand_id,
                    "recursion_depth": recursion_depth + 1,
                    "sub_demand": {
                        "surface_demand": gap.suggested_sub_demand,
                        "deep_understanding": {
                            "type": "sub_demand",
                            "motivation": f"Fill gap: {gap.description}",
                            "parent_gap_type": gap.gap_type.value
                        }
                    }
                },
                timeout=180  # Built-in timeout
            )

            # Track parent-child relationship
            self._track_relationship(analysis_result.channel_id, task_id)
            created_task_ids.append(task_id)

        return created_task_ids

    def _track_relationship(self, parent_id: str, task_id: str):
        if parent_id not in self._parent_children:
            self._parent_children[parent_id] = []
        self._parent_children[parent_id].append(task_id)
```

**Handling Completion**:
```python
class TowowCoordinatorAgent(TowowWorkerAgent):

    @on_event("task.notification.completed")
    async def handle_task_completed(self, context: EventContext):
        """Handle subnet task completion."""
        task = context.event.payload.get("task", {})
        task_payload = task.get("payload", {})

        if task_payload.get("type") == "subnet_demand":
            await self.subnet_manager.handle_subnet_completed(
                task_id=task.get("id"),
                success=task.get("status") == "completed",
                result=task.get("result")
            )
```

**Result Integration**:
```python
async def integrate_subnet_results(
    self,
    parent_channel_id: str,
    parent_proposal: Dict[str, Any]
) -> Dict[str, Any]:
    """Integrate completed subnet results into parent proposal."""

    task_ids = self._parent_children.get(parent_channel_id, [])
    successful_results = []

    for task_id in task_ids:
        task_result = await self.delegation.get_task_result(task_id)
        if task_result and task_result.get("success"):
            successful_results.append(task_result)

    # Merge assignments from successful subnets
    integrated = dict(parent_proposal)
    for result in successful_results:
        sub_assignments = result.get("proposal", {}).get("assignments", [])
        for assignment in sub_assignments:
            assignment["source"] = "subnet"
            assignment["task_id"] = result.get("task_id")
        integrated.setdefault("assignments", []).extend(sub_assignments)

    integrated["subnet_integration"] = {
        "total_tasks": len(task_ids),
        "successful": len(successful_results),
        "failed": len(task_ids) - len(successful_results)
    }

    return integrated
```

---

## Appendix C: Migration Checklist

### Pre-Migration Verification
- [ ] OpenAgent 0.8.x installed and tested
- [ ] Network configuration validated
- [ ] All existing tests passing

### G-01 Circuit Breaker
- [ ] CircuitBreakerAdapter implemented
- [ ] Fallback responses accessible
- [ ] Statistics tracking working
- [ ] Unit tests passing

### G-02 State Machine
- [ ] StateEventBridge implemented
- [ ] All 8 states covered
- [ ] Transition events emitting
- [ ] Integration tests passing

### G-03 SSE Bridge
- [ ] SSEEventBridge implemented
- [ ] Event format compatible
- [ ] Frontend unchanged
- [ ] E2E SSE flow tested

### G-04 Subnet
- [ ] Task delegation integration complete
- [ ] Parent-child tracking working
- [ ] Result integration tested
- [ ] Recursion depth enforced

---

**Document End**
