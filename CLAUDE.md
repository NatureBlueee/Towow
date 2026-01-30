# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ToWow is an AI Agent collaboration platform built on OpenAgents framework. It enables multiple AI agents to negotiate and collaborate on user demands through a structured coordination system with three agent roles: Coordinator (central admin), ChannelAdmin (per-negotiation manager), and UserAgent (represents individual users).

## Repository Structure

```
Towow/
├── towow/                 # Python backend (FastAPI + PostgreSQL)
│   ├── api/               # FastAPI routes and endpoints
│   │   ├── main.py        # Application entry, lifespan, middleware setup
│   │   └── routers/       # demand.py, events.py, admin.py, health.py
│   ├── openagents/        # Agent system implementation
│   │   └── agents/        # Coordinator, ChannelAdmin, UserAgent, Router
│   ├── services/          # Business logic (LLM, SecondMe, demo_mode, gap_identification)
│   ├── events/            # Event bus and recording system
│   ├── database/          # SQLAlchemy models, connection, migrations
│   └── config.py          # Centralized configuration (env-based)
├── towow-frontend/        # React frontend (Vite + TypeScript)
│   └── src/
│       ├── pages/         # Main pages (SubmitDemand, Negotiation)
│       ├── features/      # Feature modules (demand, negotiation, dashboard)
│       ├── stores/        # Zustand state management (demandStore, eventStore)
│       └── api/           # API client functions
├── raphael/requirement_demo/  # Demo project with website
│   ├── towow-website/     # Next.js 16 website (deployed to Vercel)
│   │   ├── app/           # App Router pages
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks (useAuth, useNegotiation, useWebSocket)
│   │   └── lib/           # Utilities and API clients
│   ├── web/               # FastAPI backend for demo
│   │   ├── app.py         # Main application
│   │   ├── agent_manager.py  # Agent lifecycle management
│   │   ├── bridge_agent.py   # OpenAgents network bridge
│   │   └── websocket_manager.py  # WebSocket connections
│   └── scripts/           # Startup scripts
└── docs/                  # Design documents and technical specs
```

## Development Commands

### Backend (towow/)
```bash
cd towow
source venv/bin/activate

# Start dev server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest                              # All tests
pytest tests/test_api.py            # Single file
pytest -v                           # Verbose output

# Code quality
ruff check .                        # Linting
ruff check . --fix                  # Auto-fix
mypy .                              # Type checking

# Database
alembic upgrade head                # Run migrations
alembic current                     # Check migration status
```

### Demo Website (raphael/requirement_demo/)
```bash
cd raphael/requirement_demo

# Start backend (port 8080)
source venv/bin/activate
uvicorn web.app:app --reload --port 8080

# Start frontend (port 3000)
cd towow-website
npm install
npm run dev

# Or use the startup script
./scripts/start_demo.sh        # Real agents mode
./scripts/start_demo.sh --sim  # Simulation mode
```

### Frontend (towow-frontend/)
```bash
cd towow-frontend

# Install dependencies (uses pnpm)
npm install

# Development
npm run dev                         # Start dev server (port 5173)

# Build
npm run build                       # TypeScript check + Vite build

# Linting
npm run lint                        # ESLint
```

### Quick Start (both services)
```bash
# Terminal 1 - Backend
cd towow && source venv/bin/activate && uvicorn api.main:app --reload --port 8000

# Terminal 2 - Frontend
cd towow-frontend && npm run dev
```

## Architecture Key Concepts

### Agent Hierarchy
1. **Coordinator** (`towow/openagents/agents/coordinator.py`): Singleton agent that manages the network, receives demands, performs agent filtering via LLM
2. **ChannelAdmin** (`towow/openagents/agents/channel_admin.py`): Created per-negotiation, manages multi-round negotiation lifecycle, aggregates offers into proposals
3. **UserAgent** (`towow/openagents/agents/user_agent.py`): Represents each user, generates offers based on SecondMe persona data

### Negotiation Flow
1. User submits demand via `/api/demand/submit`
2. Coordinator filters relevant agents using LLM
3. ChannelAdmin orchestrates negotiation rounds (max configurable via `MAX_NEGOTIATION_ROUNDS`)
4. UserAgents submit offers based on their capabilities
5. ChannelAdmin aggregates offers, identifies gaps, may trigger subnet recursion

### Event System
- SSE-based real-time updates via `/api/events/stream/{demand_id}`
- Event types: `filter_*`, `agent_*`, `negotiation_*`, `proposal_*`, `gap_*`, `subnet_*`
- Frontend subscribes via `eventStore.ts` and displays progressive UI updates

### State Management
- Backend: Config via environment variables (see `.env.example`)
- Frontend: Zustand stores for demand and negotiation events

## Important Configuration

Key environment variables in `towow/.env`:
- `ANTHROPIC_API_KEY` - Required for LLM calls
- `DATABASE_URL` - PostgreSQL connection
- `TOWOW_MAX_NEGOTIATION_ROUNDS` - Max rounds before forcing decision (default: 3)
- `TOWOW_ENABLE_STAGE_DELAYS` - Enable realistic UX delays (default: true)

Key environment variables in `raphael/requirement_demo/web/.env`:
- `SECONDME_CLIENT_ID` - SecondMe OAuth2 client ID
- `SECONDME_CLIENT_SECRET` - SecondMe OAuth2 client secret
- `SECONDME_REDIRECT_URI` - OAuth2 callback URL
- `COOKIE_SECURE` - Set to `true` in production for HTTPS-only cookies
- `USE_REAL_AGENTS` - Set to `true` to use real OpenAgents network
- `OPENAGENTS_WORKERS_PASSWORD_HASH` - Password hash for OpenAgents workers

## Demo Website Deployment

- **Production URL**: https://towow-website.vercel.app
- **Vercel Dashboard**: https://vercel.com/natureblueees-projects/towow-website

For China CDN configuration, see `raphael/requirement_demo/towow-website/CDN_CHINA_ACCESS_GUIDE.md`

## Issue Tracking

This project uses **bd** (beads) for issue tracking:
```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```
