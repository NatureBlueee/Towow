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
