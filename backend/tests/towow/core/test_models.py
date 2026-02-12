"""Tests for core data models — validates structure and basic behavior."""

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


class TestGenerateId:
    def test_generates_unique_ids(self):
        ids = {generate_id("test") for _ in range(100)}
        assert len(ids) == 100

    def test_prefix_applied(self):
        assert generate_id("neg").startswith("neg_")

    def test_no_prefix(self):
        assert "_" not in generate_id("")


class TestNegotiationSession:
    def test_initial_state(self):
        session = NegotiationSession(
            negotiation_id="neg_test",
            demand=DemandSnapshot(raw_intent="test"),
        )
        assert session.state == NegotiationState.CREATED
        assert session.center_rounds == 0
        assert session.participants == []
        assert session.plan_output is None

    def test_barrier_met_empty_participants(self):
        session = NegotiationSession(
            negotiation_id="neg_test",
            demand=DemandSnapshot(raw_intent="test"),
        )
        assert session.is_barrier_met is True  # vacuously true

    def test_barrier_not_met(self):
        session = NegotiationSession(
            negotiation_id="neg_test",
            demand=DemandSnapshot(raw_intent="test"),
            participants=[
                AgentParticipant(agent_id="a1", display_name="A1"),
                AgentParticipant(agent_id="a2", display_name="A2"),
            ],
        )
        assert session.is_barrier_met is False

    def test_barrier_met_all_replied(self):
        session = NegotiationSession(
            negotiation_id="neg_test",
            demand=DemandSnapshot(raw_intent="test"),
            participants=[
                AgentParticipant(agent_id="a1", display_name="A1", state=AgentState.REPLIED),
                AgentParticipant(agent_id="a2", display_name="A2", state=AgentState.EXITED),
            ],
        )
        assert session.is_barrier_met is True

    def test_tools_restricted(self):
        session = NegotiationSession(
            negotiation_id="neg_test",
            demand=DemandSnapshot(raw_intent="test"),
            center_rounds=5,  # max_center_rounds default is 5
        )
        assert session.tools_restricted is True

    def test_tools_not_restricted(self):
        session = NegotiationSession(
            negotiation_id="neg_test",
            demand=DemandSnapshot(raw_intent="test"),
            center_rounds=1,
        )
        assert session.tools_restricted is False

    def test_collected_offers(self):
        offer = Offer(agent_id="a1", content="I can help")
        session = NegotiationSession(
            negotiation_id="neg_test",
            demand=DemandSnapshot(raw_intent="test"),
            participants=[
                AgentParticipant(agent_id="a1", display_name="A1", offer=offer, state=AgentState.REPLIED),
                AgentParticipant(agent_id="a2", display_name="A2", state=AgentState.ACTIVE),
            ],
        )
        assert len(session.collected_offers) == 1
        assert session.collected_offers[0].content == "I can help"


class TestTraceChain:
    def test_add_entry(self):
        trace = TraceChain(negotiation_id="neg_test")
        trace.add_entry("formulation", input_summary="raw intent")
        assert len(trace.entries) == 1
        assert trace.entries[0].step == "formulation"

    def test_to_dict(self):
        trace = TraceChain(negotiation_id="neg_test")
        trace.add_entry("step1")
        trace.add_entry("step2")
        d = trace.to_dict()
        assert d["negotiation_id"] == "neg_test"
        assert len(d["entries"]) == 2
