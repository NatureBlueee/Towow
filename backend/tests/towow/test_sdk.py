"""
SDK public API tests — verify the SDK surface, EngineBuilder,
NullEventPusher, LoggingEventPusher, and CenterToolHandler registry.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

# ---------- SDK import surface ----------


def test_sdk_imports():
    """All public symbols are importable from the top-level package."""
    from towow import (
        AdapterError,
        BaseAdapter,
        BaseSkill,
        CenterToolHandler,
        ConfigError,
        DemandSnapshot,
        EncodingError,
        EngineBuilder,
        EngineError,
        EventPusher,
        EventType,
        LLMError,
        LoggingEventPusher,
        NegotiationEngine,
        NegotiationEvent,
        NegotiationSession,
        NegotiationState,
        NullEventPusher,
        Offer,
        PlatformLLMClient,
        ProfileDataSource,
        ResonanceDetector,
        Skill,
        SkillError,
        TowowError,
        Vector,
        WebSocketEventPusher,
    )
    # If we get here, all imports work
    assert NegotiationEngine is not None
    assert EngineBuilder is not None


# ---------- NullEventPusher ----------


@pytest.mark.asyncio
async def test_null_event_pusher_push():
    """NullEventPusher silently discards events."""
    from towow import NullEventPusher
    from towow.core.events import NegotiationEvent, EventType

    pusher = NullEventPusher()
    event = NegotiationEvent(
        event_type=EventType.PLAN_READY,
        negotiation_id="test",
        data={"plan_text": "hello"},
    )
    # Should not raise
    await pusher.push(event)
    await pusher.push_many([event, event])


@pytest.mark.asyncio
async def test_logging_event_pusher(caplog):
    """LoggingEventPusher logs events at INFO level."""
    from towow import LoggingEventPusher
    from towow.core.events import NegotiationEvent, EventType

    pusher = LoggingEventPusher()
    event = NegotiationEvent(
        event_type=EventType.PLAN_READY,
        negotiation_id="test-log",
        data={"plan_text": "log me"},
    )
    import logging
    with caplog.at_level(logging.INFO, logger="towow.infra.event_pusher"):
        await pusher.push(event)

    assert "test-log" in caplog.text
    assert "plan.ready" in caplog.text


# ---------- CenterToolHandler registry ----------


def test_register_custom_tool_handler():
    """Engine accepts custom tool handlers via register_tool_handler."""
    from towow import NegotiationEngine, NullEventPusher

    encoder = MagicMock()
    detector = MagicMock()

    engine = NegotiationEngine(
        encoder=encoder,
        resonance_detector=detector,
        event_pusher=NullEventPusher(),
    )

    class MyHandler:
        @property
        def tool_name(self) -> str:
            return "search_database"

        async def handle(self, session, tool_args, context):
            return {"found": True}

    handler = MyHandler()
    engine.register_tool_handler(handler)
    assert "search_database" in engine._tool_handlers


def test_cannot_override_output_plan():
    """output_plan is always built-in and cannot be overridden."""
    from towow import NegotiationEngine, NullEventPusher

    engine = NegotiationEngine(
        encoder=MagicMock(),
        resonance_detector=MagicMock(),
        event_pusher=NullEventPusher(),
    )

    class BadHandler:
        @property
        def tool_name(self) -> str:
            return "output_plan"

        async def handle(self, session, tool_args, context):
            return {}

    with pytest.raises(ValueError, match="output_plan"):
        engine.register_tool_handler(BadHandler())


@pytest.mark.asyncio
async def test_custom_tool_handler_dispatched():
    """Custom handler is invoked when Center calls the registered tool."""
    from towow import NegotiationEngine, NullEventPusher
    from towow.core.models import (
        NegotiationSession, DemandSnapshot, NegotiationState,
    )

    # Mock encoder/detector
    encoder = MagicMock()
    detector = MagicMock()

    engine = NegotiationEngine(
        encoder=encoder,
        resonance_detector=detector,
        event_pusher=NullEventPusher(),
    )

    # Register custom handler
    handler_called = asyncio.Event()
    handler_result = {"query": "test", "rows": 42}

    class DBSearchHandler:
        @property
        def tool_name(self) -> str:
            return "search_database"

        async def handle(self, session, tool_args, context):
            handler_called.set()
            assert "adapter" in context
            assert "llm_client" in context
            assert "engine" in context
            return handler_result

    engine.register_tool_handler(DBSearchHandler())

    # Create a session in SYNTHESIZING state to test dispatch
    session = NegotiationSession(
        negotiation_id="test-dispatch",
        demand=DemandSnapshot(raw_intent="test"),
    )
    session.state = NegotiationState.SYNTHESIZING

    # Store context (normally done by start_negotiation)
    adapter = AsyncMock()
    llm_client = AsyncMock()
    center_skill = MagicMock()
    center_skill.name = "center"

    engine._neg_contexts["test-dispatch"] = {
        "adapter": adapter,
        "llm_client": llm_client,
        "center_skill": center_skill,
        "agent_display_names": {},
    }

    # Simulate Center returning our custom tool + output_plan
    center_skill.execute = AsyncMock(return_value={
        "tool_calls": [
            {"name": "search_database", "arguments": {"query": "find lawyers"}},
            {"name": "output_plan", "arguments": {"plan_text": "Found via custom tool"}},
        ],
    })

    await engine._run_synthesis(session, adapter, llm_client, center_skill)

    assert handler_called.is_set()
    assert session.plan_output == "Found via custom tool"
    assert session.state == NegotiationState.COMPLETED


# ---------- EngineBuilder ----------


def test_engine_builder_basic():
    """EngineBuilder creates an engine with NullEventPusher by default."""
    from towow import EngineBuilder

    encoder = MagicMock()
    detector = MagicMock()
    adapter = MagicMock()
    llm_client = MagicMock()
    center_skill = MagicMock()
    center_skill.name = "center"

    engine, defaults = (
        EngineBuilder()
        .with_encoder(encoder)
        .with_resonance_detector(detector)
        .with_adapter(adapter)
        .with_llm_client(llm_client)
        .with_center_skill(center_skill)
        .with_k_star(3)
        .build()
    )

    assert engine is not None
    assert defaults["adapter"] is adapter
    assert defaults["llm_client"] is llm_client
    assert defaults["center_skill"] is center_skill
    assert defaults["k_star"] == 3


def test_engine_builder_with_custom_tool():
    """EngineBuilder registers tool handlers on the built engine."""
    from towow import EngineBuilder

    class MyTool:
        @property
        def tool_name(self):
            return "my_tool"

        async def handle(self, session, tool_args, context):
            return {"ok": True}

    engine, _ = (
        EngineBuilder()
        .with_encoder(MagicMock())
        .with_resonance_detector(MagicMock())
        .with_tool_handler(MyTool())
        .build()
    )

    assert "my_tool" in engine._tool_handlers


def test_engine_builder_null_pusher_default():
    """EngineBuilder uses NullEventPusher when no pusher specified."""
    from towow import EngineBuilder
    from towow.infra.event_pusher import NullEventPusher

    engine, _ = (
        EngineBuilder()
        .with_encoder(MagicMock())
        .with_resonance_detector(MagicMock())
        .build()
    )

    assert isinstance(engine._event_pusher, NullEventPusher)


# ---------- Protocol runtime checks ----------


def test_protocol_runtime_checkable():
    """Protocols are runtime_checkable — isinstance works."""
    from towow import (
        CenterToolHandler,
        Encoder,
        EventPusher,
        NullEventPusher,
        PlatformLLMClient,
        ProfileDataSource,
        ResonanceDetector,
        Skill,
    )

    # NullEventPusher satisfies EventPusher Protocol
    assert isinstance(NullEventPusher(), EventPusher)
