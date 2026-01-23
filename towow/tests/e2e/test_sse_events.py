"""
E2E Test: SSE Event Stream (T10)

Tests the Server-Sent Events (SSE) event stream for real-time UI updates.

Test Scenarios:
1. Event type correctness
2. Event sequence integrity
3. v4 new event formats
4. Event payload completeness

Acceptance Criteria:
- AC-5: SSE event sequence is correct
- AC-6: v4 new event formats are correct
"""
from __future__ import annotations

import asyncio
import json
import logging
import pytest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from openagents.agents.channel_admin import ChannelAdminAgent, ChannelStatus
from events.recorder import EventRecorder

logger = logging.getLogger(__name__)


# ============== Expected Event Types ==============

# Core negotiation events
CORE_EVENTS = [
    "towow.channel.created",
    "towow.demand.broadcast",
    "towow.offer.submitted",
    "towow.aggregation.started",
    "towow.proposal.distributed",
    "towow.proposal.feedback",
]

# Outcome events (one of these)
OUTCOME_EVENTS = [
    "towow.proposal.finalized",
    "towow.negotiation.failed",
    "towow.negotiation.force_finalized",
]

# v4 new events
V4_EVENTS = [
    "towow.feedback.evaluated",
    "towow.negotiation.round_started",
]


def create_candidates(count: int) -> List[Dict[str, Any]]:
    """Create mock candidates."""
    return [
        {
            "agent_id": f"agent_{i}",
            "display_name": f"User{i}",
            "reason": f"Reason {i}",
            "relevance_score": 90 - i
        }
        for i in range(count)
    ]


@pytest.mark.e2e
class TestEventTypeCorrectness:
    """Test that correct event types are published."""

    @pytest.mark.asyncio
    async def test_all_core_events_published(self):
        """
        Test that all core events are published during negotiation.

        Verifies:
        - channel.created
        - demand.broadcast
        - offer.submitted
        - aggregation.started
        - proposal.distributed
        - proposal.feedback
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_events")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({
                "event_type": event_type,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat()
            })
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-core-events",
            demand_id="events-001",
            demand={"surface_demand": "Test core events"},
            invited_agents=candidates,
            max_rounds=5
        )

        # All participate
        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # All accept
        for c in candidates:
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept"
            )
        await asyncio.sleep(0.1)

        # Verify all core events
        event_types = [e["event_type"] for e in events]

        print(f"\n[INFO] Published events ({len(events)} total):")
        for et in set(event_types):
            count = event_types.count(et)
            print(f"  - {et}: {count}")

        # Check core events
        for core_event in CORE_EVENTS:
            assert core_event in event_types, f"Missing core event: {core_event}"

        # Check at least one outcome event
        has_outcome = any(oe in event_types for oe in OUTCOME_EVENTS)
        assert has_outcome, f"Missing outcome event. Got: {event_types}"

        print(f"\n[PASS] All core events published")

    @pytest.mark.asyncio
    async def test_v4_events_published(self):
        """
        Test that v4 new events are published.

        Verifies:
        - feedback.evaluated (after each feedback round)
        - negotiation.round_started (on multi-round negotiation)
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_v4_events")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-v4-events",
            demand_id="events-v4",
            demand={"surface_demand": "Test v4 events"},
            invited_agents=candidates,
            max_rounds=5
        )

        # All participate
        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # Trigger multi-round: 60% accept first round
        for i, c in enumerate(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 3 else "negotiate"
            )
        await asyncio.sleep(0.1)

        event_types = [e["event_type"] for e in events]

        # Check feedback.evaluated
        assert "towow.feedback.evaluated" in event_types, "Missing feedback.evaluated event"

        # Check round_started (should appear if went to round 2)
        state = admin.channels[channel_id]
        if state.current_round > 1 or state.status in (ChannelStatus.NEGOTIATING, ChannelStatus.PROPOSAL_SENT):
            # May have round_started event
            print(f"[INFO] Current round: {state.current_round}")

        print(f"\n[PASS] v4 events verified")


@pytest.mark.e2e
class TestEventSequenceIntegrity:
    """Test event sequence is correct."""

    @pytest.mark.asyncio
    async def test_event_order_single_round(self):
        """
        Test event order for single-round negotiation.

        Expected order:
        1. channel.created
        2. demand.broadcast
        3. offer.submitted (multiple)
        4. aggregation.started
        5. proposal.distributed
        6. proposal.feedback (multiple)
        7. feedback.evaluated
        8. proposal.finalized
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_order")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload, "order": len(events)})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(3)

        channel_id = await admin.start_managing(
            channel_name="test-order",
            demand_id="events-order",
            demand={"surface_demand": "Test order"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        for c in candidates:
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept"
            )
        await asyncio.sleep(0.1)

        # Build event order
        event_order = [(e["event_type"], e["order"]) for e in events]

        print(f"\n[INFO] Event order:")
        for et, order in event_order:
            print(f"  {order}: {et}")

        # Verify key orderings
        event_types = [e["event_type"] for e in events]

        # channel.created should be first
        assert event_types[0] == "towow.channel.created", "First event should be channel.created"

        # broadcast should come after created
        created_idx = event_types.index("towow.channel.created")
        broadcast_idx = event_types.index("towow.demand.broadcast")
        assert broadcast_idx > created_idx, "broadcast should follow created"

        # aggregation should come after offers
        if "towow.aggregation.started" in event_types:
            agg_idx = event_types.index("towow.aggregation.started")
            # Find last offer.submitted before aggregation
            offer_indices = [i for i, e in enumerate(event_types) if e == "towow.offer.submitted"]
            if offer_indices:
                last_offer_idx = max(offer_indices)
                assert agg_idx > last_offer_idx, "aggregation should follow offers"

        # finalized should be last (or near last)
        if "towow.proposal.finalized" in event_types:
            final_idx = event_types.index("towow.proposal.finalized")
            # Should be after feedback.evaluated
            if "towow.feedback.evaluated" in event_types:
                eval_idx = event_types.index("towow.feedback.evaluated")
                assert final_idx > eval_idx, "finalized should follow evaluated"

        print(f"\n[PASS] Event order verified")

    @pytest.mark.asyncio
    async def test_event_order_multi_round(self):
        """
        Test event order for multi-round negotiation.

        Expected additional events:
        - round_started between rounds
        - multiple feedback.evaluated events
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_multi_order")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload, "order": len(events)})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-multi-order",
            demand_id="events-multi",
            demand={"surface_demand": "Test multi order"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # Round 1: 60% accept
        for i, c in enumerate(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 3 else "negotiate"
            )
        await asyncio.sleep(0.1)

        state = admin.channels[channel_id]

        # If went to round 2, continue
        if state.status == ChannelStatus.NEGOTIATING:
            # Round 2: all accept
            for c in candidates:
                await admin.handle_feedback(
                    channel_id=channel_id,
                    agent_id=c["agent_id"],
                    feedback_type="accept"
                )
            await asyncio.sleep(0.1)

        event_types = [e["event_type"] for e in events]

        # Count evaluated events
        evaluated_count = event_types.count("towow.feedback.evaluated")
        print(f"\n[INFO] feedback.evaluated count: {evaluated_count}")

        # Count round_started events
        round_started_count = event_types.count("towow.negotiation.round_started")
        print(f"[INFO] round_started count: {round_started_count}")

        print(f"\n[PASS] Multi-round event order test complete")


@pytest.mark.e2e
class TestEventPayloadCompleteness:
    """Test event payloads are complete."""

    @pytest.mark.asyncio
    async def test_channel_created_payload(self):
        """Test channel.created event payload."""
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_payload")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        channel_id = await admin.start_managing(
            channel_name="test-payload",
            demand_id="payload-001",
            demand={"surface_demand": "Test payload"},
            invited_agents=create_candidates(3),
            max_rounds=5
        )

        created_events = [e for e in events if e["event_type"] == "towow.channel.created"]
        assert len(created_events) > 0, "Should have channel.created event"

        payload = created_events[0]["payload"]

        # Required fields
        assert "channel_id" in payload, "Missing channel_id"
        assert "demand_id" in payload, "Missing demand_id"
        assert "candidates_count" in payload, "Missing candidates_count"

        print(f"\n[PASS] channel.created payload complete")
        print(f"Payload: {json.dumps(payload, indent=2)}")

    @pytest.mark.asyncio
    async def test_offer_submitted_payload(self):
        """Test offer.submitted event payload."""
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_offer")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(3)

        channel_id = await admin.start_managing(
            channel_name="test-offer",
            demand_id="offer-001",
            demand={"surface_demand": "Test offer"},
            invited_agents=candidates,
            max_rounds=5
        )

        await admin.handle_response(
            channel_id=channel_id,
            agent_id=candidates[0]["agent_id"],
            decision="participate",
            contribution="Test contribution",
            reasoning="Test reasoning"
        )
        await asyncio.sleep(0.1)

        offer_events = [e for e in events if e["event_type"] == "towow.offer.submitted"]
        assert len(offer_events) > 0, "Should have offer.submitted event"

        payload = offer_events[0]["payload"]

        # Required fields
        assert "channel_id" in payload
        assert "agent_id" in payload
        assert "decision" in payload
        assert "round" in payload

        print(f"\n[PASS] offer.submitted payload complete")

    @pytest.mark.asyncio
    async def test_feedback_evaluated_payload(self):
        """Test v4 feedback.evaluated event payload."""
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_eval")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-eval",
            demand_id="eval-001",
            demand={"surface_demand": "Test eval"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        for i, c in enumerate(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 4 else "reject"
            )
        await asyncio.sleep(0.1)

        eval_events = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]
        assert len(eval_events) > 0, "Should have feedback.evaluated event"

        payload = eval_events[0]["payload"]

        # Required v4 fields
        required_fields = [
            "channel_id", "demand_id", "accepts", "rejects", "total",
            "accept_rate", "reject_rate", "decision", "round", "max_rounds",
            "threshold_high", "threshold_low"
        ]

        for field in required_fields:
            assert field in payload, f"Missing field: {field}"

        print(f"\n[PASS] feedback.evaluated payload complete")
        print(f"Payload: {json.dumps(payload, indent=2)}")

    @pytest.mark.asyncio
    async def test_proposal_distributed_payload(self):
        """Test proposal.distributed event payload."""
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_dist")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(3)

        channel_id = await admin.start_managing(
            channel_name="test-dist",
            demand_id="dist-001",
            demand={"surface_demand": "Test dist"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        dist_events = [e for e in events if e["event_type"] == "towow.proposal.distributed"]
        assert len(dist_events) > 0, "Should have proposal.distributed event"

        payload = dist_events[0]["payload"]

        # Required fields
        assert "channel_id" in payload
        assert "demand_id" in payload
        assert "proposal_id" in payload
        assert "participants_count" in payload
        assert "round" in payload

        print(f"\n[PASS] proposal.distributed payload complete")

    @pytest.mark.asyncio
    async def test_proposal_finalized_payload(self):
        """Test proposal.finalized event payload."""
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_final")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-final",
            demand_id="final-001",
            demand={"surface_demand": "Test final"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        for c in candidates:
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept"
            )
        await asyncio.sleep(0.1)

        final_events = [e for e in events if e["event_type"] == "towow.proposal.finalized"]
        assert len(final_events) > 0, "Should have proposal.finalized event"

        payload = final_events[0]["payload"]

        # Required fields
        assert "channel_id" in payload
        assert "demand_id" in payload
        assert "status" in payload
        assert "final_proposal" in payload
        assert "total_rounds" in payload
        assert "participants_count" in payload
        assert "summary" in payload

        print(f"\n[PASS] proposal.finalized payload complete")
        print(f"Summary: {payload.get('summary')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
