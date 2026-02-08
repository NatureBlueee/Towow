"""Tests for GapRecursionSkill."""

from __future__ import annotations

import json

import pytest

from towow.core.errors import SkillError
from towow.skills.gap_recursion import GapRecursionSkill

from ..conftest import MockPlatformLLMClient


@pytest.fixture
def skill() -> GapRecursionSkill:
    return GapRecursionSkill()


@pytest.fixture
def mock_llm() -> MockPlatformLLMClient:
    return MockPlatformLLMClient()


class TestGapRecursionSkill:
    def test_name(self, skill):
        assert skill.name == "gap_recursion"

    @pytest.mark.asyncio
    async def test_execute_with_json_response(self, skill, mock_llm):
        mock_llm.add_response({
            "content": json.dumps({
                "sub_demand_text": "Need a DevOps engineer experienced with Kubernetes and CI/CD pipelines",
                "context": "Part of a larger AI product team formation. The team already has ML and frontend covered.",
            }),
            "tool_calls": None,
            "stop_reason": "end_turn",
        })

        result = await skill.execute({
            "gap_description": "No one covers infrastructure and deployment",
            "demand_context": "Building an AI product startup team",
            "llm_client": mock_llm,
        })

        assert "DevOps" in result["sub_demand_text"]
        assert "context" in result

    @pytest.mark.asyncio
    async def test_execute_with_plain_text_response(self, skill, mock_llm):
        """Lenient: plain text becomes the sub-demand."""
        mock_llm.add_response({
            "content": "Looking for an infrastructure engineer with cloud deployment experience.",
            "tool_calls": None,
            "stop_reason": "end_turn",
        })

        result = await skill.execute({
            "gap_description": "No infrastructure coverage",
            "demand_context": "Building a team",
            "llm_client": mock_llm,
        })

        assert "infrastructure engineer" in result["sub_demand_text"]

    @pytest.mark.asyncio
    async def test_execute_missing_gap_description(self, skill, mock_llm):
        with pytest.raises(SkillError, match="gap_description is required"):
            await skill.execute({"llm_client": mock_llm})

    @pytest.mark.asyncio
    async def test_execute_missing_llm_client(self, skill):
        with pytest.raises(SkillError, match="llm_client"):
            await skill.execute({"gap_description": "test"})

    @pytest.mark.asyncio
    async def test_execute_empty_response_raises(self, skill, mock_llm):
        mock_llm.add_response({
            "content": json.dumps({"sub_demand_text": "", "context": ""}),
            "tool_calls": None,
            "stop_reason": "end_turn",
        })

        with pytest.raises(SkillError, match="sub_demand_text is empty"):
            await skill.execute({
                "gap_description": "test gap",
                "llm_client": mock_llm,
            })

    @pytest.mark.asyncio
    async def test_prompt_contains_gap_and_context(self, skill):
        _, messages = skill._build_prompt({
            "gap_description": "Missing DevOps",
            "demand_context": "AI startup team",
        })

        content = messages[0]["content"]
        assert "Missing DevOps" in content
        assert "AI startup team" in content
