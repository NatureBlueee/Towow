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

### Backend Architecture

**API Layer (api/):**
- `main.py` - FastAPI application entry point with CORS, middleware, and router registration
- `routers/` - API endpoints:
  - `admin.py` - Central admin agent management and network coordination
  - `demand.py` - Demand broadcasting, offer collection, negotiation flow
  - `events.py` - SSE (Server-Sent Events) for real-time updates
  - `health.py` - Health check endpoints

**Database Layer (database/):**
- `models.py` - SQLAlchemy models for users, agents, demands, offers, channels
- `services.py` - Database service layer with business logic
- `connection.py` - Database connection and session management
- `migrations/` - Alembic migration files

**OpenAgents Integration (openagents/):**
- Event-driven architecture for agent communication
- Three agent types:
  - **Central Admin Agent** - Single instance, listens for `demand.broadcast`, routes to channel admins
  - **Channel Admin Agent** - Per-demand instance, manages negotiation in isolated channels
  - **User Agent** - Per-user instance, responds to demands and participates in negotiation
- Agents communicate through OpenAgents events, not direct API calls

**Services Layer (services/):**
- Business logic for demand processing, offer evaluation, negotiation coordination
- LLM integration for intelligent filtering and response generation

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

- **OPENAGENTS_DEV_GUIDE.md** - Comprehensive OpenAgents framework guide
- **TESTING_GUIDE.md** - Testing setup and procedures
- **ToWow-Design-MVP.md** - Product design and MVP scope
- **AGENTS.md** - Agent workflow and session completion checklist
- Backend README: `towow/README.md`
- Frontend README: `towow-frontend/README.md`

## Common Gotchas

1. **Agent vs API confusion:** Agents communicate via OpenAgents events, not REST API. The API is for web UI only.

2. **Async all the way:** Backend is fully async. Don't mix sync and async database calls.

3. **Environment setup:** Both `ANTHROPIC_API_KEY` and `DATABASE_URL` must be set before backend starts.

4. **OpenAgents ports:** If testing full agent network, ensure ports 8600, 8700, 8800 are available.

5. **Database migrations:** After changing models, always create and run migrations with Alembic.

6. **Frontend API base URL:** In development, Vite proxy handles CORS. In production, set `VITE_API_BASE_URL` correctly.

7. **Test isolation:** Tests use async fixtures and auto mode. Ensure proper cleanup in `conftest.py`.

8. **Session completion:** Work is NOT done until changes are pushed to remote. This is mandatory.

## MVP Scope (Reference)

**Core MVP Features (In Scope):**
- Unified identity (user_id + secondme_id mapping)
- Agent cards in PostgreSQL (no A2A protocol yet)
- Three agent roles (Central Admin, Channel Admin, User Agent)
- Channel-based collaboration (using OpenAgents native channels)
- Demand broadcasting and intelligent filtering
- Offer mechanism and multi-round negotiation (max 5 rounds)
- Subnet recursion (max 2 layers)

**Future Features (Out of Scope for MVP):**
- Context as Agent
- A2A protocol for cross-network
- Disconnection/reconnection tokens
- Client-side filtering
- Offer caching and knowledge base
- Agent reputation system
- Waiting room mechanism

When implementing features, refer to ToWow-Design-MVP.md for detailed requirements and success criteria (e.g., support 2000 concurrent users, demonstrate emergent negotiation effects).
