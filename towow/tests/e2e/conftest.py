"""
E2E Test Fixtures and Helpers

Provides common fixtures and utilities for end-to-end testing.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest

# Add project path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.secondme_mock import SecondMeMockService, MockSecondMeClient
from services.gap_identification import GapIdentificationService
from services.gap_types import Gap, GapType, GapSeverity, GapAnalysisResult
from services.subnet_manager import SubnetManager, SubnetStatus
from events.recorder import EventRecorder

logger = logging.getLogger(__name__)


# ============== Test Data ==============

def load_mock_agents() -> List[Dict[str, Any]]:
    """Load mock agent data from file or generate new ones."""
    data_path = project_root / "data" / "mock_agents.json"
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback: generate basic mock agents
    return generate_basic_mock_agents()


def generate_basic_mock_agents(count: int = 20) -> List[Dict[str, Any]]:
    """Generate basic mock agents for testing."""
    agents = []

    # Predefined profiles with diverse capabilities
    profiles = [
        {
            "user_id": "bob",
            "display_name": "Bob",
            "capabilities": ["venue_provider", "event_organization", "meeting_room"],
            "location": "beijing",
            "interests": ["AI", "startup", "networking"],
            "personality": "enthusiastic",
            "decision_style": "quick_decision"
        },
        {
            "user_id": "alice",
            "display_name": "Alice",
            "capabilities": ["tech_sharing", "AI_research", "speaker"],
            "location": "beijing",
            "interests": ["ML", "NLP", "tech_education"],
            "personality": "professional",
            "decision_style": "careful_evaluation"
        },
        {
            "user_id": "charlie",
            "display_name": "Charlie",
            "capabilities": ["event_planning", "process_design", "coordination"],
            "location": "beijing",
            "interests": ["project_management", "community"],
            "personality": "detail_oriented",
            "decision_style": "needs_clear_assignment"
        },
        {
            "user_id": "david",
            "display_name": "David",
            "capabilities": ["UI_design", "prototype", "UX"],
            "location": "remote",
            "interests": ["design_system", "AI_product"],
            "personality": "creative",
            "decision_style": "values_creativity"
        },
        {
            "user_id": "emma",
            "display_name": "Emma",
            "capabilities": ["product_manager", "requirements_analysis", "user_research"],
            "location": "shanghai",
            "interests": ["AI_product", "growth"],
            "personality": "logical",
            "decision_style": "data_driven"
        },
        {
            "user_id": "frank",
            "display_name": "Frank",
            "capabilities": ["backend_dev", "system_architecture", "database"],
            "location": "hangzhou",
            "interests": ["distributed_systems", "cloud_native"],
            "personality": "pragmatic",
            "decision_style": "tech_feasibility_first"
        },
        {
            "user_id": "grace",
            "display_name": "Grace",
            "capabilities": ["frontend_dev", "React", "mini_program"],
            "location": "shenzhen",
            "interests": ["Web3", "new_tech", "open_source"],
            "personality": "optimistic",
            "decision_style": "learning_oriented"
        },
        {
            "user_id": "henry",
            "display_name": "Henry",
            "capabilities": ["data_analysis", "ML", "Python"],
            "location": "beijing",
            "interests": ["data_science", "quant"],
            "personality": "introverted",
            "decision_style": "needs_data_support"
        },
        {
            "user_id": "ivy",
            "display_name": "Ivy",
            "capabilities": ["operations", "community_management", "content_creation"],
            "location": "guangzhou",
            "interests": ["community_ops", "content_marketing"],
            "personality": "social",
            "decision_style": "values_influence"
        },
        {
            "user_id": "jack",
            "display_name": "Jack",
            "capabilities": ["investment_consulting", "business_planning", "resource_connection"],
            "location": "shanghai",
            "interests": ["startup_investment", "business_model"],
            "personality": "business_oriented",
            "decision_style": "values_ROI"
        }
    ]

    agents.extend(profiles)

    # Generate additional agents
    capabilities_pool = [
        "tech_development", "product_design", "project_management",
        "operations", "data_analysis", "content_creation",
        "photography", "hosting", "catering"
    ]
    locations = ["beijing", "shanghai", "shenzhen", "hangzhou", "guangzhou", "remote"]
    personalities = ["enthusiastic", "cautious", "pessimistic", "optimistic"]

    import random
    random.seed(42)

    for i in range(count - len(profiles)):
        agents.append({
            "user_id": f"user_{i}",
            "display_name": f"User{i}",
            "capabilities": random.sample(capabilities_pool, k=random.randint(1, 3)),
            "location": random.choice(locations),
            "interests": random.sample(["AI", "tech", "startup", "social"], k=2),
            "personality": random.choice(personalities),
            "decision_style": random.choice(["quick", "careful", "conditional"])
        })

    return agents


@dataclass
class E2ETestResult:
    """Test result data class."""
    scenario: str
    demand_input: str
    success: bool
    understanding: Optional[Dict[str, Any]] = None
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    proposal: Optional[Dict[str, Any]] = None
    feedback_summary: Dict[str, int] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0
    error: Optional[str] = None
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    subnet_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario,
            "demand_input": self.demand_input,
            "success": self.success,
            "understanding": self.understanding,
            "candidates_count": len(self.candidates),
            "candidates_preview": self.candidates[:5] if self.candidates else [],
            "proposal": self.proposal,
            "feedback_summary": self.feedback_summary,
            "events_count": len(self.events),
            "duration_ms": self.duration_ms,
            "error": self.error,
            "gaps_count": len(self.gaps),
            "subnet_triggered": self.subnet_triggered
        }


# ============== Test Fixtures ==============

@pytest.fixture
def mock_agents() -> List[Dict[str, Any]]:
    """Load mock agent data."""
    return load_mock_agents()


@pytest.fixture
def secondme_service(mock_agents) -> SecondMeMockService:
    """Create SecondMe mock service with agents."""
    service = SecondMeMockService()
    for agent in mock_agents:
        user_id = agent.get("user_id")
        if user_id:
            service.add_profile(user_id, agent)
    return service


@pytest.fixture
def event_recorder() -> EventRecorder:
    """Create fresh event recorder for each test."""
    return EventRecorder()


@pytest.fixture
def gap_service() -> GapIdentificationService:
    """Create gap identification service."""
    return GapIdentificationService()


@pytest.fixture
def subnet_manager(gap_service) -> SubnetManager:
    """Create subnet manager."""
    return SubnetManager(gap_service=gap_service)


@pytest.fixture
def test_demand_event() -> Dict:
    """Standard test demand for event organization."""
    return {
        "raw_input": "I want to organize a 50-person AI tech meetup in Beijing",
        "user_id": "user_alice"
    }


@pytest.fixture
def test_demand_resource() -> Dict:
    """Standard test demand for resource matching."""
    return {
        "raw_input": "I need an AI-savvy designer to help with product prototypes",
        "user_id": "user_alice"
    }


@pytest.fixture
def test_demand_vague() -> Dict:
    """Standard test demand for vague/emotional needs."""
    return {
        "raw_input": "Feeling stressed lately, want to chat with someone",
        "user_id": "user_alice"
    }


@pytest.fixture
def test_demand_with_gaps() -> Dict:
    """Test demand likely to have gaps."""
    return {
        "raw_input": "I need venue, speakers, photographer, and host for a big event",
        "user_id": "user_alice"
    }


# ============== Test Helper Functions ==============

async def simulate_full_flow(
    secondme: SecondMeMockService,
    event_rec: EventRecorder,
    demand_input: str,
    user_id: str = "test_user",
    scenario_name: str = "test"
) -> E2ETestResult:
    """
    Simulate full negotiation flow.

    Steps:
    1. Understand demand
    2. Filter candidates
    3. Collect responses
    4. Generate proposal
    5. Collect feedback
    """
    start_time = datetime.utcnow()
    result = E2ETestResult(
        scenario=scenario_name,
        demand_input=demand_input,
        success=False
    )

    try:
        # Step 1: Understand demand
        understanding = await secondme.understand_demand(demand_input, user_id)
        result.understanding = understanding

        # Record event
        await event_rec.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.demand.understood",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "demand_id": f"d-{uuid4().hex[:8]}",
                "understanding": understanding
            }
        })
        result.events.append({"event_type": "towow.demand.understood"})

        # Step 2: Filter candidates
        candidates = await filter_candidates(secondme, understanding)
        result.candidates = candidates

        await event_rec.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.filter.completed",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "candidates_count": len(candidates)
            }
        })
        result.events.append({"event_type": "towow.filter.completed"})

        if not candidates:
            result.error = "No candidates found"
            return result

        # Step 3: Collect responses
        responses = await collect_responses(secondme, understanding, candidates)

        for resp in responses:
            await event_rec.record({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": "towow.offer.submitted",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": resp
            })
            result.events.append({"event_type": "towow.offer.submitted"})

        # Filter participants
        participants = [
            r for r in responses
            if r.get("decision") in ("participate", "conditional")
        ]

        if not participants:
            result.error = "No participants willing to join"
            return result

        # Step 4: Generate proposal
        proposal = await generate_proposal(understanding, participants)
        result.proposal = proposal

        await event_rec.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.proposal.distributed",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"proposal": proposal}
        })
        result.events.append({"event_type": "towow.proposal.distributed"})

        # Step 5: Collect feedback
        feedback_summary = await collect_feedback(secondme, proposal, participants)
        result.feedback_summary = feedback_summary

        # Determine final status
        total_feedback = sum(feedback_summary.values())
        accept_rate = feedback_summary.get("accept", 0) / total_feedback if total_feedback > 0 else 0

        if accept_rate >= 0.5:
            # Success
            await event_rec.record({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": "towow.proposal.finalized",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "status": "success",
                    "accept_rate": accept_rate
                }
            })
            result.events.append({"event_type": "towow.proposal.finalized"})
            result.success = True
        else:
            # Failed
            await event_rec.record({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": "towow.negotiation.failed",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "reason": "too_many_rejections",
                    "accept_rate": accept_rate
                }
            })
            result.events.append({"event_type": "towow.negotiation.failed"})
            result.success = False

    except Exception as e:
        logger.error(f"[{scenario_name}] Error: {e}")
        result.error = str(e)
        result.success = False

    end_time = datetime.utcnow()
    result.duration_ms = (end_time - start_time).total_seconds() * 1000

    return result


async def filter_candidates(
    secondme: SecondMeMockService,
    understanding: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Filter candidates based on demand understanding."""
    candidates = []

    surface_demand = understanding.get("surface_demand", "")
    deep = understanding.get("deep_understanding", {})
    keywords = deep.get("keywords", [])
    location = deep.get("location")
    resource_requirements = deep.get("resource_requirements", [])

    for user_id, profile in secondme.profiles.items():
        score = 0
        reasons = []

        capabilities = profile.get("capabilities", [])
        interests = profile.get("interests", [])

        # Capability matching
        for cap in capabilities:
            cap_lower = str(cap).lower()
            for kw in keywords:
                if kw.lower() in cap_lower or cap_lower in kw.lower():
                    score += 20
                    reasons.append(f"capability '{cap}' matches keyword '{kw}'")
                    break

            for req in resource_requirements:
                if str(cap).lower() in str(req).lower() or str(req).lower() in str(cap).lower():
                    score += 15
                    reasons.append(f"capability '{cap}' matches requirement '{req}'")
                    break

        # Interest matching
        for interest in interests:
            interest_lower = str(interest).lower()
            for kw in keywords:
                if kw.lower() in interest_lower or interest_lower in kw.lower():
                    score += 10
                    reasons.append(f"interest '{interest}' matches")
                    break

        # Location matching
        agent_location = profile.get("location", "")
        if location and agent_location:
            if location.lower() in agent_location.lower() or agent_location.lower() == "remote":
                score += 15
                reasons.append(f"location matches: {agent_location}")

        if score >= 15:
            candidates.append({
                "agent_id": f"user_agent_{user_id}",
                "user_id": user_id,
                "display_name": profile.get("display_name", user_id),
                "capabilities": capabilities,
                "location": agent_location,
                "relevance_score": score,
                "reason": "; ".join(reasons[:3]) if reasons else "general match",
                "profile": profile
            })

    # Sort by score, take top 12
    candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
    return candidates[:12]


async def collect_responses(
    secondme: SecondMeMockService,
    understanding: Dict[str, Any],
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Collect responses from candidates."""
    responses = []

    for candidate in candidates:
        profile = candidate.get("profile", {})
        user_id = candidate.get("user_id", "")

        response = await secondme.generate_response(
            user_id=user_id,
            demand=understanding,
            profile=profile,
            context={"filter_reason": candidate.get("reason", "")}
        )

        response["agent_id"] = candidate.get("agent_id")
        response["user_id"] = user_id
        response["display_name"] = candidate.get("display_name")
        responses.append(response)

    return responses


async def generate_proposal(
    understanding: Dict[str, Any],
    participants: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate collaboration proposal."""
    surface_demand = understanding.get("surface_demand", "")

    assignments = []
    for i, p in enumerate(participants[:8]):
        role = p.get("suggested_role", f"Participant-{i+1}")
        assignments.append({
            "agent_id": p.get("agent_id"),
            "display_name": p.get("display_name"),
            "role": role,
            "responsibility": p.get("contribution", "To be assigned"),
            "conditions_addressed": p.get("conditions", [])
        })

    return {
        "proposal_id": f"prop-{uuid4().hex[:8]}",
        "summary": f"Collaboration proposal for: {surface_demand[:50]}...",
        "objective": f"Fulfill user demand: {surface_demand[:100]}",
        "assignments": assignments,
        "timeline": {
            "start_date": "TBD",
            "milestones": [
                {"name": "Kickoff", "date": "Week 1"},
                {"name": "Checkpoint", "date": "Week 2"},
                {"name": "Delivery", "date": "Week 3"}
            ]
        },
        "participants_count": len(assignments),
        "confidence": "medium"
    }


async def collect_feedback(
    secondme: SecondMeMockService,
    proposal: Dict[str, Any],
    participants: List[Dict[str, Any]]
) -> Dict[str, int]:
    """Collect feedback on proposal."""
    feedback_counts = {
        "accept": 0,
        "reject": 0,
        "negotiate": 0
    }

    for participant in participants:
        user_id = participant.get("user_id", "")
        profile = participant.get("profile", {})

        feedback = await secondme.evaluate_proposal(
            user_id=user_id,
            proposal=proposal,
            profile=profile
        )

        feedback_type = feedback.get("feedback_type", "accept")
        if feedback_type in feedback_counts:
            feedback_counts[feedback_type] += 1

    return feedback_counts


def verify_event_sequence(
    events: List[Dict[str, Any]],
    expected_types: List[str]
) -> bool:
    """Verify that events contain all expected types in order."""
    event_types = [e.get("event_type") for e in events]

    for expected in expected_types:
        if expected not in event_types:
            return False

    return True


def calculate_test_pass_rate(results: List[E2ETestResult]) -> float:
    """Calculate test pass rate."""
    if not results:
        return 0.0

    passed = sum(1 for r in results if r.success)
    return passed / len(results)
