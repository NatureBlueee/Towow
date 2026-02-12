"""
Shared test fixtures for all Towow V1 tests.

Provides mock adapters, mock encoders, sample data, and
utility factories for creating test objects.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Optional

import numpy as np
import pytest

from towow.core.models import (
    AgentIdentity,
    AgentParticipant,
    AgentState,
    AgentType,
    DemandSnapshot,
    NegotiationSession,
    NegotiationState,
    Offer,
    SceneDefinition,
    SourceType,
    TraceChain,
    generate_id,
)
from towow.core.engine import NegotiationEngine
from towow.core.events import EventType, NegotiationEvent
from towow.core.protocols import Vector
from towow.skills.center import CenterCoordinatorSkill


# ============ Sample Data ============

SAMPLE_AGENTS = [
    AgentIdentity(
        agent_id="agent_alice",
        display_name="Alice",
        source_type=SourceType.CLAUDE,
        metadata={"skills": ["python", "machine-learning", "data-science"]},
    ),
    AgentIdentity(
        agent_id="agent_bob",
        display_name="Bob",
        source_type=SourceType.SECONDME,
        metadata={"skills": ["frontend", "react", "design"]},
    ),
    AgentIdentity(
        agent_id="agent_carol",
        display_name="Carol",
        source_type=SourceType.TEMPLATE,
        metadata={"skills": ["blockchain", "smart-contracts", "solidity"]},
    ),
    AgentIdentity(
        agent_id="agent_dave",
        display_name="Dave",
        source_type=SourceType.CLAUDE,
        metadata={"skills": ["devops", "kubernetes", "aws"]},
    ),
    AgentIdentity(
        agent_id="agent_eve",
        display_name="Eve",
        source_type=SourceType.CUSTOM,
        metadata={"skills": ["product-management", "growth", "analytics"]},
    ),
]

SAMPLE_DEMAND = DemandSnapshot(
    raw_intent="I need a technical co-founder who can build an AI product",
    user_id="user_test",
    scene_id="scene_startup",
)


# ============ Mock Adapter ============

class MockProfileDataSource:
    """Mock client-side adapter for testing."""

    def __init__(self, profiles: dict[str, dict[str, Any]] | None = None):
        self._profiles = profiles or {}
        self._chat_responses: dict[str, str] = {}
        self._default_response = "Mock response"

    def set_chat_response(self, agent_id: str, response: str) -> None:
        self._chat_responses[agent_id] = response

    def set_default_chat_response(self, response: str) -> None:
        self._default_response = response

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        return self._profiles.get(agent_id, {"agent_id": agent_id})

    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        if agent_id in self._chat_responses:
            return self._chat_responses[agent_id]
        return self._default_response

    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        response = await self.chat(agent_id, messages, system_prompt)
        yield response


# ============ Mock Encoder ============

class MockEncoder:
    """Mock encoder for testing. Returns deterministic vectors based on text hash."""

    def __init__(self, dim: int = 128):
        self.dim = dim

    async def encode(self, text: str) -> Vector:
        rng = np.random.RandomState(hash(text) % (2**31))
        vec = rng.randn(self.dim).astype(np.float32)
        return vec / np.linalg.norm(vec)

    async def batch_encode(self, texts: list[str]) -> list[Vector]:
        return [await self.encode(t) for t in texts]


# ============ Mock Resonance Detector ============

class MockResonanceDetector:
    """Mock resonance detector that uses cosine similarity.

    Returns (activated, filtered) tuple per PLAN-003 contract:
    - activated: agents with score >= min_score, limited to k_star
    - filtered: agents with score < min_score
    """

    async def detect(
        self,
        demand_vector: Vector,
        agent_vectors: dict[str, Vector],
        k_star: int,
        min_score: float = 0.0,
    ) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        results = []
        for agent_id, agent_vec in agent_vectors.items():
            sim = float(np.dot(demand_vector, agent_vec) / (
                np.linalg.norm(demand_vector) * np.linalg.norm(agent_vec) + 1e-8
            ))
            results.append((agent_id, sim))
        results.sort(key=lambda x: x[1], reverse=True)

        # Split by min_score threshold
        activated = [(aid, s) for aid, s in results if s >= min_score]
        filtered = [(aid, s) for aid, s in results if s < min_score]

        # Apply k_star limit to activated only
        activated = activated[:k_star]

        return activated, filtered


# ============ Mock Platform LLM Client ============

class MockPlatformLLMClient:
    """Mock platform-side LLM client for testing Center tool-use."""

    def __init__(self):
        self._responses: list[dict[str, Any]] = []
        self._call_count = 0

    def add_response(self, response: dict[str, Any]) -> None:
        self._responses.append(response)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        if self._call_count < len(self._responses):
            resp = self._responses[self._call_count]
            self._call_count += 1
            return resp
        self._call_count += 1
        return {
            "content": None,
            "tool_calls": [
                {
                    "name": "output_plan",
                    "arguments": {"plan_text": "Default mock plan output."},
                    "id": f"call_{self._call_count}",
                }
            ],
            "stop_reason": "tool_use",
        }


# ============ Mock Event Pusher ============

class MockEventPusher:
    """Collects pushed events for test assertions."""

    def __init__(self):
        self.events: list[NegotiationEvent] = []

    async def push(self, event: NegotiationEvent) -> None:
        self.events.append(event)

    async def push_many(self, events: list[NegotiationEvent]) -> None:
        self.events.extend(events)

    def get_events_by_type(self, event_type: EventType) -> list[NegotiationEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def reset(self) -> None:
        self.events.clear()


# ============ Fixtures ============

@pytest.fixture
def sample_agents() -> list[AgentIdentity]:
    return list(SAMPLE_AGENTS)


@pytest.fixture
def sample_demand() -> DemandSnapshot:
    return DemandSnapshot(
        raw_intent="I need a technical co-founder who can build an AI product",
        user_id="user_test",
        scene_id="scene_startup",
    )


@pytest.fixture
def sample_scene() -> SceneDefinition:
    return SceneDefinition(
        scene_id="scene_startup",
        name="Startup Co-founder Matching",
        description="Find technical co-founders for AI startups",
        organizer_id="organizer_1",
        expected_responders=3,
        agent_ids=[a.agent_id for a in SAMPLE_AGENTS],
    )


@pytest.fixture
def mock_adapter() -> MockProfileDataSource:
    adapter = MockProfileDataSource()
    adapter.set_default_chat_response("This is a mock LLM response.")
    return adapter


@pytest.fixture
def mock_encoder() -> MockEncoder:
    return MockEncoder(dim=128)


@pytest.fixture
def mock_resonance() -> MockResonanceDetector:
    return MockResonanceDetector()


@pytest.fixture
def mock_llm() -> MockPlatformLLMClient:
    return MockPlatformLLMClient()


@pytest.fixture
def mock_pusher() -> MockEventPusher:
    return MockEventPusher()


@pytest.fixture
def center_skill() -> CenterCoordinatorSkill:
    return CenterCoordinatorSkill()


@pytest.fixture
def sample_session(sample_demand: DemandSnapshot) -> NegotiationSession:
    return NegotiationSession(
        negotiation_id=generate_id("neg"),
        demand=sample_demand,
        trace=TraceChain(negotiation_id="test"),
    )


# ============ Auto-Confirm Helper ============

async def run_with_auto_confirm(
    engine: NegotiationEngine,
    session: NegotiationSession,
    **kwargs: Any,
) -> NegotiationSession:
    """Run engine with automatic confirmation at formulation step.

    Production code waits for user confirmation (Section 10.2).
    This helper auto-confirms for tests that focus on other aspects.
    """
    async def _auto_confirm() -> None:
        # Poll until engine is waiting for confirmation
        while not engine.is_awaiting_confirmation(session.negotiation_id):
            await asyncio.sleep(0.001)
        engine.confirm_formulation(session.negotiation_id)

    confirm_task = asyncio.create_task(_auto_confirm())
    try:
        result = await engine.start_negotiation(session=session, **kwargs)
    finally:
        confirm_task.cancel()
        try:
            await confirm_task
        except asyncio.CancelledError:
            pass
    return result
