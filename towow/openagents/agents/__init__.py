"""Agent implementations."""

from .base import TowowBaseAgent, EventContext, ChannelMessageContext
from .user_agent import UserAgent
from .coordinator import CoordinatorAgent
from .channel_admin import ChannelAdminAgent
from .factory import (
    AgentFactory,
    init_agent_factory,
    get_agent_factory,
)
from .user_agent_factory import (
    UserAgentFactory,
    init_user_agent_factory,
    get_user_agent_factory,
)

__all__ = [
    # Base classes
    "TowowBaseAgent",
    "EventContext",
    "ChannelMessageContext",
    # Agents
    "UserAgent",
    "CoordinatorAgent",
    "ChannelAdminAgent",
    # General Agent Factory
    "AgentFactory",
    "init_agent_factory",
    "get_agent_factory",
    # UserAgent Factory (TASK-006)
    "UserAgentFactory",
    "init_user_agent_factory",
    "get_user_agent_factory",
]
