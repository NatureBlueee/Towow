"""Tests for AgentRegistry — unified adapter routing."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from towow.infra.agent_registry import AgentEntry, AgentRegistry


# ============ Fixtures ============

@pytest.fixture
def registry():
    return AgentRegistry()


@pytest.fixture
def mock_adapter():
    adapter = AsyncMock()
    adapter.get_profile = AsyncMock(return_value={"agent_id": "a1"})
    adapter.chat = AsyncMock(return_value="hello")
    return adapter


@pytest.fixture
def rich_adapter():
    """Adapter that returns rich profile (like SecondMe)."""
    adapter = AsyncMock()
    adapter.get_profile = AsyncMock(return_value={
        "agent_id": "sm_user",
        "name": "Alice",
        "shades": ["python", "ml"],
        "bio": "ML engineer",
    })
    adapter.chat = AsyncMock(return_value="response")
    return adapter


@pytest.fixture
def json_adapter():
    """Adapter with agent_ids and display_names (like JSONFileAdapter)."""
    adapter = AsyncMock()
    adapter.agent_ids = ["j1", "j2", "j3"]
    adapter.get_display_names = lambda: {"j1": "Jason", "j2": "Jenny", "j3": "Jack"}
    adapter.get_profile = AsyncMock(side_effect=lambda aid: {
        "agent_id": aid, "skills": ["coding"], "bio": f"Agent {aid}"
    })
    adapter.chat = AsyncMock(return_value="json response")
    return adapter


# ============ Registration Tests ============

class TestRegisterAgent:
    def test_registers_single_agent(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter, source="claude", display_name="Alice")
        assert registry.agent_count == 1
        assert "a1" in registry.all_agent_ids

    def test_overwrites_on_duplicate(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter, display_name="Old")
        registry.register_agent("a1", mock_adapter, display_name="New")
        assert registry.agent_count == 1
        info = registry.get_identity("a1")
        assert info["display_name"] == "New"

    def test_stores_profile_data(self, registry, mock_adapter):
        registry.register_agent(
            "a1", mock_adapter,
            profile_data={"skills": ["python"], "bio": "dev"},
        )
        entry = registry._agents["a1"]
        assert entry.profile_data == {"skills": ["python"], "bio": "dev"}

    def test_stores_scene_ids(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter, scene_ids=["s1", "s2"])
        info = registry.get_identity("a1")
        assert info["scene_ids"] == ["s1", "s2"]


class TestRegisterSource:
    def test_registers_batch(self, registry, json_adapter):
        registered = registry.register_source(
            "hackathon", json_adapter, scene_ids=["hack"]
        )
        assert registered == ["j1", "j2", "j3"]
        assert registry.agent_count == 3

    def test_uses_adapter_display_names(self, registry, json_adapter):
        registry.register_source("hackathon", json_adapter)
        names = registry.get_display_names()
        assert "Jason" in names["j1"]
        assert "Jenny" in names["j2"]

    def test_explicit_agent_ids(self, registry, mock_adapter):
        # Use spec to avoid auto-creating get_display_names
        from unittest.mock import AsyncMock as AM
        plain_adapter = AM(spec=[])
        registered = registry.register_source(
            "custom", plain_adapter, agent_ids=["x1", "x2"]
        )
        assert registered == ["x1", "x2"]
        assert registry.agent_count == 2


class TestUnregister:
    def test_removes_agent(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter)
        assert registry.unregister_agent("a1") is True
        assert registry.agent_count == 0

    def test_returns_false_for_unknown(self, registry):
        assert registry.unregister_agent("nonexistent") is False


# ============ Query Tests ============

class TestScopeQuery:
    def test_all_scope(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter, scene_ids=["s1"])
        registry.register_agent("a2", mock_adapter, scene_ids=["s2"])
        assert len(registry.get_agents_by_scope("all")) == 2
        assert len(registry.get_agents_by_scope("network")) == 2

    def test_scene_scope(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter, scene_ids=["s1"])
        registry.register_agent("a2", mock_adapter, scene_ids=["s2"])
        registry.register_agent("a3", mock_adapter, scene_ids=["s1", "s2"])
        result = registry.get_agents_by_scope("scene:s1")
        assert sorted(result) == ["a1", "a3"]

    def test_unknown_scope_returns_all(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter)
        assert len(registry.get_agents_by_scope("unknown:xyz")) == 1


class TestGetIdentity:
    def test_returns_info(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter, source="claude", display_name="Alice")
        info = registry.get_identity("a1")
        assert info["agent_id"] == "a1"
        assert info["display_name"] == "Alice"
        assert info["source"] == "claude"

    def test_returns_none_for_unknown(self, registry):
        assert registry.get_identity("bad") is None


# ============ ProfileDataSource Protocol Tests ============

class TestGetProfile:
    @pytest.mark.asyncio
    async def test_routes_to_adapter(self, registry, rich_adapter):
        registry.register_agent("sm_user", rich_adapter)
        profile = await registry.get_profile("sm_user")
        assert profile["name"] == "Alice"
        assert profile["shades"] == ["python", "ml"]

    @pytest.mark.asyncio
    async def test_fallback_to_profile_data(self, registry, mock_adapter):
        """When adapter returns minimal profile, use stored profile_data."""
        registry.register_agent(
            "a1", mock_adapter,
            profile_data={"skills": ["python"], "bio": "dev"},
        )
        profile = await registry.get_profile("a1")
        assert profile["skills"] == ["python"]
        assert profile["bio"] == "dev"
        assert profile["agent_id"] == "a1"

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_minimal(self, registry):
        profile = await registry.get_profile("unknown")
        assert profile == {"agent_id": "unknown"}

    @pytest.mark.asyncio
    async def test_injects_source_and_scene(self, registry, mock_adapter):
        registry.register_agent(
            "a1", mock_adapter,
            source="demo", scene_ids=["s1"],
            profile_data={"bio": "test"},
        )
        profile = await registry.get_profile("a1")
        assert profile["source"] == "demo"
        assert profile["scene_ids"] == ["s1"]


class TestChat:
    @pytest.mark.asyncio
    async def test_routes_to_adapter(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter)
        result = await registry.chat("a1", [{"role": "user", "content": "hi"}])
        assert result == "hello"
        mock_adapter.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_agent_raises(self, registry):
        from towow.core.errors import AdapterError
        with pytest.raises(AdapterError, match="未注册"):
            await registry.chat("bad", [])


# ============ Default Adapter Tests ============

class TestDefaultAdapter:
    def test_set_and_get(self, registry, mock_adapter):
        assert registry.default_adapter is None
        registry.set_default_adapter(mock_adapter)
        assert registry.default_adapter is mock_adapter

    def test_add_scene_to_agent(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter, scene_ids=["s1"])
        registry.add_scene_to_agent("a1", "s2")
        info = registry.get_identity("a1")
        assert "s2" in info["scene_ids"]

    def test_add_scene_no_duplicate(self, registry, mock_adapter):
        registry.register_agent("a1", mock_adapter, scene_ids=["s1"])
        registry.add_scene_to_agent("a1", "s1")
        info = registry.get_identity("a1")
        assert info["scene_ids"] == ["s1"]
