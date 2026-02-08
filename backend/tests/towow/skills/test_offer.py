"""Tests for OfferGenerationSkill."""

from __future__ import annotations

import json

import pytest

from towow.core.errors import SkillError
from towow.skills.offer import OfferGenerationSkill

from ..conftest import MockProfileDataSource


@pytest.fixture
def skill() -> OfferGenerationSkill:
    return OfferGenerationSkill()


@pytest.fixture
def adapter() -> MockProfileDataSource:
    return MockProfileDataSource(
        profiles={
            "agent_alice": {"name": "Alice", "skills": ["python", "ML", "data-science"]},
            "agent_bob": {"name": "Bob", "skills": ["frontend", "react"]},
        }
    )


class TestOfferGenerationSkill:
    def test_name(self, skill: OfferGenerationSkill):
        assert skill.name == "offer_generation"

    @pytest.mark.asyncio
    async def test_execute_with_json_response(self, skill, adapter):
        response = json.dumps({
            "content": "I can help with ML model development",
            "capabilities": ["python", "machine-learning"],
            "confidence": 0.85,
        })
        adapter.set_chat_response("agent_alice", response)

        result = await skill.execute({
            "agent_id": "agent_alice",
            "demand_text": "Need ML engineer",
            "profile_data": {"name": "Alice", "skills": ["python", "ML"]},
            "adapter": adapter,
        })

        assert result["content"] == "I can help with ML model development"
        assert result["capabilities"] == ["python", "machine-learning"]
        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_execute_with_plain_text_response(self, skill, adapter):
        """Lenient parsing: plain text becomes content with default confidence."""
        adapter.set_chat_response("agent_alice", "I have experience with Python and ML")

        result = await skill.execute({
            "agent_id": "agent_alice",
            "demand_text": "Need ML engineer",
            "profile_data": {},
            "adapter": adapter,
        })

        assert result["content"] == "I have experience with Python and ML"
        assert result["capabilities"] == []
        assert result["confidence"] == 0.5  # default for text fallback

    @pytest.mark.asyncio
    async def test_anti_fabrication_only_own_profile(self, skill, adapter):
        """Verify that only the specified agent's profile data goes into the prompt."""
        # We set profile_data to Alice's data; Bob's data should NOT appear
        alice_profile = {"name": "Alice", "skills": ["python", "ML"]}

        response = json.dumps({
            "content": "I can help",
            "capabilities": ["python"],
            "confidence": 0.7,
        })
        adapter.set_chat_response("agent_alice", response)

        result = await skill.execute({
            "agent_id": "agent_alice",
            "demand_text": "Need help",
            "profile_data": alice_profile,
            "adapter": adapter,
        })

        # Build the prompt and verify it only contains Alice's data
        system, messages = skill._build_prompt({
            "demand_text": "Need help",
            "profile_data": alice_profile,
        })
        assert "Alice" in system
        assert "Bob" not in system

    @pytest.mark.asyncio
    async def test_confidence_clamped(self, skill, adapter):
        """Confidence values should be clamped to [0, 1]."""
        response = json.dumps({
            "content": "I can help",
            "capabilities": [],
            "confidence": 5.0,
        })
        adapter.set_chat_response("agent_alice", response)

        result = await skill.execute({
            "agent_id": "agent_alice",
            "demand_text": "test",
            "profile_data": {},
            "adapter": adapter,
        })
        assert result["confidence"] == 1.0

        # Test negative
        response = json.dumps({
            "content": "I can help",
            "capabilities": [],
            "confidence": -0.5,
        })
        adapter.set_chat_response("agent_alice", response)

        result = await skill.execute({
            "agent_id": "agent_alice",
            "demand_text": "test",
            "profile_data": {},
            "adapter": adapter,
        })
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_execute_missing_demand_text(self, skill, adapter):
        with pytest.raises(SkillError, match="demand_text is required"):
            await skill.execute({"agent_id": "agent_alice", "adapter": adapter})

    @pytest.mark.asyncio
    async def test_execute_empty_content_raises(self, skill, adapter):
        adapter.set_chat_response("agent_alice", json.dumps({"content": "", "capabilities": [], "confidence": 0.5}))
        with pytest.raises(SkillError, match="content is empty"):
            await skill.execute({
                "agent_id": "agent_alice",
                "demand_text": "test",
                "profile_data": {},
                "adapter": adapter,
            })
