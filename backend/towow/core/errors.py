"""
Unified exception hierarchy for the Towow system.

All exceptions inherit from TowowError. Each module has its own
exception type for clear error attribution.
"""


class TowowError(Exception):
    """Base exception for all Towow errors."""
    pass


class AdapterError(TowowError):
    """Client-side adapter failure (LLM unavailable, auth expired, etc.)."""
    pass


class LLMError(TowowError):
    """Platform-side LLM call failure."""
    pass


class SkillError(TowowError):
    """Skill execution failure (output format error, timeout, etc.)."""
    pass


class EngineError(TowowError):
    """Orchestration engine internal error (invalid state transition, etc.)."""
    pass


class EncodingError(TowowError):
    """Vector encoding or resonance detection error."""
    pass


class ConfigError(TowowError):
    """Configuration error (missing env vars, invalid config, etc.)."""
    pass
