# Towow SDK Guide

Build Agent-to-Agent (AToA) negotiation applications on top of the Towow engine.

## Quick Start

```bash
pip install towow-sdk                     # core (numpy only)
pip install towow-sdk[claude,embeddings]  # with Claude + embeddings
```

```python
import asyncio
from towow import (
    EngineBuilder, NegotiationSession, DemandSnapshot,
    CenterCoordinatorSkill, DemandFormulationSkill, OfferGenerationSkill,
    LoggingEventPusher,
)
from towow.adapters.claude_adapter import ClaudeAdapter
from towow.infra.llm_client import ClaudePlatformClient

async def main():
    adapter = ClaudeAdapter(api_key="sk-ant-...", agent_profiles={
        "alice": {"name": "Alice", "role": "ML Engineer", "skills": ["Python", "PyTorch"]},
        "bob":   {"name": "Bob",   "role": "Designer",    "skills": ["Figma", "UX"]},
    })

    engine, defaults = (
        EngineBuilder()
        .with_adapter(adapter)
        .with_llm_client(ClaudePlatformClient(api_key="sk-ant-..."))
        .with_center_skill(CenterCoordinatorSkill())
        .with_formulation_skill(DemandFormulationSkill())
        .with_offer_skill(OfferGenerationSkill())
        .with_event_pusher(LoggingEventPusher())
        .with_display_names({"alice": "Alice", "bob": "Bob"})
        .build()
    )

    session = NegotiationSession(
        negotiation_id="my-first-negotiation",
        demand=DemandSnapshot(raw_intent="I need a technical co-founder"),
    )

    # Auto-confirm formulation (in production, user confirms via UI)
    async def auto_confirm():
        for _ in range(60):
            await asyncio.sleep(1)
            if engine.is_awaiting_confirmation(session.negotiation_id):
                engine.confirm_formulation(session.negotiation_id)
                return

    asyncio.create_task(auto_confirm())
    result = await engine.start_negotiation(session=session, **defaults)

    print(f"State: {result.state.value}")
    print(f"Plan: {result.plan_output[:500]}")

asyncio.run(main())
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Your Application                    │
│  (custom adapters, skills, tools, UI)               │
├─────────────────────────────────────────────────────┤
│                   Towow SDK                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Protocols │  │ Builder  │  │ Default Impls    │  │
│  │ (6 + 1)  │  │          │  │ (replaceable)    │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────┤
│              Sealed Protocol Layer                    │
│  State machine · Barrier · Confirmation · Recursion  │
│  (you cannot modify this — and you don't need to)    │
└─────────────────────────────────────────────────────┘
```

### Three Layers

| Layer | What | Can you change it? |
|-------|------|--------------------|
| **Protocol** | State machine (8 states), barrier, confirmation, recursion depth, anti-fabrication | No (sealed) |
| **Contract** | 7 Protocols: `Encoder`, `ResonanceDetector`, `ProfileDataSource`, `PlatformLLMClient`, `Skill`, `EventPusher`, `CenterToolHandler` | Implement your own |
| **Implementation** | Default skills, adapters, encoders, pushers | Replace freely |

## Extension Points

### 1. Custom LLM Adapter

Connect any LLM provider as the agent-side model.

```python
from towow import BaseAdapter

class MyAdapter(BaseAdapter):
    async def get_profile(self, agent_id: str) -> dict:
        return self._db.get_agent(agent_id)

    async def chat(self, agent_id, messages, system_prompt=None) -> str:
        return await my_llm.complete(messages, system=system_prompt)

    async def chat_stream(self, agent_id, messages, system_prompt=None):
        async for chunk in my_llm.stream(messages, system=system_prompt):
            yield chunk
```

See `examples/custom_adapter.py` for a complete example.

### 2. Custom Skill

Replace any of the 6 default skills with your domain-specific logic.

```python
from towow import BaseSkill

class MyOfferSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "my_offer"

    async def execute(self, context: dict) -> dict:
        # Your custom offer generation logic
        return {"content": "...", "capabilities": [...]}

    def _build_prompt(self, context):
        return "system prompt", [{"role": "user", "content": "..."}]
```

### 3. Custom Center Tool

Add tools that Center can use during synthesis.

```python
# Step 1: Define the handler
class SearchDBHandler:
    @property
    def tool_name(self) -> str:
        return "search_database"

    async def handle(self, session, tool_args, context):
        rows = await db.search(tool_args["query"])
        return {"results": rows}

# Step 2: Extend CenterCoordinatorSkill to include the tool schema
from towow import CenterCoordinatorSkill

class MyCenterSkill(CenterCoordinatorSkill):
    def _get_tools(self):
        tools = super()._get_tools()
        tools.append({
            "name": "search_database",
            "description": "Search the database",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        })
        return tools

# Step 3: Register both with the engine
engine, defaults = (
    EngineBuilder()
    .with_center_skill(MyCenterSkill())
    .with_tool_handler(SearchDBHandler())
    # ... other config ...
    .build()
)
```

See `examples/custom_tool.py` for a complete example.

### 4. Custom Event Transport

Replace WebSocket with any event transport.

```python
class KafkaEventPusher:
    async def push(self, event):
        await kafka_producer.send("towow-events", event.to_dict())

    async def push_many(self, events):
        for e in events:
            await self.push(e)
```

Built-in options: `WebSocketEventPusher`, `LoggingEventPusher`, `NullEventPusher`.

### 5. Custom Encoder / Resonance Detector

Replace the vector encoding and matching algorithms.

```python
class FAISSResonanceDetector:
    async def detect(self, demand_vector, agent_vectors, k_star):
        # Your FAISS/ANN implementation
        return [(agent_id, score), ...]
```

## Headless Mode

Run negotiations without a web server — useful for scripts, notebooks, and CI.

```python
from towow import EngineBuilder, NullEventPusher

engine, defaults = (
    EngineBuilder()
    .with_event_pusher(NullEventPusher())  # no WebSocket needed
    # ... other config ...
    .build()
)
```

## Negotiation Lifecycle

The engine drives sessions through 8 states:

```
CREATED → FORMULATING → FORMULATED → ENCODING → OFFERING
    → BARRIER_WAITING → SYNTHESIZING → COMPLETED
```

Key mechanisms (all enforced by code, not prompts):

- **Barrier**: All agents must respond before Center starts (prevents first-proposal bias)
- **Confirmation**: User must confirm formulation before encoding begins
- **Recursion**: Center can trigger sub-negotiations (depth=1 max in V1)
- **Round limit**: Center gets max 2 rounds before forced output_plan
- **Anti-fabrication**: Each agent only sees its own profile during offer generation

## API Reference

### Core Concepts (must understand)

| Concept | Class | Description |
|---------|-------|-------------|
| Engine | `NegotiationEngine` | Drives the state machine |
| Session | `NegotiationSession` | All data for one negotiation |
| Adapter | `BaseAdapter` / `ProfileDataSource` | Client-side LLM connection |
| Skill | `BaseSkill` / `Skill` | Intelligence module (formulation, offer, center) |
| Platform LLM | `PlatformLLMClient` | Platform-side LLM with tool-use |

### Optional Concepts (advanced)

| Concept | When needed |
|---------|-------------|
| `Encoder` + `ResonanceDetector` | Custom vector matching |
| `EventPusher` | Custom event transport |
| `CenterToolHandler` | Custom Center tools |

### Default Skills

| Skill | Class | Role |
|-------|-------|------|
| Formulation | `DemandFormulationSkill` | Enriches raw demand into structured form |
| Offer | `OfferGenerationSkill` | Generates agent's response to demand |
| Center | `CenterCoordinatorSkill` | Coordinates offers, identifies gaps, outputs plan |
| Sub-negotiation | `SubNegotiationSkill` | Discovers complementarities between agents |
| Gap recursion | `GapRecursionSkill` | Converts gaps into sub-demands |
| Reflection | `ReflectionSelectorSkill` | Selects best proposal (reserved) |

### Errors

All errors inherit from `TowowError`:

| Error | When |
|-------|------|
| `EngineError` | Invalid state transition, engine internal error |
| `SkillError` | Skill execution failure |
| `AdapterError` | Client-side LLM failure |
| `LLMError` | Platform-side LLM failure |
| `EncodingError` | Vector encoding failure |
| `ConfigError` | Configuration error |

## Examples

- `examples/headless.py` — Full negotiation without web server
- `examples/custom_adapter.py` — Connect your own LLM provider
- `examples/custom_tool.py` — Add custom Center tools

## Install from Source

```bash
cd backend
pip install -e .                    # core only
pip install -e ".[all]"             # all optional deps
pip install -e ".[dev]"             # development deps
```
