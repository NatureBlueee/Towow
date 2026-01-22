"""Tests for Coordinator Agent."""

import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import directly from the module to avoid openagents/__init__.py issues
from openagents.agents.coordinator import CoordinatorAgent


class TestCoordinatorAgent:
    """Test suite for CoordinatorAgent."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance for testing."""
        return CoordinatorAgent()

    @pytest.fixture
    def coordinator_with_services(self):
        """Create a CoordinatorAgent with mock services."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value='{"candidates": []}')
        mock_db = MagicMock()
        mock_secondme = MagicMock()
        mock_secondme.understand_demand = AsyncMock(return_value={
            "surface_demand": "Test demand",
            "deep_understanding": {"motivation": "test"},
            "uncertainties": [],
            "confidence": "high"
        })

        return CoordinatorAgent(
            secondme_service=mock_secondme,
            llm_service=mock_llm,
            db=mock_db
        )

    def test_init(self, coordinator):
        """Test CoordinatorAgent initialization."""
        assert coordinator.AGENT_TYPE == "coordinator"
        assert coordinator.active_demands == {}
        assert coordinator.secondme is None

    def test_init_with_services(self, coordinator_with_services):
        """Test initialization with services."""
        assert coordinator_with_services.secondme is not None
        assert coordinator_with_services.llm is not None
        assert coordinator_with_services.db is not None


class TestDemandUnderstanding:
    """Tests for demand understanding functionality."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        return CoordinatorAgent()

    @pytest.mark.asyncio
    async def test_understand_demand_without_secondme(self, coordinator):
        """Test demand understanding without SecondMe service."""
        result = await coordinator._understand_demand(
            "I want to organize a tech meetup",
            "user_123"
        )

        assert result["surface_demand"] == "I want to organize a tech meetup"
        assert result["confidence"] == "low"
        assert "deep_understanding" in result

    @pytest.mark.asyncio
    async def test_understand_demand_with_secondme(self):
        """Test demand understanding with SecondMe service."""
        mock_secondme = MagicMock()
        mock_secondme.understand_demand = AsyncMock(return_value={
            "surface_demand": "Organize tech meetup",
            "deep_understanding": {"motivation": "networking"},
            "uncertainties": ["venue size"],
            "confidence": "high"
        })

        coordinator = CoordinatorAgent(secondme_service=mock_secondme)
        result = await coordinator._understand_demand(
            "I want to organize a tech meetup",
            "user_123"
        )

        assert result["confidence"] == "high"
        assert result["deep_understanding"]["motivation"] == "networking"
        mock_secondme.understand_demand.assert_called_once()

    @pytest.mark.asyncio
    async def test_understand_demand_secondme_error(self):
        """Test demand understanding when SecondMe fails."""
        mock_secondme = MagicMock()
        mock_secondme.understand_demand = AsyncMock(
            side_effect=Exception("SecondMe unavailable")
        )

        coordinator = CoordinatorAgent(secondme_service=mock_secondme)
        result = await coordinator._understand_demand(
            "I want to organize a tech meetup",
            "user_123"
        )

        # Should fallback to basic understanding
        assert result["confidence"] == "low"
        assert result["surface_demand"] == "I want to organize a tech meetup"


class TestSmartFilter:
    """Tests for smart filtering functionality."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        return CoordinatorAgent()

    def test_mock_filter(self, coordinator):
        """Test mock filter returns candidates."""
        understanding = {"surface_demand": "Test demand"}
        result = coordinator._mock_filter(understanding)

        assert len(result) == 3
        assert all("agent_id" in c for c in result)
        assert all("reason" in c for c in result)
        assert all("relevance_score" in c for c in result)

    def test_build_filter_prompt(self, coordinator):
        """Test filter prompt construction."""
        understanding = {
            "surface_demand": "Tech meetup",
            "deep_understanding": {"motivation": "networking"},
            "uncertainties": ["venue"]
        }
        agents = [
            {"agent_id": "agent_1", "display_name": "Bob", "capabilities": ["venue"]}
        ]

        prompt = coordinator._build_filter_prompt(understanding, agents)

        assert "Tech meetup" in prompt
        assert "networking" in prompt
        assert "agent_1" in prompt

    def test_parse_filter_response_valid(self, coordinator):
        """Test parsing valid filter response."""
        response = '''
        Based on the demand, here are the candidates:
        ```json
        {
            "candidates": [
                {"agent_id": "agent_1", "reason": "Good fit", "relevance_score": 90}
            ],
            "filtering_logic": "Matched by skills"
        }
        ```
        '''
        agents = [{"agent_id": "agent_1"}, {"agent_id": "agent_2"}]

        result = coordinator._parse_filter_response(response, agents)

        assert len(result) == 1
        assert result[0]["agent_id"] == "agent_1"

    def test_parse_filter_response_invalid_agent(self, coordinator):
        """Test parsing response with invalid agent ID."""
        response = '''
        {
            "candidates": [
                {"agent_id": "nonexistent", "reason": "Invalid", "relevance_score": 90}
            ]
        }
        '''
        agents = [{"agent_id": "agent_1"}]

        result = coordinator._parse_filter_response(response, agents)

        assert len(result) == 0

    def test_parse_filter_response_invalid_json(self, coordinator):
        """Test parsing invalid JSON response."""
        response = "This is not valid JSON"
        agents = [{"agent_id": "agent_1"}]

        result = coordinator._parse_filter_response(response, agents)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_smart_filter_without_llm(self, coordinator):
        """Test smart filter without LLM service uses mock."""
        understanding = {"surface_demand": "Test"}

        result = await coordinator._smart_filter("d-123", understanding)

        # Should return mock results
        assert len(result) == 3


class TestDemandHandling:
    """Tests for demand handling functionality."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        return CoordinatorAgent()

    def test_get_demand_status_not_found(self, coordinator):
        """Test getting status for non-existent demand."""
        result = coordinator.get_demand_status("nonexistent")
        assert result is None

    def test_get_demand_status_found(self, coordinator):
        """Test getting status for existing demand."""
        coordinator.active_demands["d-123"] = {
            "demand_id": "d-123",
            "status": "filtering"
        }

        result = coordinator.get_demand_status("d-123")

        assert result is not None
        assert result["status"] == "filtering"

    def test_list_active_demands_empty(self, coordinator):
        """Test listing active demands when empty."""
        result = coordinator.list_active_demands()
        assert result == []

    def test_list_active_demands_filters_completed(self, coordinator):
        """Test that completed demands are filtered out."""
        coordinator.active_demands = {
            "d-1": {"demand_id": "d-1", "status": "filtering"},
            "d-2": {"demand_id": "d-2", "status": "negotiating"},
            "d-3": {"demand_id": "d-3", "status": "completed"},
            "d-4": {"demand_id": "d-4", "status": "failed"}
        }

        result = coordinator.list_active_demands()

        assert len(result) == 2
        demand_ids = [d["demand_id"] for d in result]
        assert "d-1" in demand_ids
        assert "d-2" in demand_ids


class TestEventPublishing:
    """Tests for event publishing functionality."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        return CoordinatorAgent()

    @pytest.mark.asyncio
    async def test_publish_event_without_bus(self, coordinator):
        """Test event publishing when event bus is not available."""
        # Should not raise an error
        await coordinator._publish_event("test.event", {"data": "test"})

    @pytest.mark.asyncio
    async def test_publish_event_with_bus(self, coordinator):
        """Test event publishing with event bus."""
        # The event_bus is imported inside _publish_event method
        # We need to mock the module that gets imported
        mock_bus = MagicMock()
        mock_bus.publish = AsyncMock()

        with patch.dict('sys.modules', {'events.bus': MagicMock(event_bus=mock_bus)}):
            # Clear any cached imports
            import importlib
            # Call publish event - it should use the mocked bus
            await coordinator._publish_event("test.event", {"data": "test"})
            # Since the module was mocked, the call should succeed without error


class TestChannelCreation:
    """Tests for channel creation functionality."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        coordinator = CoordinatorAgent()
        coordinator.send_to_agent = AsyncMock()
        return coordinator

    @pytest.mark.asyncio
    async def test_create_channel(self, coordinator):
        """Test channel creation."""
        demand_id = "d-123"
        channel_id = "collab-123"
        understanding = {"surface_demand": "Test"}
        candidates = [{"agent_id": "agent_1"}]

        coordinator.active_demands[demand_id] = {"status": "filtering"}

        await coordinator._create_channel(
            demand_id, channel_id, understanding, candidates
        )

        # Verify send_to_agent was called
        coordinator.send_to_agent.assert_called_once()
        call_args = coordinator.send_to_agent.call_args
        assert call_args[0][0] == "channel_admin"
        assert call_args[0][1]["type"] == "create_channel"

        # Verify demand status updated
        assert coordinator.active_demands[demand_id]["status"] == "negotiating"
        assert coordinator.active_demands[demand_id]["channel_id"] == channel_id


class TestChannelCompletion:
    """Tests for channel completion handling."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        return CoordinatorAgent()

    @pytest.mark.asyncio
    async def test_handle_channel_completed_success(self, coordinator):
        """Test handling successful channel completion."""
        demand_id = "d-123"
        coordinator.active_demands[demand_id] = {"status": "negotiating"}

        mock_ctx = MagicMock()
        data = {
            "demand_id": demand_id,
            "success": True,
            "proposal": {"agreement": "Test agreement"}
        }

        await coordinator._handle_channel_completed(mock_ctx, data)

        assert coordinator.active_demands[demand_id]["status"] == "completed"
        assert coordinator.active_demands[demand_id]["final_proposal"] is not None

    @pytest.mark.asyncio
    async def test_handle_channel_completed_failure(self, coordinator):
        """Test handling failed channel completion."""
        demand_id = "d-123"
        coordinator.active_demands[demand_id] = {"status": "negotiating"}

        mock_ctx = MagicMock()
        data = {
            "demand_id": demand_id,
            "success": False,
            "proposal": None
        }

        await coordinator._handle_channel_completed(mock_ctx, data)

        assert coordinator.active_demands[demand_id]["status"] == "failed"


class TestSmartFilterWithLLM:
    """Tests for smart filter with LLM integration - TASK-T02."""

    @pytest.mark.asyncio
    async def test_smart_filter_with_llm(self):
        """Test LLM 智能筛选 - AC-1, AC-2, AC-3."""
        mock_llm = MagicMock()
        # Mock LLM response with valid JSON format
        mock_llm.complete = AsyncMock(return_value='''
```json
{
    "analysis": "Based on the demand for AI meetup",
    "candidates": [
        {
            "agent_id": "agent_1",
            "display_name": "Bob",
            "reason": "场地资源丰富",
            "relevance_score": 90,
            "expected_role": "场地提供者"
        },
        {
            "agent_id": "agent_2",
            "display_name": "Alice",
            "reason": "技术分享能力强",
            "relevance_score": 85,
            "expected_role": "技术顾问"
        },
        {
            "agent_id": "agent_3",
            "display_name": "Charlie",
            "reason": "活动策划经验",
            "relevance_score": 80,
            "expected_role": "活动策划"
        }
    ],
    "coverage": {
        "covered": ["场地", "技术", "策划"],
        "uncovered": []
    }
}
```
        ''')

        mock_db = MagicMock()

        coordinator = CoordinatorAgent(llm_service=mock_llm, db=mock_db)
        # Mock _get_available_agents to return test agents
        coordinator._get_available_agents = AsyncMock(return_value=[
            {"agent_id": "agent_1", "display_name": "Bob", "capabilities": ["场地"]},
            {"agent_id": "agent_2", "display_name": "Alice", "capabilities": ["技术"]},
            {"agent_id": "agent_3", "display_name": "Charlie", "capabilities": ["策划"]}
        ])

        understanding = {
            "surface_demand": "办一场AI聚会",
            "deep_understanding": {"motivation": "networking", "type": "event"},
            "capability_tags": ["场地提供", "技术分享"]
        }

        candidates = await coordinator._smart_filter("d-test", understanding)

        # AC-1: LLM 调用成功
        mock_llm.complete.assert_called_once()

        # AC-2: 候选人数量在 3-15 人之间
        assert 3 <= len(candidates) <= 15

        # AC-3: 每个候选人都有 relevance_score 和 reason
        assert all("agent_id" in c for c in candidates)
        assert all("relevance_score" in c for c in candidates)
        assert all("reason" in c for c in candidates)

    @pytest.mark.asyncio
    async def test_smart_filter_fallback_no_llm(self):
        """Test LLM 不可用时降级 - AC-4."""
        coordinator = CoordinatorAgent(llm_service=None)

        understanding = {
            "surface_demand": "办一场AI聚会",
            "capability_tags": ["场地提供", "技术分享"]
        }

        candidates = await coordinator._smart_filter("d-test", understanding)

        # AC-4: 应该返回 Mock 数据
        assert len(candidates) > 0
        # Verify mock filter returns proper structure
        assert all("agent_id" in c for c in candidates)
        assert all("display_name" in c for c in candidates)
        assert all("reason" in c for c in candidates)
        assert all("relevance_score" in c for c in candidates)

    @pytest.mark.asyncio
    async def test_smart_filter_fallback_no_agents(self):
        """Test 无可用 Agent 时降级到 Mock."""
        mock_llm = MagicMock()
        coordinator = CoordinatorAgent(llm_service=mock_llm)
        coordinator._get_available_agents = AsyncMock(return_value=[])

        understanding = {"surface_demand": "办一场AI聚会"}

        candidates = await coordinator._smart_filter("d-test", understanding)

        # Should return mock data when no agents available
        assert len(candidates) > 0
        # LLM should not be called
        mock_llm.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_smart_filter_fallback_llm_error(self):
        """Test LLM 调用失败时降级 - AC-4."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=Exception("LLM Error"))

        coordinator = CoordinatorAgent(llm_service=mock_llm)
        coordinator._get_available_agents = AsyncMock(return_value=[
            {"agent_id": "agent_1", "display_name": "Bob"}
        ])

        understanding = {"surface_demand": "办一场AI聚会"}

        candidates = await coordinator._smart_filter("d-test", understanding)

        # Should return mock data on LLM error
        assert len(candidates) > 0

    @pytest.mark.asyncio
    async def test_smart_filter_llm_empty_response(self):
        """Test LLM 返回空结果时降级."""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value='{"candidates": []}')

        coordinator = CoordinatorAgent(llm_service=mock_llm)
        coordinator._get_available_agents = AsyncMock(return_value=[
            {"agent_id": "agent_1", "display_name": "Bob"}
        ])

        understanding = {"surface_demand": "办一场AI聚会"}

        candidates = await coordinator._smart_filter("d-test", understanding)

        # Should fallback to mock when LLM returns empty
        assert len(candidates) > 0


class TestMockFilterWithKeywords:
    """Tests for mock filter keyword matching - TASK-T02 降级策略."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        return CoordinatorAgent()

    def test_mock_filter_with_capability_tags(self, coordinator):
        """Test mock filter matches based on capability_tags."""
        understanding = {
            "surface_demand": "需要场地和技术分享",
            "capability_tags": ["场地", "技术"]
        }

        result = coordinator._mock_filter(understanding)

        # Should match agents with relevant keywords
        agent_ids = [c["agent_id"] for c in result]
        assert "user_agent_bob" in agent_ids  # 场地
        assert "user_agent_alice" in agent_ids  # 技术

    def test_mock_filter_without_capability_tags(self, coordinator):
        """Test mock filter returns default when no capability_tags."""
        understanding = {"surface_demand": "一些需求"}

        result = coordinator._mock_filter(understanding)

        # Should return default 3 agents
        assert len(result) == 3

    def test_mock_filter_response_structure(self, coordinator):
        """Test mock filter returns complete structure."""
        understanding = {"surface_demand": "办活动", "capability_tags": ["场地"]}

        result = coordinator._mock_filter(understanding)

        for candidate in result:
            assert "agent_id" in candidate
            assert "display_name" in candidate
            assert "reason" in candidate
            assert "relevance_score" in candidate
            assert "expected_role" in candidate
            # keywords should be removed
            assert "keywords" not in candidate


class TestFilterSystemPrompt:
    """Tests for filter system prompt - TASK-T02."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        return CoordinatorAgent()

    def test_get_filter_system_prompt(self, coordinator):
        """Test system prompt contains key elements."""
        prompt = coordinator._get_filter_system_prompt()

        # Check key elements exist
        assert "ToWow" in prompt
        assert "筛选" in prompt
        assert "能力匹配" in prompt
        assert "3-15" in prompt
        assert "JSON" in prompt


class TestParseFilterResponse:
    """Tests for parsing filter response - TASK-T02 鲁棒性增强."""

    @pytest.fixture
    def coordinator(self):
        """Create a CoordinatorAgent instance."""
        return CoordinatorAgent()

    def test_parse_json_code_block(self, coordinator):
        """Test parsing JSON in code block format."""
        response = '''
Some analysis here...
```json
{
    "candidates": [
        {"agent_id": "agent_1", "reason": "Good", "relevance_score": 90}
    ]
}
```
        '''
        agents = [{"agent_id": "agent_1", "display_name": "Bob"}]

        result = coordinator._parse_filter_response(response, agents)

        assert len(result) == 1
        assert result[0]["agent_id"] == "agent_1"
        assert result[0]["display_name"] == "Bob"  # Should be filled from agents

    def test_parse_raw_json(self, coordinator):
        """Test parsing raw JSON without code block."""
        response = '''
{
    "candidates": [
        {"agent_id": "agent_1", "relevance_score": 85}
    ]
}
        '''
        agents = [{"agent_id": "agent_1", "display_name": "Bob"}]

        result = coordinator._parse_filter_response(response, agents)

        assert len(result) == 1
        assert result[0]["reason"] == "符合需求"  # Default reason

    def test_parse_sorts_by_relevance(self, coordinator):
        """Test candidates are sorted by relevance_score."""
        response = '''
{
    "candidates": [
        {"agent_id": "agent_2", "relevance_score": 70},
        {"agent_id": "agent_1", "relevance_score": 90},
        {"agent_id": "agent_3", "relevance_score": 80}
    ]
}
        '''
        agents = [
            {"agent_id": "agent_1"},
            {"agent_id": "agent_2"},
            {"agent_id": "agent_3"}
        ]

        result = coordinator._parse_filter_response(response, agents)

        # Should be sorted by relevance_score descending
        assert result[0]["agent_id"] == "agent_1"  # 90
        assert result[1]["agent_id"] == "agent_3"  # 80
        assert result[2]["agent_id"] == "agent_2"  # 70

    def test_parse_limits_to_15(self, coordinator):
        """Test results are limited to 15 candidates."""
        candidates = [
            {"agent_id": f"agent_{i}", "relevance_score": 90-i}
            for i in range(20)
        ]
        response = f'{{"candidates": {candidates}}}'.replace("'", '"')
        agents = [{"agent_id": f"agent_{i}"} for i in range(20)]

        result = coordinator._parse_filter_response(response, agents)

        assert len(result) <= 15

    def test_parse_filters_invalid_agents(self, coordinator):
        """Test invalid agent IDs are filtered out."""
        response = '''
{
    "candidates": [
        {"agent_id": "valid_agent", "relevance_score": 90},
        {"agent_id": "invalid_agent", "relevance_score": 85}
    ]
}
        '''
        agents = [{"agent_id": "valid_agent"}]

        result = coordinator._parse_filter_response(response, agents)

        assert len(result) == 1
        assert result[0]["agent_id"] == "valid_agent"
