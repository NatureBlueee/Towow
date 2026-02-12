"""
Module-boundary Protocol definitions — the contracts between modules.

These Protocols define WHAT each module must do, not HOW.
Any implementation that satisfies the Protocol can be used interchangeably.
This is the foundation for parallel development — each team member
codes against these interfaces.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator, Optional, Protocol, runtime_checkable

import numpy as np

from .models import (
    AgentIdentity,
    AgentParticipant,
    DemandSnapshot,
    NegotiationSession,
    Offer,
    SceneDefinition,
)
from .events import NegotiationEvent


# ============ Vector Types ============

# V1: numpy array (dense float or binary). Interface doesn't prescribe shape.
Vector = np.ndarray


# ============ HDC / Encoding ============

@runtime_checkable
class Encoder(Protocol):
    """
    Encodes text into vectors. V1: embedding cosine. V2: HDC binary.

    The encoder is the "lens" in projection-as-function:
    profile_data × lens → vector
    """

    async def encode(self, text: str) -> Vector:
        """Encode a single text into a vector."""
        ...

    async def batch_encode(self, texts: list[str]) -> list[Vector]:
        """Encode multiple texts into vectors."""
        ...


@runtime_checkable
class ResonanceDetector(Protocol):
    """
    Detects resonance between a demand vector and agent vectors.

    Uses k* mechanism: returns top-k* agents by similarity,
    where k* is derived from scene config (expected_responders).
    """

    async def detect(
        self,
        demand_vector: Vector,
        agent_vectors: dict[str, Vector],  # agent_id -> vector
        k_star: int,
        min_score: float = 0.0,
    ) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        """
        Returns (activated, filtered):
        - activated: (agent_id, score) where score >= min_score, max k_star, descending
        - filtered: (agent_id, score) where score < min_score, descending
        """
        ...


# ============ Adapters (Client-side LLM) ============

@runtime_checkable
class ProfileDataSource(Protocol):
    """
    Adapter for accessing an agent's profile data.

    Client-side: calls the user's own model (SecondMe, Claude, etc.)
    through their API. The adapter abstracts away which model is used.
    """

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """Get agent's profile data for projection."""
        ...

    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send a chat request to the agent's model.
        Used for Formulation and Offer generation (client-side Skills).
        Returns the complete response text.
        """
        ...

    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming version of chat."""
        ...


# ============ Platform-side LLM Client ============

@runtime_checkable
class PlatformLLMClient(Protocol):
    """
    Platform-side LLM client with tool-use support.

    Used for Center, SubNegotiation, and GapRecursion — these are
    our own Claude API calls, not the user's model.
    """

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Send a chat request, optionally with tools.

        Returns the full response including any tool_use blocks.
        Response format:
        {
            "content": str | None,
            "tool_calls": [{"name": str, "arguments": dict, "id": str}] | None,
            "stop_reason": str,
        }
        """
        ...


# ============ Skills ============

@runtime_checkable
class Skill(Protocol):
    """
    Base protocol for all 6 Skills.

    Each Skill has a single entry point: execute().
    Input/output types vary by Skill, wrapped in dict for flexibility.
    """

    @property
    def name(self) -> str:
        """Skill name identifier."""
        ...

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the skill with the given context.

        Context keys and return keys are Skill-specific.
        See each Skill's implementation for details.
        """
        ...


# ============ Event Pusher ============

@runtime_checkable
class EventPusher(Protocol):
    """
    Pushes negotiation events to the product layer via WebSocket.

    The protocol layer pushes ALL events (principle: full push).
    The product layer decides what to display.
    """

    async def push(self, event: NegotiationEvent) -> None:
        """Push a single event."""
        ...

    async def push_many(self, events: list[NegotiationEvent]) -> None:
        """Push multiple events."""
        ...


# ============ Center Tool Handler ============

@runtime_checkable
class CenterToolHandler(Protocol):
    """
    Handler for a custom Center tool.

    Developers can register custom tools with the engine. When Center
    calls a tool by name, the engine dispatches to the registered handler.

    output_plan is always built-in (triggers state transition to COMPLETED)
    and cannot be overridden.
    """

    @property
    def tool_name(self) -> str:
        """The tool name that Center will use to invoke this handler."""
        ...

    async def handle(
        self,
        session: NegotiationSession,
        tool_args: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Handle the tool call, return result for Center's history.

        Args:
            session: The current NegotiationSession.
            tool_args: Arguments from the Center's tool call.
            context: Engine-provided dependencies:
                - adapter: ProfileDataSource
                - llm_client: PlatformLLMClient
                - display_names: dict[str, str]
                - neg_context: dict with skills and config
                - engine: NegotiationEngine reference (for recursive calls)

        Returns:
            Dict to store in history, or None to skip history entry.
        """
        ...
