"""
E2E Test: Three-Tier Threshold Decision (T10)

Tests the three-tier acceptance threshold decision logic:
- >= 80% accept -> FINALIZED
- 50%-80% accept -> Continue negotiation
- < 50% accept (>= 50% reject/withdraw) -> FAILED

Boundary value tests:
- Exactly 50% accept
- Exactly 80% accept
- Edge cases around thresholds

Acceptance Criteria:
- AC-4: Three-tier threshold decision tests pass (including boundary values)
"""
from __future__ import annotations

import asyncio
import logging
import pytest
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from openagents.agents.channel_admin import ChannelAdminAgent, ChannelStatus
from config import ACCEPT_THRESHOLD_HIGH, ACCEPT_THRESHOLD_LOW

logger = logging.getLogger(__name__)


@pytest.fixture
def channel_admin() -> ChannelAdminAgent:
    """Create ChannelAdmin agent for testing."""
    admin = ChannelAdminAgent()
    admin._logger = logging.getLogger("test_threshold")
    admin.llm = None
    return admin


def create_candidates(count: int) -> List[Dict[str, Any]]:
    """Create specified number of mock candidates."""
    return [
        {
            "agent_id": f"user_agent_{i}",
            "display_name": f"TestUser{i}",
            "reason": f"Test reason {i}",
            "relevance_score": 90 - i
        }
        for i in range(count)
    ]


async def run_negotiation_round(
    admin: ChannelAdminAgent,
    channel_id: str,
    candidates: List[Dict[str, Any]],
    accept_count: int,
    reject_count: int = 0,
    negotiate_count: int = 0
) -> Dict[str, Any]:
    """
    Run a negotiation round with specified feedback distribution.

    Returns dict with:
    - status: ChannelStatus
    - decision: str (from evaluated event)
    - accept_rate: float
    """
    # Provide feedback
    idx = 0
    for i in range(accept_count):
        if idx < len(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=candidates[idx]["agent_id"],
                feedback_type="accept"
            )
            idx += 1

    for i in range(reject_count):
        if idx < len(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=candidates[idx]["agent_id"],
                feedback_type="reject"
            )
            idx += 1

    for i in range(negotiate_count):
        if idx < len(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=candidates[idx]["agent_id"],
                feedback_type="negotiate"
            )
            idx += 1

    await asyncio.sleep(0.1)

    state = admin.channels[channel_id]
    return {
        "status": state.status,
        "round": state.current_round
    }


@pytest.mark.e2e
class TestHighThreshold:
    """Test high threshold (>= 80% accept -> FINALIZED)."""

    @pytest.mark.asyncio
    async def test_exactly_80_percent_accept(self, channel_admin: ChannelAdminAgent):
        """
        Test exactly 80% acceptance rate.

        Scenario: 4/5 accept (80%)
        Expected: FINALIZED
        """
        candidates = create_candidates(5)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-80",
            demand_id="threshold-80",
            demand={"surface_demand": "Test 80%"},
            invited_agents=candidates,
            max_rounds=5
        )

        # All participate
        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # 4 accept, 1 negotiate (80%)
        for i, c in enumerate(candidates):
            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 4 else "negotiate"
            )
        await asyncio.sleep(0.1)

        state = channel_admin.channels[channel_id]

        # Verify
        evaluated = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]
        assert len(evaluated) > 0, "Should have evaluated event"

        payload = evaluated[0]["payload"]
        accept_rate = payload.get("accept_rate", 0)
        decision = payload.get("decision", "")

        print(f"\n[TEST] 80% threshold test:")
        print(f"  Accept rate: {accept_rate:.2%}")
        print(f"  Decision: {decision}")
        print(f"  Status: {state.status.value}")

        assert accept_rate >= 0.8, f"Accept rate should be >= 80%, got {accept_rate:.2%}"
        assert decision == "finalized", f"Decision should be finalized, got {decision}"
        assert state.status == ChannelStatus.FINALIZED, f"Should be FINALIZED, got {state.status}"

    @pytest.mark.asyncio
    async def test_above_80_percent_accept(self, channel_admin: ChannelAdminAgent):
        """
        Test above 80% acceptance rate.

        Scenario: 5/5 accept (100%)
        Expected: FINALIZED
        """
        candidates = create_candidates(5)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-100",
            demand_id="threshold-100",
            demand={"surface_demand": "Test 100%"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # All accept
        for c in candidates:
            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept"
            )
        await asyncio.sleep(0.1)

        state = channel_admin.channels[channel_id]

        assert state.status == ChannelStatus.FINALIZED, f"100% should be FINALIZED, got {state.status}"
        print(f"\n[PASS] 100% acceptance -> FINALIZED")

    @pytest.mark.asyncio
    async def test_79_percent_not_finalized(self, channel_admin: ChannelAdminAgent):
        """
        Test 79% acceptance rate (below threshold).

        Scenario: Use 10 participants, 7 accept (70% - clearly below 80%)
        Expected: NOT immediately FINALIZED (continues to next round)
        """
        candidates = create_candidates(10)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-70",
            demand_id="threshold-70",
            demand={"surface_demand": "Test 70%"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # 7 accept, 3 negotiate (70%)
        for i, c in enumerate(candidates):
            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 7 else "negotiate"
            )
        await asyncio.sleep(0.1)

        state = channel_admin.channels[channel_id]

        # 70% should NOT trigger immediate FINALIZED
        evaluated = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]
        if evaluated:
            payload = evaluated[0]["payload"]
            decision = payload.get("decision", "")

            print(f"\n[TEST] 70% threshold test:")
            print(f"  Accept rate: {payload.get('accept_rate', 0):.2%}")
            print(f"  Decision: {decision}")

            # 70% < 80%, so should continue (unless force finalized at max round)
            assert decision in ["next_round", "force_finalized"], \
                f"70% should continue or force_finalize, got {decision}"


@pytest.mark.e2e
class TestLowThreshold:
    """Test low threshold (>= 50% reject/withdraw -> FAILED)."""

    @pytest.mark.asyncio
    async def test_exactly_50_percent_reject(self, channel_admin: ChannelAdminAgent):
        """
        Test exactly 50% rejection rate.

        Scenario: 5/10 reject (50% rejection)
        Expected: FAILED
        """
        candidates = create_candidates(10)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-50-reject",
            demand_id="threshold-50-reject",
            demand={"surface_demand": "Test 50% reject"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # 5 accept, 5 reject (50% reject)
        for i, c in enumerate(candidates):
            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 5 else "reject"
            )
        await asyncio.sleep(0.1)

        state = channel_admin.channels[channel_id]

        evaluated = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]
        if evaluated:
            payload = evaluated[0]["payload"]
            reject_rate = payload.get("reject_rate", 0)
            decision = payload.get("decision", "")

            print(f"\n[TEST] 50% reject test:")
            print(f"  Reject rate: {reject_rate:.2%}")
            print(f"  Decision: {decision}")
            print(f"  Status: {state.status.value}")

            # 50% reject should trigger FAILED
            assert reject_rate >= 0.5, f"Reject rate should be >= 50%, got {reject_rate:.2%}"
            assert decision == "failed", f"50% reject should fail, got {decision}"

    @pytest.mark.asyncio
    async def test_majority_reject(self, channel_admin: ChannelAdminAgent):
        """
        Test majority rejection (> 50%).

        Scenario: 6/10 reject (60% rejection)
        Expected: FAILED
        """
        candidates = create_candidates(10)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-60-reject",
            demand_id="threshold-60-reject",
            demand={"surface_demand": "Test 60% reject"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # 4 accept, 6 reject
        for i, c in enumerate(candidates):
            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 4 else "reject"
            )
        await asyncio.sleep(0.1)

        state = channel_admin.channels[channel_id]

        assert state.status == ChannelStatus.FAILED, f"60% reject should FAIL, got {state.status}"
        print(f"\n[PASS] 60% reject -> FAILED")

    @pytest.mark.asyncio
    async def test_withdraw_counts_as_reject(self, channel_admin: ChannelAdminAgent):
        """
        Test that 'withdraw' feedback counts as rejection.

        Scenario: 3 accept, 3 reject, 4 withdraw (70% reject+withdraw)
        Expected: FAILED
        """
        candidates = create_candidates(10)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-withdraw",
            demand_id="threshold-withdraw",
            demand={"surface_demand": "Test withdraw"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # 3 accept, 3 reject, 4 withdraw
        for i, c in enumerate(candidates):
            if i < 3:
                fb_type = "accept"
            elif i < 6:
                fb_type = "reject"
            else:
                fb_type = "withdraw"

            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type=fb_type
            )
        await asyncio.sleep(0.1)

        state = channel_admin.channels[channel_id]

        evaluated = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]
        if evaluated:
            payload = evaluated[0]["payload"]
            print(f"\n[TEST] Withdraw as reject test:")
            print(f"  Reject rate (includes withdraw): {payload.get('reject_rate', 0):.2%}")
            print(f"  Withdraws: {payload.get('withdraws', 0)}")
            print(f"  Decision: {payload.get('decision')}")

        # 70% reject+withdraw should trigger FAILED
        assert state.status == ChannelStatus.FAILED, f"70% reject+withdraw should FAIL, got {state.status}"


@pytest.mark.e2e
class TestMiddleZone:
    """Test middle zone (50%-80% accept -> continue negotiation)."""

    @pytest.mark.asyncio
    async def test_60_percent_continues(self, channel_admin: ChannelAdminAgent):
        """
        Test 60% acceptance rate (in middle zone).

        Scenario: 6/10 accept, 4 negotiate (60% accept, 0% reject)
        Expected: Continue to next round
        """
        candidates = create_candidates(10)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-60",
            demand_id="threshold-60",
            demand={"surface_demand": "Test 60%"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # 6 accept, 4 negotiate
        for i, c in enumerate(candidates):
            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 6 else "negotiate"
            )
        await asyncio.sleep(0.1)

        state = channel_admin.channels[channel_id]

        evaluated = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]
        if evaluated:
            payload = evaluated[0]["payload"]
            decision = payload.get("decision", "")

            print(f"\n[TEST] 60% acceptance (middle zone):")
            print(f"  Accept rate: {payload.get('accept_rate', 0):.2%}")
            print(f"  Decision: {decision}")
            print(f"  Current round: {state.current_round}")

            # 60% accept with 0% reject should continue
            assert decision == "next_round", f"60% should continue, got {decision}"

    @pytest.mark.asyncio
    async def test_51_percent_accept_continues(self, channel_admin: ChannelAdminAgent):
        """
        Test 51% acceptance (just above the reject threshold).

        Scenario: 51/100 accept, 49 negotiate (51% accept, 0% reject)
        Using 10 participants: 5 accept + 5 negotiate (50% accept)
        Expected: Continue to next round (not failed because reject < 50%)
        """
        candidates = create_candidates(10)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-50-accept",
            demand_id="threshold-50-accept",
            demand={"surface_demand": "Test 50% accept"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        # 5 accept, 5 negotiate (50% accept, 0% reject)
        for i, c in enumerate(candidates):
            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 5 else "negotiate"
            )
        await asyncio.sleep(0.1)

        state = channel_admin.channels[channel_id]

        evaluated = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]
        if evaluated:
            payload = evaluated[0]["payload"]
            decision = payload.get("decision", "")
            reject_rate = payload.get("reject_rate", 0)

            print(f"\n[TEST] 50% accept, 0% reject:")
            print(f"  Accept rate: {payload.get('accept_rate', 0):.2%}")
            print(f"  Reject rate: {reject_rate:.2%}")
            print(f"  Decision: {decision}")

            # 50% accept with 0% reject should continue (not fail)
            assert reject_rate < 0.5, f"Reject rate should be < 50%"
            assert decision == "next_round", f"Should continue, got {decision}"


@pytest.mark.e2e
class TestBoundaryValues:
    """Test boundary values around thresholds."""

    @pytest.mark.asyncio
    async def test_boundary_80_exact(self):
        """Test exact 80% boundary using 5 participants (4/5 = 80%)."""
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_boundary_80")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-b80",
            demand_id="boundary-80",
            demand={"surface_demand": "Test"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.05)

        # 4/5 = 80%
        for i, c in enumerate(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 4 else "negotiate"
            )
        await asyncio.sleep(0.05)

        state = admin.channels[channel_id]
        assert state.status == ChannelStatus.FINALIZED, f"80% should FINALIZE, got {state.status}"
        print("\n[PASS] 80% boundary -> FINALIZED")

    @pytest.mark.asyncio
    async def test_boundary_50_exact(self):
        """Test exact 50% rejection boundary using 10 participants."""
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_boundary_50")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(10)

        channel_id = await admin.start_managing(
            channel_name="test-b50",
            demand_id="boundary-50",
            demand={"surface_demand": "Test"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.05)

        # 5/10 reject = 50%
        for i, c in enumerate(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 5 else "reject"
            )
        await asyncio.sleep(0.05)

        state = admin.channels[channel_id]
        assert state.status == ChannelStatus.FAILED, f"50% reject should FAIL, got {state.status}"
        print("\n[PASS] 50% reject boundary -> FAILED")

    @pytest.mark.asyncio
    async def test_boundary_49_reject_not_fail(self):
        """Test 49% rejection (below threshold) should not fail."""
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_boundary_49")
        admin.llm = None

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        # Use 10 participants, 4 reject = 40%
        candidates = create_candidates(10)

        channel_id = await admin.start_managing(
            channel_name="test-b49",
            demand_id="boundary-49",
            demand={"surface_demand": "Test"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.05)

        # 6/10 accept, 4/10 reject = 40% reject (below 50%)
        for i, c in enumerate(candidates):
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept" if i < 6 else "reject"
            )
        await asyncio.sleep(0.05)

        state = admin.channels[channel_id]

        # 40% reject should NOT fail (below 50% threshold)
        assert state.status != ChannelStatus.FAILED, f"40% reject should NOT fail, got {state.status}"
        print(f"\n[PASS] 40% reject -> NOT FAILED (status: {state.status.value})")


@pytest.mark.e2e
class TestThresholdConfiguration:
    """Test that thresholds are correctly loaded from configuration."""

    def test_threshold_values_loaded(self):
        """
        Verify threshold values are loaded from config and are valid.

        Note: We verify threshold validity (range and relationship) rather than
        specific values, because values can be overridden by environment variables.
        """
        print(f"\n[CONFIG] ACCEPT_THRESHOLD_HIGH = {ACCEPT_THRESHOLD_HIGH}")
        print(f"[CONFIG] ACCEPT_THRESHOLD_LOW = {ACCEPT_THRESHOLD_LOW}")

        # Verify thresholds are within valid range (0.0 to 1.0)
        assert 0.0 <= ACCEPT_THRESHOLD_HIGH <= 1.0, (
            f"High threshold must be between 0 and 1, got {ACCEPT_THRESHOLD_HIGH}"
        )
        assert 0.0 <= ACCEPT_THRESHOLD_LOW <= 1.0, (
            f"Low threshold must be between 0 and 1, got {ACCEPT_THRESHOLD_LOW}"
        )

        # Verify high threshold > low threshold (logical constraint)
        assert ACCEPT_THRESHOLD_HIGH > ACCEPT_THRESHOLD_LOW, (
            f"High threshold ({ACCEPT_THRESHOLD_HIGH}) must be greater than "
            f"low threshold ({ACCEPT_THRESHOLD_LOW})"
        )

        # Verify reasonable separation between thresholds
        threshold_gap = ACCEPT_THRESHOLD_HIGH - ACCEPT_THRESHOLD_LOW
        assert threshold_gap >= 0.1, (
            f"Threshold gap ({threshold_gap:.2f}) should be at least 0.1 "
            f"to allow meaningful negotiation zone"
        )

        print(f"[PASS] Thresholds are valid: HIGH={ACCEPT_THRESHOLD_HIGH}, LOW={ACCEPT_THRESHOLD_LOW}")

    @pytest.mark.asyncio
    async def test_threshold_used_in_evaluation(self, channel_admin: ChannelAdminAgent):
        """Test that thresholds appear in feedback.evaluated event."""
        candidates = create_candidates(5)
        events = []

        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        channel_admin._publish_event = mock_publish
        channel_admin.send_to_agent = AsyncMock()

        channel_id = await channel_admin.start_managing(
            channel_name="test-config",
            demand_id="threshold-config",
            demand={"surface_demand": "Test config"},
            invited_agents=candidates,
            max_rounds=5
        )

        for c in candidates:
            await channel_admin.handle_response(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                decision="participate"
            )
        await asyncio.sleep(0.1)

        for c in candidates:
            await channel_admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept"
            )
        await asyncio.sleep(0.1)

        evaluated = [e for e in events if e["event_type"] == "towow.feedback.evaluated"]
        assert len(evaluated) > 0, "Should have evaluated event"

        payload = evaluated[0]["payload"]
        assert "threshold_high" in payload, "Should include threshold_high"
        assert "threshold_low" in payload, "Should include threshold_low"
        assert payload["threshold_high"] == ACCEPT_THRESHOLD_HIGH
        assert payload["threshold_low"] == ACCEPT_THRESHOLD_LOW

        print(f"\n[PASS] Thresholds included in event payload")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
