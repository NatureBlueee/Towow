"""Tests for event definitions — validates event structure and factory functions."""

import pytest
from towow.core.events import (
    EventType,
    NegotiationEvent,
    formulation_ready,
    resonance_activated,
    offer_received,
    barrier_complete,
    center_tool_call,
    plan_ready,
    sub_negotiation_started,
)


class TestEventType:
    def test_all_nine_types_defined(self):
        assert len(EventType) == 9

    def test_v1_types(self):
        v1_types = [
            EventType.FORMULATION_READY,
            EventType.RESONANCE_ACTIVATED,
            EventType.OFFER_RECEIVED,
            EventType.BARRIER_COMPLETE,
            EventType.CENTER_TOOL_CALL,
            EventType.PLAN_READY,
            EventType.SUB_NEGOTIATION_STARTED,
        ]
        assert len(v1_types) == 7


class TestNegotiationEvent:
    def test_to_dict_structure(self):
        event = NegotiationEvent(
            event_type=EventType.PLAN_READY,
            negotiation_id="neg_123",
            data={"plan_text": "test plan"},
        )
        d = event.to_dict()
        assert d["event_type"] == "plan.ready"
        assert d["negotiation_id"] == "neg_123"
        assert "timestamp" in d
        assert d["data"]["plan_text"] == "test plan"


class TestEventFactories:
    def test_formulation_ready(self):
        event = formulation_ready("neg_1", "raw", "formulated")
        assert event.event_type == EventType.FORMULATION_READY
        assert event.data["raw_intent"] == "raw"
        assert event.data["formulated_text"] == "formulated"
        assert event.data["degraded"] is False
        assert event.data["degraded_reason"] == ""

    def test_formulation_ready_degraded(self):
        event = formulation_ready(
            "neg_1", "raw", "raw",
            degraded=True, degraded_reason="formulation_timeout",
        )
        assert event.data["degraded"] is True
        assert event.data["degraded_reason"] == "formulation_timeout"
        assert event.data["formulated_text"] == "raw"

    def test_resonance_activated(self):
        agents = [{"agent_id": "a1", "score": 0.9}]
        event = resonance_activated("neg_1", 1, agents)
        assert event.data["activated_count"] == 1

    def test_offer_received(self):
        event = offer_received("neg_1", "a1", "Alice", "I can help")
        assert event.data["agent_id"] == "a1"
        assert event.data["content"] == "I can help"

    def test_barrier_complete(self):
        event = barrier_complete("neg_1", 5, 4, 1)
        assert event.data["total_participants"] == 5
        assert event.data["offers_received"] == 4
        assert event.data["exited_count"] == 1

    def test_center_tool_call(self):
        event = center_tool_call("neg_1", "ask_agent", {"agent_id": "a1"}, 1)
        assert event.data["tool_name"] == "ask_agent"
        assert event.data["round_number"] == 1

    def test_plan_ready(self):
        event = plan_ready("neg_1", "Final plan", 2, ["a1", "a2"])
        assert event.data["plan_text"] == "Final plan"
        assert event.data["center_rounds"] == 2

    def test_sub_negotiation_started(self):
        event = sub_negotiation_started("neg_1", "sub_1", "Need designer")
        assert event.data["sub_negotiation_id"] == "sub_1"
