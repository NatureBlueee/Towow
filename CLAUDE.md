# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ToWow (通爻) is an AI Agent collaboration platform. Core concepts: Projection (投影), Resonance (共振), Echo (回声). It enables AI agents to discover, negotiate, and collaborate through a response paradigm — agents respond to signals rather than being searched.

## Repository Structure

```
Towow/
├── website/               # Next.js 16 website (deployed to Vercel)
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   ├── hooks/             # Custom hooks (useAuth, useNegotiation, useWebSocket)
│   └── lib/               # Utilities and API clients
├── backend/               # FastAPI backend
│   ├── app.py             # Main application
│   ├── agent_manager.py   # Agent lifecycle management
│   ├── bridge_agent.py    # OpenAgents network bridge
│   └── websocket_manager.py  # WebSocket connections
├── docs/                  # Design documents and technical specs
│   ├── ARCHITECTURE_DESIGN.md  # Main architecture document
│   ├── DESIGN_LOG_*.md    # Design decision logs
│   ├── tasks/             # Contribution task definitions
│   ├── articles/          # Published articles
│   ├── screenshots/       # UI screenshots
│   └── archive/           # Archived task files
├── research/              # Community research outputs
├── agents/                # Agent implementations
├── mods/                  # OpenAgents modules
├── scripts/               # Startup and test scripts
├── .agents/               # Agent configuration
├── .ai/                   # AI task tracking
├── .beads/                # Issue tracking (bd)
├── .claude/               # Claude Code settings
├── CLAUDE.md              # This file
└── .gitignore             # Git ignore rules
```

## Development Commands

### Website + Backend
```bash
# Start backend (port 8080)
cd backend
source venv/bin/activate
uvicorn web.app:app --reload --port 8080

# Start frontend (port 3000)
cd website
npm install
npm run dev

# Or use the startup script
./scripts/start_demo.sh        # Real agents mode
./scripts/start_demo.sh --sim  # Simulation mode
```

### Website Frontend Only
```bash
cd website

npm install
npm run dev                    # Start dev server (port 3000)
npm run build                  # Production build
npm run lint                   # ESLint
```

## Important Configuration

Key environment variables in `backend/.env`:
- `SECONDME_CLIENT_ID` - SecondMe OAuth2 client ID
- `SECONDME_CLIENT_SECRET` - SecondMe OAuth2 client secret
- `SECONDME_REDIRECT_URI` - OAuth2 callback URL
- `COOKIE_SECURE` - Set to `true` in production for HTTPS-only cookies
- `USE_REAL_AGENTS` - Set to `true` to use real OpenAgents network
- `OPENAGENTS_WORKERS_PASSWORD_HASH` - Password hash for OpenAgents workers

## Demo Website Deployment

- **Production URL**: https://towow-website.vercel.app
- **Vercel Dashboard**: https://vercel.com/natureblueees-projects/towow-website

For China CDN configuration, see `website/CDN_CHINA_ACCESS_GUIDE.md`

## Issue Tracking

This project uses **bd** (beads) for issue tracking:
```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## V1 Negotiation Engine (port 8081)

```bash
# Run backend
cd backend && source venv/bin/activate
TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn towow.api.app:app --reload --port 8081

# Run tests (180 total)
cd backend && source venv/bin/activate && python -m pytest tests/towow/ -v
```

### Code Map
```
backend/towow/
  core/     engine.py (状态机+编排) | models.py | events.py | protocols.py | errors.py
  api/      app.py (lifespan+demo seed) | routes.py (5 REST+1 WS) | schemas.py
  skills/   center.py | formulation.py | offer.py | gap_recursion.py | sub_negotiation.py | reflection.py
  hdc/      encoder.py (MiniLM-L12-v2) | resonance.py
  adapters/ claude_adapter.py | secondme_adapter.py
  infra/    llm_client.py | event_pusher.py | config.py
```

## Agent-Parallel Development Guidelines

When implementing features that touch multiple independent modules, use **TeamCreate + parallel Task agents** to maximize throughput. Each agent should load the relevant engineering skill.

### When to Use Parallel Agents
- **Multi-module changes**: e.g., backend model + API + frontend type + tests can split across agents
- **Research + implementation**: one agent explores codebase/docs, another implements
- **Independent file groups**: files with no dependency between them

### When NOT to Use (Sequential is Better)
- **Linear dependency chain**: e.g., models.py → engine.py → routes.py → tests (each depends on the previous)
- **Single-file core changes**: e.g., engine.py state machine rewrite
- **< 3 files total**: overhead of team coordination exceeds benefit

### Engineering Skill Loading
Each agent MUST load the relevant `.claude/skills/` for its domain:

| Domain | Skill | Agent Type |
|--------|-------|------------|
| State machine / engine | `towow-eng-orchestrator` | general-purpose |
| LLM integration / prompts | `towow-eng-prompt` | general-purpose |
| HDC encoding / resonance | `towow-eng-hdc` | general-purpose |
| Frontend WS / UI | `towow-eng-frontend` | general-purpose |
| Test design / verification | `towow-eng-test` | general-purpose |
| Architecture alignment | `arch` | Explore or Plan |
| Overall coordination | `towow-eng` (Leader) | Plan |

### Pattern: Architecture-Aligned Development
1. **Before coding**: Use `arch` skill or Plan agent to verify design aligns with `docs/ARCHITECTURE_DESIGN.md`
2. **During coding**: Each implementation agent reads the relevant SKILL.md for constraints
3. **After coding**: Run full test suite (`pytest tests/towow/ -v`), update MEMORY.md
4. **Key principles to check**:
   - 代码保障 > Prompt 保障 (Section 0.5)
   - 确认是协议步骤 (Section 10.2)
   - 投影即函数 (Section 7.1.6)
   - 协议层不可改，基础设施层可替换 (Section 0.2)

### Pattern: Codex for Mechanical Tasks
Use `mcp__codex__codex` for:
- Boilerplate generation (new test files, schema fields, type definitions)
- Repetitive edits across many files (rename, add field everywhere)
- Code formatting / migration patterns

Do NOT use Codex for:
- State machine logic or protocol-layer changes
- Anything requiring understanding of the negotiation lifecycle
- Test design (tests encode architectural invariants)

## Architecture Key Concepts

### Core Mechanism
- **Projection (投影)**: Agent = projection function, not stateful object. Profile data lives in data sources (SecondMe/Claude/GPT/...), ToWow only projects.
- **Resonance (共振)**: Three-tier cascade — Bloom Filter (90%) → HDC hypervectors (9%) → LLM (1%)
- **Echo (回声)**: Real-world execution signals via WOWOK blockchain, not LLM self-judgment

### Negotiation Flow
1. User submits demand
2. Signal broadcast with resonance filtering
3. Agents respond with offers (parallel propose → aggregate)
4. Center coordinates, identifies gaps, may trigger sub-negotiation
5. Contract output → WOWOK Machine for execution
6. Execution signals echo back → profile evolution

### Demo Scenario
Demo scenario config: `backend/demo_scenario.json`

Current scenario: **Finding a Technical Co-founder**
- 7 Agents with distinct capabilities
- 6 stages: Discovery → Response → Discussion → Deep Negotiation → Consensus → Proposal
- Demonstrates cognitive shift: user thinks they need a "tech co-founder", discovers they need "ability to validate ideas quickly"
