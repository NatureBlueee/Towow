"""
Requirement Network Mod for OpenAgents.

This mod enables a requirement-driven workflow with:
- User agents submitting requirements in natural language
- Automatic channel creation for each requirement
- Agent registry with admin-only access
- Admin agent invitation of relevant agents
- Coordinator task distribution and response handling

Key features:
- Submit requirements in natural language
- Auto-create dedicated channels for each requirement
- Maintain agent registry with capabilities and agent cards
- Admin-only registry access for agent discovery
- Invite relevant agents to requirement channels
- Distribute tasks and handle responses (accept/reject/propose)
"""

import sys
from pathlib import Path

# Add local mod directory to path for imports
_mod_dir = Path(__file__).parent
if str(_mod_dir) not in sys.path:
    sys.path.insert(0, str(_mod_dir))

# Use absolute imports after adding to path
from adapter import RequirementNetworkAdapter
from mod import RequirementNetworkMod
from requirement_messages import (
    AgentRegistryEntry,
    RequirementChannel,
    RequirementSubmitMessage,
    RegistryRegisterMessage,
    RegistryReadMessage,
    AgentInviteMessage,
    TaskDistributeMessage,
    TaskRespondMessage,
)

__all__ = [
    "RequirementNetworkAdapter",
    "RequirementNetworkMod",
    "AgentRegistryEntry",
    "RequirementChannel",
    "RequirementSubmitMessage",
    "RegistryRegisterMessage",
    "RegistryReadMessage",
    "AgentInviteMessage",
    "TaskDistributeMessage",
    "TaskRespondMessage",
]
