"""Tests for CenterCoordinatorSkill — the most complex Skill."""

from __future__ import annotations

import pytest

from towow.core.errors import SkillError
from towow.core.models import (
    AgentParticipant,
    DemandSnapshot,
    Offer,
)
from towow.skills.center import (
    ALL_TOOLS,
    RESTRICTED_TOOLS,
    VALID_TOOL_NAMES,
    CenterCoordinatorSkill,
)

from ..conftest import MockPlatformLLMClient


@pytest.fixture
def skill() -> CenterCoordinatorSkill:
    return CenterCoordinatorSkill()


@pytest.fixture
def mock_llm() -> MockPlatformLLMClient:
    return MockPlatformLLMClient()


@pytest.fixture
def sample_demand() -> DemandSnapshot:
    return DemandSnapshot(
        raw_intent="I need a technical co-founder",
        formulated_text="I need a technical co-founder who can build AI products and has startup experience",
    )


@pytest.fixture
def sample_offers() -> list[Offer]:
    return [
        Offer(
            agent_id="agent_alice",
            content="I have ML experience and can build AI products",
            capabilities=["python", "machine-learning"],
            confidence=0.85,
        ),
        Offer(
            agent_id="agent_bob",
            content="I can do frontend development",
            capabilities=["react", "typescript"],
            confidence=0.6,
        ),
    ]


@pytest.fixture
def sample_participants() -> list[AgentParticipant]:
    return [
        AgentParticipant(agent_id="agent_alice", display_name="Alice", resonance_score=0.9),
        AgentParticipant(agent_id="agent_bob", display_name="Bob", resonance_score=0.7),
    ]


class TestToolSchemaGeneration:
    def test_all_tools_have_required_fields(self):
        for tool in ALL_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert tool["input_schema"]["type"] == "object"

    def test_tool_names(self):
        expected = {"output_plan", "create_sub_demand", "create_machine"}
        assert VALID_TOOL_NAMES == expected

    def test_restricted_tools(self):
        restricted_names = {t["name"] for t in RESTRICTED_TOOLS}
        assert restricted_names == {"output_plan", "create_machine"}


class TestCenterCoordinatorSkill:
    def test_name(self, skill):
        assert skill.name == "center_coordinator"

    @pytest.mark.asyncio
    async def test_execute_output_plan(self, skill, mock_llm, sample_demand, sample_offers, sample_participants):
        """Test basic output_plan tool call."""
        mock_llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": "output_plan",
                    "arguments": {"plan_text": "Alice leads AI, Bob handles frontend."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await skill.execute({
            "demand": sample_demand,
            "offers": sample_offers,
            "participants": sample_participants,
            "llm_client": mock_llm,
            "round_number": 1,
        })

        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "output_plan"
        assert "Alice leads AI" in result["tool_calls"][0]["arguments"]["plan_text"]

    @pytest.mark.asyncio
    async def test_execute_multiple_tool_calls(self, skill, mock_llm, sample_demand, sample_offers, sample_participants):
        """Test multiple tool calls in one response (output_plan + create_sub_demand)."""
        mock_llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": "output_plan",
                    "arguments": {"plan_text": "Main plan here."},
                    "id": "call_1",
                },
                {
                    "name": "create_sub_demand",
                    "arguments": {"gap_description": "Need a DevOps engineer"},
                    "id": "call_2",
                },
            ],
            "stop_reason": "tool_use",
        })

        result = await skill.execute({
            "demand": sample_demand,
            "offers": sample_offers,
            "participants": sample_participants,
            "llm_client": mock_llm,
            "round_number": 1,
        })

        assert len(result["tool_calls"]) == 2
        assert result["tool_calls"][0]["name"] == "output_plan"
        assert result["tool_calls"][1]["name"] == "create_sub_demand"


class TestToolsRestricted:
    @pytest.mark.asyncio
    async def test_restricted_mode_only_output_plan(self, skill, mock_llm, sample_demand, sample_offers):
        """When tools_restricted=True, only output_plan and create_machine are available."""
        mock_llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": "output_plan",
                    "arguments": {"plan_text": "Final plan after max rounds."},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        result = await skill.execute({
            "demand": sample_demand,
            "offers": sample_offers,
            "llm_client": mock_llm,
            "round_number": 3,
            "tools_restricted": True,
        })

        assert result["tool_calls"][0]["name"] == "output_plan"


class TestObservationMasking:
    @pytest.mark.asyncio
    async def test_round_1_shows_full_offers(self, skill, sample_demand, sample_offers, sample_participants):
        """Round 1: full offers visible in the prompt."""
        _, messages = skill._build_prompt({
            "demand": sample_demand,
            "offers": sample_offers,
            "participants": sample_participants,
            "round_number": 1,
        })

        content = messages[0]["content"]
        assert "I have ML experience" in content  # Alice's full offer
        assert "frontend development" in content  # Bob's full offer

class TestInvalidToolRejection:
    @pytest.mark.asyncio
    async def test_invalid_tool_name_rejected(self, skill, mock_llm, sample_demand, sample_offers):
        """Invalid tool names should raise SkillError."""
        mock_llm.add_response({
            "content": None,
            "tool_calls": [
                {
                    "name": "nonexistent_tool",
                    "arguments": {"data": "foo"},
                    "id": "call_1",
                }
            ],
            "stop_reason": "tool_use",
        })

        with pytest.raises(SkillError, match="invalid tool name 'nonexistent_tool'"):
            await skill.execute({
                "demand": sample_demand,
                "offers": sample_offers,
                "llm_client": mock_llm,
            })


class TestFormatErrorDegradation:
    @pytest.mark.asyncio
    async def test_text_response_degrades_to_output_plan(self, skill, mock_llm, sample_demand, sample_offers):
        """If LLM responds with text instead of tool calls, degrade to output_plan."""
        mock_llm.add_response({
            "content": "I think Alice should lead the project.",
            "tool_calls": None,
            "stop_reason": "end_turn",
        })

        result = await skill.execute({
            "demand": sample_demand,
            "offers": sample_offers,
            "llm_client": mock_llm,
        })

        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "output_plan"
        assert "Alice should lead" in result["tool_calls"][0]["arguments"]["plan_text"]

    @pytest.mark.asyncio
    async def test_empty_response_raises(self, skill, mock_llm, sample_demand, sample_offers):
        """No tool calls and no content should raise SkillError."""
        mock_llm.add_response({
            "content": "",
            "tool_calls": None,
            "stop_reason": "end_turn",
        })

        with pytest.raises(SkillError, match="no tool calls and no content"):
            await skill.execute({
                "demand": sample_demand,
                "offers": sample_offers,
                "llm_client": mock_llm,
            })

    @pytest.mark.asyncio
    async def test_missing_demand_raises(self, skill, mock_llm, sample_offers):
        with pytest.raises(SkillError, match="demand"):
            await skill.execute({
                "offers": sample_offers,
                "llm_client": mock_llm,
            })

    @pytest.mark.asyncio
    async def test_missing_offers_raises(self, skill, mock_llm, sample_demand):
        with pytest.raises(SkillError, match="offers"):
            await skill.execute({
                "demand": sample_demand,
                "llm_client": mock_llm,
            })
