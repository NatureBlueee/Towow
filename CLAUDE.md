# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ToWow (通爻) is an AI Agent collaboration platform. Core concepts: Projection (投影), Resonance (共振), Echo (回声). It enables AI agents to discover, negotiate, and collaborate through a response paradigm — agents respond to signals rather than being searched.

## Repository Structure

```
Towow/
├── backend/
│   ├── server.py              # Unified entry (Auth + V1 Engine + App Store)
│   ├── towow/                 # V1 negotiation engine
│   │   ├── core/              # State machine, models, events, protocols
│   │   ├── api/               # REST + WebSocket endpoints
│   │   ├── skills/            # Center, Formulation, Offer, Gap, Sub-negotiation
│   │   ├── hdc/               # Embedding encoder + resonance detector
│   │   ├── adapters/          # Claude, SecondMe adapters
│   │   └── infra/             # LLM client, event pusher, config
│   ├── routers/               # Auth routes
│   └── tests/towow/           # 256 tests
├── apps/
│   └── app_store/             # App Store (frontend + backend)
├── website/                   # Next.js 16 frontend (Vercel)
│   ├── app/                   # App Router pages (store/, playground/, negotiation/, articles/)
│   │   └── playground/        # Open registration + negotiation (ADR-009)
│   ├── components/            # React components (negotiation/, home/, ui/)
│   └── hooks/                 # useNegotiationStream, useNegotiationApi
├── docs/                      # Architecture + design logs
│   ├── ARCHITECTURE_DESIGN.md # V1 architecture (13 sections)
│   ├── ENGINEERING_REFERENCE.md
│   ├── DEV_LOG_V1.md
│   ├── DESIGN_LOG_001-005.md
│   └── prompts/               # V1 skill prompts
├── .claude/skills/            # Engineering skills (lead, arch, towow-eng, towow-dev, etc.)
├── Dockerfile                 # Production deployment
├── railway.toml               # Railway config
└── CLAUDE.md                  # This file
```

## Development Commands

```bash
# Unified backend (Auth + V1 + App Store, port 8080)
cd backend && source venv/bin/activate
TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn server:app --reload --port 8080

# Frontend (port 3000)
cd website && npm run dev

# Tests (256 total)
cd backend && source venv/bin/activate && python -m pytest tests/towow/ -v

# Frontend build
cd website && npm run build
```

## Route Layout

| Prefix | Subsystem |
|--------|-----------|
| `/api/auth/*` | SecondMe OAuth2 |
| `/v1/api/*` | V1 Negotiation Engine |
| `/v1/ws/*` | V1 WebSocket |
| `/store/api/*` | App Store Network |
| `/store/*` | App Store Frontend |
| `/playground` | Open registration + negotiation (ADR-009) |
| `/health` | Health check |

## Important Configuration

Key environment variables in `backend/.env`:
- `TOWOW_ANTHROPIC_API_KEY` - Anthropic API key for V1 engine
- `SECONDME_CLIENT_ID` - SecondMe OAuth2 client ID
- `SECONDME_CLIENT_SECRET` - SecondMe OAuth2 client secret
- `SECONDME_REDIRECT_URI` - OAuth2 callback URL
- `COOKIE_SECURE` - Set to `true` in production for HTTPS-only cookies

## V1 Negotiation Engine

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

### State Machine (8 states)
```
CREATED → FORMULATING → FORMULATED → ENCODING → OFFERING → BARRIER_WAITING → SYNTHESIZING → COMPLETED
```

### 7 Event Types
`formulation.ready` → `resonance.activated` → `offer.received` ×N → `barrier.complete` → `center.tool_call` ×N → `plan.ready` | `sub_negotiation.started`

## Development Governance

所有功能开发和改动遵循 5 阶段流程（详见 `.claude/skills/lead/SKILL.md`）：

```
① 讨论沉淀 → ② 决策书(ADR) → ③ 接口设计 → ④ 实现方案 → ⑤ 代码实现
```

**硬性原则**：
- **生产级标准，一步到位**：不写"为了测试而通过"的临时代码
- **改契约必须追踪消费方**：URL、API schema、Protocol 接口、事件格式是契约，改了必须同步所有消费方
- **类型对齐 ≠ 数据流通**：编译通过不代表数据真的流过每一环，必须逐段验证
- **模块化改动**：新功能通过 Protocol 接入，不修改已有模块内部逻辑
- **改动必须反映到文档**：契约变更 → ENGINEERING_REFERENCE.md，架构决策 → docs/decisions/

**快速通道**：小修改（≤3 文件，无契约变更）可直接进入阶段 ⑤。

## Agent-Parallel Development Guidelines

When implementing features that touch multiple independent modules, use **TeamCreate + parallel Task agents** to maximize throughput. Each agent should load the relevant engineering skill.

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
| Engineering coordination | `towow-eng` (Leader) | Plan |
| **Full lifecycle (default)** | **`lead`** | **general-purpose** |

### Key Principles
- 代码保障 > Prompt 保障 (Section 0.5): State machine, barrier, round limits are all code-enforced
- 确认是协议步骤 (Section 10.2): Engine always waits for confirmation
- 投影即函数 (Section 7.1.6): Agent is stateless, projects from profile each time
- 协议层不可改，基础设施层可替换 (Section 0.2)

## Architecture Key Concepts

- **Projection (投影)**: Agent = projection function, not stateful object
- **Resonance (共振)**: Three-tier cascade — Bloom Filter (90%) → HDC hypervectors (9%) → LLM (1%)
- **Echo (回声)**: Real-world execution signals via WOWOK blockchain

### Negotiation Flow
1. User submits demand
2. Signal broadcast with resonance filtering
3. Agents respond with offers (parallel propose → aggregate)
4. Center coordinates, identifies gaps, may trigger sub-negotiation
5. Plan output

## Archive

Legacy code preserved on branch `archive/pre-v1-cleanup`. All files removed from main were pre-V1 MVP artifacts (old agents, mods, scripts, narrative docs).
