"""Tests for event definitions — validates event structure and factory functions.

Updated for PLAN-003:
- resonance_activated: filtered_agents support
- plan_ready: plan_json is now required
"""

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

    def test_to_dict_has_event_id(self):
        event = NegotiationEvent(
            event_type=EventType.PLAN_READY,
            negotiation_id="neg_123",
            data={},
        )
        d = event.to_dict()
        assert "event_id" in d
        assert d["event_id"].startswith("evt_")


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
        assert event.data["agents"] == agents
        assert event.data["filtered_agents"] == []

    def test_resonance_activated_with_filtered_agents(self):
        """resonance_activated should include filtered_agents in data."""
        agents = [
            {"agent_id": "a1", "display_name": "Alice", "resonance_score": 0.9},
        ]
        filtered = [
            {"agent_id": "a2", "display_name": "Bob", "resonance_score": 0.3},
            {"agent_id": "a3", "display_name": "Carol", "resonance_score": 0.1},
        ]
        event = resonance_activated("neg_1", 1, agents, filtered_agents=filtered)
        assert event.data["activated_count"] == 1
        assert event.data["agents"] == agents
        assert event.data["filtered_agents"] == filtered
        assert len(event.data["filtered_agents"]) == 2

    def test_resonance_activated_filtered_agents_default_empty(self):
        """When filtered_agents is not provided, it defaults to empty list."""
        agents = [{"agent_id": "a1", "resonance_score": 0.9}]
        event = resonance_activated("neg_1", 1, agents)
        assert event.data["filtered_agents"] == []

    def test_resonance_activated_serialization(self):
        """resonance_activated event should serialize correctly with filtered_agents."""
        agents = [{"agent_id": "a1", "display_name": "Alice", "resonance_score": 0.9}]
        filtered = [{"agent_id": "a2", "display_name": "Bob", "resonance_score": 0.2}]
        event = resonance_activated("neg_1", 1, agents, filtered_agents=filtered)
        d = event.to_dict()
        assert d["event_type"] == "resonance.activated"
        assert d["data"]["agents"] == agents
        assert d["data"]["filtered_agents"] == filtered
        assert d["data"]["activated_count"] == 1

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

    def test_plan_ready_with_plan_json(self):
        """plan_ready now requires plan_json (always carried)."""
        plan_json = {
            "summary": "Test plan",
            "participants": [{"agent_id": "a1", "display_name": "Alice", "role_in_plan": "developer"}],
            "tasks": [{"id": "t1", "title": "Build API", "assignee_id": "a1", "prerequisites": [], "status": "pending"}],
            "topology": {"edges": []},
        }
        event = plan_ready("neg_1", "Final plan", 2, ["a1", "a2"], plan_json=plan_json)
        assert event.data["plan_text"] == "Final plan"
        assert event.data["center_rounds"] == 2
        assert event.data["participating_agents"] == ["a1", "a2"]
        assert event.data["plan_json"] == plan_json
        assert event.data["plan_json"]["tasks"][0]["title"] == "Build API"

    def test_plan_ready_serialization_includes_plan_json(self):
        """plan_ready event should always serialize with plan_json in data."""
        plan_json = {
            "summary": "Plan summary",
            "participants": [],
            "tasks": [{"id": "t1", "title": "Task 1", "assignee_id": "a1", "prerequisites": [], "status": "pending"}],
        }
        event = plan_ready("neg_1", "Plan text", 1, ["a1"], plan_json=plan_json)
        d = event.to_dict()
        assert "plan_json" in d["data"]
        assert d["data"]["plan_json"]["summary"] == "Plan summary"

    def test_sub_negotiation_started(self):
        event = sub_negotiation_started("neg_1", "sub_1", "Need designer")
        assert event.data["sub_negotiation_id"] == "sub_1"
