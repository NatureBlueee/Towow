# V1 开发日志

## 2026-02-09: Phase 0 + Phase 1 + Phase 2 完成

### 进度总结
- **Phase 0 (Foundation)**: COMPLETE — 项目结构、Protocol 定义、核心模型、测试基础
- **Phase 1 (5 Parallel Streams)**: COMPLETE — 所有 5 个 Stream 完成
- **Phase 2 (Integration)**: COMPLETE — API 层、端到端集成测试、前端类型修复
- **全部 172 个后端测试通过**
- **前端 `next build` 通过**

### 模块状态

| 模块 | 文件 | 测试数 | 状态 |
|------|------|--------|------|
| Core Models | `towow/core/models.py` | 12 | DONE |
| Core Events | `towow/core/events.py` | 10 | DONE |
| Core Engine | `towow/core/engine.py` | 29 | DONE |
| HDC Encoder | `towow/hdc/encoder.py` | 17 | DONE |
| HDC Resonance | `towow/hdc/resonance.py` | 14 | DONE |
| Claude Adapter | `towow/adapters/claude_adapter.py` | 7 | DONE |
| SecondMe Adapter | `towow/adapters/secondme_adapter.py` | 7 | DONE |
| Platform LLM Client | `towow/infra/llm_client.py` | 5 | DONE |
| Event Pusher | `towow/infra/event_pusher.py` | 3 | DONE |
| Config | `towow/infra/config.py` | 2 | DONE |
| Formulation Skill | `towow/skills/formulation.py` | 7 | DONE |
| Offer Skill | `towow/skills/offer.py` | 7 | DONE |
| Center Skill | `towow/skills/center.py` | 16 | DONE |
| SubNeg Skill | `towow/skills/sub_negotiation.py` | 6 | DONE |
| Gap Recursion Skill | `towow/skills/gap_recursion.py` | 7 | DONE |
| API Layer | `towow/api/` (app + routes + schemas) | 17 | DONE |
| E2E Integration | `tests/towow/test_e2e.py` | 6 | DONE |
| Frontend Types | `website/types/negotiation.ts` | — | DONE |
| Frontend Hooks | `useNegotiationStream.ts` + `useNegotiationApi.ts` | — | DONE |
| Frontend API Client | `website/lib/negotiation-api.ts` | — | DONE |
| Frontend Components | `website/components/negotiation/` (10 组件) | — | DONE |
| Frontend Pages | `/negotiate` + `/negotiation` 路由 | — | DONE |

### 关键决策记录

1. **Embedding 模型**: `paraphrase-multilingual-MiniLM-L12-v2` (384 dim, 多语言, 快速)
2. **状态机**: 8 个状态（CREATED → FORMULATING → FORMULATED → ENCODING → OFFERING → BARRIER_WAITING → SYNTHESIZING → COMPLETED）
3. **Center Tool-Use**: 5 个工具 schema 定义，Claude API function calling 格式
4. **Adapter 架构**: ClaudeAdapter (默认通道) + SecondMeAdapter (oauth2 封装)
5. **Event Pusher**: 基于现有 WebSocketManager，channel 命名 `negotiation:{id}`
6. **Config**: pydantic-settings, TOWOW_ 前缀环境变量
7. **API 端口**: V1 API 运行在 8081（独立于旧 app.py 的 8080）
8. **Python 兼容性**: 修复 asyncio.TaskGroup → asyncio.gather（兼容 3.9+，虽然 venv 是 3.12）
9. **前端路由**: 两个入口 `/negotiate`（旧版视图）和 `/negotiation`（新版完整 UI）

### Phase 2 修复记录

- **asyncio.TaskGroup 兼容性**: engine.py 使用了 Python 3.11+ 的 TaskGroup，系统 python3 是 3.9。改为 asyncio.gather 保持向后兼容。venv python3.12 可用但不应依赖。
- **TypeScript 类型错误**: FormulationConfirm.tsx 中 `formulation.enrichments.detected_skills` 类型为 unknown，React 不接受。改为 Array.isArray() 检查。
- **接口 index signature**: NegotiationEvent.data 是 Record<string, unknown>，但具体事件数据接口缺少 index signature。给所有 data 接口添加 `[key: string]: unknown`。

### 前端组件清单

| 组件 | 职责 |
|------|------|
| NegotiationPage | 主页面：需求输入 + 进度条 + 双栏布局 + 事件日志 |
| NegotiationView | 旧版编排视图 |
| DemandInput | 需求文本输入 + 提交 |
| FormulationConfirm | 展示 formulation 结果，支持编辑和确认 |
| ResonanceDisplay | 共振匹配结果展示（Agent 列表 + 分数条） |
| OfferCard | 单个 Agent Offer 卡片 |
| AgentPanel | Agent 面板：匹配 + Offer 状态 + 展开详情 |
| CenterActivity | Center 综合活动（简版） |
| CenterPanel | Center 面板：工具调用 + 方案输出 |
| EventTimeline | 事件时间线（7 种事件类型，彩色标记） |
| PlanResult | 最终方案展示 + 接受/拒绝 |

### E2E 测试覆盖

6 个端到端集成测试，验证完整协商闭环：
1. **Happy path** — 5 agents, 完整事件序列，方案输出
2. **Center multi-round** — ask_agent 工具调用 + output_plan
3. **No agents** — 空 agent 列表仍然完成协商
4. **Agent timeout** — 部分 agent 超时，优雅降级
5. **Trace chain** — 追溯链完整性和时间戳
6. **Trace multi-round** — 多轮追溯链条目

### Phase 3 进行中

#### 第一轮修复（routes.py）
1. **cancel 不取消后台任务**：已添加 `task.cancel()` 调用
2. **_run_negotiation 错误不保证终态**：已确保 except 块中 `session.state = COMPLETED`

#### 第二轮修复（跨模块 context 键名不匹配 — 关键）

背景代码审查发现 engine.py 传递给 Skill 的 context 字典键名与 Skill 实际期望的不一致。E2E 测试用 mock skill 不校验键名所以通过了，但真实 Skill 会立即失败。

3. **Formulation Skill context 不匹配**：engine 传 `{"demand": DemandSnapshot}` 但 skill 期望 `{"raw_intent": str, "agent_id": str}`。已修复 engine.py 传正确键。
4. **Offer Skill context 不匹配**：engine 传 `{"demand": DemandSnapshot}` 但 skill 期望 `{"demand_text": str, "profile_data": dict}`。已修复 engine.py + 添加 profile_data 获取。
5. **Center Skill 缺少 llm_client**：engine context 没传 `llm_client` 但 skill 要求必须有。已修复。
6. **Offer confidence 未传播**：skill 返回 confidence 但 engine 创建 Offer 时未设置。已修复。
7. **前端 SubmitDemandRequest 缺 user_id**：后端 schema 有 `user_id` 字段但前端类型定义没有。已修复类型 + API client + hook + 两个 page 组件。
8. **前端 confirmFormulation 字段名错误**：hook 发送 `formulated_text` 但后端期望 `confirmed_text`。已修复。

#### 文档更新
- `ENGINEERING_REFERENCE.md`：更新代码结构、asyncio.gather 决策、V1 实际实现决策表、测试覆盖统计
- `MEMORY.md`：更新为 V1 Phase 3 状态

#### 验证结果
- 172 后端测试通过
- `next build` 通过

#### 手动验收待做
- 启动后端 `uvicorn towow.api.app:app --port 8081` + 前端 `npm run dev`
- 配置 TOWOW_ANTHROPIC_API_KEY 环境变量
- 跑一次完整协商流程（需要 API key）
