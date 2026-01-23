"""Tests for UserAgent response generation - TASK-T03."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the class under test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openagents.agents.user_agent import UserAgent, OfferResponse, NegotiationPoint


class TestUserAgentV4ResponseType:
    """Tests for v4 response_type and negotiation_points."""

    @pytest.fixture
    def profile_with_capabilities(self):
        """Profile with matching capabilities."""
        return {
            "name": "Bob",
            "user_id": "bob",
            "location": "Beijing",
            "capabilities": ["venue_management", "event_planning"],
            "tags": ["venue", "events", "community"],
            "interests": ["AI", "technology", "networking"],
            "availability": "weekends",
            "description": "I have a 50-person meeting room in Zhongguancun",
        }

    def test_parse_response_with_response_type_offer(self, profile_with_capabilities):
        """Test _parse_response correctly parses response_type: offer."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '''```json
{
  "response_type": "offer",
  "decision": "participate",
  "contribution": "I can provide a 50-person meeting room",
  "conditions": [],
  "reasoning": "My venue matches the requirements",
  "decline_reason": "",
  "confidence": 85,
  "enthusiasm_level": "high",
  "suggested_role": "Venue Provider",
  "negotiation_points": []
}
```'''

        result = agent._parse_response(response)

        assert result["response_type"] == "offer"
        assert result["decision"] == "participate"
        assert result["negotiation_points"] == []

    def test_parse_response_with_response_type_negotiate(self, profile_with_capabilities):
        """Test _parse_response correctly parses response_type: negotiate with points."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '''```json
{
  "response_type": "negotiate",
  "decision": "conditional",
  "contribution": "I can provide a meeting room",
  "conditions": ["Must be on weekends"],
  "reasoning": "Weekday availability is limited",
  "decline_reason": "",
  "confidence": 70,
  "enthusiasm_level": "medium",
  "suggested_role": "Venue Provider",
  "negotiation_points": [
    {
      "aspect": "时间安排",
      "current_value": "周末",
      "desired_value": "工作日晚上",
      "reason": "周末有其他安排"
    }
  ]
}
```'''

        result = agent._parse_response(response)

        assert result["response_type"] == "negotiate"
        assert result["decision"] == "conditional"
        assert len(result["negotiation_points"]) == 1
        assert result["negotiation_points"][0]["aspect"] == "时间安排"
        assert result["negotiation_points"][0]["desired_value"] == "工作日晚上"

    def test_parse_response_invalid_response_type_defaults_to_offer(self, profile_with_capabilities):
        """Test that invalid response_type defaults to offer."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '{"response_type": "invalid", "decision": "participate"}'

        result = agent._parse_response(response)

        assert result["response_type"] == "offer"

    def test_mock_response_includes_v4_fields(self, profile_with_capabilities):
        """Test that mock response includes response_type and negotiation_points."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        result = agent._mock_response({})

        assert "response_type" in result
        assert result["response_type"] == "offer"
        assert "negotiation_points" in result
        assert result["negotiation_points"] == []

    def test_fallback_response_includes_message_id(self, profile_with_capabilities):
        """Test that fallback response includes message_id."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        result = agent._get_fallback_response({}, "msg-test12345")

        assert "message_id" in result
        assert result["message_id"] == "msg-test12345"
        assert "response_type" in result

    def test_summarize_negotiation_points_empty(self, profile_with_capabilities):
        """Test _summarize_negotiation_points with empty list."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        result = agent._summarize_negotiation_points([])

        assert result is None

    def test_summarize_negotiation_points_with_data(self, profile_with_capabilities):
        """Test _summarize_negotiation_points with data."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        points = [
            {"aspect": "时间", "desired_value": "周末"},
            {"aspect": "角色", "desired_value": "技术顾问"},
        ]

        result = agent._summarize_negotiation_points(points)

        assert result is not None
        assert "时间: 期望周末" in result
        assert "角色: 期望技术顾问" in result


class TestNegotiationPointDataclass:
    """Tests for NegotiationPoint dataclass."""

    def test_negotiation_point_to_dict(self):
        """Test NegotiationPoint.to_dict()."""
        point = NegotiationPoint(
            aspect="时间安排",
            current_value="周末",
            desired_value="工作日晚上",
            reason="周末有其他安排"
        )

        result = point.to_dict()

        assert result["aspect"] == "时间安排"
        assert result["current_value"] == "周末"
        assert result["desired_value"] == "工作日晚上"
        assert result["reason"] == "周末有其他安排"


class TestOfferResponseDataclass:
    """Tests for OfferResponse dataclass."""

    def test_offer_response_to_dict(self):
        """Test OfferResponse.to_dict()."""
        offer = OfferResponse(
            offer_id="offer-123",
            agent_id="bob",
            display_name="Bob",
            demand_id="d-456",
            response_type="negotiate",
            decision="conditional",
            contribution="I can provide a meeting room",
            conditions=["Must be on weekends"],
            negotiation_points=[
                NegotiationPoint(
                    aspect="时间",
                    current_value="周末",
                    desired_value="工作日",
                    reason="周末忙"
                )
            ],
            reasoning="有部分能力匹配",
            confidence=70,
            message_id="msg-789",
            submitted_at="2026-01-23T10:00:00Z"
        )

        result = offer.to_dict()

        assert result["offer_id"] == "offer-123"
        assert result["response_type"] == "negotiate"
        assert result["decision"] == "conditional"
        assert len(result["negotiation_points"]) == 1
        assert result["negotiation_points"][0]["aspect"] == "时间"
        assert result["message_id"] == "msg-789"


class TestUserAgentV4Integration:
    """Integration tests for v4 features."""

    @pytest.mark.asyncio
    async def test_llm_generate_response_includes_message_id(self):
        """Test that _llm_generate_response includes message_id."""
        profile = {
            "name": "Integration Test User",
            "capabilities": ["event_planning"],
        }

        agent = UserAgent(user_id="test_user", profile=profile)

        # Mock LLM to return valid response
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value=json.dumps({
            "response_type": "offer",
            "decision": "participate",
            "contribution": "test",
            "confidence": 80
        }))
        agent.llm = mock_llm

        demand = {"demand_id": "d-test", "surface_demand": "test"}

        result = await agent._llm_generate_response(demand, "test reason")

        assert "message_id" in result
        assert result["message_id"].startswith("msg-")
        assert result["response_type"] == "offer"

    @pytest.mark.asyncio
    async def test_llm_generate_response_fallback_on_error(self):
        """Test that _llm_generate_response falls back on LLM error."""
        profile = {
            "name": "Test User",
            "capabilities": ["event_planning"],
        }

        agent = UserAgent(user_id="test_user", profile=profile)

        # Mock LLM to raise exception
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(side_effect=Exception("LLM Error"))
        agent.llm = mock_llm

        demand = {"demand_id": "d-test", "surface_demand": "test"}

        result = await agent._llm_generate_response(demand, "test reason")

        # Should return fallback response with message_id
        assert "message_id" in result
        assert "response_type" in result
        assert result["response_type"] == "offer"

    @pytest.mark.asyncio
    async def test_generate_response_with_negotiate_type(self):
        """Test generating negotiate type response."""
        profile = {
            "name": "Negotiator",
            "capabilities": ["event_planning"],
        }

        agent = UserAgent(user_id="negotiator", profile=profile)

        # Mock LLM to return negotiate response
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value=json.dumps({
            "response_type": "negotiate",
            "decision": "conditional",
            "contribution": "I can help",
            "conditions": ["weekend only"],
            "confidence": 65,
            "negotiation_points": [
                {
                    "aspect": "timing",
                    "current_value": "weekday",
                    "desired_value": "weekend",
                    "reason": "availability"
                }
            ]
        }))
        agent.llm = mock_llm

        demand = {"demand_id": "d-test", "surface_demand": "event"}

        result = await agent._llm_generate_response(demand, "matching skills")

        assert result["response_type"] == "negotiate"
        assert len(result["negotiation_points"]) == 1
        assert result["negotiation_points"][0]["aspect"] == "timing"


class TestUserAgentResponseGeneration:
    """Tests for UserAgent._generate_response and related methods."""

    @pytest.fixture
    def profile_with_capabilities(self):
        """Profile with matching capabilities."""
        return {
            "name": "Bob",
            "user_id": "bob",
            "location": "Beijing",
            "capabilities": ["venue_management", "event_planning"],
            "tags": ["venue", "events", "community"],
            "interests": ["AI", "technology", "networking"],
            "availability": "weekends",
            "description": "I have a 50-person meeting room in Zhongguancun",
        }

    @pytest.fixture
    def profile_without_capabilities(self):
        """Profile without matching capabilities."""
        return {
            "name": "Alice",
            "user_id": "alice",
            "location": "Shanghai",
            "capabilities": ["software_development", "machine_learning"],
            "tags": ["coding", "ML", "backend"],
            "interests": ["programming", "AI research"],
            "availability": "flexible",
            "description": "Senior software engineer",
        }

    @pytest.fixture
    def demand_venue(self):
        """Demand requiring venue resources."""
        return {
            "demand_id": "d-test001",
            "surface_demand": "I want to host an AI meetup in Beijing, need a venue and speakers",
            "deep_understanding": {
                "type": "event_organization",
                "motivation": "community building",
                "location": "Beijing",
            },
            "capability_tags": ["venue", "speaker", "event_planning"],
            "context": {
                "location": "Beijing",
                "expected_attendees": 50,
            },
        }

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service."""
        mock = AsyncMock()
        return mock

    def test_build_profile_summary_with_list_capabilities(self, profile_with_capabilities):
        """Test _build_profile_summary with list capabilities."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        summary = agent._build_profile_summary()

        assert "Bob" in summary
        assert "Beijing" in summary
        assert "venue_management" in summary or "event_planning" in summary
        assert "weekends" in summary

    def test_build_profile_summary_with_dict_capabilities(self):
        """Test _build_profile_summary with dict capabilities."""
        profile = {
            "name": "Charlie",
            "capabilities": {"venue": "large meeting room", "catering": "basic"},
            "location": "Shenzhen",
        }
        agent = UserAgent(user_id="charlie", profile=profile)

        summary = agent._build_profile_summary()

        assert "Charlie" in summary
        assert "Shenzhen" in summary
        assert "venue" in summary or "catering" in summary

    def test_build_demand_summary(self, profile_with_capabilities, demand_venue):
        """Test _build_demand_summary."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        summary = agent._build_demand_summary(demand_venue)

        assert "AI meetup" in summary
        assert "event_organization" in summary
        assert "venue" in summary or "speaker" in summary
        assert "Beijing" in summary

    def test_parse_response_valid_json(self, profile_with_capabilities):
        """Test _parse_response with valid JSON."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '''```json
{
  "decision": "participate",
  "contribution": "I can provide a 50-person meeting room",
  "conditions": [],
  "reasoning": "My venue matches the requirements",
  "decline_reason": "",
  "confidence": 85,
  "enthusiasm_level": "high",
  "suggested_role": "Venue Provider"
}
```'''

        result = agent._parse_response(response)

        assert result["decision"] == "participate"
        assert "meeting room" in result["contribution"]
        assert result["confidence"] == 85
        assert result["enthusiasm_level"] == "high"
        assert result["suggested_role"] == "Venue Provider"

    def test_parse_response_json_without_codeblock(self, profile_with_capabilities):
        """Test _parse_response with JSON without markdown code block."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '''{
  "decision": "conditional",
  "contribution": "I can provide technical support",
  "conditions": ["Must be on weekends"],
  "reasoning": "Weekday availability is limited",
  "decline_reason": "",
  "confidence": 70,
  "enthusiasm_level": "medium",
  "suggested_role": "Tech Support"
}'''

        result = agent._parse_response(response)

        assert result["decision"] == "conditional"
        assert result["conditions"] == ["Must be on weekends"]
        assert result["confidence"] == 70
        assert result["enthusiasm_level"] == "medium"

    def test_parse_response_invalid_decision_defaults_to_decline(self, profile_with_capabilities):
        """Test that invalid decision type defaults to decline."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '{"decision": "maybe", "contribution": "test"}'

        result = agent._parse_response(response)

        assert result["decision"] == "decline"

    def test_parse_response_invalid_enthusiasm_defaults_to_medium(self, profile_with_capabilities):
        """Test that invalid enthusiasm level defaults to medium."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '{"decision": "participate", "enthusiasm_level": "super_excited"}'

        result = agent._parse_response(response)

        assert result["enthusiasm_level"] == "medium"

    def test_parse_response_confidence_string_converted(self, profile_with_capabilities):
        """Test that string confidence is converted to int."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '{"decision": "participate", "confidence": "75"}'

        result = agent._parse_response(response)

        assert result["confidence"] == 75

    def test_parse_response_confidence_clamped(self, profile_with_capabilities):
        """Test that confidence is clamped to 0-100."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = '{"decision": "participate", "confidence": 150}'

        result = agent._parse_response(response)

        assert result["confidence"] == 100

    def test_parse_response_invalid_json_returns_mock(self, profile_with_capabilities):
        """Test that invalid JSON returns mock response."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        response = "This is not valid JSON at all"

        result = agent._parse_response(response)

        # Should return a mock response with all required fields
        assert "decision" in result
        assert result["decision"] in ["participate", "decline", "conditional"]
        assert "confidence" in result
        assert "enthusiasm_level" in result

    def test_mock_response_participate_with_matching_capabilities(
        self, profile_with_capabilities, demand_venue
    ):
        """Test mock response with matching capabilities returns participate."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        # Modify demand to match profile capabilities
        demand = {
            "surface_demand": "Need venue_management help",
            "capability_tags": ["venue"],
        }

        result = agent._mock_response(demand)

        assert result["decision"] == "participate"
        assert result["confidence"] == 70
        assert result["enthusiasm_level"] == "medium"
        assert "venue_management" in result["contribution"] or "support" in result["contribution"]
        assert result["decline_reason"] == ""

    def test_mock_response_decline_without_matching_capabilities(
        self, profile_without_capabilities
    ):
        """Test mock response without matching capabilities returns decline."""
        agent = UserAgent(user_id="alice", profile=profile_without_capabilities)

        demand = {
            "surface_demand": "Need venue for event",
            "capability_tags": ["venue", "catering"],
        }

        result = agent._mock_response(demand)

        assert result["decision"] == "decline"
        assert result["confidence"] == 60
        assert result["enthusiasm_level"] == "low"
        assert result["decline_reason"] != ""

    def test_mock_response_with_dict_capabilities(self):
        """Test mock response handles dict capabilities correctly."""
        profile = {
            "name": "Dave",
            "capabilities": {"photography": "professional", "videography": "amateur"},
            "tags": [],
        }
        agent = UserAgent(user_id="dave", profile=profile)

        demand = {
            "surface_demand": "Need photography for event",
            "capability_tags": ["photography"],
        }

        result = agent._mock_response(demand)

        assert result["decision"] == "participate"
        assert "photography" in result["contribution"].lower() or "support" in result["contribution"].lower()

    def test_mock_response_tag_matching(self, profile_with_capabilities):
        """Test mock response matches by tags as well."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        demand = {
            "surface_demand": "Something unrelated",
            "capability_tags": ["venue"],  # Matches profile tags
        }

        result = agent._mock_response(demand)

        assert result["decision"] == "participate"

    def test_mock_response_all_required_fields(self, profile_with_capabilities):
        """Test mock response includes all required fields."""
        agent = UserAgent(user_id="bob", profile=profile_with_capabilities)

        result = agent._mock_response({})

        required_fields = [
            "decision",
            "contribution",
            "conditions",
            "reasoning",
            "decline_reason",
            "confidence",
            "enthusiasm_level",
            "suggested_role",
        ]

        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_generate_response_uses_llm_when_available(
        self, profile_with_capabilities, demand_venue, mock_llm_service
    ):
        """Test _generate_response uses LLM when available."""
        mock_llm_service.complete = AsyncMock(
            return_value='{"decision": "participate", "contribution": "test", "confidence": 80}'
        )

        agent = UserAgent(
            user_id="bob",
            profile=profile_with_capabilities,
        )
        agent.llm = mock_llm_service

        result = await agent._generate_response(demand_venue, "venue resources")

        mock_llm_service.complete.assert_called_once()
        assert result["decision"] == "participate"

    @pytest.mark.asyncio
    async def test_generate_response_fallback_on_llm_error(
        self, profile_with_capabilities, demand_venue, mock_llm_service
    ):
        """Test _generate_response falls back to mock on LLM error."""
        mock_llm_service.complete = AsyncMock(side_effect=Exception("LLM Error"))

        agent = UserAgent(
            user_id="bob",
            profile=profile_with_capabilities,
        )
        agent.llm = mock_llm_service

        result = await agent._generate_response(demand_venue, "venue resources")

        # Should return a valid mock response
        assert "decision" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_generate_response_without_llm_uses_mock(
        self, profile_with_capabilities, demand_venue
    ):
        """Test _generate_response without LLM uses mock response."""
        agent = UserAgent(
            user_id="bob",
            profile=profile_with_capabilities,
        )
        agent.llm = None
        agent.secondme = None

        result = await agent._generate_response(demand_venue, "venue resources")

        # Should return a mock response
        assert "decision" in result
        assert result["decision"] in ["participate", "decline", "conditional"]


class TestUserAgentSystemPrompt:
    """Tests for system prompt generation."""

    def test_get_response_system_prompt(self):
        """Test system prompt content."""
        agent = UserAgent(user_id="test", profile={})

        prompt = agent._get_response_system_prompt()

        assert "JSON" in prompt
        assert "decline" in prompt
        assert "conditional" in prompt


class TestUserAgentIntegration:
    """Integration tests for UserAgent response flow."""

    @pytest.mark.asyncio
    async def test_full_response_flow_participate(self):
        """Test full response flow resulting in participate."""
        profile = {
            "name": "Integration Test User",
            "capabilities": ["event_planning", "venue_management"],
            "tags": ["events", "venue"],
            "location": "Beijing",
        }

        agent = UserAgent(user_id="test_user", profile=profile)
        agent.llm = None
        agent.secondme = None

        demand = {
            "surface_demand": "Need venue_management for AI event",
            "capability_tags": ["venue"],
            "deep_understanding": {"type": "event"},
        }

        result = await agent._generate_response(demand, "has venue resources")

        # With matching capabilities and no LLM, should use mock and participate
        assert result["decision"] == "participate"
        assert result["confidence"] >= 60
        assert result["enthusiasm_level"] in ["high", "medium", "low"]
        assert result["decline_reason"] == ""

    @pytest.mark.asyncio
    async def test_full_response_flow_decline(self):
        """Test full response flow resulting in decline."""
        profile = {
            "name": "Non-matching User",
            "capabilities": ["cooking", "gardening"],
            "tags": ["food", "plants"],
            "location": "Rural",
        }

        agent = UserAgent(user_id="test_user2", profile=profile)
        agent.llm = None
        agent.secondme = None

        demand = {
            "surface_demand": "Need AI expertise for tech summit",
            "capability_tags": ["AI", "machine_learning", "tech"],
            "deep_understanding": {"type": "tech_event"},
        }

        result = await agent._generate_response(demand, "might have related skills")

        # With no matching capabilities and no LLM, should decline
        assert result["decision"] == "decline"
        assert result["decline_reason"] != ""
        assert result["enthusiasm_level"] == "low"
