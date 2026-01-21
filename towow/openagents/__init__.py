"""ToWow OpenAgents module."""

from openagents.agents.base import TowowBaseAgent, EventContext, ChannelMessageContext
from openagents.config import openagent_config, app_config, OpenAgentConfig, AppConfig

# Lazy import launcher to avoid external dependency issues during testing
try:
    from openagents.launcher import AgentLauncher, AgentConfig, launcher, quick_start
    _LAUNCHER_AVAILABLE = True
except ImportError:
    AgentLauncher = None
    AgentConfig = None
    launcher = None
    quick_start = None
    _LAUNCHER_AVAILABLE = False

__all__ = [
    "TowowBaseAgent",
    "EventContext",
    "ChannelMessageContext",
    "openagent_config",
    "app_config",
    "OpenAgentConfig",
    "AppConfig",
]

if _LAUNCHER_AVAILABLE:
    __all__.extend(["AgentLauncher", "AgentConfig", "launcher", "quick_start"])
