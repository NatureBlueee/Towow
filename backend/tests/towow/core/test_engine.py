"""
Tests for the NegotiationEngine — the orchestration state machine.

All tests use mocks. No real LLM calls. Fast and deterministic.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional
from unittest.mock import AsyncMock

import numpy as np
import pytest

from towow.core.engine import (
    DEFAULT_OFFER_TIMEOUT_S,
    NegotiationEngine,
    TOOL_ASK_AGENT,
    TOOL_CREATE_SUB_DEMAND,
    TOOL_OUTPUT_PLAN,
    TOOL_START_DISCOVERY,
    VALID_TRANSITIONS,
)
from towow.core.errors import EngineError
from towow.core.events import EventType
from towow.core.models import (
    AgentParticipant,
    AgentState,
    DemandSnapshot,
    NegotiationSession,
    NegotiationState,
    Offer,
    TraceChain,
    generate_id,
)

from tests.towow.conftest import (
    MockEncoder,
    MockEventPusher,
    MockPlatformLLMClient,
    MockProfileDataSource,
    MockResonanceDetector,
    SAMPLE_AGENTS,
    run_with_auto_confirm,
)
from towow.skills.center import CenterCoordinatorSkill


# ============ Fixtures ============


@pytest.fixture
def encoder() -> MockEncoder:
    return MockEncoder(dim=128)


@pytest.fixture
def resonance() -> MockResonanceDetector:
    return MockResonanceDetector()


@pytest.fixture
def pusher() -> MockEventPusher:
    return MockEventPusher()


@pytest.fixture
def adapter() -> MockProfileDataSource:
    a = MockProfileDataSource()
    a.set_default_chat_response("I can help with that project.")
    return a


@pytest.fixture
def llm() -> MockPlatformLLMClient:
    return MockPlatformLLMClient()


@pytest.fixture
def center_skill() -> CenterCoordinatorSkill:
    return CenterCoordinatorSkill()


@pytest.fixture
def engine(
    encoder: MockEncoder,
    resonance: MockResonanceDetector,
    pusher: MockEventPusher,
) -> NegotiationEngine:
    return NegotiationEngine(
        encoder=encoder,
        resonance_detector=resonance,
        event_pusher=pusher,
        offer_timeout_s=5.0,
    )


@pytest.fixture
def session() -> NegotiationSession:
    nid = generate_id("neg")
    return NegotiationSession(
        negotiation_id=nid,
        demand=DemandSnapshot(
            raw_intent="I need a technical co-founder for my AI startup",
            user_id="user_1",
            scene_id="scene_1",
        ),
        trace=TraceChain(negotiation_id=nid),
    )


async def _build_agent_vectors(encoder: MockEncoder) -> dict[str, np.ndarray]:
    """Build agent vectors for the sample agents."""
    vectors = {}
    for agent in SAMPLE_AGENTS[:3]:  # Use first 3 for speed
        vec = await encoder.encode(
            " ".join(agent.metadata.get("skills", []))
        )
        vectors[agent.agent_id] = vec
    return vectors


# ============ Happy Path ============


class TestHappyPath:
    """Full flow from CREATED to COMPLETED with mock data."""

    @pytest.mark.asyncio
    async def test_full_negotiation_flow(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Complete negotiation: formulation -> encoding -> offers -> synthesis -> plan."""
        agent_vectors = await _build_agent_vectors(encoder)

        # LLM returns output_plan on first Center call
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Here is your team plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output == "Here is your team plan."
        assert result.completed_at is not None
        assert result.demand.formulated_text is not None
        assert len(result.participants) > 0
        assert result.center_rounds == 1

    @pytest.mark.asyncio
    async def test_full_flow_events_pushed(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Verify all expected events are pushed in correct order."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Final plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        event_types = [e.event_type for e in pusher.events]

        # Must see: formulation.ready, resonance.activated, offer.received (x N),
        # barrier.complete, center.tool_call, plan.ready
        assert EventType.FORMULATION_READY in event_types
        assert EventType.RESONANCE_ACTIVATED in event_types
        assert EventType.BARRIER_COMPLETE in event_types
        assert EventType.CENTER_TOOL_CALL in event_types
        assert EventType.PLAN_READY in event_types

        # Offer events should exist for each participant that replied
        offer_events = pusher.get_events_by_type(EventType.OFFER_RECEIVED)
        assert len(offer_events) > 0

        # Plan ready should be last
        assert event_types[-1] == EventType.PLAN_READY


# ============ State Transition Validation ============


class TestStateTransitions:
    """Test state machine transitions — valid and invalid."""

    @pytest.mark.asyncio
    async def test_valid_transitions_all(
        self, engine: NegotiationEngine, session: NegotiationSession
    ):
        """All valid transitions should succeed."""
        # CREATED -> FORMULATING
        engine._transition(session, NegotiationState.FORMULATING)
        assert session.state == NegotiationState.FORMULATING

        # FORMULATING -> FORMULATED
        engine._transition(session, NegotiationState.FORMULATED)
        assert session.state == NegotiationState.FORMULATED

        # FORMULATED -> ENCODING
        engine._transition(session, NegotiationState.ENCODING)
        assert session.state == NegotiationState.ENCODING

        # ENCODING -> OFFERING
        engine._transition(session, NegotiationState.OFFERING)
        assert session.state == NegotiationState.OFFERING

        # OFFERING -> BARRIER_WAITING
        engine._transition(session, NegotiationState.BARRIER_WAITING)
        assert session.state == NegotiationState.BARRIER_WAITING

        # BARRIER_WAITING -> SYNTHESIZING
        engine._transition(session, NegotiationState.SYNTHESIZING)
        assert session.state == NegotiationState.SYNTHESIZING

        # SYNTHESIZING -> SYNTHESIZING (self-loop)
        engine._transition(session, NegotiationState.SYNTHESIZING)
        assert session.state == NegotiationState.SYNTHESIZING

        # SYNTHESIZING -> COMPLETED
        engine._transition(session, NegotiationState.COMPLETED)
        assert session.state == NegotiationState.COMPLETED

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(
        self, engine: NegotiationEngine, session: NegotiationSession
    ):
        """Invalid transitions should raise EngineError."""
        # CREATED -> SYNTHESIZING (skip ahead)
        with pytest.raises(EngineError, match="Invalid state transition"):
            engine._transition(session, NegotiationState.SYNTHESIZING)

    @pytest.mark.asyncio
    async def test_cannot_transition_from_completed(
        self, engine: NegotiationEngine, session: NegotiationSession
    ):
        """COMPLETED is terminal — cannot transition out."""
        engine._transition(session, NegotiationState.FORMULATING)
        engine._transition(session, NegotiationState.FORMULATED)
        engine._transition(session, NegotiationState.ENCODING)
        engine._transition(session, NegotiationState.OFFERING)
        engine._transition(session, NegotiationState.BARRIER_WAITING)
        engine._transition(session, NegotiationState.SYNTHESIZING)
        engine._transition(session, NegotiationState.COMPLETED)

        with pytest.raises(EngineError, match="Invalid state transition"):
            engine._transition(session, NegotiationState.CREATED)

    @pytest.mark.asyncio
    async def test_any_state_can_reach_completed(
        self, engine: NegotiationEngine
    ):
        """Every state (except COMPLETED) should allow transition to COMPLETED."""
        for state in NegotiationState:
            if state == NegotiationState.COMPLETED:
                continue
            s = NegotiationSession(
                negotiation_id=generate_id("neg"),
                demand=DemandSnapshot(raw_intent="test"),
                state=state,
            )
            engine._transition(s, NegotiationState.COMPLETED)
            assert s.state == NegotiationState.COMPLETED

    @pytest.mark.asyncio
    async def test_invalid_skip_states(
        self, engine: NegotiationEngine
    ):
        """Cannot skip intermediate states."""
        s = NegotiationSession(
            negotiation_id=generate_id("neg"),
            demand=DemandSnapshot(raw_intent="test"),
        )
        # CREATED -> ENCODING (skipping FORMULATING, FORMULATED)
        with pytest.raises(EngineError):
            engine._transition(s, NegotiationState.ENCODING)

        # CREATED -> OFFERING
        with pytest.raises(EngineError):
            engine._transition(s, NegotiationState.OFFERING)

        # CREATED -> BARRIER_WAITING
        with pytest.raises(EngineError):
            engine._transition(s, NegotiationState.BARRIER_WAITING)


# ============ Parallel Offers with Timeout ============


class TestParallelOffers:
    """Test parallel offer generation including timeouts."""

    @pytest.mark.asyncio
    async def test_all_agents_reply(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """All agents should successfully generate offers."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        # All participants should have REPLIED
        for p in result.participants:
            assert p.state == AgentState.REPLIED
            assert p.offer is not None

    @pytest.mark.asyncio
    async def test_agent_timeout_marks_exited(
        self,
        encoder: MockEncoder,
        resonance: MockResonanceDetector,
        pusher: MockEventPusher,
        llm: MockPlatformLLMClient,
        center_skill: CenterCoordinatorSkill,
    ):
        """An agent that times out should be marked EXITED, not block others."""
        # Use a very short timeout
        engine = NegotiationEngine(
            encoder=encoder,
            resonance_detector=resonance,
            event_pusher=pusher,
            offer_timeout_s=0.1,  # 100ms timeout
        )

        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Need help"),
            trace=TraceChain(negotiation_id=nid),
        )

        # Create a slow adapter that times out for one agent
        class SlowAdapter(MockProfileDataSource):
            async def chat(
                self,
                agent_id: str,
                messages: list[dict[str, str]],
                system_prompt: Optional[str] = None,
            ) -> str:
                if agent_id == "agent_alice":
                    await asyncio.sleep(10)  # Will timeout
                return "Quick response"

        adapter = SlowAdapter()
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan despite timeout."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED

        # alice should be EXITED (timed out)
        alice = next(
            (p for p in result.participants if p.agent_id == "agent_alice"),
            None,
        )
        if alice:
            assert alice.state == AgentState.EXITED
            assert alice.offer is None

        # Other agents should have replied
        replied = [p for p in result.participants if p.state == AgentState.REPLIED]
        assert len(replied) >= 1  # At least some agents replied

    @pytest.mark.asyncio
    async def test_agent_error_marks_exited(
        self,
        encoder: MockEncoder,
        resonance: MockResonanceDetector,
        pusher: MockEventPusher,
        llm: MockPlatformLLMClient,
        center_skill: CenterCoordinatorSkill,
    ):
        """An agent that errors should be marked EXITED."""
        engine = NegotiationEngine(
            encoder=encoder,
            resonance_detector=resonance,
            event_pusher=pusher,
        )

        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Need help"),
            trace=TraceChain(negotiation_id=nid),
        )

        class ErrorAdapter(MockProfileDataSource):
            async def chat(
                self,
                agent_id: str,
                messages: list[dict[str, str]],
                system_prompt: Optional[str] = None,
            ) -> str:
                if agent_id == "agent_bob":
                    raise RuntimeError("LLM connection failed")
                return "Response"

        adapter = ErrorAdapter()
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        bob = next(
            (p for p in result.participants if p.agent_id == "agent_bob"),
            None,
        )
        if bob:
            assert bob.state == AgentState.EXITED


# ============ Barrier Completion ============


class TestBarrier:
    """Test the wait barrier behavior."""

    @pytest.mark.asyncio
    async def test_barrier_triggers_after_all_replied(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Barrier complete event should fire after all agents resolved."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        barrier_events = pusher.get_events_by_type(EventType.BARRIER_COMPLETE)
        assert len(barrier_events) == 1

        be = barrier_events[0]
        assert be.data["total_participants"] == len(result.participants)
        assert be.data["offers_received"] + be.data["exited_count"] == be.data["total_participants"]

    @pytest.mark.asyncio
    async def test_barrier_with_no_participants(
        self,
        engine: NegotiationEngine,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """With no agent vectors, barrier should still complete gracefully."""
        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Test"),
            trace=TraceChain(negotiation_id=nid),
        )

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan with no agents."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=None,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED
        assert len(result.participants) == 0


# ============ Center Multi-Round ============


class TestCenterMultiRound:
    """Test Center tool-use loop with multiple rounds."""

    @pytest.mark.asyncio
    async def test_ask_agent_then_output_plan(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Center asks an agent first, then outputs plan on second round."""
        agent_vectors = await _build_agent_vectors(encoder)

        # Round 1: ask_agent
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_ASK_AGENT,
                    "arguments": {
                        "agent_id": "agent_alice",
                        "question": "What is your experience with ML?",
                    },
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        # Round 2: output_plan
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan after asking Alice."},
                    "id": "call_2",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output == "Plan after asking Alice."
        assert result.center_rounds == 2

        # Should have center.tool_call events for both rounds
        tool_events = pusher.get_events_by_type(EventType.CENTER_TOOL_CALL)
        assert len(tool_events) == 2
        assert tool_events[0].data["tool_name"] == TOOL_ASK_AGENT
        assert tool_events[1].data["tool_name"] == TOOL_OUTPUT_PLAN

    @pytest.mark.asyncio
    async def test_start_discovery_then_plan(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Center starts discovery, then outputs plan."""
        agent_vectors = await _build_agent_vectors(encoder)

        # Round 1: start_discovery
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_START_DISCOVERY,
                    "arguments": {"topic": "AI product validation methods"},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        # Round 2: output_plan
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan after discovery."},
                    "id": "call_2",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output == "Plan after discovery."

    @pytest.mark.asyncio
    async def test_create_sub_demand(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Center creates a sub-demand, then outputs plan."""
        agent_vectors = await _build_agent_vectors(encoder)

        # Round 1: create_sub_demand
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_CREATE_SUB_DEMAND,
                    "arguments": {"gap_description": "Need a UX designer"},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        # Round 2: output_plan
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan with sub-demand."},
                    "id": "call_2",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED

        # Should have sub_negotiation.started event
        sub_events = pusher.get_events_by_type(EventType.SUB_NEGOTIATION_STARTED)
        assert len(sub_events) == 1
        assert sub_events[0].data["gap_description"] == "Need a UX designer"

    @pytest.mark.asyncio
    async def test_no_tool_calls_uses_content_as_plan(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """If Center returns text without tool calls, use as plan."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": "Here is a direct text plan.",
            "tool_calls": None,
            "stop_reason": "end_turn",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output == "Here is a direct text plan."


# ============ Round Limit ============


class TestRoundLimit:
    """Test that round limits are enforced."""

    @pytest.mark.asyncio
    async def test_round_limit_forces_output_plan(
        self,
        engine: NegotiationEngine,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """After max_center_rounds, tools should be restricted to output_plan."""
        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Test round limit"),
            max_center_rounds=2,
            trace=TraceChain(negotiation_id=nid),
        )
        agent_vectors = await _build_agent_vectors(encoder)

        # Round 1: ask_agent
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_ASK_AGENT,
                    "arguments": {"agent_id": "agent_alice", "question": "Q1?"},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        # Round 2: ask_agent again — this hits the round limit
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_ASK_AGENT,
                    "arguments": {"agent_id": "agent_bob", "question": "Q2?"},
                    "id": "call_2",
                }
            ],
            "stop_reason": "tool_use",
        })

        # Round 3 (forced): output_plan (tools restricted)
        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Forced plan after round limit."},
                    "id": "call_3",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output == "Forced plan after round limit."

    @pytest.mark.asyncio
    async def test_tools_restricted_property(self):
        """tools_restricted should be True after max rounds."""
        s = NegotiationSession(
            negotiation_id="test",
            demand=DemandSnapshot(raw_intent="test"),
            max_center_rounds=2,
        )
        assert not s.tools_restricted
        s.center_rounds = 1
        assert not s.tools_restricted
        s.center_rounds = 2
        assert s.tools_restricted
        s.center_rounds = 3
        assert s.tools_restricted


# ============ Event Completeness ============


class TestEventCompleteness:
    """Verify all expected events are pushed in correct order."""

    @pytest.mark.asyncio
    async def test_event_order_happy_path(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Events should follow the negotiation flow order."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        types = [e.event_type for e in pusher.events]

        # Find indices
        form_idx = types.index(EventType.FORMULATION_READY)
        res_idx = types.index(EventType.RESONANCE_ACTIVATED)
        barrier_idx = types.index(EventType.BARRIER_COMPLETE)
        plan_idx = types.index(EventType.PLAN_READY)

        # Order: formulation -> resonance -> offers -> barrier -> tool_call -> plan
        assert form_idx < res_idx
        assert res_idx < barrier_idx
        assert barrier_idx < plan_idx

    @pytest.mark.asyncio
    async def test_all_events_have_negotiation_id(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Every event should carry the correct negotiation_id."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        for event in pusher.events:
            assert event.negotiation_id == session.negotiation_id


# ============ Trace Chain ============


class TestTraceChain:
    """Verify the trace chain records all steps."""

    @pytest.mark.asyncio
    async def test_trace_has_entries(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Trace should have entries for formulation, encoding, offers, synthesis."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.trace is not None
        steps = [e.step for e in result.trace.entries]

        assert "formulation" in steps
        assert "encoding_resonance" in steps
        assert "offers_barrier" in steps
        assert "synthesis_complete" in steps

    @pytest.mark.asyncio
    async def test_trace_has_timing(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Each trace entry should have a duration_ms."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        for entry in result.trace.entries:
            assert entry.duration_ms is not None
            assert entry.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_trace_completed_at_set(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Trace completed_at should be set when negotiation completes."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.trace.completed_at is not None

    @pytest.mark.asyncio
    async def test_trace_to_dict(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Trace should serialize to dict properly."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        trace_dict = result.trace.to_dict()
        assert "negotiation_id" in trace_dict
        assert "entries" in trace_dict
        assert len(trace_dict["entries"]) > 0


# ============ Agent Exits ============


class TestAgentExits:
    """Test graceful handling of agent exits."""

    @pytest.mark.asyncio
    async def test_all_agents_exit_still_completes(
        self,
        encoder: MockEncoder,
        resonance: MockResonanceDetector,
        pusher: MockEventPusher,
        llm: MockPlatformLLMClient,
        center_skill: CenterCoordinatorSkill,
    ):
        """If all agents exit, negotiation should still reach COMPLETED."""
        engine = NegotiationEngine(
            encoder=encoder,
            resonance_detector=resonance,
            event_pusher=pusher,
            offer_timeout_s=0.1,
        )

        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Help needed"),
            trace=TraceChain(negotiation_id=nid),
        )

        class AlwaysFailAdapter(MockProfileDataSource):
            async def chat(
                self,
                agent_id: str,
                messages: list[dict[str, str]],
                system_prompt: Optional[str] = None,
            ) -> str:
                raise RuntimeError("All agents are down")

        adapter = AlwaysFailAdapter()
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan despite all exits."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED
        for p in result.participants:
            assert p.state == AgentState.EXITED

        barrier_events = pusher.get_events_by_type(EventType.BARRIER_COMPLETE)
        assert len(barrier_events) == 1
        assert barrier_events[0].data["exited_count"] == len(result.participants)

    @pytest.mark.asyncio
    async def test_mixed_reply_and_exit(
        self,
        encoder: MockEncoder,
        resonance: MockResonanceDetector,
        pusher: MockEventPusher,
        llm: MockPlatformLLMClient,
        center_skill: CenterCoordinatorSkill,
    ):
        """Mix of replies and exits should all be tracked correctly."""
        engine = NegotiationEngine(
            encoder=encoder,
            resonance_detector=resonance,
            event_pusher=pusher,
            offer_timeout_s=0.1,
        )

        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Help needed"),
            trace=TraceChain(negotiation_id=nid),
        )

        class MixedAdapter(MockProfileDataSource):
            async def chat(
                self,
                agent_id: str,
                messages: list[dict[str, str]],
                system_prompt: Optional[str] = None,
            ) -> str:
                if agent_id == "agent_carol":
                    raise RuntimeError("Carol is unavailable")
                return f"Offer from {agent_id}"

        adapter = MixedAdapter()
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Mixed plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.state == NegotiationState.COMPLETED
        assert result.is_barrier_met

        carol = next(
            (p for p in result.participants if p.agent_id == "agent_carol"),
            None,
        )
        if carol:
            assert carol.state == AgentState.EXITED


# ============ Edge Cases ============


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_no_formulation_skill(
        self,
        engine: NegotiationEngine,
        session: NegotiationSession,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Without formulation skill, raw intent should be used directly."""
        agent_vectors = await _build_agent_vectors(encoder)

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            formulation_skill=None,
            agent_vectors=agent_vectors,
            k_star=3,
        )

        assert result.demand.formulated_text == result.demand.raw_intent

    @pytest.mark.asyncio
    async def test_session_without_trace(
        self,
        engine: NegotiationEngine,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        encoder: MockEncoder,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Engine should create trace if session doesn't have one."""
        session = NegotiationSession(
            negotiation_id=generate_id("neg"),
            demand=DemandSnapshot(raw_intent="Test"),
            trace=None,
        )

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
        )

        assert result.trace is not None
        assert result.state == NegotiationState.COMPLETED

    @pytest.mark.asyncio
    async def test_valid_transitions_map_completeness(self):
        """Every NegotiationState should appear in VALID_TRANSITIONS."""
        for state in NegotiationState:
            assert state in VALID_TRANSITIONS, f"{state} missing from VALID_TRANSITIONS"


# ============ Confirmation Mechanism ============


class TestConfirmationMechanism:
    """Test the formulation confirmation wait mechanism (Section 10.2)."""

    @pytest.mark.asyncio
    async def test_confirm_unblocks_engine(
        self,
        engine: NegotiationEngine,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """Engine should pause at FORMULATED and resume on confirm_formulation()."""
        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Test confirmation"),
            trace=TraceChain(negotiation_id=nid),
        )

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan after confirm."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        async def _delayed_confirm():
            # Wait until engine reaches confirmation wait
            while not engine.is_awaiting_confirmation(nid):
                await asyncio.sleep(0.001)
            # At this point, session should be FORMULATED
            assert session.state == NegotiationState.FORMULATED
            engine.confirm_formulation(nid)

        confirm_task = asyncio.create_task(_delayed_confirm())
        try:
            result = await engine.start_negotiation(
                session=session,
                adapter=adapter,
                llm_client=llm,
                center_skill=center_skill,
            )
        finally:
            confirm_task.cancel()
            try:
                await confirm_task
            except asyncio.CancelledError:
                pass

        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output == "Plan after confirm."

    @pytest.mark.asyncio
    async def test_confirm_timeout_auto_proceeds(
        self,
        encoder: MockEncoder,
        resonance: MockResonanceDetector,
        pusher: MockEventPusher,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        center_skill: CenterCoordinatorSkill,
    ):
        """If confirmation times out, engine should auto-proceed with original text."""
        engine = NegotiationEngine(
            encoder=encoder,
            resonance_detector=resonance,
            event_pusher=pusher,
            confirmation_timeout_s=0.05,  # 50ms — will timeout quickly
        )

        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Timeout test"),
            trace=TraceChain(negotiation_id=nid),
        )

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan after timeout."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        # Do NOT confirm — let it timeout
        result = await engine.start_negotiation(
            session=session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
        )

        assert result.state == NegotiationState.COMPLETED
        # Original text used since nobody confirmed
        assert result.demand.formulated_text == "Timeout test"
        assert result.plan_output == "Plan after timeout."

    @pytest.mark.asyncio
    async def test_confirm_with_modified_text(
        self,
        engine: NegotiationEngine,
        adapter: MockProfileDataSource,
        llm: MockPlatformLLMClient,
        pusher: MockEventPusher,
        center_skill: CenterCoordinatorSkill,
    ):
        """User can modify the formulated text during confirmation."""
        nid = generate_id("neg")
        session = NegotiationSession(
            negotiation_id=nid,
            demand=DemandSnapshot(raw_intent="Original intent"),
            trace=TraceChain(negotiation_id=nid),
        )

        llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": TOOL_OUTPUT_PLAN,
                    "arguments": {"plan_text": "Plan with modified text."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        modified_text = "User-refined intent with more detail"

        async def _confirm_with_text():
            while not engine.is_awaiting_confirmation(nid):
                await asyncio.sleep(0.001)
            engine.confirm_formulation(nid, confirmed_text=modified_text)

        confirm_task = asyncio.create_task(_confirm_with_text())
        try:
            result = await engine.start_negotiation(
                session=session,
                adapter=adapter,
                llm_client=llm,
                center_skill=center_skill,
            )
        finally:
            confirm_task.cancel()
            try:
                await confirm_task
            except asyncio.CancelledError:
                pass

        assert result.state == NegotiationState.COMPLETED
        assert result.demand.formulated_text == modified_text
        assert result.plan_output == "Plan with modified text."
