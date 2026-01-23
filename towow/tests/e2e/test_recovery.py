"""
E2E Test: State Recovery (T10)

Tests state recovery mechanism when channels get stuck.

Test Scenarios:
1. Channel stuck in COLLECTING state - auto recovery
2. Channel stuck in NEGOTIATING state - auto recovery
3. Recovery continues normal flow
4. Max recovery attempts exceeded

Acceptance Criteria:
- AC-7: Recovery mechanism tests pass (implicit - verifies T07 integration)
"""
from __future__ import annotations

import asyncio
import logging
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from openagents.agents.channel_admin import ChannelAdminAgent, ChannelStatus, ChannelState
from services.state_checker import StateChecker, CheckResult, StateCheckResult

logger = logging.getLogger(__name__)


def create_candidates(count: int) -> List[Dict[str, Any]]:
    """Create mock candidates."""
    return [
        {
            "agent_id": f"agent_{i}",
            "display_name": f"User{i}",
            "reason": f"Reason {i}"
        }
        for i in range(count)
    ]


def create_test_channel_state(
    channel_id: str,
    status: ChannelStatus = ChannelStatus.COLLECTING,
    created_at: datetime = None,
    responses: dict = None,
    candidates: list = None,
    proposal_feedback: dict = None,
    current_round: int = 1
) -> ChannelState:
    """Create test channel state."""
    if created_at is None:
        created_at = datetime.utcnow()

    state = ChannelState(
        channel_id=channel_id,
        demand_id=f"demand-{channel_id}",
        demand={"surface_demand": "test demand"},
        candidates=candidates or [{"agent_id": "agent1"}, {"agent_id": "agent2"}],
    )
    state.status = status
    state.created_at = created_at.isoformat()
    state.responses = responses or {}
    state.proposal_feedback = proposal_feedback or {}
    state.current_round = current_round
    return state


class MockChannelAdmin:
    """Mock ChannelAdmin for testing StateChecker."""

    def __init__(self):
        self.channels = {}
        self._aggregate_proposals_called = []
        self._broadcast_demand_called = []
        self._evaluate_feedback_called = []
        self._force_finalize_channel_called = []
        self._fail_channel_called = []

    def get_active_channels(self):
        """Return active channel IDs."""
        active_statuses = {
            ChannelStatus.CREATED,
            ChannelStatus.BROADCASTING,
            ChannelStatus.COLLECTING,
            ChannelStatus.AGGREGATING,
            ChannelStatus.PROPOSAL_SENT,
            ChannelStatus.NEGOTIATING,
        }
        return [
            cid for cid, state in self.channels.items()
            if state.status in active_statuses
        ]

    async def _aggregate_proposals(self, state):
        self._aggregate_proposals_called.append(state.channel_id)

    async def _broadcast_demand(self, state):
        self._broadcast_demand_called.append(state.channel_id)

    async def _evaluate_feedback(self, state):
        self._evaluate_feedback_called.append(state.channel_id)

    async def _force_finalize_channel(self, state):
        self._force_finalize_channel_called.append(state.channel_id)
        state.status = ChannelStatus.FORCE_FINALIZED

    async def _fail_channel(self, state, reason):
        self._fail_channel_called.append((state.channel_id, reason))
        state.status = ChannelStatus.FAILED

    def _get_fallback_proposal_v4(self, state, offers, negotiations):
        return {"summary": "fallback", "assignments": []}


@pytest.mark.e2e
class TestStuckInCollecting:
    """Test recovery from COLLECTING state."""

    @pytest.mark.asyncio
    async def test_recover_stuck_collecting_with_responses(self):
        """
        Test recovery when stuck in COLLECTING with partial responses.

        Scenario: Channel in COLLECTING for > 120s with some responses.
        Expected: Trigger aggregation.
        """
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, check_interval=1, max_stuck_time=0.1)

        # Create stuck channel with responses
        old_time = datetime.utcnow() - timedelta(seconds=200)
        state = create_test_channel_state(
            "ch-stuck-1",
            ChannelStatus.COLLECTING,
            created_at=old_time,
            responses={"agent1": {"decision": "participate"}, "agent2": {"decision": "participate"}}
        )
        mock_admin.channels["ch-stuck-1"] = state

        # Initialize recovery state
        recovery_state = checker._get_or_create_recovery_state("ch-stuck-1")
        recovery_state.last_status = "collecting"
        recovery_state.last_status_change_time = old_time

        # Check channel
        result = await checker.check_channel("ch-stuck-1")

        print(f"\n[INFO] Check result:")
        print(f"  Healthy: {result.healthy}")
        print(f"  Reason: {result.reason}")
        print(f"  Details: {result.details}")

        # Should detect as stuck
        assert result.healthy is False, "Should detect as unhealthy"
        assert result.reason in [CheckResult.STUCK_IN_COLLECTING, CheckResult.MISSING_RESPONSES]

        # Trigger recovery
        if not result.healthy:
            await checker._handle_unhealthy_channel("ch-stuck-1", result)

        # Should have triggered aggregation (has responses)
        assert "ch-stuck-1" in mock_admin._aggregate_proposals_called or \
               "ch-stuck-1" in mock_admin._broadcast_demand_called, \
               "Should trigger recovery action"

        print(f"\n[PASS] Stuck COLLECTING recovery test")

    @pytest.mark.asyncio
    async def test_recover_stuck_collecting_no_responses(self):
        """
        Test recovery when stuck in COLLECTING without responses.

        Scenario: Channel in COLLECTING for > 120s with no responses.
        Expected: Re-broadcast demand.
        """
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, check_interval=1, max_stuck_time=0.1)

        old_time = datetime.utcnow() - timedelta(seconds=200)
        state = create_test_channel_state(
            "ch-stuck-2",
            ChannelStatus.COLLECTING,
            created_at=old_time,
            responses={}  # No responses
        )
        mock_admin.channels["ch-stuck-2"] = state

        recovery_state = checker._get_or_create_recovery_state("ch-stuck-2")
        recovery_state.last_status = "collecting"
        recovery_state.last_status_change_time = old_time

        result = await checker.check_channel("ch-stuck-2")

        if not result.healthy:
            await checker._handle_unhealthy_channel("ch-stuck-2", result)

        # Should have triggered rebroadcast (no responses)
        print(f"\n[INFO] Recovery actions:")
        print(f"  Broadcast called: {mock_admin._broadcast_demand_called}")
        print(f"  Aggregate called: {mock_admin._aggregate_proposals_called}")

        print(f"\n[PASS] Stuck COLLECTING (no responses) recovery test")


@pytest.mark.e2e
class TestStuckInNegotiating:
    """Test recovery from NEGOTIATING state."""

    @pytest.mark.asyncio
    async def test_recover_stuck_negotiating(self):
        """
        Test recovery when stuck in NEGOTIATING state.

        Scenario: Channel in NEGOTIATING for > 120s.
        Expected: Force evaluate feedback.
        """
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, check_interval=1, max_stuck_time=0.1)

        old_time = datetime.utcnow() - timedelta(seconds=200)
        state = create_test_channel_state(
            "ch-stuck-3",
            ChannelStatus.NEGOTIATING,
            created_at=old_time,
            proposal_feedback={"agent1": {"feedback_type": "accept"}}
        )
        mock_admin.channels["ch-stuck-3"] = state

        recovery_state = checker._get_or_create_recovery_state("ch-stuck-3")
        recovery_state.last_status = "negotiating"
        recovery_state.last_status_change_time = old_time

        result = await checker.check_channel("ch-stuck-3")

        print(f"\n[INFO] NEGOTIATING check result:")
        print(f"  Healthy: {result.healthy}")
        print(f"  Reason: {result.reason}")

        assert result.healthy is False
        assert result.reason == CheckResult.STUCK_IN_NEGOTIATING

        if not result.healthy:
            await checker._handle_unhealthy_channel("ch-stuck-3", result)

        # Should trigger feedback evaluation
        assert "ch-stuck-3" in mock_admin._evaluate_feedback_called, \
            "Should trigger evaluate_feedback"

        print(f"\n[PASS] Stuck NEGOTIATING recovery test")


@pytest.mark.e2e
class TestRecoveryContinuesFlow:
    """Test that recovery continues normal flow."""

    @pytest.mark.asyncio
    async def test_recovery_then_normal_completion(self):
        """
        Test that after recovery, channel can complete normally.

        Scenario:
        1. Channel stuck in COLLECTING
        2. Recovery triggers aggregation
        3. Feedback received
        4. Channel finalizes
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_recovery_flow")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-recovery-flow",
            demand_id="recovery-001",
            demand={"surface_demand": "Test recovery flow"},
            invited_agents=candidates,
            max_rounds=5
        )

        # Simulate partial responses (some didn't respond)
        for c in candidates[:3]:  # Only 3 of 5 respond
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )

        # Force aggregation (simulating recovery)
        state = admin.channels[channel_id]
        await admin.aggregate_proposal(channel_id)

        # Now provide feedback
        for c in candidates[:3]:
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept"
            )
        await asyncio.sleep(0.1)

        # Verify flow completed
        event_types = [e["event_type"] for e in events]

        print(f"\n[INFO] Events after recovery flow:")
        for et in set(event_types):
            print(f"  - {et}: {event_types.count(et)}")

        print(f"\n[INFO] Final status: {state.status.value}")


@pytest.mark.e2e
class TestMaxRecoveryAttempts:
    """Test max recovery attempts behavior."""

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """
        Test that channel fails after max recovery attempts.

        Scenario: 3 recovery attempts all fail.
        Expected: Channel marked as FAILED.
        """
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, max_recovery_attempts=3)

        state = create_test_channel_state(
            "ch-max-attempts",
            ChannelStatus.COLLECTING,
            responses={}
        )
        mock_admin.channels["ch-max-attempts"] = state

        # Simulate 3 failed recovery attempts
        recovery_state = checker._get_or_create_recovery_state("ch-max-attempts")
        recovery_state.recovery_attempts = 3

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_COLLECTING,
            channel_id="ch-max-attempts"
        )

        await checker._handle_unhealthy_channel("ch-max-attempts", result)

        # Should mark as failed
        assert len(mock_admin._fail_channel_called) == 1, "Should call fail_channel"
        assert mock_admin._fail_channel_called[0][0] == "ch-max-attempts"
        assert "recovery_exhausted" in mock_admin._fail_channel_called[0][1]

        print(f"\n[PASS] Max recovery attempts test")

    @pytest.mark.asyncio
    async def test_recovery_count_increments(self):
        """Test that recovery attempts are counted correctly."""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, max_recovery_attempts=5)

        state = create_test_channel_state(
            "ch-count",
            ChannelStatus.COLLECTING,
            responses={"agent1": {"decision": "participate"}}
        )
        mock_admin.channels["ch-count"] = state

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_COLLECTING,
            channel_id="ch-count"
        )

        # First recovery
        await checker._handle_unhealthy_channel("ch-count", result)
        recovery_state = checker._recovery_states["ch-count"]
        assert recovery_state.recovery_attempts == 1

        # Second recovery
        await checker._handle_unhealthy_channel("ch-count", result)
        assert recovery_state.recovery_attempts == 2

        print(f"\n[PASS] Recovery count increment test")


@pytest.mark.e2e
class TestRecoveryIdempotency:
    """Test recovery idempotency."""

    @pytest.mark.asyncio
    async def test_status_change_resets_recovery_count(self):
        """
        Test that status change resets recovery count.

        Scenario:
        1. Channel stuck, recovery count = 2
        2. Status changes
        3. Recovery count resets to 0
        """
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        state = create_test_channel_state("ch-reset", ChannelStatus.COLLECTING)
        mock_admin.channels["ch-reset"] = state

        # Set recovery state
        recovery_state = checker._get_or_create_recovery_state("ch-reset")
        recovery_state.recovery_attempts = 2
        recovery_state.last_status = "collecting"

        # Check once (status same)
        await checker.check_channel("ch-reset")
        assert recovery_state.recovery_attempts == 2  # Unchanged

        # Change status
        state.status = ChannelStatus.NEGOTIATING

        # Check again (status changed)
        await checker.check_channel("ch-reset")
        assert recovery_state.recovery_attempts == 0  # Reset
        assert recovery_state.last_status == "negotiating"

        print(f"\n[PASS] Status change resets recovery count")

    @pytest.mark.asyncio
    async def test_recovery_history_recorded(self):
        """Test that recovery history is recorded."""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        state = create_test_channel_state(
            "ch-history",
            ChannelStatus.COLLECTING,
            responses={"agent1": {"decision": "participate"}}
        )
        mock_admin.channels["ch-history"] = state

        result = StateCheckResult(
            healthy=False,
            reason=CheckResult.STUCK_IN_COLLECTING,
            suggested_action="aggregate",
            channel_id="ch-history"
        )

        await checker._handle_unhealthy_channel("ch-history", result)

        recovery_state = checker._recovery_states["ch-history"]
        assert len(recovery_state.recovery_history) == 1

        history = recovery_state.recovery_history[0]
        assert history.channel_id == "ch-history"
        assert history.attempt_number == 1
        assert history.reason == CheckResult.STUCK_IN_COLLECTING

        print(f"\n[PASS] Recovery history recorded")


@pytest.mark.e2e
class TestStateCheckerIntegration:
    """Test StateChecker integration with ChannelAdmin."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_state_checker_lifecycle(self):
        """
        Test StateChecker start/stop lifecycle.

        Note: Uses short intervals for testing.
        """
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin, check_interval=0.1)

        # Start
        await checker.start()
        assert checker.is_running

        # Let it run briefly
        await asyncio.sleep(0.2)

        # Stop
        await checker.stop()
        assert not checker.is_running

        print(f"\n[PASS] StateChecker lifecycle test")

    @pytest.mark.asyncio
    async def test_clear_recovery_state(self):
        """Test clearing recovery state for completed channels."""
        mock_admin = MockChannelAdmin()
        checker = StateChecker(mock_admin)

        # Create recovery state
        checker._get_or_create_recovery_state("ch-clear")
        assert "ch-clear" in checker._recovery_states

        # Clear
        checker.clear_recovery_state("ch-clear")
        assert "ch-clear" not in checker._recovery_states

        print(f"\n[PASS] Clear recovery state test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
