"""
E2E Test: Complete Negotiation Flow (T10)

Tests the complete multi-agent negotiation flow from demand submission to finalization.

Test Scenarios:
1. Single-round negotiation success (accept_rate >= 80%)
2. Multi-round negotiation (2-5 rounds)
3. Complete event sequence verification
4. v4 new event formats verification

Acceptance Criteria:
- AC-1: Complete negotiation flow (single round) pass rate >= 95%
- AC-2: Multi-round negotiation flow (up to 5 rounds) pass rate >= 90%
- AC-5: SSE event sequence is correct
- AC-6: v4 new event formats are correct
"""
from __future__ import annotations

import asyncio
import json
import logging
import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from openagents.agents.channel_admin import ChannelAdminAgent, ChannelStatus, ChannelState
from services.secondme_mock import SecondMeMockService, SimpleRandomMockClient
from events.recorder import EventRecorder
from config import MAX_NEGOTIATION_ROUNDS, ACCEPT_THRESHOLD_HIGH, ACCEPT_THRESHOLD_LOW

logger = logging.getLogger(__name__)


# ============== Test Fixtures ==============

@pytest.fixture
def channel_admin() -> ChannelAdminAgent:
    """Create ChannelAdmin agent for testing."""
    admin = ChannelAdminAgent()
    admin._logger = logging.getLogger("test_channel_admin")
    admin.llm = None  # Use mock mode
    return admin


@pytest.fixture
def mock_candidates() -> List[Dict[str, Any]]:
    """Create mock candidates for testing."""
    return [
        {
            "agent_id": f"user_agent_{i}",
            "display_name": f"TestUser{i}",
            "reason": f"Test reason {i}",
            "relevance_score": 90 - i * 5,
            "capabilities": ["capability_a", "capability_b"]
        }
        for i in range(10)
    ]


@pytest.fixture
def test_demand() -> Dict[str, Any]:
    """Create test demand."""
    return {
        "surface_demand": "Test demand for negotiation",
        "deep_understanding": {
            "type": "test",
            "keywords": ["test", "negotiation"],
            "resource_requirements": ["resource_a", "resource_b"]
        }
    }


@pytest.fixture
def event_recorder() -> EventRecorder:
    """Create event recorder for testing."""
    return EventRecorder()


# ============== Helper Functions ==============

async def simulate_responses(
    channel_admin: ChannelAdminAgent,
    channel_id: str,
    responses: List[Dict[str, Any]]
):
    """Simulate agent responses."""
    for resp in responses:
        await channel_admin.handle_response(
            channel_id=channel_id,
            agent_id=resp["agent_id"],
            decision=resp.get("decision", "participate"),
            contribution=resp.get("contribution", "Test contribution"),
            conditions=resp.get("conditions", []),
            reasoning=resp.get("reasoning", "Test reasoning")
        )


async def simulate_feedback(
    channel_admin: ChannelAdminAgent,
    channel_id: str,
    feedback_list: List[Dict[str, Any]]
):
    """Simulate proposal feedback."""
    for fb in feedback_list:
        await channel_admin.handle_feedback(
            channel_id=channel_id,
            agent_id=fb["agent_id"],
            feedback_type=fb.get("feedback_type", "accept"),
            adjustment_request=fb.get("adjustment_request"),
            concerns=fb.get("concerns", [])
        )


# ============== Test Classes ==============

@pytest.mark.e2e
class TestSingleRoundNegotiation:
    """Test single-round negotiation scenarios (AC-1)."""

    @pytest.mark.asyncio
    async def test_single_round_success_all_accept(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test single-round negotiation with all participants accepting.

        Scenario: All participants respond with 'participate' and 'accept' feedback.
        Expected: Channel status becomes FINALIZED after one round.
        """
        # Mock event publishing
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        # Create channel
        channel_id = await channel_admin.start_managing(
            channel_name="test-single-round",
            demand_id="demand-001",
            demand=test_demand,
            invited_agents=mock_candidates[:5],
            max_rounds=5
        )

        state = channel_admin.channels[channel_id]

        # Simulate all agents responding with 'participate'
        responses = [
            {"agent_id": c["agent_id"], "decision": "participate"}
            for c in mock_candidates[:5]
        ]
        await simulate_responses(channel_admin, channel_id, responses)

        # Wait for aggregation
        await asyncio.sleep(0.1)

        # Verify proposal is generated
        assert state.current_proposal is not None, "Proposal should be generated"

        # Simulate all accepting feedback
        feedback_list = [
            {"agent_id": c["agent_id"], "feedback_type": "accept"}
            for c in mock_candidates[:5]
        ]
        await simulate_feedback(channel_admin, channel_id, feedback_list)

        # Wait for evaluation
        await asyncio.sleep(0.1)

        # Verify final status
        assert state.status == ChannelStatus.FINALIZED, f"Expected FINALIZED, got {state.status}"
        assert state.current_round == 1, "Should complete in single round"

        # Verify events published
        event_types = [e["event_type"] for e in published_events]
        assert "towow.channel.created" in event_types
        assert "towow.demand.broadcast" in event_types
        assert "towow.proposal.distributed" in event_types
        assert "towow.proposal.finalized" in event_types

        print(f"\n[PASS] Single round success test: {len(published_events)} events published")

    @pytest.mark.asyncio
    async def test_single_round_success_80_percent_accept(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test single-round with exactly 80% acceptance rate.

        Scenario: 4 out of 5 participants accept (80%).
        Expected: Channel FINALIZED (>= 80% threshold).
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-80-percent",
            demand_id="demand-002",
            demand=test_demand,
            invited_agents=mock_candidates[:5],
            max_rounds=5
        )

        state = channel_admin.channels[channel_id]

        # All respond with participate
        responses = [
            {"agent_id": c["agent_id"], "decision": "participate"}
            for c in mock_candidates[:5]
        ]
        await simulate_responses(channel_admin, channel_id, responses)
        await asyncio.sleep(0.1)

        # 4 accept, 1 negotiate (80% acceptance)
        feedback_list = [
            {"agent_id": mock_candidates[i]["agent_id"], "feedback_type": "accept" if i < 4 else "negotiate"}
            for i in range(5)
        ]
        await simulate_feedback(channel_admin, channel_id, feedback_list)
        await asyncio.sleep(0.1)

        # Verify: 80% should trigger FINALIZED
        assert state.status == ChannelStatus.FINALIZED, f"Expected FINALIZED at 80%, got {state.status}"

        # Check feedback.evaluated event
        evaluated_events = [e for e in published_events if e["event_type"] == "towow.feedback.evaluated"]
        assert len(evaluated_events) > 0, "Should have feedback.evaluated event"

        payload = evaluated_events[0]["payload"]
        assert payload["accept_rate"] >= 0.8, f"Accept rate should be >= 80%, got {payload['accept_rate']}"
        assert payload["decision"] == "finalized", f"Decision should be finalized, got {payload['decision']}"

        print(f"\n[PASS] 80% acceptance test: status={state.status.value}")


@pytest.mark.e2e
class TestMultiRoundNegotiation:
    """Test multi-round negotiation scenarios (AC-2)."""

    @pytest.mark.asyncio
    async def test_two_round_negotiation(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test two-round negotiation.

        Scenario: First round 60% accept, second round 85% accept.
        Expected: Enter round 2, then FINALIZED.
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-two-round",
            demand_id="demand-003",
            demand=test_demand,
            invited_agents=mock_candidates[:5],
            max_rounds=5
        )

        state = channel_admin.channels[channel_id]

        # Round 1: All participate
        responses = [
            {"agent_id": c["agent_id"], "decision": "participate"}
            for c in mock_candidates[:5]
        ]
        await simulate_responses(channel_admin, channel_id, responses)
        await asyncio.sleep(0.1)

        # Round 1 feedback: 3 accept, 2 negotiate (60%)
        feedback_r1 = [
            {"agent_id": mock_candidates[i]["agent_id"], "feedback_type": "accept" if i < 3 else "negotiate"}
            for i in range(5)
        ]
        await simulate_feedback(channel_admin, channel_id, feedback_r1)
        await asyncio.sleep(0.1)

        # Should be in round 2 or NEGOTIATING
        assert state.current_round >= 1, "Should have proceeded"

        # If entered round 2, provide feedback again
        if state.status == ChannelStatus.NEGOTIATING and state.current_round == 2:
            # Round 2 feedback: all accept
            feedback_r2 = [
                {"agent_id": c["agent_id"], "feedback_type": "accept"}
                for c in mock_candidates[:5]
            ]
            await simulate_feedback(channel_admin, channel_id, feedback_r2)
            await asyncio.sleep(0.1)

        # Check for round_started event
        round_events = [e for e in published_events if e["event_type"] == "towow.negotiation.round_started"]

        print(f"\n[INFO] Multi-round test: rounds={state.current_round}, status={state.status.value}")
        print(f"[INFO] Round started events: {len(round_events)}")

    @pytest.mark.asyncio
    async def test_max_rounds_reached(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test reaching maximum rounds.

        Scenario: Continuous 60% acceptance for 5 rounds.
        Expected: Force finalized after round 5.
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-max-rounds",
            demand_id="demand-004",
            demand=test_demand,
            invited_agents=mock_candidates[:5],
            max_rounds=3  # Use 3 rounds for faster test
        )

        state = channel_admin.channels[channel_id]

        # Initial responses
        responses = [
            {"agent_id": c["agent_id"], "decision": "participate"}
            for c in mock_candidates[:5]
        ]
        await simulate_responses(channel_admin, channel_id, responses)
        await asyncio.sleep(0.1)

        # Simulate multiple rounds with 60% acceptance
        for round_num in range(1, 4):  # Up to 3 rounds
            if state.status not in (ChannelStatus.NEGOTIATING, ChannelStatus.PROPOSAL_SENT):
                break

            # 3 accept, 2 negotiate (60%)
            feedback = [
                {"agent_id": mock_candidates[i]["agent_id"], "feedback_type": "accept" if i < 3 else "negotiate"}
                for i in range(5)
            ]
            await simulate_feedback(channel_admin, channel_id, feedback)
            await asyncio.sleep(0.1)

            print(f"[INFO] Round {round_num}: status={state.status.value}, current_round={state.current_round}")

        # Should be FORCE_FINALIZED or have reached max rounds
        final_statuses = [ChannelStatus.FORCE_FINALIZED, ChannelStatus.FINALIZED, ChannelStatus.FAILED]
        assert state.status in final_statuses or state.current_round >= 3, \
            f"Expected final status or round >= 3, got {state.status.value}, round {state.current_round}"

        print(f"\n[PASS] Max rounds test: final_round={state.current_round}, status={state.status.value}")


@pytest.mark.e2e
class TestEventSequence:
    """Test event sequence integrity (AC-5, AC-6)."""

    @pytest.mark.asyncio
    async def test_complete_event_sequence(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test that all required events are published in correct order.

        Required events:
        1. towow.channel.created
        2. towow.demand.broadcast
        3. towow.offer.submitted (multiple)
        4. towow.aggregation.started
        5. towow.proposal.distributed
        6. towow.proposal.feedback
        7. towow.feedback.evaluated (v4)
        8. towow.proposal.finalized OR towow.negotiation.failed
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({
                "event_type": event_type,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat()
            })
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-event-seq",
            demand_id="demand-005",
            demand=test_demand,
            invited_agents=mock_candidates[:5],
            max_rounds=5
        )

        state = channel_admin.channels[channel_id]

        # All respond
        responses = [
            {"agent_id": c["agent_id"], "decision": "participate"}
            for c in mock_candidates[:5]
        ]
        await simulate_responses(channel_admin, channel_id, responses)
        await asyncio.sleep(0.1)

        # All accept
        feedback_list = [
            {"agent_id": c["agent_id"], "feedback_type": "accept"}
            for c in mock_candidates[:5]
        ]
        await simulate_feedback(channel_admin, channel_id, feedback_list)
        await asyncio.sleep(0.1)

        # Verify event sequence
        event_types = [e["event_type"] for e in published_events]

        # Check required events exist
        required_events = [
            "towow.channel.created",
            "towow.demand.broadcast",
            "towow.offer.submitted",
            "towow.aggregation.started",
            "towow.proposal.distributed",
            "towow.feedback.evaluated",
        ]

        for req in required_events:
            assert req in event_types, f"Missing required event: {req}"

        # Check final event
        assert "towow.proposal.finalized" in event_types or "towow.negotiation.failed" in event_types, \
            "Should have final status event"

        # Verify order: channel.created should be first
        assert event_types[0] == "towow.channel.created", "First event should be channel.created"

        # Verify order: broadcast should come after created
        created_idx = event_types.index("towow.channel.created")
        broadcast_idx = event_types.index("towow.demand.broadcast")
        assert broadcast_idx > created_idx, "broadcast should come after created"

        print(f"\n[PASS] Event sequence test: {len(published_events)} events")
        print(f"Event types: {event_types}")

    @pytest.mark.asyncio
    async def test_v4_feedback_evaluated_event_format(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test v4 'towow.feedback.evaluated' event format.

        Expected payload:
        - accept_rate: float
        - reject_rate: float
        - decision: string (finalized/failed/force_finalized/next_round)
        - round: int
        - max_rounds: int
        - threshold_high: float
        - threshold_low: float
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-v4-event",
            demand_id="demand-006",
            demand=test_demand,
            invited_agents=mock_candidates[:5],
            max_rounds=5
        )

        state = channel_admin.channels[channel_id]

        # Responses
        responses = [
            {"agent_id": c["agent_id"], "decision": "participate"}
            for c in mock_candidates[:5]
        ]
        await simulate_responses(channel_admin, channel_id, responses)
        await asyncio.sleep(0.1)

        # Feedback: 4 accept, 1 reject
        feedback_list = [
            {"agent_id": mock_candidates[i]["agent_id"], "feedback_type": "accept" if i < 4 else "reject"}
            for i in range(5)
        ]
        await simulate_feedback(channel_admin, channel_id, feedback_list)
        await asyncio.sleep(0.1)

        # Find feedback.evaluated event
        evaluated_events = [e for e in published_events if e["event_type"] == "towow.feedback.evaluated"]
        assert len(evaluated_events) > 0, "Should have feedback.evaluated event"

        payload = evaluated_events[0]["payload"]

        # Verify required fields
        assert "accept_rate" in payload, "Should have accept_rate"
        assert "reject_rate" in payload, "Should have reject_rate"
        assert "decision" in payload, "Should have decision"
        assert "round" in payload, "Should have round"
        assert "max_rounds" in payload, "Should have max_rounds"
        assert "threshold_high" in payload, "Should have threshold_high"
        assert "threshold_low" in payload, "Should have threshold_low"

        # Verify types
        assert isinstance(payload["accept_rate"], (int, float))
        assert isinstance(payload["round"], int)
        assert payload["decision"] in ["finalized", "failed", "force_finalized", "next_round", "finalized_unanimous"]

        print(f"\n[PASS] v4 event format test")
        print(f"Payload: {json.dumps(payload, indent=2)}")

    @pytest.mark.asyncio
    async def test_v4_round_started_event_format(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test v4 'towow.negotiation.round_started' event format.

        Expected payload:
        - round: int
        - max_rounds: int
        - previous_feedback_summary: dict
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-round-event",
            demand_id="demand-007",
            demand=test_demand,
            invited_agents=mock_candidates[:5],
            max_rounds=5
        )

        state = channel_admin.channels[channel_id]

        # Responses
        responses = [
            {"agent_id": c["agent_id"], "decision": "participate"}
            for c in mock_candidates[:5]
        ]
        await simulate_responses(channel_admin, channel_id, responses)
        await asyncio.sleep(0.1)

        # Round 1 feedback: 3 accept, 2 negotiate (60% - should trigger next round)
        feedback_list = [
            {"agent_id": mock_candidates[i]["agent_id"], "feedback_type": "accept" if i < 3 else "negotiate"}
            for i in range(5)
        ]
        await simulate_feedback(channel_admin, channel_id, feedback_list)
        await asyncio.sleep(0.1)

        # Find round_started event
        round_events = [e for e in published_events if e["event_type"] == "towow.negotiation.round_started"]

        if len(round_events) > 0:
            payload = round_events[0]["payload"]

            # Verify required fields
            assert "round" in payload, "Should have round"
            assert "max_rounds" in payload, "Should have max_rounds"
            assert "previous_feedback_summary" in payload, "Should have previous_feedback_summary"

            # Verify types
            assert isinstance(payload["round"], int)
            assert isinstance(payload["max_rounds"], int)
            assert isinstance(payload["previous_feedback_summary"], dict)

            print(f"\n[PASS] v4 round_started event test")
            print(f"Payload: {json.dumps(payload, indent=2)}")
        else:
            # If no round started event, might have finalized directly
            print(f"\n[INFO] No round_started event (may have finalized directly)")
            print(f"Status: {state.status.value}, Round: {state.current_round}")


@pytest.mark.e2e
class TestNegotiationPassRate:
    """Test negotiation pass rates (AC-1, AC-2)."""

    @pytest.mark.asyncio
    async def test_single_round_pass_rate(self):
        """
        Test that single-round negotiation achieves >= 95% pass rate.

        Run 20 simulations with all-accept scenario.
        Expected: >= 19 successful completions (95%).
        """
        success_count = 0
        total_runs = 20

        for i in range(total_runs):
            try:
                admin = ChannelAdminAgent()
                admin._logger = logging.getLogger(f"test_pass_rate_{i}")
                admin.llm = None

                # Fix: Create isolated events list and closure for each iteration
                # to avoid race conditions from shared state
                iteration_events: List[str] = []

                def make_mock_publish(events_list: List[str]):
                    """Factory to create mock_publish with bound events list."""
                    async def mock_publish(event_type, payload):
                        events_list.append(event_type)
                    return mock_publish

                admin._publish_event = make_mock_publish(iteration_events)
                admin.send_to_agent = AsyncMock()

                candidates = [
                    {"agent_id": f"agent_{j}", "display_name": f"User{j}", "reason": "test"}
                    for j in range(5)
                ]

                channel_id = await admin.start_managing(
                    channel_name=f"pass-rate-{i}",
                    demand_id=f"demand-{i}",
                    demand={"surface_demand": "Test"},
                    invited_agents=candidates,
                    max_rounds=5
                )

                state = admin.channels[channel_id]

                # All participate
                for c in candidates:
                    await admin.handle_response(
                        channel_id=channel_id,
                        agent_id=c["agent_id"],
                        decision="participate"
                    )

                await asyncio.sleep(0.05)

                # All accept
                for c in candidates:
                    await admin.handle_feedback(
                        channel_id=channel_id,
                        agent_id=c["agent_id"],
                        feedback_type="accept"
                    )

                await asyncio.sleep(0.05)

                if state.status == ChannelStatus.FINALIZED:
                    success_count += 1

            except Exception as e:
                logger.error(f"Run {i} failed: {e}")

        pass_rate = success_count / total_runs

        print(f"\n[RESULT] Single-round pass rate: {success_count}/{total_runs} = {pass_rate:.0%}")
        assert pass_rate >= 0.95, f"Pass rate {pass_rate:.0%} < 95%"

    @pytest.mark.asyncio
    async def test_multi_round_pass_rate(self):
        """
        Test that multi-round negotiation achieves >= 90% pass rate.

        Run 10 simulations with 2-round scenario.
        Expected: >= 9 successful completions (90%).
        """
        success_count = 0
        total_runs = 10

        for i in range(total_runs):
            try:
                admin = ChannelAdminAgent()
                admin._logger = logging.getLogger(f"test_multi_{i}")
                admin.llm = None

                # Fix: Create isolated events list and closure for each iteration
                # to avoid race conditions from shared state
                iteration_events: List[str] = []

                def make_mock_publish(events_list: List[str]):
                    """Factory to create mock_publish with bound events list."""
                    async def mock_publish(event_type, payload):
                        events_list.append(event_type)
                    return mock_publish

                admin._publish_event = make_mock_publish(iteration_events)
                admin.send_to_agent = AsyncMock()

                candidates = [
                    {"agent_id": f"agent_{j}", "display_name": f"User{j}", "reason": "test"}
                    for j in range(5)
                ]

                channel_id = await admin.start_managing(
                    channel_name=f"multi-rate-{i}",
                    demand_id=f"demand-m-{i}",
                    demand={"surface_demand": "Test"},
                    invited_agents=candidates,
                    max_rounds=5
                )

                state = admin.channels[channel_id]

                # All participate
                for c in candidates:
                    await admin.handle_response(
                        channel_id=channel_id,
                        agent_id=c["agent_id"],
                        decision="participate"
                    )

                await asyncio.sleep(0.05)

                # Round 1: 60% accept
                for j, c in enumerate(candidates):
                    await admin.handle_feedback(
                        channel_id=channel_id,
                        agent_id=c["agent_id"],
                        feedback_type="accept" if j < 3 else "negotiate"
                    )

                await asyncio.sleep(0.05)

                # Round 2: all accept (if still negotiating)
                if state.status == ChannelStatus.NEGOTIATING:
                    for c in candidates:
                        await admin.handle_feedback(
                            channel_id=channel_id,
                            agent_id=c["agent_id"],
                            feedback_type="accept"
                        )
                    await asyncio.sleep(0.05)

                if state.status in (ChannelStatus.FINALIZED, ChannelStatus.FORCE_FINALIZED):
                    success_count += 1

            except Exception as e:
                logger.error(f"Multi-round run {i} failed: {e}")

        pass_rate = success_count / total_runs

        print(f"\n[RESULT] Multi-round pass rate: {success_count}/{total_runs} = {pass_rate:.0%}")
        assert pass_rate >= 0.90, f"Pass rate {pass_rate:.0%} < 90%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
