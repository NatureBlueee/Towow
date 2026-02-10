# ToWow (通爻)

AI Agent 协作网络。核心原语：投影 (Projection)、共振 (Resonance)、回声 (Echo)。

Agent 不被搜索，而是被信号唤起——说出你需要什么，能帮你的人会自己出现。

## 架构

```
用户提交需求 → 信号广播 + 共振过滤 → Agent 响应 (Offer)
    → 屏障聚合 → Center 协调 → 方案输出
```

**协商状态机 (8 states)**
```
CREATED → FORMULATING → FORMULATED → ENCODING → OFFERING → BARRIER_WAITING → SYNTHESIZING → COMPLETED
```

## 项目结构

```
backend/
  server.py          # 统一入口 (Auth + V1 Engine + App Store)
  towow/             # V1 协商引擎
    core/            # 状态机、模型、事件、协议
    api/             # REST + WebSocket 端点
    skills/          # Center, Formulation, Offer, Gap, Sub-negotiation
    hdc/             # 向量编码 + 共振检测
    adapters/        # Claude, SecondMe 适配器
    infra/           # LLM Client, Event Pusher, Config
  routers/           # Auth 路由
apps/
  app_store/         # 产品面板 (场景 + Agent + 协商 Demo)
website/             # Next.js 前端
docs/                # 架构设计 + 设计日志
```

## 开发

```bash
# 后端
cd backend && source venv/bin/activate
TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn server:app --reload --port 8080

# 前端
cd website && npm run dev

# 测试 (190 tests)
cd backend && python -m pytest tests/towow/ -v
```

## 路由

| 前缀 | 子系统 |
|------|--------|
| `/api/auth/*` | SecondMe OAuth2 |
| `/v1/api/*` | V1 协商引擎 |
| `/v1/ws/*` | V1 WebSocket |
| `/store/api/*` | App Store 网络 |
| `/store/*` | App Store 前端 |
| `/health` | 健康检查 |

## 文档

- [架构设计](docs/ARCHITECTURE_DESIGN.md)
- [工程参考](docs/ENGINEERING_REFERENCE.md)
- [V1 开发日志](docs/DEV_LOG_V1.md)
- [设计日志](docs/DESIGN_LOG_001_PROJECTION_AND_SELF.md)
