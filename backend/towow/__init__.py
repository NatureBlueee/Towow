"""
Towow SDK — Agent-to-Agent negotiation engine.

Public API surface. Import everything you need from here::

    from towow import NegotiationEngine, EngineBuilder, NegotiationSession

Extension points (implement these Protocols to customize):

- ``ProfileDataSource`` / ``BaseAdapter`` — connect your own LLM
- ``PlatformLLMClient`` — swap the platform-side LLM
- ``Skill`` / ``BaseSkill`` — custom formulation / offer / center logic
- ``Encoder`` — custom vector encoding
- ``ResonanceDetector`` — custom matching algorithm
- ``EventPusher`` — custom event transport
- ``CenterToolHandler`` — add new Center tools
"""

# -- Core engine (sealed protocol layer) --
from towow.core.engine import NegotiationEngine

# -- Data models --
from towow.core.models import (
    AgentIdentity,
    AgentParticipant,
    DemandSnapshot,
    NegotiationSession,
    NegotiationState,
    Offer,
    SceneDefinition,
)

# -- Events --
from towow.core.events import EventType, NegotiationEvent

# -- Errors --
from towow.core.errors import (
    AdapterError,
    ConfigError,
    EncodingError,
    EngineError,
    LLMError,
    SkillError,
    TowowError,
)

# -- Protocols (contracts for extension) --
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

# -- Base classes (inherit to implement) --
from towow.adapters.base import BaseAdapter
from towow.skills.base import BaseSkill

# -- Builder --
from towow.builder import EngineBuilder

# -- Default implementations --
from towow.infra.event_pusher import (
    LoggingEventPusher,
    NullEventPusher,
    WebSocketEventPusher,
)

# -- Default Skills (use these or implement your own) --
from towow.skills import (
    CenterCoordinatorSkill,
    DemandFormulationSkill,
    GapRecursionSkill,
    OfferGenerationSkill,
    ReflectionSelectorSkill,
    SubNegotiationSkill,
)

__all__ = [
    # Engine
    "NegotiationEngine",
    "EngineBuilder",
    # Models
    "NegotiationSession",
    "NegotiationState",
    "DemandSnapshot",
    "SceneDefinition",
    "AgentIdentity",
    "AgentParticipant",
    "Offer",
    # Events
    "NegotiationEvent",
    "EventType",
    # Errors
    "TowowError",
    "EngineError",
    "SkillError",
    "AdapterError",
    "LLMError",
    "EncodingError",
    "ConfigError",
    # Protocols
    "Encoder",
    "ResonanceDetector",
    "ProfileDataSource",
    "PlatformLLMClient",
    "Skill",
    "EventPusher",
    "CenterToolHandler",
    "Vector",
    # Base classes
    "BaseAdapter",
    "BaseSkill",
    # Default implementations
    "NullEventPusher",
    "LoggingEventPusher",
    "WebSocketEventPusher",
    # Default Skills
    "CenterCoordinatorSkill",
    "DemandFormulationSkill",
    "GapRecursionSkill",
    "OfferGenerationSkill",
    "ReflectionSelectorSkill",
    "SubNegotiationSkill",
]
