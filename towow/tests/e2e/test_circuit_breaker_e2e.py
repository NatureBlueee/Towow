"""
E2E Test: Circuit Breaker Integration (T10)

Tests circuit breaker integration in E2E negotiation scenarios.

Test Scenarios:
1. LLM failure triggers fallback
2. Circuit opens after consecutive failures
3. Fallback responses allow negotiation to continue
4. At least returns fallback candidates

Acceptance Criteria:
- AC-7: Circuit breaker degradation tests pass
"""
from __future__ import annotations

import asyncio
import json
import logging
import pytest
import time
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from openagents.agents.channel_admin import ChannelAdminAgent, ChannelStatus
from services.llm import (
    CircuitBreaker,
    CircuitState,
    FALLBACK_RESPONSES,
    LLMService,
    LLMServiceWithFallback,
)

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


@pytest.mark.e2e
class TestCircuitBreakerDegradation:
    """Test circuit breaker degradation in E2E scenarios."""

    @pytest.mark.asyncio
    async def test_negotiation_continues_with_fallback(self):
        """
        Test that negotiation can continue when using fallback responses.

        Scenario: LLM service is unavailable, system uses fallback.
        Expected: Negotiation still completes with fallback proposal.
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_cb_fallback")
        admin.llm = None  # No LLM = use fallback

        events = []
        async def mock_publish(event_type, payload):
            events.append({"event_type": event_type, "payload": payload})
        admin._publish_event = mock_publish
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-cb-fallback",
            demand_id="cb-001",
            demand={"surface_demand": "Test with fallback"},
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
        await asyncio.sleep(0.1)

        # Verify proposal was generated (using fallback)
        assert state.current_proposal is not None, "Should have generated fallback proposal"
        assert state.current_proposal.get("is_mock") or state.current_proposal.get("is_fallback") or \
               "assignments" in state.current_proposal, "Should have valid proposal structure"

        # All accept
        for c in candidates:
            await admin.handle_feedback(
                channel_id=channel_id,
                agent_id=c["agent_id"],
                feedback_type="accept"
            )
        await asyncio.sleep(0.1)

        # Verify completed
        assert state.status == ChannelStatus.FINALIZED, f"Should finalize with fallback, got {state.status}"

        print(f"\n[PASS] Negotiation completed with fallback proposal")

    @pytest.mark.asyncio
    async def test_fallback_proposal_has_assignments(self):
        """
        Test that fallback proposal contains valid assignments.

        Expected: Fallback proposal includes all participants.
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_fb_assign")
        admin.llm = None

        admin._publish_event = AsyncMock()
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(5)

        channel_id = await admin.start_managing(
            channel_name="test-fb-assign",
            demand_id="cb-002",
            demand={"surface_demand": "Test assignments"},
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
        await asyncio.sleep(0.1)

        # Check proposal structure
        proposal = state.current_proposal
        assert proposal is not None, "Should have proposal"
        assert "assignments" in proposal, "Should have assignments"
        assert len(proposal["assignments"]) > 0, "Should have at least one assignment"

        # Each assignment should have agent_id
        for assignment in proposal["assignments"]:
            assert "agent_id" in assignment, "Assignment should have agent_id"

        print(f"\n[PASS] Fallback proposal has {len(proposal['assignments'])} assignments")


@pytest.mark.e2e
class TestCircuitBreakerWithLLM:
    """Test circuit breaker with LLM service."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        """
        Test that circuit opens after consecutive LLM failures.

        Scenario: 3 consecutive LLM failures.
        Expected: Circuit enters OPEN state.
        """
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=Exception("LLM Error"))

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            circuit_breaker=CircuitBreaker(failure_threshold=3)
        )

        # Simulate 3 failures
        for _ in range(3):
            result = await service.complete(
                prompt="test",
                fallback_key="default"
            )

        assert service.circuit_breaker.state == CircuitState.OPEN, \
            f"Circuit should be OPEN after 3 failures, got {service.circuit_breaker.state}"

        # Verify stats
        assert service.stats["failure_count"] == 3

        print(f"\n[PASS] Circuit opens after 3 failures")

    @pytest.mark.asyncio
    async def test_circuit_open_returns_fallback(self):
        """
        Test that OPEN circuit returns fallback without calling LLM.

        Expected: LLM not called, fallback returned.
        """
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()
        mock_llm.complete = AsyncMock()

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            circuit_breaker=CircuitBreaker(failure_threshold=3)
        )

        # Manually open circuit
        service.circuit_breaker.state = CircuitState.OPEN
        service.circuit_breaker.last_failure_time = time.time()

        # Call should not reach LLM
        result = await service.complete(
            prompt="test",
            fallback_key="default"
        )

        # Verify LLM not called
        mock_llm.complete.assert_not_called()

        # Verify fallback returned
        parsed = json.loads(result)
        assert "status" in parsed or "message" in parsed, "Should return fallback response"

        # Verify stats
        assert service.stats["circuit_open_count"] == 1
        assert service.stats["fallback_count"] == 1

        print(f"\n[PASS] Circuit open returns fallback without LLM call")

    @pytest.mark.asyncio
    async def test_circuit_half_open_allows_test(self):
        """
        Test that HALF_OPEN state allows test request.

        Expected: One request allowed, success closes circuit.
        """
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()
        mock_llm.complete = AsyncMock(return_value='{"result": "success"}')

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            circuit_breaker=CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=0.1  # Short timeout for testing
            )
        )

        # Open circuit
        service.circuit_breaker.state = CircuitState.OPEN
        service.circuit_breaker.last_failure_time = time.time() - 0.2  # Past recovery time

        # Request should go through
        result = await service.complete(
            prompt="test",
            fallback_key="default"
        )

        # Should have called LLM and closed circuit
        assert result == '{"result": "success"}'
        assert service.circuit_breaker.state == CircuitState.CLOSED

        print(f"\n[PASS] Circuit closes after successful half-open test")


@pytest.mark.e2e
class TestFallbackResponsesInNegotiation:
    """Test fallback responses work in real negotiation scenarios."""

    @pytest.mark.asyncio
    async def test_proposal_aggregation_fallback_works(self):
        """
        Test that proposal_aggregation fallback produces valid proposal.

        Expected: Fallback response can be parsed and used.
        """
        fallback = FALLBACK_RESPONSES.get("proposal_aggregation")
        assert fallback is not None, "proposal_aggregation fallback should exist"

        parsed = json.loads(fallback)

        # Should have required fields
        assert "summary" in parsed
        assert "assignments" in parsed
        assert "confidence" in parsed

        print(f"\n[PASS] proposal_aggregation fallback is valid")
        print(f"Summary: {parsed.get('summary', '')[:50]}...")

    @pytest.mark.asyncio
    async def test_response_generation_fallback_works(self):
        """
        Test that response_generation fallback produces valid response.

        Expected: Fallback response has decision and reasoning.
        """
        fallback = FALLBACK_RESPONSES.get("response_generation")
        assert fallback is not None, "response_generation fallback should exist"

        parsed = json.loads(fallback)

        # Should have required fields
        assert "decision" in parsed
        assert parsed["decision"] in ["participate", "decline", "conditional"]
        assert "reasoning" in parsed

        print(f"\n[PASS] response_generation fallback is valid")
        print(f"Decision: {parsed.get('decision')}")

    @pytest.mark.asyncio
    async def test_smart_filter_fallback_works(self):
        """
        Test that smart_filter fallback produces valid candidates.

        Expected: Fallback response has candidates array.
        """
        fallback = FALLBACK_RESPONSES.get("smart_filter")
        assert fallback is not None, "smart_filter fallback should exist"

        parsed = json.loads(fallback)

        # Should have candidates
        assert "candidates" in parsed
        assert isinstance(parsed["candidates"], list)

        print(f"\n[PASS] smart_filter fallback is valid")
        print(f"Candidates count: {len(parsed.get('candidates', []))}")


@pytest.mark.e2e
class TestCircuitBreakerRecovery:
    """Test circuit breaker recovery scenarios."""

    @pytest.mark.asyncio
    async def test_full_recovery_cycle(self):
        """
        Test complete recovery cycle: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.

        Scenario:
        1. Start CLOSED
        2. 3 failures -> OPEN
        3. Wait -> HALF_OPEN
        4. Success -> CLOSED
        """
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            circuit_breaker=CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=0.1
            )
        )

        # Phase 1: CLOSED - failures trigger OPEN
        mock_llm.complete = AsyncMock(side_effect=Exception("Error"))
        for _ in range(3):
            await service.complete("test", fallback_key="default")

        assert service.circuit_breaker.state == CircuitState.OPEN
        print(f"Phase 1: OPEN after 3 failures")

        # Phase 2: Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Phase 3: HALF_OPEN - success closes circuit
        mock_llm.complete = AsyncMock(return_value='{"ok": true}')
        result = await service.complete("test", fallback_key="default")

        assert service.circuit_breaker.state == CircuitState.CLOSED
        print(f"Phase 2-3: CLOSED after successful recovery")

        print(f"\n[PASS] Full recovery cycle complete")

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        """
        Test that failure in HALF_OPEN reopens circuit.

        Expected: HALF_OPEN -> failure -> OPEN
        """
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=Exception("Still failing"))

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            circuit_breaker=CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=0.1
            )
        )

        # Set to HALF_OPEN
        service.circuit_breaker.state = CircuitState.HALF_OPEN

        # Fail in HALF_OPEN
        await service.complete("test", fallback_key="default")

        # Should be back to OPEN
        assert service.circuit_breaker.state == CircuitState.OPEN

        print(f"\n[PASS] HALF_OPEN failure reopens circuit")


@pytest.mark.e2e
class TestAtLeastFallbackCandidates:
    """Test that system always returns at least fallback candidates."""

    @pytest.mark.asyncio
    async def test_always_returns_candidates(self):
        """
        Test that even with circuit open, we get fallback candidates.

        This ensures the system never returns empty results.
        """
        # Verify fallback has candidates
        fallback = FALLBACK_RESPONSES.get("smart_filter")
        parsed = json.loads(fallback)

        candidates = parsed.get("candidates", [])
        assert len(candidates) >= 1, "Fallback should have at least 1 candidate"

        for candidate in candidates:
            assert "agent_id" in candidate, "Candidate should have agent_id"

        print(f"\n[PASS] Fallback always returns {len(candidates)} candidates")

    @pytest.mark.asyncio
    async def test_negotiation_never_fails_due_to_circuit(self):
        """
        Test that negotiation doesn't fail just because circuit is open.

        Expected: Negotiation completes using fallback.
        """
        admin = ChannelAdminAgent()
        admin._logger = logging.getLogger("test_no_fail")
        admin.llm = None  # Simulate circuit open / no LLM

        admin._publish_event = AsyncMock()
        admin.send_to_agent = AsyncMock()

        candidates = create_candidates(3)

        channel_id = await admin.start_managing(
            channel_name="test-no-fail",
            demand_id="nf-001",
            demand={"surface_demand": "Test no fail"},
            invited_agents=candidates,
            max_rounds=5
        )

        state = admin.channels[channel_id]

        # Complete negotiation
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

        # Should complete (not fail due to missing LLM)
        assert state.status != ChannelStatus.FAILED, \
            f"Should not fail due to circuit, got {state.status}"

        print(f"\n[PASS] Negotiation completes without LLM (status: {state.status.value})")


@pytest.mark.e2e
class TestCircuitBreakerStats:
    """Test circuit breaker statistics."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Test that statistics are tracked correctly."""
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.client = MagicMock()

        service = LLMServiceWithFallback(
            llm_service=mock_llm,
            circuit_breaker=CircuitBreaker(failure_threshold=3)
        )

        # Successful calls
        mock_llm.complete = AsyncMock(return_value='{"ok": true}')
        for _ in range(5):
            await service.complete("test", fallback_key="default")

        assert service.stats["total_calls"] == 5
        assert service.stats["success_count"] == 5

        # Failed calls
        mock_llm.complete = AsyncMock(side_effect=Exception("Error"))
        for _ in range(3):
            await service.complete("test", fallback_key="default")

        assert service.stats["total_calls"] == 8
        assert service.stats["failure_count"] == 3

        # Calls when open
        # Circuit should be open now
        for _ in range(2):
            await service.complete("test", fallback_key="default")

        assert service.stats["circuit_open_count"] >= 2
        assert service.stats["fallback_count"] >= 2

        print(f"\n[PASS] Stats tracking verified")
        print(f"Stats: {json.dumps(service.stats, indent=2)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
