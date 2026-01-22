# TASK: OpenAgent Migration Tasks

> **Document Version**: v1.0
> **Created**: 2026-01-22
> **Status**: DRAFT
> **Related**: MIGRATION-openagent-analysis.md

---

## Overview

This document breaks down the OpenAgent migration into executable tasks with clear acceptance criteria and dependencies.

**Total Phases**: 5 (Phase 0-4)
**Estimated Duration**: 8-10 weeks

---

## Phase 0: Compatibility Layer Verification (NEW - Week 0-1)

### Purpose

Before full migration, validate that OpenAgent framework can integrate with ToWow without breaking existing functionality. This phase creates a minimal compatibility layer and runs verification tests.

---

### T0.1: OpenAgent Environment Setup

**Priority**: P0 (Blocker)
**Estimated Effort**: 2h
**Dependencies**: None

**Description**:
Set up OpenAgent development environment in the feature branch.

**Tasks**:
- [ ] Install OpenAgent 0.8.x (`pip install openagents>=0.8.0`)
- [ ] Verify Python version compatibility (3.10+)
- [ ] Create minimal `network.yaml` for local testing
- [ ] Start OpenAgent network and verify Studio UI accessible

**Acceptance Criteria**:
1. `python -c "import openagents; print(openagents.__version__)"` returns >= 0.8.0
2. OpenAgent network starts without errors
3. Studio UI accessible at http://localhost:8700

**Verification Command**:
```bash
cd towow && python -c "from openagents.agents.worker_agent import WorkerAgent; print('OK')"
```

---

### T0.2: Minimal WorkerAgent Wrapper

**Priority**: P0 (Blocker)
**Estimated Effort**: 4h
**Dependencies**: T0.1

**Description**:
Create a minimal `TowowWorkerAgent` base class that extends OpenAgent's `WorkerAgent` while maintaining backward compatibility with existing ToWow agent interfaces.

**Tasks**:
- [ ] Create `towow/agents/compat/__init__.py`
- [ ] Create `towow/agents/compat/base.py` with `TowowWorkerAgent`
- [ ] Implement `send_to_agent()` wrapper method
- [ ] Implement `post_to_channel()` wrapper method
- [ ] Implement `_publish_event()` wrapper method

**Implementation Skeleton**:
```python
# towow/agents/compat/base.py

from openagents.agents.worker_agent import WorkerAgent, on_event
from typing import Dict, Any, Optional

class TowowWorkerAgent(WorkerAgent):
    """Compatibility layer: ToWow agent on OpenAgent framework."""

    def __init__(self, db=None, llm_service=None, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.llm = llm_service
        self._logger = logging.getLogger(self.__class__.__name__)

    # Backward compatibility: ToWow send_to_agent -> OpenAgent workspace().agent().send()
    async def send_to_agent(self, agent_id: str, data: Dict[str, Any]):
        return await self.workspace().agent(agent_id).send(data)

    # Backward compatibility: ToWow post_to_channel -> OpenAgent workspace().channel().post()
    async def post_to_channel(self, channel: str, data: Dict[str, Any]):
        return await self.workspace().channel(channel).post(data)

    # Backward compatibility: ToWow _publish_event -> OpenAgent client event
    async def _publish_event(self, event_type: str, payload: Dict[str, Any]):
        # Bridge to existing EventBus for SSE
        from events.bus import event_bus
        await event_bus.publish({
            "event_type": event_type,
            "payload": payload
        })
```

**Acceptance Criteria**:
1. `TowowWorkerAgent` can be imported without errors
2. `send_to_agent()` method signature matches existing `TowowBaseAgent`
3. `post_to_channel()` method signature matches existing interface
4. Unit test passes: `test_compat_agent_methods()`

---

### T0.3: Compatibility Integration Test

**Priority**: P0 (Blocker)
**Estimated Effort**: 4h
**Dependencies**: T0.2

**Description**:
Create integration test that validates the compatibility layer works with existing ToWow components.

**Tasks**:
- [ ] Create `towow/tests/compat/test_worker_agent.py`
- [ ] Test agent initialization with db/llm injection
- [ ] Test `send_to_agent()` message delivery
- [ ] Test `_publish_event()` event bus integration
- [ ] Test `@on_event()` decorator handling

**Test Cases**:
```python
# towow/tests/compat/test_worker_agent.py

class TestTowowWorkerAgentCompat:

    async def test_initialization_with_dependencies(self):
        """Agent should accept db and llm_service in constructor."""
        agent = TowowWorkerAgent(
            agent_id="test_agent",
            db=mock_db,
            llm_service=mock_llm
        )
        assert agent.db == mock_db
        assert agent.llm == mock_llm

    async def test_send_to_agent_compatibility(self):
        """send_to_agent should work like existing interface."""
        # ...

    async def test_event_publishing_bridges_to_event_bus(self):
        """_publish_event should publish to ToWow EventBus."""
        # ...
```

**Acceptance Criteria**:
1. All 4 test cases pass
2. No changes required to existing agent implementations
3. Event bus receives events from `_publish_event()`

---

### T0.4: Dual-Mode Agent Factory

**Priority**: P1
**Estimated Effort**: 3h
**Dependencies**: T0.2

**Description**:
Update `AgentFactory` to support both legacy `TowowBaseAgent` and new `TowowWorkerAgent` modes via configuration flag.

**Tasks**:
- [ ] Add `USE_OPENAGENT_MODE` environment variable
- [ ] Update `AgentFactory.get_coordinator()` to check mode
- [ ] Update `AgentFactory.get_channel_admin()` to check mode
- [ ] Update `AgentFactory.get_user_agent()` to check mode
- [ ] Add mode switching in `api/main.py`

**Implementation**:
```python
# towow/openagents/agents/factory.py

import os

USE_OPENAGENT_MODE = os.getenv("USE_OPENAGENT_MODE", "false").lower() == "true"

class AgentFactory:
    @classmethod
    def get_coordinator(cls, **kwargs):
        if USE_OPENAGENT_MODE:
            from agents.compat.coordinator import TowowCoordinatorAgentCompat
            return TowowCoordinatorAgentCompat(**kwargs)
        else:
            from openagents.agents.coordinator import CoordinatorAgent
            return CoordinatorAgent(**kwargs)
```

**Acceptance Criteria**:
1. `USE_OPENAGENT_MODE=false` returns existing agents (default)
2. `USE_OPENAGENT_MODE=true` returns compat-layer agents
3. Existing tests pass with both modes
4. No runtime errors in either mode

---

## Phase 1: Foundation Setup (Week 1-2)

### T1.1: Network Configuration

**Priority**: P0 (Blocker)
**Estimated Effort**: 2h
**Dependencies**: T0.1

**Description**:
Create OpenAgent network configuration file with ToWow-specific settings.

**Tasks**:
- [ ] Create `network.yaml` in project root
- [ ] Configure HTTP transport (port 8700)
- [ ] Configure gRPC transport (port 8600)
- [ ] Enable Studio for debugging
- [ ] Configure messaging mod
- [ ] Configure task_delegation mod

**Deliverable**:
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
      config:
        max_message_size: 65536
    - name: openagents.mods.coordination.task_delegation
      enabled: true
      config:
        default_timeout: 300

  agents:
    coordinator:
      class: towow.agents.coordinator.TowowCoordinatorAgent
      auto_start: true
    channel_admin:
      class: towow.agents.channel_admin.TowowChannelAdminAgent
      auto_start: true
```

**Acceptance Criteria**:
1. Network starts with `openagents network start`
2. Studio accessible and shows configured agents
3. All mods load without errors

---

### T1.2: Custom ToWow Events Mod

**Priority**: P1
**Estimated Effort**: 4h
**Dependencies**: T1.1

**Description**:
Create custom OpenAgent mod to register ToWow-specific event types.

**Tasks**:
- [ ] Create `towow/mods/towow_events/__init__.py`
- [ ] Create `towow/mods/towow_events/mod.py`
- [ ] Register all `towow.*` event patterns
- [ ] Add event validation hooks
- [ ] Write unit tests

**Deliverable**:
```python
# towow/mods/towow_events/mod.py

from openagents.core.base_mod import BaseMod

class TowowEventsMod(BaseMod):
    """Custom mod for ToWow-specific events."""

    EVENT_PATTERNS = [
        "towow.demand.*",
        "towow.channel.*",
        "towow.proposal.*",
        "towow.negotiation.*",
        "towow.offer.*",
        "towow.feedback.*",
        "towow.gap.*",
        "towow.subnet.*",
        "towow.agent.*",
    ]

    async def initialize(self):
        for pattern in self.EVENT_PATTERNS:
            self.register_event_type(pattern)
        self.logger.info(f"Registered {len(self.EVENT_PATTERNS)} ToWow event patterns")
```

**Acceptance Criteria**:
1. Mod loads without errors
2. All 9 event patterns registered
3. Events matching patterns are routed correctly

---

### T1.3: CircuitBreakerAdapter Implementation (G-01)

**Priority**: P0 (Blocker)
**Estimated Effort**: 6h
**Dependencies**: T0.2

**Description**:
Implement adapter to integrate existing CircuitBreaker with OpenAgent framework.

**Tasks**:
- [ ] Create `towow/adapters/__init__.py`
- [ ] Create `towow/adapters/circuit_breaker_adapter.py`
- [ ] Wrap existing `CircuitBreaker` class
- [ ] Implement `wrap_call()` async method
- [ ] Implement `get_fallback()` method
- [ ] Add statistics export
- [ ] Write unit tests

**Deliverable**:
```python
# towow/adapters/circuit_breaker_adapter.py

from services.llm import CircuitBreaker, CircuitState, FALLBACK_RESPONSES

class CircuitBreakerAdapter:
    """Adapter for CircuitBreaker integration with OpenAgent."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        timeout: float = 10.0
    ):
        self.breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        self.timeout = timeout
        self.stats = {...}

    async def wrap_call(self, coro, fallback_key: str = None):
        """Execute coroutine with circuit breaker protection."""
        if not self.breaker.can_execute():
            self.stats["circuit_open_count"] += 1
            return self._get_fallback(fallback_key)

        try:
            result = await asyncio.wait_for(coro, timeout=self.timeout)
            self.breaker.record_success()
            self.stats["success_count"] += 1
            return result
        except asyncio.TimeoutError:
            self.breaker.record_failure()
            self.stats["timeout_count"] += 1
            return self._get_fallback(fallback_key)
        except Exception as e:
            self.breaker.record_failure()
            self.stats["failure_count"] += 1
            return self._get_fallback(fallback_key)

    def _get_fallback(self, key: str) -> str:
        return FALLBACK_RESPONSES.get(key, FALLBACK_RESPONSES["default"])
```

**Acceptance Criteria**:
1. Adapter wraps existing CircuitBreaker without modification
2. `wrap_call()` handles timeout correctly
3. Fallback responses returned when circuit is open
4. Statistics tracking works
5. All unit tests pass

---

## Phase 2: Core Agent Migration (Week 3-4)

### T2.1: CoordinatorAgent Migration

**Priority**: P0 (Blocker)
**Estimated Effort**: 8h
**Dependencies**: T1.1, T1.2, T1.3

**Description**:
Migrate CoordinatorAgent to extend TowowWorkerAgent with OpenAgent event handlers.

**Tasks**:
- [ ] Create `towow/agents/coordinator.py`
- [ ] Extend `TowowWorkerAgent`
- [ ] Replace `on_direct()` with `@on_event()` decorators
- [ ] Migrate `_handle_new_demand()` logic
- [ ] Migrate `_handle_subnet_demand()` logic
- [ ] Migrate `_smart_filter()` with CircuitBreakerAdapter
- [ ] Update agent registration in network.yaml
- [ ] Write integration tests

**Event Handler Mapping**:
| Old Method | New Handler |
|------------|-------------|
| `on_direct(type="new_demand")` | `@on_event("towow.demand.new")` |
| `on_direct(type="subnet_demand")` | `@on_event("towow.subnet.request")` |
| `on_direct(type="channel_completed")` | `@on_event("towow.channel.completed")` |

**Acceptance Criteria**:
1. Agent starts and registers with network
2. Demand submission triggers `handle_new_demand()`
3. Smart filter works with CircuitBreakerAdapter
4. Channel creation flows correctly
5. All existing coordinator tests pass

---

### T2.2: ChannelAdminAgent Migration (with G-02)

**Priority**: P0 (Blocker)
**Estimated Effort**: 12h
**Dependencies**: T2.1

**Description**:
Migrate ChannelAdminAgent with state machine event bridge integration.

**Tasks**:
- [ ] Create `towow/agents/channel_admin.py`
- [ ] Create `towow/mods/negotiation/state_event_bridge.py` (G-02)
- [ ] Extend `TowowWorkerAgent`
- [ ] Migrate `ChannelState` and `ChannelStatus`
- [ ] Implement `_change_state()` with StateEventBridge
- [ ] Replace `on_direct()` with `@on_event()` decorators
- [ ] Migrate all message handlers
- [ ] Update agent registration
- [ ] Write integration tests

**State Event Bridge (G-02)**:
```python
# towow/mods/negotiation/state_event_bridge.py

class StateEventBridge:
    TRANSITION_EVENTS = {
        (ChannelStatus.CREATED, ChannelStatus.BROADCASTING): "towow.channel.broadcasting",
        (ChannelStatus.BROADCASTING, ChannelStatus.COLLECTING): "towow.channel.collecting",
        # ... all 8 state transitions
    }

    async def on_state_change(self, channel_id, from_state, to_state, context):
        event_type = self.TRANSITION_EVENTS.get((from_state, to_state))
        if event_type:
            await self.client.publish_event(event_type, {...})
```

**Acceptance Criteria**:
1. Agent manages channel lifecycle correctly
2. State transitions emit correct events
3. All 8 ChannelStatus states handled
4. Proposal generation/distribution works
5. Negotiation rounds work correctly
6. All existing channel_admin tests pass

---

### T2.3: UserAgent Migration

**Priority**: P0 (Blocker)
**Estimated Effort**: 6h
**Dependencies**: T2.1

**Description**:
Migrate UserAgent to extend TowowWorkerAgent.

**Tasks**:
- [ ] Create `towow/agents/user_agent.py`
- [ ] Extend `TowowWorkerAgent`
- [ ] Migrate profile-based initialization
- [ ] Replace `on_direct()` with `@on_event()` decorators
- [ ] Migrate demand evaluation logic
- [ ] Migrate proposal review logic
- [ ] Migrate feedback generation
- [ ] Update dynamic agent creation
- [ ] Write integration tests

**Event Handler Mapping**:
| Old Method | New Handler |
|------------|-------------|
| `on_direct(type="demand_offer")` | `@on_event("towow.invite.received")` |
| `on_direct(type="proposal_review")` | `@on_event("towow.proposal.received")` |

**Acceptance Criteria**:
1. UserAgent creates with profile correctly
2. Demand invitation handling works
3. LLM-based response generation works
4. Proposal feedback works
5. Withdrawal/bargaining works
6. All existing user_agent tests pass

---

## Phase 3: Business Logic Migration (Week 5-6)

### T3.1: SSE Event Bridge Implementation (G-03)

**Priority**: P0 (Blocker)
**Estimated Effort**: 6h
**Dependencies**: T2.1, T2.2

**Description**:
Implement bridge to forward OpenAgent events to ToWow SSE system.

**Tasks**:
- [ ] Create `towow/bridges/__init__.py`
- [ ] Create `towow/bridges/sse_event_bridge.py`
- [ ] Subscribe to all `towow.*` event patterns
- [ ] Convert OpenAgent events to SSE format
- [ ] Forward to EventRecorder
- [ ] Integrate in FastAPI lifespan
- [ ] Write integration tests
- [ ] Verify frontend receives events unchanged

**Deliverable**:
```python
# towow/bridges/sse_event_bridge.py

class SSEEventBridge:
    EVENT_PATTERNS = ["towow.*"]

    def __init__(self, openagent_client):
        self.client = openagent_client
        self._setup_subscriptions()

    def _setup_subscriptions(self):
        for pattern in self.EVENT_PATTERNS:
            self.client.subscribe(pattern, self._handle_event)

    async def _handle_event(self, event):
        sse_event = {
            "event_id": event.id,
            "event_type": event.type,
            "timestamp": event.timestamp,
            "payload": event.payload
        }
        await event_recorder.record(sse_event)
```

**Acceptance Criteria**:
1. Bridge subscribes to all ToWow events
2. Events converted to correct SSE format
3. Frontend EventSource receives events
4. No changes to frontend code required
5. SSE reconnection still works

---

### T3.2: Subnet Manager Adaptation (G-04)

**Priority**: P1
**Estimated Effort**: 8h
**Dependencies**: T2.1, T2.2

**Description**:
Adapt SubnetManager to use OpenAgent task delegation for recursive sub-negotiations.

**Tasks**:
- [ ] Create `towow/services/subnet_manager_openagent.py`
- [ ] Implement `process_gaps()` using TaskDelegationAdapter
- [ ] Implement parent-child relationship tracking
- [ ] Handle task completion via `@on_event("task.notification.completed")`
- [ ] Implement `integrate_subnet_results()`
- [ ] Respect MAX_RECURSION_DEPTH (1)
- [ ] Respect MAX_SUBNETS_PER_LAYER (3)
- [ ] Write integration tests

**Acceptance Criteria**:
1. Gap identification triggers subnet tasks
2. Recursion depth enforced (max 1)
3. Subnet results integrated into parent proposal
4. Task timeout handled correctly
5. All existing subnet tests pass

---

### T3.3: Gap Identification Service Adaptation

**Priority**: P1
**Estimated Effort**: 4h
**Dependencies**: T2.2

**Description**:
Ensure GapIdentificationService works with OpenAgent event system.

**Tasks**:
- [ ] Review `services/gap_identification.py`
- [ ] Update event publishing to use OpenAgent client
- [ ] Ensure `towow.gap.identified` event emitted
- [ ] Update CircuitBreakerAdapter integration
- [ ] Write integration tests

**Acceptance Criteria**:
1. Gap identification works with LLM
2. Events emitted correctly
3. Fallback responses work when circuit is open

---

## Phase 4: Integration & Testing (Week 7-8)

### T4.1: API Layer Integration

**Priority**: P0 (Blocker)
**Estimated Effort**: 6h
**Dependencies**: T3.1

**Description**:
Update FastAPI endpoints to work with OpenAgent network.

**Tasks**:
- [ ] Update `api/main.py` lifespan for OpenAgent
- [ ] Connect to OpenAgent network on startup
- [ ] Initialize SSEEventBridge
- [ ] Update `POST /api/demand` to send OpenAgent event
- [ ] Verify SSE endpoint still works
- [ ] Update health check endpoint

**Acceptance Criteria**:
1. API starts and connects to OpenAgent network
2. Demand submission works end-to-end
3. SSE events stream correctly
4. Health endpoint shows network status

---

### T4.2: End-to-End Testing

**Priority**: P0 (Blocker)
**Estimated Effort**: 8h
**Dependencies**: T4.1

**Description**:
Create comprehensive E2E test suite for migrated system.

**Tasks**:
- [ ] Create `towow/tests/e2e/test_openagent_integration.py`
- [ ] Test happy path: demand -> proposal -> finalized
- [ ] Test failure path: demand -> no participants -> failed
- [ ] Test negotiation rounds
- [ ] Test gap identification and subnet
- [ ] Test SSE event delivery
- [ ] Test circuit breaker scenarios
- [ ] Performance benchmark comparison

**Test Scenarios**:
1. `test_happy_path_single_round` - Quick consensus
2. `test_multi_round_negotiation` - 3 rounds to consensus
3. `test_negotiation_failure` - Majority reject
4. `test_gap_triggers_subnet` - Subnet created for gap
5. `test_circuit_breaker_fallback` - LLM failure handling
6. `test_sse_event_delivery` - Frontend receives events

**Acceptance Criteria**:
1. All 6 E2E scenarios pass
2. No regression from existing tests
3. Performance within 10% of baseline
4. SSE latency < 500ms

---

### T4.3: Migration Cleanup

**Priority**: P2
**Estimated Effort**: 4h
**Dependencies**: T4.2

**Description**:
Remove legacy code and finalize migration.

**Tasks**:
- [ ] Remove `AgentRouter` (replaced by OpenAgent)
- [ ] Remove `_MockWorkspace` from base.py
- [ ] Update imports throughout codebase
- [ ] Remove `USE_OPENAGENT_MODE` flag (default to OpenAgent)
- [ ] Update documentation
- [ ] Archive legacy files

**Acceptance Criteria**:
1. Legacy code removed
2. All imports updated
3. No dead code
4. Documentation current

---

## Task Dependency Graph

```
Phase 0 (Compatibility)
  T0.1 ─────> T0.2 ─────> T0.3
              │           │
              v           v
              T0.4 ───────┘

Phase 1 (Foundation)
  T0.1 ─────> T1.1 ─────> T1.2
              │
              v
  T0.2 ─────> T1.3

Phase 2 (Core Agents)
  T1.1 + T1.2 + T1.3 ─────> T2.1 ─────> T2.2 ─────> T2.3
                                          │
                                          v
                                   (includes G-02)

Phase 3 (Business Logic)
  T2.1 + T2.2 ─────> T3.1 (G-03)
                       │
                       v
  T2.1 + T2.2 ─────> T3.2 (G-04)
                       │
                       v
  T2.2 ─────────────> T3.3

Phase 4 (Integration)
  T3.1 ─────> T4.1 ─────> T4.2 ─────> T4.3
```

---

## Risk Mitigation

| Risk | Mitigation | Owner |
|------|------------|-------|
| OpenAgent version incompatibility | Pin version in requirements.txt | T0.1 |
| Event format mismatch | SSEEventBridge conversion layer | T3.1 |
| Performance regression | Benchmark in T4.2, optimize if needed | T4.2 |
| Frontend breaking changes | Zero frontend changes via bridge | T3.1 |
| Circuit breaker state loss | Adapter preserves existing behavior | T1.3 |

---

## Success Criteria

### Phase 0 Complete
- [ ] Compatibility layer working
- [ ] Dual-mode factory operational
- [ ] All existing tests pass

### Phase 1 Complete
- [ ] Network configuration working
- [ ] Custom events mod loaded
- [ ] CircuitBreakerAdapter tested

### Phase 2 Complete
- [ ] All 3 agents migrated
- [ ] State machine events emitting
- [ ] Agent-to-agent communication working

### Phase 3 Complete
- [ ] SSE bridge delivering events
- [ ] Subnet manager using task delegation
- [ ] Gap identification integrated

### Phase 4 Complete
- [ ] E2E tests pass
- [ ] Performance benchmarks met
- [ ] Legacy code removed
- [ ] Documentation updated

---

**Document End**
