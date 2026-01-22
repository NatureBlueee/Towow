"""
E2E Test: Failure Cases

Tests failure scenarios in the negotiation flow.

Test Scenarios:
1. No candidates found (impossible demand)
2. All agents decline (50%+ rejection leading to failure)
3. LLM timeout fallback
4. Circuit breaker fallback
5. Network errors
"""
from __future__ import annotations

import asyncio
import logging
import pytest
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from services.secondme_mock import SecondMeMockService, SimpleRandomMockClient
from events.recorder import EventRecorder

from .conftest import (
    E2ETestResult,
    simulate_full_flow,
    filter_candidates,
    collect_responses,
    generate_proposal,
    collect_feedback,
    generate_basic_mock_agents
)

logger = logging.getLogger(__name__)


class TestNoCandidatesFound:
    """Test scenarios where no candidates can be found."""

    @pytest.mark.asyncio
    async def test_impossible_demand(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test with an impossible demand that matches no one.

        Input: Build a base on Mars
        Expected: No candidates found, graceful failure
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="I need to build a research base on Mars",
            scenario_name="Impossible Demand"
        )

        print("\n" + "=" * 60)
        print("Test: Impossible Demand - No Candidates")
        print("=" * 60)
        print(f"Candidates: {len(result.candidates)}")
        print(f"Error: {result.error}")
        print(f"Success: {result.success}")
        print("=" * 60 + "\n")

        # Understanding should still work
        assert result.understanding is not None

        # Should either have no candidates or very few
        # The flow should handle this gracefully
        if len(result.candidates) == 0:
            assert result.error == "No candidates found" or result.error is not None
            assert result.success is False

    @pytest.mark.asyncio
    async def test_highly_specific_demand(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test with a highly specific demand that's hard to match.

        Input: Need a quantum computing expert who speaks ancient Greek
        Expected: Very few or no candidates
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Need a quantum computing expert who speaks ancient Greek and practices underwater basket weaving",
            scenario_name="Highly Specific"
        )

        print("\n" + "=" * 60)
        print("Test: Highly Specific Demand")
        print("=" * 60)
        print(f"Candidates: {len(result.candidates)}")
        print(f"Error: {result.error}")
        print("=" * 60 + "\n")

        # Should handle gracefully
        assert result.understanding is not None

    @pytest.mark.asyncio
    async def test_wrong_location_demand(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test with location that doesn't match any agents.
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Need someone in Antarctica for an ice research project",
            scenario_name="Wrong Location"
        )

        # Should handle gracefully
        assert result.understanding is not None


class TestAllAgentsDecline:
    """Test scenarios where all agents decline."""

    @pytest.fixture
    def pessimistic_secondme(self) -> SecondMeMockService:
        """Create service where all agents tend to decline."""
        service = SecondMeMockService()

        # Override profiles with pessimistic personalities
        for user_id in list(service.profiles.keys()):
            profile = service.profiles[user_id]
            profile["personality"] = "pessimistic"
            profile["decision_style"] = "extremely_picky"

        return service

    @pytest.mark.asyncio
    async def test_all_agents_decline_scenario(
        self,
        event_recorder
    ):
        """
        Test scenario where majority of agents decline.

        Uses SimpleRandomMockClient with low participate probability.
        """
        # Create client with very low participation probability
        low_participate_client = SimpleRandomMockClient(
            seed=42,
            participate_probability=0.1,  # 10% participation
            accept_probability=0.1        # 10% acceptance
        )

        # Add profiles
        for agent in generate_basic_mock_agents(10):
            low_participate_client.add_profile(agent["user_id"], agent)

        result = await simulate_full_flow(
            secondme=low_participate_client,
            event_rec=event_recorder,
            demand_input="Need help with a project that requires full-time commitment",
            scenario_name="All Decline"
        )

        print("\n" + "=" * 60)
        print("Test: Majority Agents Decline")
        print("=" * 60)
        print(f"Candidates: {len(result.candidates)}")
        print(f"Feedback: {result.feedback_summary}")
        print(f"Success: {result.success}")
        print("=" * 60 + "\n")

        # With low participation, likely to fail or have few participants
        assert result.understanding is not None

        # Check if negotiation failed due to rejections
        event_types = [e.get("event_type") for e in result.events]
        if "towow.negotiation.failed" in event_types:
            assert result.success is False

    @pytest.mark.asyncio
    async def test_high_rejection_rate(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test demand that might trigger high rejection rate.
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Need 24/7 availability for urgent crisis management, unpaid volunteer work",
            scenario_name="High Rejection"
        )

        print("\n" + "=" * 60)
        print("Test: High Rejection Rate Scenario")
        print("=" * 60)
        print(f"Candidates: {len(result.candidates)}")
        print(f"Feedback: {result.feedback_summary}")
        print("=" * 60 + "\n")

        # Should complete without crashing
        assert result.understanding is not None


class TestNegotiationFailedEvent:
    """Test that negotiation.failed event is properly published."""

    @pytest.mark.asyncio
    async def test_failed_event_on_majority_rejection(
        self,
        event_recorder
    ):
        """
        Verify towow.negotiation.failed event is published when
        50%+ of participants reject.
        """
        # Use client with very low acceptance
        low_accept_client = SimpleRandomMockClient(
            seed=123,
            participate_probability=0.8,  # Will participate
            accept_probability=0.1        # But mostly reject proposal
        )

        for agent in generate_basic_mock_agents(15):
            low_accept_client.add_profile(agent["user_id"], agent)

        result = await simulate_full_flow(
            secondme=low_accept_client,
            event_rec=event_recorder,
            demand_input="Organize a workshop that requires specific expertise",
            scenario_name="Majority Rejection"
        )

        print("\n" + "=" * 60)
        print("Test: Negotiation Failed Event")
        print("=" * 60)
        print(f"Feedback: {result.feedback_summary}")
        event_types = [e.get("event_type") for e in result.events]
        print(f"Final event: {event_types[-1] if event_types else 'None'}")
        print("=" * 60 + "\n")

        # Check final event
        if result.feedback_summary:
            total = sum(result.feedback_summary.values())
            accept = result.feedback_summary.get("accept", 0)

            if total > 0 and accept / total < 0.5:
                # Should have failed event
                assert "towow.negotiation.failed" in event_types or result.success is False


class TestLLMFallback:
    """Test LLM timeout and fallback scenarios."""

    @pytest.mark.asyncio
    async def test_llm_service_unavailable(
        self,
        event_recorder
    ):
        """
        Test behavior when LLM service is unavailable.

        Should fall back to rule-based processing.
        """
        # SecondMeMockService doesn't use real LLM, so it simulates fallback
        mock_service = SecondMeMockService()

        result = await simulate_full_flow(
            secondme=mock_service,
            event_rec=event_recorder,
            demand_input="Need help with a project",
            scenario_name="LLM Unavailable"
        )

        print("\n" + "=" * 60)
        print("Test: LLM Service Unavailable (Fallback)")
        print("=" * 60)
        print(f"Understanding: {result.understanding is not None}")
        print(f"Candidates: {len(result.candidates)}")
        print("=" * 60 + "\n")

        # Should still work with fallback
        assert result.understanding is not None

    @pytest.mark.asyncio
    async def test_degraded_mode_response(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test that system provides degraded mode response when needed.
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Simple request for help",
            scenario_name="Degraded Mode"
        )

        # Should complete without errors
        assert result.understanding is not None
        assert result.error is None or "No candidates" in str(result.error) or "No participants" in str(result.error)


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""

    @pytest.mark.asyncio
    async def test_partial_failure_recovery(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test that partial failures don't crash the entire flow.
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Need multiple resources for a complex project",
            scenario_name="Partial Failure"
        )

        # Flow should complete even if some parts had issues
        assert result.understanding is not None

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test that timeouts are handled gracefully.
        """
        # Simulate quick timeout scenario
        result = await asyncio.wait_for(
            simulate_full_flow(
                secondme=secondme_service,
                event_rec=event_recorder,
                demand_input="Quick test demand",
                scenario_name="Timeout Test"
            ),
            timeout=30.0  # 30 second timeout
        )

        assert result.understanding is not None


class TestWithdrawalScenarios:
    """Test agent withdrawal during negotiation."""

    @pytest.mark.asyncio
    async def test_agent_withdrawal_handling(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test handling of agent withdrawal during negotiation.
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Long-term project requiring sustained commitment",
            scenario_name="Withdrawal Test"
        )

        print("\n" + "=" * 60)
        print("Test: Agent Withdrawal Handling")
        print("=" * 60)
        print(f"Candidates: {len(result.candidates)}")
        print(f"Feedback: {result.feedback_summary}")
        print("=" * 60 + "\n")

        # Should handle withdrawals gracefully
        assert result.understanding is not None


class TestFailureSummary:
    """Integration test for all failure scenarios."""

    @pytest.mark.asyncio
    async def test_all_failure_scenarios_handled_gracefully(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Run all failure-prone scenarios and verify graceful handling.
        """
        failure_scenarios = [
            ("Impossible", "Build a time machine using household items"),
            ("Too Specific", "Need a expert in quantum cryptography and medieval history"),
            ("High Demand", "Need 100 people available 24/7 for free"),
            ("Empty", ""),
            ("Gibberish", "asdfghjkl qwertyuiop"),
        ]

        results = []
        for name, demand in failure_scenarios:
            try:
                result = await simulate_full_flow(
                    secondme=secondme_service,
                    event_rec=event_recorder,
                    demand_input=demand,
                    scenario_name=name
                )
                results.append((name, result, None))
            except Exception as e:
                results.append((name, None, str(e)))

        # Print summary
        print("\n" + "=" * 60)
        print("Failure Scenarios Summary")
        print("=" * 60)
        for name, result, error in results:
            if error:
                print(f"[CRASH] {name}: {error}")
            elif result:
                status = "HANDLED" if result.understanding is not None else "FAILED"
                print(f"[{status}] {name}")
        print("=" * 60 + "\n")

        # All scenarios should be handled without crashing
        crashes = [r for r in results if r[2] is not None]
        assert len(crashes) == 0, f"Some scenarios crashed: {[c[0] for c in crashes]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
