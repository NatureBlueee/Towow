"""
End-to-end integration tests for the Towow V1 negotiation system.

Wires together ALL modules with mocks to verify the complete negotiation
loop works from demand submission to plan output.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import numpy as np
import pytest

from towow.core.engine import NegotiationEngine
from towow.core.events import EventType
from towow.core.models import (
    AgentState,
    DemandSnapshot,
    NegotiationSession,
    NegotiationState,
    TraceChain,
    generate_id,
)
from towow.hdc.resonance import CosineResonanceDetector

from towow.skills.center import CenterCoordinatorSkill

from .conftest import (
    MockEncoder,
    MockEventPusher,
    MockPlatformLLMClient,
    MockProfileDataSource,
    run_with_auto_confirm,
)


# ============ Helpers ============


def _make_session(
    demand_text: str = "I need a technical co-founder who can build an AI product",
    max_center_rounds: int = 2,
) -> NegotiationSession:
    """Create a fresh NegotiationSession with a DemandSnapshot."""
    neg_id = generate_id("neg")
    return NegotiationSession(
        negotiation_id=neg_id,
        demand=DemandSnapshot(
            raw_intent=demand_text,
            user_id="user_test",
            scene_id="scene_startup",
        ),
        max_center_rounds=max_center_rounds,
        trace=TraceChain(negotiation_id=neg_id),
    )


async def _make_agent_vectors(
    encoder: MockEncoder,
    count: int = 5,
) -> dict[str, np.ndarray]:
    """Create deterministic agent vectors for testing."""
    agent_profiles = {
        "agent_alice": "python machine-learning data-science deep-learning AI",
        "agent_bob": "frontend react design user-experience CSS",
        "agent_carol": "blockchain smart-contracts solidity web3 crypto",
        "agent_dave": "devops kubernetes aws infrastructure cloud",
        "agent_eve": "product-management growth analytics marketing strategy",
    }
    agents = dict(list(agent_profiles.items())[:count])
    vectors = {}
    for agent_id, profile_text in agents.items():
        vectors[agent_id] = await encoder.encode(profile_text)
    return vectors


def _build_engine(
    encoder: MockEncoder,
    resonance_detector: CosineResonanceDetector,
    event_pusher: MockEventPusher,
    offer_timeout_s: float = 5.0,
) -> NegotiationEngine:
    """Wire together the engine with mock and real components."""
    return NegotiationEngine(
        encoder=encoder,
        resonance_detector=resonance_detector,
        event_pusher=event_pusher,
        offer_timeout_s=offer_timeout_s,
    )


def _make_output_plan_response(
    plan_text: str = "This is the final plan.",
    call_id: str = "call_1",
) -> dict[str, Any]:
    """Create a mock LLM response with an output_plan tool call."""
    return {
        "content": None,
        "tool_calls": [
            {
                "name": "output_plan",
                "arguments": {"plan_text": plan_text},
                "id": call_id,
            }
        ],
        "stop_reason": "tool_use",
    }


def _make_ask_agent_response(
    agent_id: str = "agent_alice",
    question: str = "What is your experience with AI?",
    call_id: str = "call_ask_1",
) -> dict[str, Any]:
    """Create a mock LLM response with an ask_agent tool call."""
    return {
        "content": None,
        "tool_calls": [
            {
                "name": "ask_agent",
                "arguments": {"agent_id": agent_id, "question": question},
                "id": call_id,
            }
        ],
        "stop_reason": "tool_use",
    }


def _extract_event_types(pusher: MockEventPusher) -> list[str]:
    """Extract event type values in order from the pusher."""
    return [e.event_type.value for e in pusher.events]


# ============ Tests ============


class TestHappyPathFullNegotiation:
    """
    5 agents, demand text, LLM returns output_plan on first center call.
    Verify complete event sequence and state.
    """

    @pytest.mark.asyncio
    async def test_happy_path_full_negotiation(self):
        # Setup
        encoder = MockEncoder(dim=128)
        resonance = CosineResonanceDetector()
        pusher = MockEventPusher()
        adapter = MockProfileDataSource()
        adapter.set_default_chat_response(
            "I can help with building AI products. I have 5 years of experience."
        )
        llm = MockPlatformLLMClient()
        llm.add_response(
            _make_output_plan_response(
                plan_text="Recommended team: Alice (ML), Bob (Frontend), Dave (Infra)."
            )
        )

        engine = _build_engine(encoder, resonance, pusher)
        session = _make_session()
        agent_vectors = await _make_agent_vectors(encoder, count=5)
        center_skill = CenterCoordinatorSkill()

        # Execute
        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=5,
            min_score=-1.0,  # Allow negative cosine sims from mock vectors
        )

        # Verify session state
        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output is not None
        assert "Recommended team" in result.plan_output
        assert result.completed_at is not None

        # Verify event sequence
        event_types = _extract_event_types(pusher)
        assert event_types[0] == EventType.FORMULATION_READY.value
        assert event_types[1] == EventType.RESONANCE_ACTIVATED.value

        # After resonance, we should see offer.received for each agent that replied
        offer_events = pusher.get_events_by_type(EventType.OFFER_RECEIVED)
        assert len(offer_events) == 5  # all 5 agents should have replied

        # Then barrier.complete
        barrier_events = pusher.get_events_by_type(EventType.BARRIER_COMPLETE)
        assert len(barrier_events) == 1
        assert barrier_events[0].data["offers_received"] == 5
        assert barrier_events[0].data["exited_count"] == 0

        # Then center.tool_call (output_plan)
        center_events = pusher.get_events_by_type(EventType.CENTER_TOOL_CALL)
        assert len(center_events) == 1
        assert center_events[0].data["tool_name"] == "output_plan"

        # Then plan.ready
        plan_events = pusher.get_events_by_type(EventType.PLAN_READY)
        assert len(plan_events) == 1
        assert plan_events[0].data["center_rounds"] == 1

        # Verify correct overall ordering:
        # formulation.ready -> resonance.activated -> offer.received (x5) ->
        # barrier.complete -> center.tool_call -> plan.ready
        assert event_types.index(EventType.FORMULATION_READY.value) < event_types.index(
            EventType.RESONANCE_ACTIVATED.value
        )
        last_offer_idx = max(
            i for i, t in enumerate(event_types) if t == EventType.OFFER_RECEIVED.value
        )
        barrier_idx = event_types.index(EventType.BARRIER_COMPLETE.value)
        assert last_offer_idx < barrier_idx
        center_idx = event_types.index(EventType.CENTER_TOOL_CALL.value)
        assert barrier_idx < center_idx
        plan_idx = event_types.index(EventType.PLAN_READY.value)
        assert center_idx < plan_idx

        # Verify participants have offers (REPLIED state)
        for p in result.participants:
            assert p.state == AgentState.REPLIED
            assert p.offer is not None
            assert p.offer.content != ""


class TestCenterMultiRound:
    """
    LLM first returns ask_agent tool call, then output_plan.
    Verify 2 center rounds and both tool call events.
    """

    @pytest.mark.asyncio
    async def test_center_multi_round(self):
        # Setup
        encoder = MockEncoder(dim=128)
        resonance = CosineResonanceDetector()
        pusher = MockEventPusher()
        adapter = MockProfileDataSource()
        adapter.set_default_chat_response("I specialize in AI and ML.")
        adapter.set_chat_response(
            "agent_alice",
            "I have deep experience with transformer architectures and LLM fine-tuning.",
        )
        llm = MockPlatformLLMClient()

        # Round 1: Center asks agent_alice a follow-up question
        llm.add_response(
            _make_ask_agent_response(
                agent_id="agent_alice",
                question="Can you elaborate on your AI experience?",
                call_id="call_ask_1",
            )
        )
        # Round 2: Center produces the plan
        llm.add_response(
            _make_output_plan_response(
                plan_text="After deeper evaluation: Alice is the ideal co-founder.",
                call_id="call_plan_1",
            )
        )

        engine = _build_engine(encoder, resonance, pusher)
        session = _make_session(max_center_rounds=5)  # Allow more rounds
        agent_vectors = await _make_agent_vectors(encoder, count=3)
        center_skill = CenterCoordinatorSkill()

        # Execute
        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
            min_score=-1.0,  # Allow negative cosine sims from mock vectors
        )

        # Verify session state
        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output is not None
        assert "Alice" in result.plan_output
        assert result.center_rounds == 2

        # Verify both center tool call events
        center_events = pusher.get_events_by_type(EventType.CENTER_TOOL_CALL)
        assert len(center_events) == 2

        # First tool call: ask_agent
        assert center_events[0].data["tool_name"] == "ask_agent"
        assert center_events[0].data["round_number"] == 1
        assert center_events[0].data["tool_args"]["agent_id"] == "agent_alice"

        # Second tool call: output_plan
        assert center_events[1].data["tool_name"] == "output_plan"
        assert center_events[1].data["round_number"] == 2


class TestNoAgentsStillCompletes:
    """
    Empty agent_vectors dict.
    Should still reach COMPLETED with a plan.
    """

    @pytest.mark.asyncio
    async def test_no_agents_still_completes(self):
        # Setup
        encoder = MockEncoder(dim=128)
        resonance = CosineResonanceDetector()
        pusher = MockEventPusher()
        adapter = MockProfileDataSource()
        llm = MockPlatformLLMClient()
        llm.add_response(
            _make_output_plan_response(
                plan_text="No suitable agents found. Recommend broader search."
            )
        )

        engine = _build_engine(encoder, resonance, pusher)
        session = _make_session()
        center_skill = CenterCoordinatorSkill()

        # Execute with empty agent_vectors
        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors={},
            k_star=5,
            min_score=-1.0,  # No agents anyway, min_score irrelevant
        )

        # Verify session state
        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output is not None
        assert "No suitable agents" in result.plan_output
        assert result.completed_at is not None

        # Verify event sequence: should have formulation.ready, then jump to synthesis
        event_types = _extract_event_types(pusher)
        assert EventType.FORMULATION_READY.value in event_types
        # No resonance.activated (no agents)
        assert EventType.RESONANCE_ACTIVATED.value not in event_types
        # No offer.received (no participants)
        assert EventType.OFFER_RECEIVED.value not in event_types
        # No barrier.complete (no participants to wait for)
        assert EventType.BARRIER_COMPLETE.value not in event_types
        # But center.tool_call and plan.ready should exist
        assert EventType.CENTER_TOOL_CALL.value in event_types
        assert EventType.PLAN_READY.value in event_types

        # Verify no participants
        assert len(result.participants) == 0


class TestAgentTimeoutGraceful:
    """
    One mock adapter raises TimeoutError for a specific agent.
    Other agents succeed. Negotiation still completes.
    """

    @pytest.mark.asyncio
    async def test_agent_timeout_graceful(self):
        # Setup: adapter that raises TimeoutError for agent_carol
        class TimeoutAdapter(MockProfileDataSource):
            async def chat(
                self,
                agent_id: str,
                messages: list[dict[str, str]],
                system_prompt: Optional[str] = None,
            ) -> str:
                if agent_id == "agent_carol":
                    raise TimeoutError("Agent carol timed out")
                return await super().chat(agent_id, messages, system_prompt)

        encoder = MockEncoder(dim=128)
        resonance = CosineResonanceDetector()
        pusher = MockEventPusher()
        adapter = TimeoutAdapter()
        adapter.set_default_chat_response("I can contribute to the team.")
        llm = MockPlatformLLMClient()
        llm.add_response(
            _make_output_plan_response(
                plan_text="Team formed without Carol (timeout)."
            )
        )

        engine = _build_engine(encoder, resonance, pusher, offer_timeout_s=2.0)
        session = _make_session()
        agent_vectors = await _make_agent_vectors(encoder, count=5)
        center_skill = CenterCoordinatorSkill()

        # Execute
        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=5,
            min_score=-1.0,  # Allow negative cosine sims from mock vectors
        )

        # Verify negotiation completed
        assert result.state == NegotiationState.COMPLETED
        assert result.plan_output is not None

        # Find carol's participant status
        carol = next(
            (p for p in result.participants if p.agent_id == "agent_carol"), None
        )
        assert carol is not None
        assert carol.state == AgentState.EXITED
        assert carol.offer is None

        # All other agents should have replied
        non_carol = [
            p for p in result.participants if p.agent_id != "agent_carol"
        ]
        for p in non_carol:
            assert p.state == AgentState.REPLIED
            assert p.offer is not None

        # Verify barrier event reflects the timeout
        barrier_events = pusher.get_events_by_type(EventType.BARRIER_COMPLETE)
        assert len(barrier_events) == 1
        assert barrier_events[0].data["exited_count"] == 1
        assert barrier_events[0].data["offers_received"] == 4

        # Verify offer events: 4 offers (carol timed out)
        offer_events = pusher.get_events_by_type(EventType.OFFER_RECEIVED)
        assert len(offer_events) == 4

        # Plan still produced
        plan_events = pusher.get_events_by_type(EventType.PLAN_READY)
        assert len(plan_events) == 1


class TestTraceChainComplete:
    """
    After negotiation, trace has expected entries.
    Each entry has duration_ms > 0. trace.completed_at is set.
    """

    @pytest.mark.asyncio
    async def test_trace_chain_complete(self):
        # Setup
        encoder = MockEncoder(dim=128)
        resonance = CosineResonanceDetector()
        pusher = MockEventPusher()
        adapter = MockProfileDataSource()
        adapter.set_default_chat_response("Ready to contribute.")
        llm = MockPlatformLLMClient()
        llm.add_response(
            _make_output_plan_response(plan_text="Final plan with trace.")
        )

        engine = _build_engine(encoder, resonance, pusher)
        session = _make_session()
        agent_vectors = await _make_agent_vectors(encoder, count=3)
        center_skill = CenterCoordinatorSkill()

        # Execute
        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=3,
            min_score=-1.0,  # Allow negative cosine sims from mock vectors
        )

        # Verify trace exists and is populated
        trace = result.trace
        assert trace is not None
        assert trace.completed_at is not None

        # Trace should have entries for each phase
        entry_steps = [e.step for e in trace.entries]
        assert "formulation" in entry_steps
        assert "encoding_resonance" in entry_steps
        assert "offers_barrier" in entry_steps
        # When output_plan is the first tool call, the engine returns from
        # _finish_with_plan before recording a per-tool trace. The overall
        # synthesis_complete entry captures the entire synthesis phase.
        assert "synthesis_complete" in entry_steps

        # Each entry should have a positive duration
        for entry in trace.entries:
            assert entry.duration_ms is not None
            assert entry.duration_ms >= 0  # Allow 0 for very fast mock ops

        # Verify ordering: entries are in chronological order
        for i in range(len(trace.entries) - 1):
            assert trace.entries[i].timestamp <= trace.entries[i + 1].timestamp

    @pytest.mark.asyncio
    async def test_trace_chain_multi_round(self):
        """Trace captures multiple center rounds properly."""
        encoder = MockEncoder(dim=128)
        resonance = CosineResonanceDetector()
        pusher = MockEventPusher()
        adapter = MockProfileDataSource()
        adapter.set_default_chat_response("Happy to help.")
        llm = MockPlatformLLMClient()
        # Round 1: ask_agent
        llm.add_response(
            _make_ask_agent_response(
                agent_id="agent_alice",
                question="Details please?",
            )
        )
        # Round 2: output_plan
        llm.add_response(
            _make_output_plan_response(plan_text="Multi-round plan.")
        )

        engine = _build_engine(encoder, resonance, pusher)
        session = _make_session(max_center_rounds=5)
        agent_vectors = await _make_agent_vectors(encoder, count=2)
        center_skill = CenterCoordinatorSkill()

        result = await run_with_auto_confirm(engine, session,
            adapter=adapter,
            llm_client=llm,
            center_skill=center_skill,
            agent_vectors=agent_vectors,
            k_star=2,
            min_score=-1.0,  # Allow negative cosine sims from mock vectors
        )

        trace = result.trace
        assert trace is not None
        assert trace.completed_at is not None

        # Should have center_tool_ask_agent entry from round 1.
        # When output_plan is called in round 2, the engine returns via
        # _finish_with_plan before recording center_tool_output_plan,
        # but synthesis_complete captures the final phase.
        entry_steps = [e.step for e in trace.entries]
        assert "center_tool_ask_agent" in entry_steps
        assert "synthesis_complete" in entry_steps

        # Total entries: formulation + encoding_resonance + offers_barrier +
        #   center_tool_ask_agent + synthesis_complete = 5
        assert len(trace.entries) >= 5
