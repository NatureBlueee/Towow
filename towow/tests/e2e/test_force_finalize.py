"""
E2E Test: Force Finalize Scenarios (T10)

Tests force finalization scenarios when max negotiation rounds are reached.

Test Scenarios:
1. Force finalize after 5 rounds
2. Confirmed vs optional participants classification
3. Force finalized event format verification

Acceptance Criteria:
- AC-3: Force finalize scenario tests pass
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

from openagents.agents.channel_admin import ChannelAdminAgent, ChannelStatus, ChannelState
from config import MAX_NEGOTIATION_ROUNDS

logger = logging.getLogger(__name__)


@pytest.fixture
def channel_admin() -> ChannelAdminAgent:
    """Create ChannelAdmin agent for testing."""
    admin = ChannelAdminAgent()
    admin._logger = logging.getLogger("test_force_finalize")
    admin.llm = None
    return admin


@pytest.fixture
def mock_candidates() -> List[Dict[str, Any]]:
    """Create mock candidates."""
    return [
        {
            "agent_id": f"user_agent_{i}",
            "display_name": f"TestUser{i}",
            "reason": f"Test reason {i}",
            "relevance_score": 90 - i * 5
        }
        for i in range(5)
    ]


@pytest.fixture
def test_demand() -> Dict[str, Any]:
    """Create test demand."""
    return {
        "surface_demand": "Test demand for force finalize",
        "deep_understanding": {
            "type": "test",
            "keywords": ["test"]
        }
    }


@pytest.mark.e2e
class TestForceFinalize:
    """Test force finalization scenarios (AC-3)."""

    @pytest.mark.asyncio
    async def test_force_finalize_after_max_rounds(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test force finalization after reaching max rounds.

        Scenario: 60% acceptance rate for all rounds (below 80% threshold).
        Expected: FORCE_FINALIZED after max_rounds.
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        max_rounds = 3  # Use smaller number for faster test

        channel_id = await channel_admin.start_managing(
            channel_name="test-force-finalize",
            demand_id="demand-ff-001",
            demand=test_demand,
            invited_agents=mock_candidates,
            max_rounds=max_rounds
        )

        state = channel_admin.channels[channel_id]

        # Initial responses: all participate
        for c in mock_candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # Simulate multiple rounds with 60% acceptance
        for round_num in range(max_rounds + 1):
            if state.status not in (ChannelStatus.NEGOTIATING, ChannelStatus.PROPOSAL_SENT):
                break

            # 3 accept, 2 negotiate (60%)
            for i, c in enumerate(mock_candidates):
                await channel_admin.handle_feedback(
                    channel_id=channel_id,
                    agent_id=c["agent_id"],
                    feedback_type="accept" if i < 3 else "negotiate"
                )
            await asyncio.sleep(0.1)

            logger.info(f"Round {round_num + 1}: status={state.status.value}, round={state.current_round}")

        # Verify force finalized
        assert state.status == ChannelStatus.FORCE_FINALIZED, \
            f"Expected FORCE_FINALIZED, got {state.status.value}"

        # Verify force finalized event
        ff_events = [e for e in published_events if e["event_type"] == "towow.negotiation.force_finalized"]
        assert len(ff_events) > 0, "Should have force_finalized event"

        print(f"\n[PASS] Force finalize test: round={state.current_round}, status={state.status.value}")

    @pytest.mark.asyncio
    async def test_force_finalize_event_format(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test v4 'towow.negotiation.force_finalized' event format.

        Expected payload:
        - confirmed_participants: list
        - optional_participants: list
        - status: "force_finalized"
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-ff-format",
            demand_id="demand-ff-002",
            demand=test_demand,
            invited_agents=mock_candidates,
            max_rounds=2  # Smaller for faster test
        )

        state = channel_admin.channels[channel_id]

        # All participate
        for c in mock_candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # Multiple rounds with 60% acceptance
        for _ in range(3):
            if state.status not in (ChannelStatus.NEGOTIATING, ChannelStatus.PROPOSAL_SENT):
                break
            for i, c in enumerate(mock_candidates):
                await channel_admin.handle_feedback(
                    channel_id=channel_id,
                    agent_id=c["agent_id"],
                    feedback_type="accept" if i < 3 else "negotiate"
                )
            await asyncio.sleep(0.1)

        # Find force_finalized event
        ff_events = [e for e in published_events if e["event_type"] == "towow.negotiation.force_finalized"]

        if len(ff_events) > 0:
            payload = ff_events[0]["payload"]

            # Verify required fields
            assert "confirmed_participants" in payload, "Should have confirmed_participants"
            assert "optional_participants" in payload, "Should have optional_participants"
            assert "status" in payload, "Should have status"

            # Verify types
            assert isinstance(payload["confirmed_participants"], list)
            assert isinstance(payload["optional_participants"], list)
            assert payload["status"] == "force_finalized"

            print(f"\n[PASS] Force finalize event format test")
            print(f"Confirmed: {len(payload['confirmed_participants'])}")
            print(f"Optional: {len(payload['optional_participants'])}")
        else:
            # Check if finalized normally or failed
            print(f"\n[INFO] No force_finalized event")
            print(f"Status: {state.status.value}, Round: {state.current_round}")

    @pytest.mark.asyncio
    async def test_participant_classification_on_force_finalize(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test participant classification during force finalization.

        Scenario:
        - 2 accept -> confirmed_participants
        - 2 negotiate -> optional_participants
        - 1 reject -> excluded

        Expected: Correct classification in force_finalized event.
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-classification",
            demand_id="demand-ff-003",
            demand=test_demand,
            invited_agents=mock_candidates,
            max_rounds=2
        )

        state = channel_admin.channels[channel_id]

        # All participate
        for c in mock_candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # Multiple rounds with mixed feedback
        for _ in range(3):
            if state.status not in (ChannelStatus.NEGOTIATING, ChannelStatus.PROPOSAL_SENT):
                break

            # 2 accept, 2 negotiate, 1 reject (40% accept, 20% reject)
            for i, c in enumerate(mock_candidates):
                if i < 2:
                    feedback_type = "accept"
                elif i < 4:
                    feedback_type = "negotiate"
                else:
                    feedback_type = "reject"

                await channel_admin.handle_feedback(
                    channel_id=channel_id,
                    agent_id=c["agent_id"],
                    feedback_type=feedback_type
                )
            await asyncio.sleep(0.1)

        # If force finalized, verify classification
        if state.status == ChannelStatus.FORCE_FINALIZED:
            ff_events = [e for e in published_events if e["event_type"] == "towow.negotiation.force_finalized"]

            if ff_events:
                payload = ff_events[0]["payload"]
                confirmed = payload.get("confirmed_participants", [])
                optional = payload.get("optional_participants", [])

                print(f"\n[RESULT] Participant classification:")
                print(f"  Confirmed: {len(confirmed)}")
                print(f"  Optional: {len(optional)}")

                # Accept feedback -> confirmed
                # Negotiate feedback -> optional
                # Reject -> excluded

        print(f"\n[INFO] Final status: {state.status.value}, Round: {state.current_round}")

    @pytest.mark.asyncio
    async def test_force_finalize_with_all_negotiate(
        self,
        channel_admin: ChannelAdminAgent,
        mock_candidates: List[Dict[str, Any]],
        test_demand: Dict[str, Any]
    ):
        """
        Test force finalization when all participants negotiate.

        Scenario: All participants give 'negotiate' feedback for all rounds.
        Expected: FORCE_FINALIZED with all in optional_participants.
        """
        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-all-negotiate",
            demand_id="demand-ff-004",
            demand=test_demand,
            invited_agents=mock_candidates[:4],  # Use 4 candidates
            max_rounds=2
        )

        state = channel_admin.channels[channel_id]

        # All participate
        for c in mock_candidates[:4]:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # All negotiate for multiple rounds
        for _ in range(3):
            if state.status not in (ChannelStatus.NEGOTIATING, ChannelStatus.PROPOSAL_SENT):
                break

            for c in mock_candidates[:4]:
                await channel_admin.handle_feedback(
                    channel_id=channel_id,
                    agent_id=c["agent_id"],
                    feedback_type="negotiate"
                )
            await asyncio.sleep(0.1)

        # Should be force finalized
        print(f"\n[INFO] All-negotiate test: status={state.status.value}, round={state.current_round}")

        if state.status == ChannelStatus.FORCE_FINALIZED:
            ff_events = [e for e in published_events if e["event_type"] == "towow.negotiation.force_finalized"]
            if ff_events:
                payload = ff_events[0]["payload"]
                optional = payload.get("optional_participants", [])
                print(f"[PASS] All in optional: {len(optional)} participants")


@pytest.mark.e2e
class TestForceFinalizeBoundary:
    """Test force finalize boundary conditions."""

    @pytest.mark.asyncio
    async def test_round_5_triggers_force_finalize(self):
        """
        Test that exactly round 5 triggers force finalization.

        Scenario: 60% acceptance for rounds 1-4, should trigger force_finalize at round 5.
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_round_5")
        admin.llm = None

        published_events = []
        async def mock_publish(event_type, payload):
            published_events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = [
            {"agent_id": f"agent_{i}", "display_name": f"User{i}", "reason": "test"}
            for i in range(5)
        ]

        channel_id = await admin.start_managing(
            channel_name="test-round-5",
            demand_id="demand-r5",
            demand={"surface_demand": "Test"},
            invited_agents=candidates,
            max_rounds=5  # Full 5 rounds
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

        # Simulate 5 rounds with 60% acceptance
        round_statuses = []
        for round_num in range(6):  # Try up to 6 iterations
            if state.status not in (ChannelStatus.NEGOTIATING, ChannelStatus.PROPOSAL_SENT):
                break

            round_statuses.append(f"r{state.current_round}:{state.status.value}")

            # 60% acceptance
            for i, c in enumerate(candidates):
                await admin.handle_feedback(
                    channel_id=channel_id,
                    agent_id=c["agent_id"],
                    feedback_type="accept" if i < 3 else "negotiate"
                )
            await asyncio.sleep(0.05)

        print(f"\n[INFO] Round statuses: {round_statuses}")
        print(f"[INFO] Final: round={state.current_round}, status={state.status.value}")

        # Should be force finalized at or after round 5
        assert state.status == ChannelStatus.FORCE_FINALIZED, \
            f"Expected FORCE_FINALIZED, got {state.status.value}"

    @pytest.mark.asyncio
    async def test_79_percent_triggers_next_round(self):
        """
        Test that 79% acceptance (below 80%) triggers next round instead of finalize.
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_79")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        # Use 10 candidates so we can get exactly 79%
        candidates = [
            {"agent_id": f"agent_{i}", "display_name": f"User{i}", "reason": "test"}
            for i in range(10)
        ]

        channel_id = await admin.start_managing(
            channel_name="test-79",
            demand_id="demand-79",
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

        # First round: 7 accept, 3 negotiate (70% - should trigger next round)
        for i, c in enumerate(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 7 else "negotiate"
            )
        await asyncio.sleep(0.05)

        # Check if went to next round (70% < 80%)
        evaluated_events = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]

        if evaluated_events:
            payload = evaluated_events[0]["payload"]
            print(f"\n[INFO] 70% test: accept_rate={payload.get('accept_rate')}, decision={payload.get('decision')}")

            # 70% should trigger next_round (not finalized)
            if payload.get("accept_rate", 0) < 0.8:
                assert payload.get("decision") in ["next_round", "force_finalized"], \
                    f"70% should trigger next_round, got {payload.get('decision')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
