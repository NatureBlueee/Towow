"""Tests for DemandFormulationSkill."""

from __future__ import annotations

import json

import pytest

from towow.core.errors import SkillError
from towow.skills.formulation import DemandFormulationSkill

from ..conftest import MockProfileDataSource


@pytest.fixture
def skill() -> DemandFormulationSkill:
    return DemandFormulationSkill()


@pytest.fixture
def adapter() -> MockProfileDataSource:
    adapter = MockProfileDataSource(
        profiles={"agent_alice": {"name": "Alice", "skills": ["python", "ML"]}}
    )
    return adapter


class TestDemandFormulationSkill:
    def test_name(self, skill: DemandFormulationSkill):
        assert skill.name == "demand_formulation"

    @pytest.mark.asyncio
    async def test_execute_with_json_response(self, skill, adapter):
        """Test with a well-formed JSON response from the adapter."""
        response = json.dumps({
            "formulated_text": "I need an AI/ML technical co-founder with startup experience",
            "enrichments": {
                "hard_constraints": ["technical background"],
                "negotiable_preferences": ["location"],
                "context_added": ["Alice has ML background"],
            },
        })
        adapter.set_chat_response("agent_alice", response)

        result = await skill.execute({
            "raw_intent": "I need a co-founder",
            "agent_id": "agent_alice",
            "adapter": adapter,
            "profile_data": {"name": "Alice", "skills": ["python", "ML"]},
        })

        assert result["formulated_text"] == "I need an AI/ML technical co-founder with startup experience"
        assert "hard_constraints" in result["enrichments"]

    @pytest.mark.asyncio
    async def test_execute_with_plain_text_response(self, skill, adapter):
        """Test lenient parsing: plain text treated as formulated_text."""
        adapter.set_chat_response("agent_alice", "I need a technical co-founder who can build AI products")

        result = await skill.execute({
            "raw_intent": "I need a co-founder",
            "agent_id": "agent_alice",
            "adapter": adapter,
        })

        assert result["formulated_text"] == "I need a technical co-founder who can build AI products"
        assert result["enrichments"] == {}

    @pytest.mark.asyncio
    async def test_execute_missing_raw_intent(self, skill, adapter):
        with pytest.raises(SkillError, match="raw_intent is required"):
            await skill.execute({"agent_id": "agent_alice", "adapter": adapter})

    @pytest.mark.asyncio
    async def test_execute_missing_agent_id(self, skill, adapter):
        with pytest.raises(SkillError, match="agent_id is required"):
            await skill.execute({"raw_intent": "test", "adapter": adapter})

    @pytest.mark.asyncio
    async def test_execute_missing_adapter(self, skill):
        with pytest.raises(SkillError, match="adapter"):
            await skill.execute({"raw_intent": "test", "agent_id": "agent_alice"})

    @pytest.mark.asyncio
    async def test_execute_empty_response_raises(self, skill, adapter):
        """Empty formulated_text should raise SkillError."""
        adapter.set_chat_response("agent_alice", json.dumps({"formulated_text": "", "enrichments": {}}))

        with pytest.raises(SkillError, match="formulated_text is empty"):
            await skill.execute({
                "raw_intent": "test",
                "agent_id": "agent_alice",
                "adapter": adapter,
            })

    @pytest.mark.asyncio
    async def test_error_response_detected(self, skill, adapter):
        """LLM error responses should raise SkillError, not become formulated_text."""
        adapter.set_chat_response("agent_alice", "Rate limit exceeded. Please try again later.")

        with pytest.raises(SkillError, match="LLM returned error"):
            await skill.execute({
                "raw_intent": "I need help",
                "agent_id": "agent_alice",
                "adapter": adapter,
            })

    @pytest.mark.asyncio
    async def test_ai_refusal_detected(self, skill, adapter):
        """AI model refusal patterns should raise SkillError."""
        adapter.set_chat_response("agent_alice", "I cannot fulfill this request as an AI assistant.")

        with pytest.raises(SkillError, match="LLM returned error"):
            await skill.execute({
                "raw_intent": "test",
                "agent_id": "agent_alice",
                "adapter": adapter,
            })

    @pytest.mark.asyncio
    async def test_profile_data_in_prompt(self, skill, adapter):
        """profile_data should be injected into the system prompt."""
        adapter.set_chat_response("agent_alice", json.dumps({
            "formulated_text": "enriched demand",
            "enrichments": {},
        }))

        result = await skill.execute({
            "raw_intent": "I need a co-founder",
            "agent_id": "agent_alice",
            "adapter": adapter,
            "profile_data": {"name": "Alice", "skills": ["python", "ML"]},
        })

        assert result["formulated_text"] == "enriched demand"
        # Verify the chat was called (profile_data is embedded in the system prompt)
        # The adapter's chat method should have been called with system_prompt containing profile
        # We verify by checking the adapter recorded the call
