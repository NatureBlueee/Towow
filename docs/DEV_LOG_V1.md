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

## 2026-02-09: Phase 3.5 — 真实 LLM 联调修复

### 背景
Phase 3 的自动化测试全部通过（172），但启动真实后端 + Claude API 调用后发现多个问题。
这些问题的共性：**单元测试 mock 太宽松，不验证真实运行环境中的数据流**。

### 第三轮修复（真实 LLM 联调发现）

#### Bug 9: ClaudeAdapter profiles 引用断链
- **现象**：所有 agent 的 offer 都说 "I can't help, my profile doesn't have information"
- **根因**：`claude_adapter.py:42` 使用 `self._profiles = profiles or {}`，空 dict 是 falsy，`{} or {}` 创建新 dict，切断了 `app.state.profiles` 的引用
- **修复**：改为 `self._profiles = profiles if profiles is not None else {}`
- **架构合规**：✅ 不违反架构。Adapter 的 `get_profile()` 是 Protocol 约定的接口，内部引用共享是实现细节。
- **教训**：Python `or` 对空容器的 falsy 行为是常见陷阱。对引用语义的参数，必须用 `is not None` 判断。

#### Bug 10: app.py 创建 Adapter 时未传 profiles
- **现象**：同 Bug 9 的表面现象
- **根因**：`app.py:89-92` 创建 ClaudeAdapter 时没有传入 `profiles=app.state.profiles`
- **修复**：传入 `profiles=app.state.profiles`（引用同一个 dict）
- **架构合规**：✅ 符合设计——注册 agent 后，adapter 通过共享引用自然获取 profile 数据，无需额外同步。

#### Bug 11: display_name 未传播
- **现象**：participant 显示 "agent_carol" 而不是 "Carol"
- **根因**：`engine.py` 创建 `AgentParticipant` 时硬编码 `display_name=agent_id`
- **修复**：engine.start_negotiation 新增 `agent_display_names` 参数，routes 从 `state.agents` 提取 display_name 映射
- **架构合规**：✅ engine 不直接依赖 state.agents，通过参数注入，保持 Protocol 层干净。

#### Bug 12: engine._call_center_llm 的 tool schema 格式错误
- **现象**：Center 第二轮调用报 `tools.0.custom.input_schema: Field required`
- **根因**：`engine.py:_call_center_llm()` 自己硬编码了 tool 定义，用 `parameters` 而不是正确的 `input_schema` 格式。这与 `center.py` 里正确的 `ALL_TOOLS` 是两套重复定义。
- **修复**：删除硬编码，直接 `from towow.skills.center import ALL_TOOLS, RESTRICTED_TOOLS`
- **架构合规**：⚠️ **这是一个架构违反的修复**。engine 之前违反了"本质和实现分离"原则——engine 管编排，skill 管 prompt 和 tool 定义。engine 不应该有自己的 tool schema 副本。修复后恢复了正确的职责分离。
- **教训**：当 engine 里出现 prompt 文本或 tool schema 定义时，就说明可能在越界。

#### Bug 13: engine 两条 Center 调用路径导致 prompt 质量断层
- **现象**：Center Round 2（tools_restricted=True）输出 "I can't see the offers, they're masked"
- **根因**：`engine._run_synthesis` 在 `tools_restricted=True` 时走 `_call_center_llm()` 而不是 `center_skill.execute()`，前者只有极简 system prompt，没有 observation masking 逻辑
- **修复**：tools_restricted 时也优先走 center_skill.execute()，保持一致的 prompt 质量
- **架构合规**：⚠️ **同 Bug 12，也是职责越界的后果**。engine 不该有自己的 Center prompt 生成逻辑。修复后 engine 只管调 center_skill，不管 prompt 内容。

#### Bug 14: ask_agent 发空消息
- **现象**：Claude API 报 `all messages must have non-empty content`
- **根因**：`_handle_ask_agent` 在 `question` 为空字符串时仍然调 adapter.chat
- **修复**：添加 `if not question.strip():` 早返回
- **架构合规**：✅ 边界校验，合理

#### Bug 15: Center reasoning 未存入 history
- **现象**：Round 2 的 Center 看不到 Round 1 的推理过程，只能看到 tool calls
- **根因**：engine 处理 tool_calls 前没有把 `result.get("content")` 存入 history
- **修复**：在处理 tool_calls 前，将 Center 的 reasoning text 以 `{"type": "center_reasoning", "round": N, "content": ...}` 存入 history
- **架构合规**：✅ 这是 engine 的编排职责——确保 history 完整，供 skill 下一轮使用。与 center_skill 测试中的 `test_round_2_masks_offers` 设计一致。

### 架构合规性审计

| Bug | 修复是否违反架构 | 说明 |
|-----|-----------------|------|
| 9 | ✅ 合规 | 实现细节修复，Protocol 接口不变 |
| 10 | ✅ 合规 | 正确传参 |
| 11 | ✅ 合规 | 参数注入，不增加耦合 |
| 12 | ⚠️ 修复了已有违反 | engine 不应定义 tool schema，回归正确职责 |
| 13 | ⚠️ 修复了已有违反 | engine 不应有 Center prompt 逻辑，回归 skill 负责 |
| 14 | ✅ 合规 | 边界校验 |
| 15 | ✅ 合规 | engine 编排职责内的 history 管理 |

### 关键教训

1. **`or` vs `is not None`**：对引用语义的参数，永远用 `is not None`，不用 `or`
2. **职责越界是渐进的**：Bug 12 和 13 都是因为 engine 里"顺手"写了点 prompt/tool 逻辑，看起来很小，但真实调用时就会产生两套不一致的代码路径
3. **Mock 太宽松 = 延迟发现 bug**：Phase 3 自动化审查发现了 context 键名问题，但 tool schema 格式问题只有真实 API 调用才暴露
4. **本质和实现分离要贯穿到 bug 修复**：修 bug 时容易为了"跑通"而加 hack，这会引入新的架构违反

### 真实 LLM 联调结果

| 阶段 | 结果 |
|------|------|
| Formulation | ✅ 需求结构化成功，提取约束/偏好/上下文 |
| 共振匹配 | ✅ Carol(0.61) > Alice(0.58) > Dave(0.41) > Eve(0.39) > Bob(0.15) |
| Offer 生成 | ✅ 5 个 agent 基于真实 profile 回复，质量差异明显 |
| Center 综合 | ✅ 2 轮，输出结构化方案 |
| Plan 输出 | ✅ 包含匹配分析 + 信息缺口识别 + 4 种合作场景 + 评估框架 |

### 新增文件
- `backend/scripts/seed_demo.py` — 手动测试用的 seed 脚本（创建 scene + 5 agent with profiles）
