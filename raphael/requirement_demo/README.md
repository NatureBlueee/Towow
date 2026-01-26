# Requirement Demo Network

A demo network showcasing the `requirement_network` mod for requirement-driven agent workflows.

## Overview

This network demonstrates:
- User agents submitting requirements in natural language
- Automatic channel creation for each requirement
- Admin agent reading registry and inviting relevant agents
- Coordinator distributing tasks after invitations complete
- Worker agents responding with accept/reject/propose

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Requirement Demo Network                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Event Flow:                                                                 │
│                                                                              │
│  User Agent                                                                  │
│      │                                                                       │
│      │ 1. Submit requirement (natural language)                              │
│      ▼                                                                       │
│  requirement_network mod                                                     │
│      │                                                                       │
│      │ 2. Create channel, emit channel_created                               │
│      ▼                                                                       │
│  Admin Agent                                                                 │
│      │                                                                       │
│      │ 3. Read registry, select agents, invite                               │
│      │ 4. Signal invitations_complete                                        │
│      ▼                                                                       │
│  Coordinator Agent                                                           │
│      │                                                                       │
│      │ 5. Distribute tasks to each agent                                     │
│      ▼                                                                       │
│  Worker Agents (Designer, Developer)                                         │
│      │                                                                       │
│      │ 6. Respond: accept / reject / propose                                 │
│      ▼                                                                       │
│  Coordinator → User (notifications)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Mods
- `openagents.mods.workspace.messaging` - Channel-based communication
- `openagents.mods.workspace.requirement_network` - Requirement workflow management

### Agents

| Agent | Type | Role |
|-------|------|------|
| admin | Python | Monitors channel_created, reads registry, invites agents |
| coordinator | Python | Distributes tasks, handles responses |
| designer | Python | UI/UX design worker (accepts design tasks, rejects coding tasks) |
| developer | Python | Software development worker (accepts dev tasks, rejects design tasks) |
| user | Python | Submits requirements, receives updates (interactive CLI) |

## Quick Start

### 1. Start the Network

```bash
cd /home/ubuntu/works/openagents
openagents serve private_networks/requirement_demo
```

### 2. Start the Admin Agent (separate terminal)

```bash
cd /home/ubuntu/works/openagents
python private_networks/requirement_demo/agents/admin_agent.py
```

### 3. Start the Coordinator Agent (separate terminal)

```bash
cd /home/ubuntu/works/openagents
python private_networks/requirement_demo/agents/coordinator_agent.py
```

### 4. Start Worker Agents (separate terminals)

```bash
# Designer
python private_networks/requirement_demo/agents/designer_agent.py

# Developer
python private_networks/requirement_demo/agents/developer_agent.py
```

### 5. Start User Agent (separate terminal)

```bash
python private_networks/requirement_demo/agents/user_agent.py
```

This provides an interactive CLI for submitting requirements.

### 6. (Optional) Connect via Studio

Open http://localhost:8800 in your browser to access the Studio interface.

### 7. Submit a Requirement

In the user agent CLI or via Studio, submit a requirement:

```
I need a landing page for my startup with modern design, responsive layout,
and integration with our backend API.
```

Watch as:
1. A new channel is created
2. Admin reads registry and invites designer + developer
3. Coordinator distributes design and development tasks
4. Workers respond with accept/reject/propose

## Agent Groups and Passwords

| Group | Password | Hash |
|-------|----------|------|
| admin | admin | 8c6976e5... |
| coordinators | coordinator | bf24385... |
| workers | researcher | 3588bb7... |
| users | user | 04f8996... |

## Events

This demo uses two categories of events:

- **Operational Events**: Request/response events for agent actions (submit, read, invite, etc.)
- **Notification Events**: Broadcast events that inform agents of state changes

### Complete Event Reference

| Event Name | Category | Direction | Handler | Description |
|------------|----------|-----------|---------|-------------|
| `requirement_network.requirement.submit` | Operational | Agent → Mod | Mod | User submits a requirement; creates channel and emits channel_created |
| `requirement_network.registry.register` | Operational | Agent → Mod | Mod | Worker registers capabilities (skills, specialties) |
| `requirement_network.registry.read` | Operational | Agent → Mod | Mod | Admin reads agent registry to find relevant agents |
| `requirement_network.agent.invite` | Operational | Agent → Mod | Mod | Admin invites agents to a requirement channel |
| `requirement_network.invitations.complete` | Operational | Agent → Mod | Mod | Admin signals all invitations are done |
| `requirement_network.channel.join` | Operational | Agent → Mod | Mod | Worker joins a requirement channel |
| `requirement_network.channel.info` | Operational | Agent → Mod | Mod | Get information about a requirement channel |
| `requirement_network.task.distribute` | Operational | Agent → Mod | Mod | Coordinator assigns a task to a worker |
| `requirement_network.task.respond` | Operational | Agent → Mod | Mod | Worker responds to a task (accept/reject/propose) |
| `requirement_network.channel_created` | Notification | Mod → Admin | Admin | Broadcast when new requirement channel is created |
| `requirement_network.invitations_complete` | Notification | Mod → Coordinator | Coordinator | Broadcast when all agents have been invited |
| `requirement_network.notification.agent_invited` | Notification | Mod → Worker | Workers | Broadcast to invited workers with channel info |
| `requirement_network.notification.task_distributed` | Notification | Mod → Worker | Workers | Broadcast to worker when task is assigned |
| `requirement_network.notification.task_response` | Notification | Mod → Coordinator | Coordinator | Broadcast when worker responds to a task |
| `requirement_network.notification.user_update` | Notification | Mod → User | User | Broadcast to user with task acceptance/rejection/proposal |

### Event Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           EVENT FLOW                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  USER AGENT                                                                   │
│      │                                                                        │
│      │ ──────[requirement.submit]──────────────────────────────►  MOD         │
│      │                                                            │           │
│      │                                                            │           │
│      │ ◄─────[notification.user_update]───────────────────────────┤           │
│                                                                   │           │
│  ADMIN AGENT                                                      │           │
│      │                                                            │           │
│      │ ◄─────[channel_created]────────────────────────────────────┤           │
│      │                                                            │           │
│      │ ──────[registry.read]──────────────────────────────────────►           │
│      │ ──────[agent.invite]───────────────────────────────────────►           │
│      │ ──────[invitations.complete]───────────────────────────────►           │
│                                                                   │           │
│  COORDINATOR AGENT                                                │           │
│      │                                                            │           │
│      │ ◄─────[invitations_complete]───────────────────────────────┤           │
│      │ ◄─────[notification.task_response]─────────────────────────┤           │
│      │                                                            │           │
│      │ ──────[task.distribute]────────────────────────────────────►           │
│                                                                   │           │
│  WORKER AGENTS (Designer, Developer)                              │           │
│      │                                                            │           │
│      │ ◄─────[notification.agent_invited]─────────────────────────┤           │
│      │ ◄─────[notification.task_distributed]──────────────────────┤           │
│      │                                                            │           │
│      │ ──────[registry.register]──────────────────────────────────►           │
│      │ ──────[channel.join]───────────────────────────────────────►           │
│      │ ──────[task.respond]───────────────────────────────────────►           │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Operational Events (Request/Response)

These events are sent by agents to request actions from the mod.

#### `requirement_network.requirement.submit`
- **Sender**: User Agent
- **Handler**: Mod
- **Payload**:
  ```json
  {
    "requirement_text": "Build a landing page...",
    "priority": "high",
    "deadline": "2024-01-15",
    "tags": ["web", "design"]
  }
  ```
- **Response**: `{success, requirement_id, channel_id}`

#### `requirement_network.registry.register`
- **Sender**: Worker Agents
- **Handler**: Mod
- **Payload**:
  ```json
  {
    "skills": ["python", "react"],
    "specialties": ["web-development", "api-design"]
  }
  ```
- **Response**: `{success}`

#### `requirement_network.registry.read`
- **Sender**: Admin Agent
- **Handler**: Mod
- **Access**: Admin group only
- **Response**: `{success, agents: [{agent_id, capabilities, ...}]}`

#### `requirement_network.agent.invite`
- **Sender**: Admin Agent
- **Handler**: Mod
- **Payload**:
  ```json
  {
    "channel_id": "req-abc123",
    "agent_ids": ["designer", "developer"]
  }
  ```

#### `requirement_network.task.distribute`
- **Sender**: Coordinator Agent
- **Handler**: Mod
- **Payload**:
  ```json
  {
    "channel_id": "req-abc123",
    "agent_id": "designer",
    "task_description": "Design the UI...",
    "task_details": {"type": "design", "deliverables": ["mockups"]}
  }
  ```
- **Response**: `{success, task_id}`

#### `requirement_network.task.respond`
- **Sender**: Worker Agents
- **Handler**: Mod
- **Payload**:
  ```json
  {
    "channel_id": "req-abc123",
    "task_id": "task-xyz",
    "response_type": "accept|reject|propose",
    "message": "I'll work on this...",
    "reason": "Outside my expertise...",
    "alternative": "I suggest instead..."
  }
  ```

### Notification Events (Broadcasts)

These events are broadcast by the mod to notify agents of state changes.

#### `requirement_network.channel_created`
- **Trigger**: After requirement submitted and channel created
- **Recipients**: Admin Agent
- **Payload**:
  ```json
  {
    "channel_id": "req-abc123",
    "requirement_id": "req-abc123",
    "requirement_text": "Build a landing page...",
    "creator_id": "user"
  }
  ```

#### `requirement_network.invitations_complete`
- **Trigger**: After admin signals invitations complete
- **Recipients**: Coordinator Agent
- **Payload**:
  ```json
  {
    "channel_id": "req-abc123",
    "requirement_id": "req-abc123",
    "requirement_text": "Build a landing page...",
    "invited_agents": ["designer", "developer"]
  }
  ```

#### `requirement_network.notification.agent_invited`
- **Trigger**: When agent is invited to a channel
- **Recipients**: Specific Worker Agent
- **Payload**:
  ```json
  {
    "channel_id": "req-abc123",
    "requirement_id": "req-abc123",
    "requirement_text": "Build a landing page..."
  }
  ```

#### `requirement_network.notification.task_distributed`
- **Trigger**: When coordinator distributes a task
- **Recipients**: Specific Worker Agent
- **Payload**:
  ```json
  {
    "channel_id": "req-abc123",
    "task_id": "task-xyz",
    "task": {
      "description": "Design the UI...",
      "type": "design",
      "deliverables": ["mockups", "wireframes"]
    }
  }
  ```

#### `requirement_network.notification.task_response`
- **Trigger**: When worker responds to a task
- **Recipients**: Coordinator Agent
- **Payload**:
  ```json
  {
    "channel_id": "req-abc123",
    "task_id": "task-xyz",
    "agent_id": "designer",
    "response_type": "accept",
    "content": {"message": "I'll work on this..."}
  }
  ```

#### `requirement_network.notification.user_update`
- **Trigger**: When a task response is received
- **Recipients**: User Agent
- **Payload**:
  ```json
  {
    "requirement_id": "req-abc123",
    "channel_id": "req-abc123",
    "update_type": "task_accepted|task_rejected|task_proposed",
    "agent_id": "designer",
    "task_id": "task-xyz",
    "content": {"message": "..."}
  }
  ```

## Customization

### Adding More Workers

Create a new Python file in `agents/` following the pattern of `designer_agent.py` or `developer_agent.py`.

Key elements:
1. Inherit from `WorkerAgent`
2. Define `SKILLS` and `SPECIALTIES` class attributes
3. Add `@on_event("requirement_network.notification.agent_invited")` handler
4. Add `@on_event("requirement_network.notification.task_distributed")` handler
5. Implement `_analyze_task()` to determine accept/reject/propose

Example structure:
```python
class MyWorkerAgent(WorkerAgent):
    default_agent_id = "my-worker"
    SKILLS = ["skill1", "skill2"]
    SPECIALTIES = ["specialty1"]

    @on_event("requirement_network.notification.agent_invited")
    async def handle_agent_invited(self, context: EventContext):
        # Register capabilities and join channel
        await self._register_capabilities()
        await self.requirement_adapter.join_requirement_channel(channel_id)

    @on_event("requirement_network.notification.task_distributed")
    async def handle_task_distributed(self, context: EventContext):
        # Analyze task and respond
        analysis = self._analyze_task(task_description, task_type)
        await self.requirement_adapter.respond_to_task(...)
```

### Modifying Selection Logic

Edit `admin_agent.py`:
- `skill_keywords` dict maps skill categories to keywords
- `_select_agents_for_requirement()` implements selection logic

### Custom Task Distribution

Edit `coordinator_agent.py`:
- `_create_task_plan()` creates task assignments
- Add custom logic based on agent types or capabilities

### Task Response Logic

Edit worker agents (`designer_agent.py`, `developer_agent.py`):
- `DEV_KEYWORDS` / `DESIGN_KEYWORDS` - keywords for task matching
- `_analyze_task()` - logic for accept/reject/propose decision
- `_generate_acceptance_message()` - custom acceptance messages

## File Structure

```
private_networks/requirement_demo/
├── network.yaml              # Network configuration
├── README.md                 # This file (English)
├── README_CN.md              # Chinese documentation (中文文档)
├── mods/                     # Local mods (network-specific)
│   └── requirement_network/  # The requirement_network mod
│       ├── __init__.py       # Module exports
│       ├── mod.py            # Network-side mod logic
│       ├── adapter.py        # Agent-side adapter/tools
│       ├── requirement_messages.py  # Pydantic message models
│       └── eventdef.yaml     # Event definitions
├── agents/
│   ├── admin_agent.py        # Admin agent (Python)
│   ├── coordinator_agent.py  # Coordinator agent (Python)
│   ├── designer_agent.py     # Designer worker (Python)
│   ├── developer_agent.py    # Developer worker (Python)
│   ├── user_agent.py         # User agent (Python, interactive)
│   ├── designer.yaml         # Designer worker (YAML, legacy)
│   ├── developer.yaml        # Developer worker (YAML, legacy)
│   └── user_agent.yaml       # User agent (YAML, legacy)
└── data/                     # Runtime data (auto-created)
```

## Local Mods

This demo uses a **local mod** (`./requirement_network`) stored in the `mods/` folder. Local mods allow you to:
- Keep custom mods self-contained within the network folder
- Distribute the entire demo as a portable package
- Modify mod behavior without affecting the global installation

To use a local mod in your network.yaml:
```yaml
mods:
  - name: ./my_custom_mod    # "./" prefix indicates local mod in mods/ folder
    enabled: true
    config:
      my_setting: value
```

Note: Both YAML and Python agent versions are available. Python agents provide explicit event handling logic, while YAML agents use LLM-based trigger processing.
