# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ToWow is an AI Agent collaboration platform built on OpenAgents, designed to demonstrate large-scale agent network coordination (2000+ concurrent agents). The system enables AI agents to:
- Broadcast demands and intelligently filter responses
- Submit offers and negotiate solutions through multi-round collaboration
- Form dynamic sub-networks for complex tasks (recursive up to 2 layers in MVP)
- Coordinate through three agent roles: Central Admin, Channel Admin, and User Agents

**Tech Stack:**
- **Backend:** Python 3.10+, FastAPI, PostgreSQL, SQLAlchemy, OpenAgents
- **Frontend:** React 19, TypeScript, Vite, Ant Design, TailwindCSS
- **LLM:** Anthropic Claude API

**Repository Structure:**
```
Towow/
├── towow/              # Backend (FastAPI + PostgreSQL + OpenAgents)
├── towow-frontend/     # Frontend (React + Vite + TypeScript)
├── docs/               # Documentation
├── .ai/                # AI-specific configurations
└── .beads/             # Issue tracking data
```

## Development Commands

### Backend (towow/)

**Setup:**
```bash
cd towow
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
cp .env.example .env  # Configure API keys and database
alembic upgrade head  # Run database migrations
```

**Development:**
```bash
# Start server with hot reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest

# Run tests with coverage
pytest --cov=api --cov=services --cov=database

# Run specific test file
pytest tests/test_channel_admin.py

# Code quality checks
ruff check .
ruff check . --fix  # Auto-fix issues
mypy .

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

**Docker:**
```bash
# Start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Frontend (towow-frontend/)

**Setup:**
```bash
cd towow-frontend
npm install
```

**Development:**
```bash
# Start development server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Quick Start (Both Services)

```bash
# Terminal 1 - Backend
cd towow && source venv/bin/activate && uvicorn api.main:app --reload --port 8000

# Terminal 2 - Frontend
cd towow-frontend && npm run dev
```

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### OpenAgents Network

```bash
# Start OpenAgents network (if testing agent features)
cd openagents
python3 -m openagents.cli network start

# Start an agent from config
openagents agent start agents/config.yaml

# Default ports
# - 8700: HTTP transport (network discovery)
# - 8600: gRPC transport (agent connections)
# - 8800: MCP transport
```

## Architecture Overview

### ⚠️ Critical Architecture Context

**Design Intent vs. Actual Implementation:**

The project was **designed** to use OpenAgent framework, but the actual implementation uses a **self-built lightweight agent infrastructure**. This is crucial to understand:

**Original Plan:**
- Inherit from OpenAgent's `WorkerAgent`
- Use OpenAgent's native Channel management
- Leverage OpenAgent's event bus and message routing

**Actual Implementation:**
- `TowowBaseAgent` - Custom base class (NOT inheriting from OpenAgent)
- `AgentRouter` - Custom message routing with deduplication
- `AgentFactory` - Custom agent instance management
- `AgentLauncher` - Custom lifecycle management
- Mock implementations of `workspace()`, `send_to_agent()`, `post_to_channel()`

**Why this decision was made:**
1. Time constraint (7-10 days to MVP demo)
2. Learning curve with OpenAgent APIs
3. Need for full control during rapid iteration
4. Uncertainty about OpenAgent's capabilities for 2000+ agents

**Current Status:**
- ✅ 23,000 lines of code written
- ✅ Core business logic 80-90% complete
- ✅ All three agent types implemented (Coordinator, ChannelAdmin, UserAgent)
- ⚠️ Real OpenAgent integration pending
- ⚠️ Channel broadcasting is mocked
- ⚠️ Agent registration/discovery not implemented

### Backend Architecture

**API Layer (api/):**
- `main.py` - FastAPI application entry point with CORS, middleware, and router registration
- `routers/` - API endpoints (for Web UI only, NOT for agent-to-agent communication):
  - `admin.py` - Central admin agent management and network coordination
  - `demand.py` - Demand broadcasting, offer collection, negotiation flow
  - `events.py` - SSE (Server-Sent Events) for real-time updates to frontend
  - `health.py` - Health check endpoints

**Database Layer (database/):**
- `models.py` - SQLAlchemy models for users, agents, demands, offers, channels
- `services.py` - Database service layer with business logic
- `connection.py` - Database connection and session management
- `migrations/` - Alembic migration files

**Agent Layer (openagents/)** - Self-Implemented:
- `agents/base.py` (8KB) - TowowBaseAgent with mock workspace API
- `agents/coordinator.py` (23KB) - Central coordinator for demand routing and smart filtering
- `agents/channel_admin.py` (77KB) - Channel management and negotiation orchestration
- `agents/user_agent.py` (37KB) - User digital twin for demand participation
- `agents/router.py` (7.5KB) - Message routing with deduplication logic
- `agents/factory.py` (6.5KB) - Agent instance management (singleton + caching)
- `launcher.py` (4KB) - Agent lifecycle management

**Three Agent Types:**
- **Coordinator** - Single instance, receives demands, calls LLM for smart filtering (3-15 from 2000), creates channels
- **ChannelAdmin** - Per-demand instance, manages negotiation lifecycle, aggregates proposals, handles subnet recursion (max 2 layers)
- **UserAgent** - Per-user instance (lazy-loaded, cached), interfaces with SecondMe or LLM for decision-making

**Services Layer (services/):**
- Business logic for demand processing, offer evaluation, negotiation coordination
- LLM integration for intelligent filtering and response generation
- SecondMe API integration (with mock fallback)

### Frontend Architecture

**Features-based structure (src/features/):**
- `dashboard/` - Main dashboard and network overview
- `demand/` - Demand creation and broadcasting UI
- `negotiation/` - Real-time negotiation visualization

**Shared (src/):**
- `api/` - Axios client and API service functions
- `components/` - Reusable UI components
- `stores/` - Zustand state management
- `hooks/` - Custom React hooks
- `types/` - TypeScript type definitions
- `utils/` - Helper functions

**State Management:**
- Uses Zustand for global state
- React Query patterns for server state (if applicable)
- Component-local state for UI-only concerns

### Key Architectural Patterns

**Event-Driven Agent Communication:**
- Agents don't call APIs directly; they emit and listen for OpenAgents events
- Event types: `demand.broadcast`, `offer.submitted`, `negotiation.update`, etc.
- Backend API endpoints are for web UI only, not for agent-to-agent communication

**Async Processing:**
- FastAPI uses async/await throughout
- Database operations are async (SQLAlchemy async session)
- SSE for streaming updates to frontend

**Multi-Round Negotiation Flow:**
1. User creates demand → Backend emits `demand.broadcast` event
2. Central Admin agent receives event → Filters and creates Channel
3. Channel Admin agent invites qualified User Agents
4. User Agents submit offers → Channel Admin aggregates
5. Multi-round negotiation (max 5 rounds) until consensus or timeout
6. Final solution returned to user

**Subnet Recursion:**
- If Channel Admin detects capability gaps, it can spawn a sub-demand
- Sub-demands create new channels with their own Channel Admin
- Max 2 layers of recursion in MVP (can be configured)

## Project-Specific Conventions

### Environment Variables

**Backend (.env):**
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://user:pass@localhost:5432/towow

# Optional
OPENAGENT_HOST=localhost
OPENAGENT_HTTP_PORT=8700
OPENAGENT_GRPC_PORT=8600
DEBUG=true
LOG_LEVEL=INFO
```

**Frontend (.env.local):**
```bash
VITE_API_BASE_URL=http://localhost:8000
```

### Database Models

Key entities:
- **User** - Platform users (mapped to SecondMe IDs in MVP)
- **Agent** - Agent profiles with capabilities and availability
- **Demand** - User-submitted demands for collaboration
- **Offer** - Agent responses to demands
- **Channel** - Negotiation spaces (maps to OpenAgents channels)
- **Negotiation** - Multi-round negotiation state and history

### Testing Strategy

**Backend Tests (towow/tests/):**
- `conftest.py` - Pytest fixtures and configuration
- `test_channel_admin.py` - Channel admin agent behavior
- `test_coordinator.py` - Central coordinator logic
- `test_subnet.py` - Subnet recursion
- `test_circuit_breaker.py` - Circuit breaker patterns
- `test_sse_events.py` - Server-sent events
- `e2e/` - End-to-end integration tests

**Test configuration (pyproject.toml):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

Always run tests before committing significant changes.

### Code Style

**Backend:**
- Use `ruff` for linting and formatting (max line length: 100)
- Type hints required (enforced by `mypy`)
- Async/await for all I/O operations
- Follow FastAPI best practices for routers and dependencies

**Frontend:**
- ESLint with React and TypeScript rules
- Functional components with hooks (no class components)
- TypeScript strict mode enabled
- Tailwind for styling (avoid inline styles)

## Issue Tracking with Beads

This project uses **bd** (beads) for issue tracking:

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

**Important:** When ending a work session, you MUST:
1. Create issues for remaining work
2. Run quality gates (tests, linters) if code changed
3. Update issue status
4. **Push to remote** (work is NOT complete until `git push` succeeds)
5. Verify with `git status` (must show "up to date with origin")

## Git Workflow

**Branch naming:**
- Feature branches: `claude/feature-name-<session-id>`
- Current branch: `claude/init-project-setup-3fqjb`

**Commit messages:**
- Follow conventional commits style
- Include session URL at end: `https://claude.ai/code/session_...`

**Push requirements:**
- Always use `git push -u origin <branch-name>`
- Branch must start with `claude/` and end with matching session ID
- Retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s) if network errors occur

**NEVER:**
- Force push to main/master
- Skip hooks (`--no-verify`)
- Use `git add -A` or `git add .` (prefer adding specific files)
- Amend commits after pre-commit hook failures (create new commits instead)

## Important Documentation

**Must-Read Before Starting Work:**

1. **ALIGNMENT-REPORT-v1.md** - Gap analysis between design and implementation
   - Shows what's complete (80-90%) and what's missing (10-20%)
   - Lists all Critical/High/Medium priority gaps
   - Provides SQL migration scripts for fixes

2. **docs/tech/TOWOW-AGENT-IMPLEMENTATION.md** - Deep dive into agent architecture
   - Explains why we built custom infrastructure instead of using OpenAgent
   - Documents all agent communication mechanisms
   - Outlines technical challenges and questions for OpenAgent team

3. **ToWow-Design-MVP.md** - Product design and MVP scope
   - 10 core MVP concepts
   - 21-step workflow
   - Success criteria (100 users, 2000 concurrent, subnet demo)

4. **docs/tech/TECH-TOWOW-MVP-v1.md** - Technical architecture spec
   - System architecture diagrams
   - Technology choices and rationale
   - Deployment configuration

5. **TESTING_GUIDE.md** - Testing setup and procedures
   - How to run tests for each agent type
   - E2E test scenarios
   - Mock data setup

6. **OPENAGENTS_DEV_GUIDE.md** - OpenAgent framework guide
   - Reference for what OpenAgent *should* provide
   - Note: Current code does NOT fully use this

7. **AGENTS.md** - Agent workflow and session completion checklist

8. **Task Documentation (docs/tasks/):**
   - TASK-001 to TASK-020: Detailed implementation tasks
   - Each shows planned vs actual implementation
   - Check task status before starting related work

## Project Status & Known Gaps

### Implementation Progress (Based on ALIGNMENT-REPORT-v1.md)

**Concept Coverage:** 80% (8/10 complete)
**Flow Coverage:** 90% (19/21 steps complete)
**Data Structure:** 70% (several fields missing)

### Critical Gaps (Must Fix Before Production)

1. **GAP-001: Missing `offers` table**
   - Current: Offers handled as ephemeral messages
   - Need: Dedicated table with offer_id, confidence, decision, structured_data
   - Impact: Cannot persist or analyze offer data

2. **GAP-002: Missing identity fields**
   - Current: `agent_profiles` lacks `user_id` and `secondme_id` columns
   - Need: Add these fields to support unified identity mapping
   - Impact: Cannot properly map SecondMe users to agents

3. **GAP-003: Missing capability_tags**
   - Current: `demands` table lacks `capability_tags` JSONB field
   - Need: Add for capability-based filtering
   - Impact: Smart filtering uses unstructured data

4. **GAP-004: Channel archiving not implemented**
   - Current: Channels marked complete but not archived to `collaboration_history`
   - Need: Implement `ChannelAdmin._archive_channel()` method
   - Impact: No historical record of negotiations

5. **GAP-005: notify_user not implemented**
   - Current: Final proposal not sent back to user via SecondMe
   - Need: Implement SecondMe notification callback
   - Impact: Users don't receive results

### Agent Communication Caveats

**Real vs Mock Implementation:**
```python
# ⚠️ These methods are MOCKED, not real OpenAgent calls:
await agent.send_to_agent(target_id, data)  # Goes through AgentRouter, not network
await agent.post_to_channel(channel, data)  # Logged but not broadcast
await agent.workspace().agents()             # Returns empty list

# ✅ These work as expected:
await agent.llm.complete(prompt)             # Real LLM calls
await agent.db.execute(query)                # Real database queries
```

**Message Routing:**
- All agent-to-agent messages go through `AgentRouter`
- Router uses `AgentFactory` to get target instances
- Messages delivered synchronously via `target.on_direct(context)`
- Deduplication based on `from_agent:to_agent:msg_type:channel_id` key
- Recent messages cached for 5 seconds to prevent duplicates

**Agent Instance Management:**
- Coordinator & ChannelAdmin: Singletons
- UserAgent: Lazy-loaded and cached per user_id
- No automatic cleanup (instances persist in memory)
- Factory pattern used: `get_agent_factory().get_user_agent(user_id, profile)`

## Common Gotchas

1. **Agent communication is NOT using OpenAgent:** Despite the `openagents/` directory name, the implementation is custom. Don't expect OpenAgent's native features to work.

2. **send_to_agent is synchronous:** The router waits for the target agent to process messages. In high concurrency, this can cause blocking.

3. **Channel broadcasts are mocked:** `post_to_channel()` doesn't actually broadcast. You must manually send to each participant.

4. **Agent vs API confusion:** Agents communicate via custom router, not REST API. The FastAPI endpoints are for web UI only.

5. **Async all the way:** Backend is fully async. Don't mix sync and async database calls.

6. **Environment setup:** Both `ANTHROPIC_API_KEY` and `DATABASE_URL` must be set before backend starts.

7. **OpenAgents ports:** Ports 8600, 8700, 8800 are defined but not actually used in current implementation.

8. **Database migrations:** After changing models, always create and run migrations with Alembic.

9. **Frontend API base URL:** In development, Vite proxy handles CORS. In production, set `VITE_API_BASE_URL` correctly.

10. **Test isolation:** Tests use async fixtures and auto mode. Ensure proper cleanup in `conftest.py`.

11. **Session completion:** Work is NOT done until changes are pushed to remote. This is mandatory.

12. **Event naming inconsistency:** Design docs use `plan.*` events, code uses `proposal.*`. They refer to the same thing.

## Key Technical Decisions & Rationale

### Why Custom Agent Infrastructure Instead of OpenAgent?

**Context:** Project timeline is 7-10 days to MVP demo (Feb 1, 2026).

**Decision Factors:**
1. **Time Constraint:** Learning OpenAgent's APIs would take 2-3 days
2. **Control:** Need to debug and iterate quickly without framework limitations
3. **Uncertainty:** Not sure if OpenAgent handles 2000 concurrent agents well
4. **Pragmatism:** Can build working demo with mocks, migrate to real OpenAgent later

**Current Trade-offs:**
- ✅ Fast iteration and full debugging control
- ✅ Business logic (filtering, aggregation, recursion) is framework-agnostic
- ❌ Missing real agent communication (all mocked)
- ❌ No actual Channel broadcasting
- ❌ No distributed agent deployment

**Future Migration Path:**
1. Keep business logic in agent classes
2. Replace `TowowBaseAgent` to inherit from OpenAgent's `WorkerAgent`
3. Replace `AgentRouter` with OpenAgent's native routing
4. Replace `workspace()` mocks with real OpenAgent workspace
5. Test with real OpenAgent network

### Architecture Invariants (Don't Change These)

1. **Event-Driven Design:** All agent interactions are event-based, never direct function calls
2. **Agent Autonomy:** Each agent type has its own decision-making logic via LLM
3. **Channel Isolation:** Each demand gets its own isolated channel, no cross-channel interference
4. **Idempotency:** All state changes are protected by flags (e.g., `proposal_distributed`, `finalized_notified`)
5. **Async First:** All I/O operations are async, no blocking calls
6. **Database as State:** Agent state persists in PostgreSQL, not in-memory (except for `ChannelState` during active negotiation)

### Performance Considerations

**Current Bottlenecks:**
1. **Synchronous Message Routing:** `AgentRouter` waits for target to process message (blocking)
2. **LLM Calls:** Smart filtering (2000 profiles → 15 candidates) takes 5-10 seconds
3. **No Caching:** Agent profiles loaded from DB on every filter operation
4. **SSE Fan-out:** Broadcasting events to many frontend clients can overwhelm server

**Mitigation Strategies (Implemented):**
- Rate limiting middleware (100 concurrent requests)
- Circuit breaker pattern for external services
- Demo mode with pre-computed results
- Graceful degradation if LLM/SecondMe unavailable

**Future Optimizations (If Needed):**
- Cache agent profiles in Redis
- Async message delivery (fire-and-forget)
- LLM result caching for similar demands
- SSE connection pooling

## MVP Scope (Reference)

**Core MVP Features (In Scope):**
- Unified identity (user_id + secondme_id mapping) - ⚠️ Partially complete
- Agent cards in PostgreSQL (no A2A protocol yet) - ✅ Complete
- Three agent roles (Central Admin, Channel Admin, User Agent) - ✅ Complete
- Channel-based collaboration - ⚠️ Mocked, not using OpenAgent channels
- Demand broadcasting and intelligent filtering - ✅ Complete
- Offer mechanism and multi-round negotiation (max 5 rounds) - ✅ Complete
- Subnet recursion (max 2 layers) - ✅ Complete

**Critical Gaps to Fix Before Demo:**
- Add `offers` table (GAP-001)
- Add `user_id`/`secondme_id` fields (GAP-002)
- Implement channel archiving (GAP-004)
- Implement user notification (GAP-005)

**Future Features (Out of Scope for MVP):**
- Context as Agent
- A2A protocol for cross-network
- Disconnection/reconnection tokens
- Client-side filtering
- Offer caching and knowledge base
- Agent reputation system
- Waiting room mechanism

**Success Criteria (Per Design Doc):**
- [ ] 100 real users can submit/respond to demands
- [ ] Audience can watch negotiation in real-time (SSE implemented ✅)
- [ ] At least one demo triggers subnet recursion (need pre-set scenario)
- [ ] 2000 concurrent users don't crash the system (needs load testing ⚠️)

When implementing features, refer to ToWow-Design-MVP.md for detailed requirements and ALIGNMENT-REPORT-v1.md for gap analysis.
