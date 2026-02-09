"""
EngineBuilder — convenience factory for assembling a NegotiationEngine
with all its dependencies.

Reduces the 5-argument constructor + 12-argument start_negotiation to
a fluent builder API.  Sensible defaults are provided for optional
components; only ``adapter`` and ``llm_client`` are truly required.

Usage (headless)::

    from towow import EngineBuilder

    engine, defaults = (
        EngineBuilder()
        .with_adapter(my_adapter)
        .with_llm_client(my_llm)
        .build()
    )
    session = await engine.start_negotiation(session, **defaults)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from towow.core.engine import NegotiationEngine
from towow.core.models import NegotiationSession
from towow.core.protocols import (
    CenterToolHandler,
    Encoder,
    EventPusher,
    PlatformLLMClient,
    ProfileDataSource,
    ResonanceDetector,
    Skill,
    Vector,
)
from towow.infra.event_pusher import NullEventPusher

logger = logging.getLogger(__name__)


class EngineBuilder:
    """Fluent builder for NegotiationEngine + per-run defaults."""

    def __init__(self) -> None:
        # Engine-level (set once)
        self._encoder: Encoder | None = None
        self._resonance_detector: ResonanceDetector | None = None
        self._event_pusher: EventPusher | None = None
        self._offer_timeout_s: float = 30.0
        self._confirmation_timeout_s: float = 300.0
        self._tool_handlers: list[Any] = []

        # Per-run defaults
        self._adapter: ProfileDataSource | None = None
        self._llm_client: PlatformLLMClient | None = None
        self._center_skill: Skill | None = None
        self._formulation_skill: Skill | None = None
        self._offer_skill: Skill | None = None
        self._sub_negotiation_skill: Skill | None = None
        self._gap_recursion_skill: Skill | None = None
        self._agent_vectors: dict[str, Vector] | None = None
        self._k_star: int = 5
        self._agent_display_names: dict[str, str] | None = None
        self._register_session: Callable[[NegotiationSession], None] | None = None

    # --- Engine-level ---

    def with_encoder(self, encoder: Encoder) -> EngineBuilder:
        self._encoder = encoder
        return self

    def with_resonance_detector(self, detector: ResonanceDetector) -> EngineBuilder:
        self._resonance_detector = detector
        return self

    def with_event_pusher(self, pusher: EventPusher) -> EngineBuilder:
        self._event_pusher = pusher
        return self

    def offer_timeout(self, seconds: float) -> EngineBuilder:
        self._offer_timeout_s = seconds
        return self

    def confirmation_timeout(self, seconds: float) -> EngineBuilder:
        self._confirmation_timeout_s = seconds
        return self

    def with_tool_handler(self, handler: CenterToolHandler) -> EngineBuilder:
        self._tool_handlers.append(handler)
        return self

    # --- Per-run defaults ---

    def with_adapter(self, adapter: ProfileDataSource) -> EngineBuilder:
        self._adapter = adapter
        return self

    def with_llm_client(self, client: PlatformLLMClient) -> EngineBuilder:
        self._llm_client = client
        return self

    def with_center_skill(self, skill: Skill) -> EngineBuilder:
        self._center_skill = skill
        return self

    def with_formulation_skill(self, skill: Skill) -> EngineBuilder:
        self._formulation_skill = skill
        return self

    def with_offer_skill(self, skill: Skill) -> EngineBuilder:
        self._offer_skill = skill
        return self

    def with_sub_negotiation_skill(self, skill: Skill) -> EngineBuilder:
        self._sub_negotiation_skill = skill
        return self

    def with_gap_recursion_skill(self, skill: Skill) -> EngineBuilder:
        self._gap_recursion_skill = skill
        return self

    def with_agent_vectors(self, vectors: dict[str, Vector]) -> EngineBuilder:
        self._agent_vectors = vectors
        return self

    def with_k_star(self, k: int) -> EngineBuilder:
        self._k_star = k
        return self

    def with_display_names(self, names: dict[str, str]) -> EngineBuilder:
        self._agent_display_names = names
        return self

    def with_register_session(
        self, callback: Callable[[NegotiationSession], None]
    ) -> EngineBuilder:
        self._register_session = callback
        return self

    # --- Build ---

    def build(self) -> tuple[NegotiationEngine, dict[str, Any]]:
        """Build engine and return (engine, per_run_defaults).

        ``per_run_defaults`` is a dict suitable for unpacking into
        ``engine.start_negotiation(session, **per_run_defaults)``.

        Raises ValueError if required components are missing.
        """
        # Lazy-import defaults to avoid hard dependency on optional packages
        encoder = self._encoder
        resonance = self._resonance_detector

        if encoder is None or resonance is None:
            try:
                from towow.hdc.encoder import EmbeddingEncoder
                from towow.hdc.resonance import CosineResonanceDetector
            except ImportError as exc:
                raise ValueError(
                    "No encoder/resonance_detector provided and default "
                    "implementations could not be imported. Install "
                    "'towow-sdk[embeddings]' or provide your own."
                ) from exc
            if encoder is None:
                encoder = EmbeddingEncoder()
            if resonance is None:
                resonance = CosineResonanceDetector()

        pusher = self._event_pusher or NullEventPusher()

        engine = NegotiationEngine(
            encoder=encoder,
            resonance_detector=resonance,
            event_pusher=pusher,
            offer_timeout_s=self._offer_timeout_s,
            confirmation_timeout_s=self._confirmation_timeout_s,
        )

        # Register custom tool handlers
        for handler in self._tool_handlers:
            engine.register_tool_handler(handler)

        # Build per-run defaults
        per_run: dict[str, Any] = {}
        if self._adapter is not None:
            per_run["adapter"] = self._adapter
        if self._llm_client is not None:
            per_run["llm_client"] = self._llm_client
        if self._center_skill is not None:
            per_run["center_skill"] = self._center_skill
        if self._formulation_skill is not None:
            per_run["formulation_skill"] = self._formulation_skill
        if self._offer_skill is not None:
            per_run["offer_skill"] = self._offer_skill
        if self._sub_negotiation_skill is not None:
            per_run["sub_negotiation_skill"] = self._sub_negotiation_skill
        if self._gap_recursion_skill is not None:
            per_run["gap_recursion_skill"] = self._gap_recursion_skill
        if self._agent_vectors is not None:
            per_run["agent_vectors"] = self._agent_vectors
        per_run["k_star"] = self._k_star
        if self._agent_display_names is not None:
            per_run["agent_display_names"] = self._agent_display_names
        if self._register_session is not None:
            per_run["register_session"] = self._register_session

        logger.info(
            "EngineBuilder: built engine (pusher=%s, tool_handlers=%d)",
            type(pusher).__name__,
            len(self._tool_handlers),
        )
        return engine, per_run
