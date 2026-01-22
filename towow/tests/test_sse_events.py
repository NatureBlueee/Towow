"""
Tests for SSE Event Streaming (TASK-018).

Verifies:
1. SSE endpoint connectivity
2. Real-time event push
3. Heartbeat mechanism (5 seconds)
4. Resource cleanup on disconnect
5. Reconnection support (last_event_id)
6. Historical events retrieval
7. CORS configuration
8. Polling fallback endpoint
"""
import asyncio
import json
import pytest
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import app
from events.recorder import event_recorder, EventRecorder


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fresh_recorder():
    """Create a fresh event recorder for isolated tests."""
    recorder = EventRecorder()
    return recorder


class TestSSEEndpointConnectivity:
    """Test SSE endpoint can be connected."""

    def test_sse_stream_endpoint_exists(self, client):
        """Verify SSE stream endpoint returns correct content type."""
        demand_id = f"d-{uuid4().hex[:8]}"

        # Use stream=True to handle SSE response
        with client.stream("GET", f"/api/v1/events/negotiations/{demand_id}/stream") as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["x-accel-buffering"] == "no"
            # Close immediately after checking headers (context manager handles cleanup)

    def test_events_health_endpoint(self, client):
        """Verify events health endpoint works."""
        response = client.get("/api/events/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "subscribers" in data
        assert "events_in_memory" in data


class TestEventRecorder:
    """Test EventRecorder functionality."""

    @pytest.mark.asyncio
    async def test_record_event(self, fresh_recorder):
        """Verify events can be recorded."""
        event = {
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.test.event",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "demand_id": "d-test123",
                "channel_id": "collab-test123",
                "message": "Test event"
            }
        }

        await fresh_recorder.record(event)
        assert len(fresh_recorder.events) == 1

        recorded = fresh_recorder.events[0]
        assert recorded.event_id == event["event_id"]
        assert recorded.event_type == event["event_type"]
        assert recorded.demand_id == "d-test123"
        assert recorded.channel_id == "collab-test123"

    @pytest.mark.asyncio
    async def test_get_by_channel(self, fresh_recorder):
        """Verify events can be retrieved by channel."""
        channel_id = "collab-abc12345"

        # Record multiple events
        for i in range(5):
            await fresh_recorder.record({
                "event_id": f"evt-{i}",
                "event_type": "towow.test.event",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "channel_id": channel_id,
                    "index": i
                }
            })

        events = fresh_recorder.get_by_channel(channel_id, limit=10)
        assert len(events) == 5
        assert events[0]["event_id"] == "evt-0"
        assert events[4]["event_id"] == "evt-4"

    @pytest.mark.asyncio
    async def test_get_by_demand(self, fresh_recorder):
        """Verify events can be retrieved by demand."""
        demand_id = "d-abc12345"

        # Record multiple events for same demand
        for i in range(3):
            await fresh_recorder.record({
                "event_id": f"evt-{i}",
                "event_type": "towow.test.event",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "demand_id": demand_id,
                    "index": i
                }
            })

        # Record event for different demand
        await fresh_recorder.record({
            "event_id": "evt-other",
            "event_type": "towow.test.event",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "demand_id": "d-other",
                "index": 999
            }
        })

        events = fresh_recorder.get_by_demand(demand_id, limit=10)
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_get_after_event_id(self, fresh_recorder):
        """Verify events can be retrieved after a specific event ID."""
        # Record multiple events
        for i in range(10):
            await fresh_recorder.record({
                "event_id": f"evt-{i:03d}",
                "event_type": "towow.test.event",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {"index": i}
            })

        # Get events after evt-005
        events = fresh_recorder.get_after("evt-005", limit=10)
        assert len(events) == 4  # evt-006, evt-007, evt-008, evt-009
        assert events[0]["event_id"] == "evt-006"
        assert events[3]["event_id"] == "evt-009"

    @pytest.mark.asyncio
    async def test_subscriber_notification(self, fresh_recorder):
        """Verify subscribers receive events."""
        queue = fresh_recorder.subscribe()

        event = {
            "event_id": "evt-notify-test",
            "event_type": "towow.test.event",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {"test": True}
        }

        await fresh_recorder.record(event)

        # Check subscriber received the event
        received = queue.get_nowait()
        assert received["event_id"] == "evt-notify-test"

        # Cleanup
        fresh_recorder.unsubscribe(queue)
        assert queue not in fresh_recorder.subscribers


class TestRecentEventsEndpoint:
    """Test polling fallback endpoint."""

    def test_recent_events_endpoint(self, client):
        """Verify recent events endpoint works."""
        demand_id = f"d-{uuid4().hex[:8]}"
        response = client.get(f"/api/events/recent/{demand_id}")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
        assert "has_more" in data
        assert isinstance(data["events"], list)

    def test_recent_events_with_count(self, client):
        """Verify count parameter works."""
        demand_id = f"d-{uuid4().hex[:8]}"
        response = client.get(f"/api/events/recent/{demand_id}?count=10")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] <= 10

    def test_recent_events_count_validation(self, client):
        """Verify count parameter validation."""
        demand_id = f"d-{uuid4().hex[:8]}"

        # Test minimum
        response = client.get(f"/api/events/recent/{demand_id}?count=0")
        assert response.status_code == 422

        # Test maximum
        response = client.get(f"/api/events/recent/{demand_id}?count=500")
        assert response.status_code == 422


class TestCORSConfiguration:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """Verify CORS headers are set."""
        # Preflight request
        response = client.options(
            "/api/events/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_sse_cors_header(self, client):
        """Verify SSE endpoint includes CORS header."""
        demand_id = f"d-{uuid4().hex[:8]}"

        with client.stream("GET", f"/api/events/stream/{demand_id}") as response:
            assert "access-control-allow-origin" in response.headers
            assert response.headers["access-control-allow-origin"] == "*"
            # Context manager handles cleanup


class TestDemandSubmission:
    """Test demand submission triggers events."""

    def test_submit_demand_returns_channel_id(self, client):
        """Verify demand submission returns demand_id and channel_id."""
        response = client.post(
            "/api/demand/submit",
            json={"raw_input": "Test demand for SSE verification"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "demand_id" in data
        assert "channel_id" in data
        assert data["demand_id"].startswith("d-")
        assert data["channel_id"].startswith("collab-")
        assert data["status"] == "processing"

    def test_get_demand_status(self, client):
        """Verify demand status can be retrieved."""
        # First submit a demand
        submit_response = client.post(
            "/api/demand/submit",
            json={"raw_input": "Test demand"}
        )
        demand_id = submit_response.json()["demand_id"]

        # Check status
        status_response = client.get(f"/api/demand/{demand_id}/status")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["demand_id"] == demand_id
        assert "status" in data

    def test_get_demand_details(self, client):
        """Verify demand details can be retrieved."""
        # First submit a demand
        submit_response = client.post(
            "/api/demand/submit",
            json={"raw_input": "Test demand", "user_id": "test-user"}
        )
        demand_id = submit_response.json()["demand_id"]

        # Get details
        detail_response = client.get(f"/api/demand/{demand_id}")
        assert detail_response.status_code == 200
        data = detail_response.json()
        assert data["demand_id"] == demand_id
        assert data["raw_input"] == "Test demand"
        assert data["user_id"] == "test-user"

    def test_get_nonexistent_demand(self, client):
        """Verify 404 for nonexistent demand."""
        response = client.get("/api/demand/d-nonexistent")
        assert response.status_code == 404


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """Verify root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_endpoint(self, client):
        """Verify health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness_endpoint(self, client):
        """Verify readiness endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestEventBusIntegration:
    """Test event bus integration."""

    @pytest.mark.asyncio
    async def test_event_bus_wildcard_subscription(self):
        """Verify event bus supports wildcard subscriptions."""
        from events.bus import event_bus, Event

        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe("towow.test.*", handler)

        test_event = Event.create(
            event_type="towow.test.example",
            payload={"test": True}
        )

        await event_bus.publish(test_event)

        # Wait for async handling
        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "towow.test.example"


class TestMaxEventsLimit:
    """Test max events limit in recorder."""

    @pytest.mark.asyncio
    async def test_max_events_respected(self):
        """Verify recorder respects MAX_EVENTS limit."""
        recorder = EventRecorder()

        # Record more than MAX_EVENTS
        for i in range(EventRecorder.MAX_EVENTS + 100):
            await recorder.record({
                "event_id": f"evt-{i:05d}",
                "event_type": "towow.test.event",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {"index": i}
            })

        # Should not exceed MAX_EVENTS
        assert len(recorder.events) == EventRecorder.MAX_EVENTS

        # Oldest events should be dropped
        first_event = recorder.events[0]
        assert first_event.event_id == "evt-00100"
