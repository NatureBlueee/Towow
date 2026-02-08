"""Core protocol layer — negotiation rules, events, models, errors."""

from .errors import (
    TowowError,
    AdapterError,
    LLMError,
    SkillError,
    EngineError,
    EncodingError,
    ConfigError,
)
from .events import EventType, NegotiationEvent
from .models import (
    AgentIdentity,
    AgentParticipant,
    AgentState,
    AgentType,
    DemandSnapshot,
    NegotiationSession,
    NegotiationState,
    Offer,
    SceneDefinition,
    TraceChain,
    TraceEntry,
    generate_id,
)
from .protocols import (
    Encoder,
    EventPusher,
    PlatformLLMClient,
    ProfileDataSource,
    ResonanceDetector,
    Skill,
    Vector,
)

__all__ = [
    "TowowError", "AdapterError", "LLMError", "SkillError",
    "EngineError", "EncodingError", "ConfigError",
    "EventType", "NegotiationEvent",
    "AgentIdentity", "AgentParticipant", "AgentState", "AgentType",
    "DemandSnapshot", "NegotiationSession", "NegotiationState",
    "Offer", "SceneDefinition", "TraceChain", "TraceEntry", "generate_id",
    "Encoder", "EventPusher", "PlatformLLMClient",
    "ProfileDataSource", "ResonanceDetector", "Skill", "Vector",
]
