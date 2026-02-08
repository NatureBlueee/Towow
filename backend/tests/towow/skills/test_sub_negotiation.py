"""Tests for SubNegotiationSkill."""

from __future__ import annotations

import json

import pytest

from towow.core.errors import SkillError
from towow.skills.sub_negotiation import SubNegotiationSkill

from ..conftest import MockPlatformLLMClient


@pytest.fixture
def skill() -> SubNegotiationSkill:
    return SubNegotiationSkill()


@pytest.fixture
def mock_llm() -> MockPlatformLLMClient:
    return MockPlatformLLMClient()


@pytest.fixture
def sample_context(mock_llm):
    return {
        "agent_a": {
            "agent_id": "agent_alice",
            "display_name": "Alice",
            "offer": "I can do ML model development",
            "profile": {"skills": ["python", "ML", "data-science"], "experience": "5 years ML"},
        },
        "agent_b": {
            "agent_id": "agent_bob",
            "display_name": "Bob",
            "offer": "I can handle frontend development",
            "profile": {"skills": ["react", "typescript", "design"], "experience": "3 years frontend"},
        },
        "reason": "Potential synergy between ML backend and frontend visualization",
        "llm_client": mock_llm,
    }


class TestSubNegotiationSkill:
    def test_name(self, skill):
        assert skill.name == "sub_negotiation"

    @pytest.mark.asyncio
    async def test_execute_with_json_response(self, skill, mock_llm, sample_context):
        report = {
            "discovery_report": {
                "new_associations": [
                    "Alice's data visualization experience could enhance Bob's frontend",
                    "Bob has UX research skills not mentioned in his offer",
                ],
                "coordination": "Alice provides ML APIs, Bob builds interactive dashboards",
                "additional_contributions": {
                    "agent_a": ["data visualization", "jupyter notebooks"],
                    "agent_b": ["UX research", "user testing"],
                },
                "summary": "Strong complementarity found in data visualization space",
            }
        }
        mock_llm.add_response({
            "content": json.dumps(report),
            "tool_calls": None,
            "stop_reason": "end_turn",
        })

        result = await skill.execute(sample_context)

        assert "discovery_report" in result
        assert len(result["discovery_report"]["new_associations"]) == 2
        assert result["discovery_report"]["coordination"] is not None
        assert "summary" in result["discovery_report"]

    @pytest.mark.asyncio
    async def test_execute_with_plain_text_response(self, skill, mock_llm, sample_context):
        """Lenient: plain text treated as summary."""
        mock_llm.add_response({
            "content": "Alice and Bob could collaborate on data dashboards.",
            "tool_calls": None,
            "stop_reason": "end_turn",
        })

        result = await skill.execute(sample_context)

        assert result["discovery_report"]["summary"] == "Alice and Bob could collaborate on data dashboards."

    @pytest.mark.asyncio
    async def test_execute_missing_agent_a(self, skill, mock_llm):
        with pytest.raises(SkillError, match="agent_a is required"):
            await skill.execute({
                "agent_b": {"agent_id": "b"},
                "reason": "test",
                "llm_client": mock_llm,
            })

    @pytest.mark.asyncio
    async def test_execute_missing_reason(self, skill, mock_llm):
        with pytest.raises(SkillError, match="reason is required"):
            await skill.execute({
                "agent_a": {"agent_id": "a"},
                "agent_b": {"agent_id": "b"},
                "llm_client": mock_llm,
            })

    @pytest.mark.asyncio
    async def test_prompt_contains_both_agents(self, skill):
        context = {
            "agent_a": {
                "agent_id": "agent_alice",
                "display_name": "Alice",
                "offer": "ML work",
                "profile": {"skills": ["python"]},
            },
            "agent_b": {
                "agent_id": "agent_bob",
                "display_name": "Bob",
                "offer": "Frontend work",
                "profile": {"skills": ["react"]},
            },
            "reason": "Synergy",
        }

        _, messages = skill._build_prompt(context)
        content = messages[0]["content"]

        assert "Alice" in content
        assert "Bob" in content
        assert "ML work" in content
        assert "Frontend work" in content
        assert "Synergy" in content
