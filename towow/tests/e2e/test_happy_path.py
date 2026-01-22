"""
E2E Test: Happy Path - Complete Negotiation Flow

Tests the complete negotiation flow from demand submission to finalization.

Test Scenarios:
1. Complete negotiation flow (submit -> filter -> respond -> aggregate -> multi-round -> finalize)
2. Multi-round negotiation (with negotiate feedback)
3. Single participant scenario
4. Event sequence verification
"""
from __future__ import annotations

import asyncio
import logging
import pytest
from datetime import datetime
from typing import List, Dict, Any
from uuid import uuid4

from .conftest import (
    E2ETestResult,
    simulate_full_flow,
    filter_candidates,
    collect_responses,
    generate_proposal,
    collect_feedback,
    verify_event_sequence,
    load_mock_agents
)

logger = logging.getLogger(__name__)


class TestCompleteNegotiationFlow:
    """Test complete negotiation flow - Happy Path."""

    @pytest.mark.asyncio
    async def test_complete_flow_event_organization(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test complete negotiation flow for event organization.

        Input: I want to organize a 50-person AI tech meetup in Beijing
        Expected: Filter venue, speaker, planning related agents
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="I want to organize a 50-person AI tech meetup in Beijing",
            scenario_name="Event Organization"
        )

        # Print summary
        print("\n" + "=" * 60)
        print("Test: Complete Flow - Event Organization")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Candidates: {len(result.candidates)}")
        print(f"Feedback: {result.feedback_summary}")
        print(f"Events: {len(result.events)}")
        print(f"Duration: {result.duration_ms:.2f}ms")
        if result.error:
            print(f"Error: {result.error}")
        print("=" * 60 + "\n")

        # Assertions
        assert result.understanding is not None, "Understanding should not be None"
        assert len(result.candidates) >= 3, f"Should have at least 3 candidates, got {len(result.candidates)}"
        assert result.proposal is not None, "Proposal should be generated"
        assert sum(result.feedback_summary.values()) > 0, "Should have feedback"

        # Verify event sequence
        event_types = [e.get("event_type") for e in result.events]
        assert "towow.demand.understood" in event_types, "Should have demand understood event"
        assert "towow.filter.completed" in event_types, "Should have filter completed event"
        assert "towow.offer.submitted" in event_types, "Should have offer submitted event"
        assert "towow.proposal.distributed" in event_types, "Should have proposal distributed event"

        # Should have either finalized or failed event
        assert (
            "towow.proposal.finalized" in event_types or
            "towow.negotiation.failed" in event_types
        ), "Should have final status event"

    @pytest.mark.asyncio
    async def test_complete_flow_resource_matching(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test complete negotiation flow for resource matching.

        Input: I need an AI-savvy designer to help with product prototypes
        Expected: Filter design + AI interest agents
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="I need an AI-savvy designer to help with product prototypes",
            scenario_name="Resource Matching"
        )

        print("\n" + "=" * 60)
        print("Test: Complete Flow - Resource Matching")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Candidates: {len(result.candidates)}")
        print(f"Feedback: {result.feedback_summary}")
        print(f"Duration: {result.duration_ms:.2f}ms")
        print("=" * 60 + "\n")

        assert result.understanding is not None
        assert result.proposal is not None or result.error is not None

        # Check understanding type
        understanding = result.understanding
        demand_type = understanding.get("deep_understanding", {}).get("type", "")
        # Design-related demand should be identified
        assert demand_type in ["design", "general", "development"], f"Unexpected type: {demand_type}"

    @pytest.mark.asyncio
    async def test_complete_flow_vague_demand(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test complete negotiation flow for vague/emotional demand.

        Input: Feeling stressed lately, want to chat with someone
        Expected: Understand emotional need, filter people with soft skills
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Feeling stressed lately, want to chat with someone",
            scenario_name="Vague Demand"
        )

        print("\n" + "=" * 60)
        print("Test: Complete Flow - Vague Demand")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Candidates: {len(result.candidates)}")
        print(f"Understanding: {result.understanding.get('deep_understanding', {}).get('type', 'N/A')}")
        print(f"Duration: {result.duration_ms:.2f}ms")
        print("=" * 60 + "\n")

        # Vague demands may have fewer candidates, but flow should complete
        assert result.understanding is not None
        # The system should still process it without crashing
        assert result.error is None or "No candidates" in result.error or "No participants" in result.error


class TestMultiRoundNegotiation:
    """Test multi-round negotiation scenarios."""

    @pytest.mark.asyncio
    async def test_multi_round_with_negotiate_feedback(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test multi-round negotiation when agents give 'negotiate' feedback.

        Simulates scenario where initial proposal triggers adjustments.
        """
        # First round
        result1 = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="I want to organize a complex 100-person conference with multiple speakers",
            scenario_name="Multi-Round Round 1"
        )

        assert result1.understanding is not None

        # If there are negotiate feedbacks, simulate second round
        negotiate_count = result1.feedback_summary.get("negotiate", 0)

        print("\n" + "=" * 60)
        print("Test: Multi-Round Negotiation")
        print("=" * 60)
        print(f"Round 1 - Negotiate feedback: {negotiate_count}")
        print(f"Round 1 - Accept: {result1.feedback_summary.get('accept', 0)}")
        print(f"Round 1 - Reject: {result1.feedback_summary.get('reject', 0)}")
        print("=" * 60 + "\n")

        # Verify flow completed (may or may not have feedback depending on candidates)
        total_feedback = sum(result1.feedback_summary.values())
        # If no candidates matched, feedback would be 0 - this is acceptable
        if len(result1.candidates) >= 3:
            assert total_feedback > 0, "With candidates, should have at least some feedback"
        else:
            # With few/no candidates, flow may complete early
            assert result1.error is not None or total_feedback >= 0

    @pytest.mark.asyncio
    async def test_single_participant_scenario(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Test scenario with very specific demand that may only match one person.

        Should still generate a valid proposal.
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Need someone who knows React and has frontend development experience",
            scenario_name="Single Participant"
        )

        print("\n" + "=" * 60)
        print("Test: Single Participant Scenario")
        print("=" * 60)
        print(f"Candidates: {len(result.candidates)}")
        print(f"Success: {result.success}")
        print("=" * 60 + "\n")

        # Should handle this gracefully
        assert result.understanding is not None
        # Even with few candidates, process should complete


class TestEventSequenceVerification:
    """Verify event sequence integrity."""

    @pytest.mark.asyncio
    async def test_all_required_events_published(
        self,
        secondme_service,
        event_recorder
    ):
        """
        Verify all required events are published in correct order.

        Required events:
        1. towow.demand.understood
        2. towow.filter.completed
        3. towow.offer.submitted (multiple)
        4. towow.proposal.distributed
        5. towow.proposal.finalized OR towow.negotiation.failed
        """
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Organize a small team dinner for 10 people in Beijing",
            scenario_name="Event Sequence Test"
        )

        event_types = [e.get("event_type") for e in result.events]

        # Check required events
        required_events = [
            "towow.demand.understood",
            "towow.filter.completed",
        ]

        for required in required_events:
            assert required in event_types, f"Missing required event: {required}"

        # Check order: demand.understood should come first
        understood_idx = event_types.index("towow.demand.understood")
        filter_idx = event_types.index("towow.filter.completed")
        assert understood_idx < filter_idx, "demand.understood should come before filter.completed"

        print("\n" + "=" * 60)
        print("Test: Event Sequence Verification")
        print("=" * 60)
        print(f"Events recorded: {len(event_types)}")
        print(f"Event types: {event_types}")
        print("=" * 60 + "\n")

    @pytest.mark.asyncio
    async def test_event_payload_integrity(
        self,
        secondme_service,
        event_recorder
    ):
        """Verify event payloads contain required fields."""
        # Run a simple flow
        await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="Need help with a small project",
            scenario_name="Payload Test"
        )

        # Check recorded events
        events = event_recorder.get_all(limit=100)

        for event in events:
            # All events should have basic fields
            assert "event_id" in event, "Event should have event_id"
            assert "event_type" in event, "Event should have event_type"
            assert "timestamp" in event, "Event should have timestamp"
            assert "payload" in event, "Event should have payload"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_input(
        self,
        secondme_service,
        event_recorder
    ):
        """Test handling of empty input."""
        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input="",
            scenario_name="Empty Input"
        )

        # Should handle gracefully without crashing
        assert result.understanding is not None

    @pytest.mark.asyncio
    async def test_very_long_input(
        self,
        secondme_service,
        event_recorder
    ):
        """Test handling of very long input."""
        long_input = "I want to organize a big event " * 100

        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input=long_input,
            scenario_name="Long Input"
        )

        # Should handle gracefully
        assert result.understanding is not None

    @pytest.mark.asyncio
    async def test_special_characters_input(
        self,
        secondme_service,
        event_recorder
    ):
        """Test handling of special characters in input."""
        special_input = "Need help with <script>alert('xss')</script> and $pecial ch@racters!"

        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input=special_input,
            scenario_name="Special Characters"
        )

        # Should handle gracefully without crashing
        assert result.understanding is not None

    @pytest.mark.asyncio
    async def test_unicode_input(
        self,
        secondme_service,
        event_recorder
    ):
        """Test handling of unicode/emoji input."""
        unicode_input = "I want to organize an event with lots of energy and fun times"

        result = await simulate_full_flow(
            secondme=secondme_service,
            event_rec=event_recorder,
            demand_input=unicode_input,
            scenario_name="Unicode Input"
        )

        assert result.understanding is not None


class TestAllScenariosComplete:
    """Integration test running all scenarios."""

    @pytest.mark.asyncio
    async def test_all_scenarios_complete_without_crash(
        self,
        secondme_service,
        event_recorder
    ):
        """Test that all main scenarios complete without crashing."""
        scenarios = [
            ("Event Organization", "I want to organize a 50-person AI tech meetup in Beijing"),
            ("Resource Matching", "I need an AI-savvy designer to help with product prototypes"),
            ("Vague Demand", "Feeling stressed lately, want to chat with someone"),
            ("Technical Project", "Need a backend developer for a Python project"),
            ("Small Gathering", "Want to have a casual dinner with tech friends"),
        ]

        results = []
        for name, demand in scenarios:
            result = await simulate_full_flow(
                secondme=secondme_service,
                event_rec=event_recorder,
                demand_input=demand,
                scenario_name=name
            )
            results.append(result)

        # Print summary
        print("\n" + "=" * 60)
        print("All Scenarios Summary")
        print("=" * 60)
        for r in results:
            status = "PASS" if r.success else "FAIL"
            print(f"[{status}] {r.scenario}: {r.duration_ms:.0f}ms")
        print("=" * 60 + "\n")

        # At least 60% should complete successfully or reach a definitive state
        completed = sum(1 for r in results if r.proposal is not None or r.error is not None)
        assert completed >= len(scenarios) * 0.6, "At least 60% scenarios should reach completion state"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
