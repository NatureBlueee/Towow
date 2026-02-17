# ToWow (通爻)

AI Agent 协作网络。核心原语：投影 (Projection)、共振 (Resonance)、回声 (Echo)。

Agent 不被搜索，而是被信号唤起——说出你需要什么，能帮你的人会自己出现。

## 双版本架构

### V1: 协商引擎 (Negotiation Engine)

五步协商流程：formulate → resonate → offer → synthesize → approve

```
CREATED → FORMULATING → FORMULATED → ENCODING → OFFERING → BARRIER_WAITING → SYNTHESIZING → COMPLETED
```

- 221 个单元测试, TypeScript SDK, App Store 演示
- 447 Agent (4 场景), 端到端协商流程

### V2: 意图场 (Intent Field)

两步一循环：场发现 → 结晶循环 → 收敛或递归

- BGE-M3-1024d 编码器, 多视角查询 (共振/互补/干涉)
- 零 LLM 匹配管道达到 93% 准确率
- 76+ 单元测试, Field 体验页 (`/field`)

协议基因组 v0.4 定义了 V2 的完整协议结构——详见 `docs/design-logs/DESIGN_LOG_006_CRYSTALLIZATION_PROTOCOL.md`。

## 项目结构

```
backend/
  server.py          # 统一入口 (Auth + V1 Engine + V2 Field + App Store, port 8080)
  towow/
    core/            # V1: 状态机、模型、事件、协议
    api/             # V1: REST + WebSocket 端点
    skills/          # V1: Center, Formulation, Offer, Gap, Sub-negotiation
    hdc/             # V1: 向量编码 + 共振检测 (MiniLM-L12-v2)
    field/           # V2: 意图场 (BGE-M3, 多视角, MemoryField)
    adapters/        # Claude, SecondMe 适配器
    infra/           # LLM Client, Event Pusher, Config
  routers/           # Auth 路由
apps/
  app_store/         # 产品面板 (场景 + Agent + 协商 Demo)
website/             # Next.js 16 前端 (Vercel)
  app/field/         # V2 Field 体验页
  app/playground/    # 开放注册 + 协商 (ADR-009)
docs/                # 架构设计 + 设计日志
  ARCHITECTURE_DESIGN.md   # V1 架构 (13 sections)
  ENGINEERING_REFERENCE.md # 工程标准
  decisions/         # ADR + PLAN + SPEC
  design-logs/       # 设计日志 001-006
  engineering/       # 开发日志 (V1, V2)
  research/          # 实验报告
  archive/           # 历史文档
```

## 开发

```bash
# 后端 (port 8080)
cd backend && source venv/bin/activate
TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn server:app --reload --port 8080

# 前端 (port 3000)
cd website && npm run dev

# 测试 (332 tests)
cd backend && python -m pytest tests/towow/ -v
```

## 路由

| 前缀 | 子系统 |
|------|--------|
| `/api/auth/*` | SecondMe OAuth2 |
| `/v1/api/*` | V1 协商引擎 |
| `/v1/ws/*` | V1 WebSocket |
| `/field/api/*` | V2 意图场 (deposit, match, match-owners, match-perspectives) |
| `/store/api/*` | App Store 网络 |
| `/store/*` | App Store 前端 |
| `/playground` | 开放注册 + 协商 |
| `/field` | V2 Field 体验页 |
| `/health` | 健康检查 |

## 文档

- [架构设计](docs/ARCHITECTURE_DESIGN.md) — V1 架构 (13 sections)
- [工程参考](docs/ENGINEERING_REFERENCE.md) — 工程标准和契约
- [设计日志](docs/design-logs/) — 001-006, 从投影哲学到结晶协议
- [开发日志](docs/engineering/) — V1 + V2 开发记录
- [架构决策](docs/decisions/) — ADR-001~013
- [实验报告](docs/research/) — V2 编码器对比、多视角查询、LLM-as-Judge
