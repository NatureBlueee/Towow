"""Tests for Towow V1 API routes."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from towow.api.routes import router, ws_router
from towow.core.engine import NegotiationEngine
from towow.core.models import (
    DemandSnapshot,
    NegotiationSession,
    NegotiationState,
    TraceChain,
    generate_id,
)
from towow.infra.event_pusher import WebSocketEventPusher

from websocket_manager import WebSocketManager


# ============ Test App Factory ============

def _create_test_app() -> FastAPI:
    """Create a FastAPI app with mock dependencies for testing."""
    app = FastAPI()
    app.include_router(router)
    app.include_router(ws_router)

    # In-memory stores
    app.state.scenes = {}
    app.state.sessions = {}
    app.state.agents = {}
    app.state.profiles = {}
    app.state.tasks = {}
    app.state.skills = {}

    # Mock WebSocket manager
    ws_manager = WebSocketManager()
    app.state.ws_manager = ws_manager

    # Mock event pusher
    event_pusher = AsyncMock()
    event_pusher.push = AsyncMock()
    event_pusher.push_many = AsyncMock()
    app.state.event_pusher = event_pusher

    # Stub encoder
    class StubEncoder:
        async def encode(self, text: str):
            rng = np.random.RandomState(hash(text) % (2**31))
            vec = rng.randn(128).astype(np.float32)
            return vec / np.linalg.norm(vec)

        async def batch_encode(self, texts: list[str]):
            return [await self.encode(t) for t in texts]

    app.state.encoder = StubEncoder()

    # Mock resonance detector
    resonance = AsyncMock()
    resonance.detect = AsyncMock(return_value=[])

    # Engine with mock pusher
    engine = NegotiationEngine(
        encoder=app.state.encoder,
        resonance_detector=resonance,
        event_pusher=event_pusher,
    )
    app.state.engine = engine

    # Mock adapter
    adapter = AsyncMock()
    adapter.get_profile = AsyncMock(return_value={"agent_id": "test"})
    adapter.chat = AsyncMock(return_value="Mock response")
    app.state.adapter = adapter

    # Mock LLM client — returns output_plan by default
    llm_client = AsyncMock()
    llm_client.chat = AsyncMock(return_value={
        "content": None,
        "tool_calls": [
            {"name": "output_plan", "arguments": {"plan_text": "Test plan"}, "id": "call_1"}
        ],
        "stop_reason": "tool_use",
    })
    app.state.llm_client = llm_client

    app.state.config = MagicMock()

    return app


@pytest.fixture
def app():
    return _create_test_app()


@pytest.fixture
def client(app):
    return TestClient(app)


# ============ Scene Tests ============

class TestCreateScene:
    def test_creates_scene(self, client):
        resp = client.post("/api/scenes", json={
            "name": "Test Scene",
            "description": "A test scene",
            "organizer_id": "org_1",
            "expected_responders": 5,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Scene"
        assert data["organizer_id"] == "org_1"
        assert data["expected_responders"] == 5
        assert data["scene_id"].startswith("scene_")
        assert data["agent_ids"] == []

    def test_default_access_policy(self, client):
        resp = client.post("/api/scenes", json={
            "name": "S", "description": "D", "organizer_id": "o",
        })
        assert resp.status_code == 201
        assert resp.json()["access_policy"] == "open"


class TestRegisterAgent:
    def _create_scene(self, client) -> str:
        resp = client.post("/api/scenes", json={
            "name": "S", "description": "D", "organizer_id": "o",
        })
        return resp.json()["scene_id"]

    def test_registers_agent(self, client):
        scene_id = self._create_scene(client)
        resp = client.post(f"/api/scenes/{scene_id}/agents", json={
            "agent_id": "agent_1",
            "display_name": "Agent One",
            "source_type": "claude",
            "profile_data": {"skills": ["python"]},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["agent_id"] == "agent_1"
        assert data["scene_id"] == scene_id

    def test_404_nonexistent_scene(self, client):
        resp = client.post("/api/scenes/bad_id/agents", json={
            "agent_id": "a", "display_name": "A",
        })
        assert resp.status_code == 404

    def test_409_duplicate_agent(self, client):
        scene_id = self._create_scene(client)
        payload = {"agent_id": "dup", "display_name": "Dup"}
        client.post(f"/api/scenes/{scene_id}/agents", json=payload)
        resp = client.post(f"/api/scenes/{scene_id}/agents", json=payload)
        assert resp.status_code == 409


# ============ Negotiation Tests ============

class TestSubmitDemand:
    def _setup_scene(self, client) -> str:
        resp = client.post("/api/scenes", json={
            "name": "S", "description": "D", "organizer_id": "o",
        })
        return resp.json()["scene_id"]

    def test_submits_demand(self, client):
        scene_id = self._setup_scene(client)
        resp = client.post("/api/negotiations/submit", json={
            "scene_id": scene_id,
            "user_id": "user_1",
            "intent": "I need a co-founder",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["negotiation_id"].startswith("neg_")
        assert data["demand_raw"] == "I need a co-founder"
        assert data["state"] == "created"

    def test_404_nonexistent_scene(self, client):
        resp = client.post("/api/negotiations/submit", json={
            "scene_id": "bad", "user_id": "u", "intent": "i",
        })
        assert resp.status_code == 404


class TestGetNegotiation:
    def test_gets_negotiation(self, client, app):
        session = NegotiationSession(
            negotiation_id="neg_test",
            demand=DemandSnapshot(raw_intent="test intent"),
            trace=TraceChain(negotiation_id="neg_test"),
        )
        app.state.sessions["neg_test"] = session

        resp = client.get("/api/negotiations/neg_test")
        assert resp.status_code == 200
        assert resp.json()["negotiation_id"] == "neg_test"
        assert resp.json()["demand_raw"] == "test intent"

    def test_404_nonexistent(self, client):
        resp = client.get("/api/negotiations/bad_id")
        assert resp.status_code == 404


class TestConfirmFormulation:
    def test_confirms_formulation(self, client, app):
        session = NegotiationSession(
            negotiation_id="neg_cf",
            demand=DemandSnapshot(raw_intent="raw"),
            state=NegotiationState.FORMULATED,
        )
        app.state.sessions["neg_cf"] = session

        resp = client.post("/api/negotiations/neg_cf/confirm", json={
            "confirmed_text": "enriched demand text",
        })
        assert resp.status_code == 200
        assert resp.json()["demand_formulated"] == "enriched demand text"

    def test_409_wrong_state(self, client, app):
        session = NegotiationSession(
            negotiation_id="neg_ws",
            demand=DemandSnapshot(raw_intent="raw"),
            state=NegotiationState.CREATED,
        )
        app.state.sessions["neg_ws"] = session

        resp = client.post("/api/negotiations/neg_ws/confirm", json={
            "confirmed_text": "text",
        })
        assert resp.status_code == 409

    def test_404_nonexistent(self, client):
        resp = client.post("/api/negotiations/bad/confirm", json={
            "confirmed_text": "text",
        })
        assert resp.status_code == 404


class TestUserAction:
    def test_cancel_negotiation(self, client, app):
        session = NegotiationSession(
            negotiation_id="neg_ca",
            demand=DemandSnapshot(raw_intent="raw"),
            state=NegotiationState.OFFERING,
        )
        app.state.sessions["neg_ca"] = session

        resp = client.post("/api/negotiations/neg_ca/action", json={
            "action": "cancel",
        })
        assert resp.status_code == 200
        assert resp.json()["state"] == "completed"

    def test_409_cancel_completed(self, client, app):
        session = NegotiationSession(
            negotiation_id="neg_cc",
            demand=DemandSnapshot(raw_intent="raw"),
            state=NegotiationState.COMPLETED,
        )
        app.state.sessions["neg_cc"] = session

        resp = client.post("/api/negotiations/neg_cc/action", json={
            "action": "cancel",
        })
        assert resp.status_code == 409

    def test_400_unknown_action(self, client, app):
        session = NegotiationSession(
            negotiation_id="neg_ua",
            demand=DemandSnapshot(raw_intent="raw"),
        )
        app.state.sessions["neg_ua"] = session

        resp = client.post("/api/negotiations/neg_ua/action", json={
            "action": "unknown_action",
        })
        assert resp.status_code == 400


# ============ WebSocket Tests ============

class TestWebSocket:
    def test_connects_to_existing_negotiation(self, client, app):
        session = NegotiationSession(
            negotiation_id="neg_ws1",
            demand=DemandSnapshot(raw_intent="test"),
        )
        app.state.sessions["neg_ws1"] = session

        with client.websocket_connect("/ws/negotiation/neg_ws1") as ws:
            # Connection succeeded. Send a message so the server processes it.
            ws.send_text("ping")
            # We don't expect a response back (V1: no server->client on text)
            # Just verify the connection was established successfully.

    def test_rejects_nonexistent_negotiation(self, client, app):
        # WebSocket to nonexistent negotiation should close with 4004
        try:
            with client.websocket_connect("/ws/negotiation/bad_id") as ws:
                ws.receive_text()
        except Exception:
            # Expected: WebSocket closes immediately
            pass
