# V1 开发日志

## 2026-02-09: Phase 3.7 — 真实 LLM 端到端联调通过

### 里程碑

V1 首次使用真实 Claude API 完成完整协商流程（非 Mock）。

### 端到端测试结果

- **State**: completed
- **Center rounds**: 2（第 1 轮调 ask_agent + start_discovery，第 2 轮 output_plan）
- **总耗时**: 134.4 秒（5 个 Agent 编码 + 1 次 Formulation + 3 次 Offer + 2 轮 Center）
- **参与者**: 3/5 Agent 通过共振选中（Eve 0.57, Alice 0.45, Bob 0.38）
- **事件**: 13 个事件全部推送（formulation.ready → resonance.activated → 3x offer.received → barrier.complete → 6x center.tool_call → plan.ready）
- **追溯链**: 10 个条目
- **10/10 验证检查全部通过**

### 联调发现的 Bug 和修复

**Bug: LLM 返回 JSON 被 markdown code fence 包裹**
- 现象：Claude 返回 `\`\`\`json {...} \`\`\`` 格式，`json.loads()` 失败，capabilities 和 confidence 丢失
- 根因：真实 LLM 行为与 Mock 不同——Mock 返回纯 JSON 字符串，真实 Claude 习惯用 markdown 包裹
- 修复：`BaseSkill._strip_code_fence()` 方法，用正则清洗 code fence（代码保障 > Prompt 保障）
- 影响文件：`skills/base.py`, `skills/formulation.py`, `skills/offer.py`
- 172 个 Mock 测试仍然全部通过

### 真实运行观察

1. **共振排序有效**：Eve（PM/startup）排第一（0.57），Alice（ML/healthcare）第二（0.45），Bob（前端）第三（0.38），Carol（blockchain）和 Dave（DevOps）未选中——语义匹配符合预期
2. **Offer 质量好**：Alice 高信心（0.85），Bob 诚实说不匹配（0.15），Eve 承认不是技术角色（0.30）——anti-fabrication 机制有效
3. **Center tool-use 正确**：第 1 轮调 ask_agent 追问 Alice 和 Eve，调 start_discovery 探索 Alice↔Bob 互补性；第 2 轮综合信息输出方案
4. **观察遮蔽生效**：第 2 轮 Center 看到的是 masked offers + 历史推理，不是原始 Offer

### 性能数据

- Embedding 编码（5 个 Agent）: ~3 秒（首次加载模型 ~10 秒）
- Formulation（1 次 Claude 调用）: ~5 秒
- Offer 生成（3 个并行 Claude 调用）: ~15 秒
- Center 第 1 轮（tool-use）: ~8 秒
- Center 第 2 轮（output_plan）: ~10 秒
- 总计: ~134 秒（含模型下载和初始化）

---

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

## 2026-02-09: Phase 3.6 — 架构审计与设计讨论

### 背景
Phase 3.5 真实联调修复了 7 个 bug，但发现了更深层的架构问题。用架构 Skill + 工程 Skill 做了系统性审查，与架构师讨论后达成以下共识。

### 讨论一：连通性需要被显式建立和验证

**起因**：Bug 9-10（profile 引用断链）的根因不只是 Python `or` 的陷阱，而是反映了一个更深层的问题。

**架构原则 Section 0.9 说**：完备性 = 与信息场保持连通（不是复制所有信息）。Profile Data 是"自"的数据影子，adapter 通过连通性访问它。

**问题**：当前架构说了"保持连通"，但没有说"怎么保证连通不会断"。V1 的连通性是隐式的内存引用共享——adapter 和 routes 指向同一个 dict 对象。这个引用没有任何代码层面的保障，如果有人重新赋值就会断链。

**达成共识**：

> **连通性是需要被显式建立和验证的，不能依赖隐式的运行时状态。**

这是对 Section 0.9 的补充——完备性不仅要求"与信息场保持连通"，还要求"连通性本身被保障"。

**V2 改进方向**：连通性在系统组装时显式声明，启动时可验证"所有连接是否通畅"。具体实现由 V2 工程决策。

### 讨论二：身份标识——协议层 vs 应用层

**起因**：Bug 11（display_name 显示 agent_id 而不是人类可读名称）。

**分析**：

| 层 | 标识 | 特征 | 未来演进 |
|----|------|------|---------|
| 协议层 | agent_id（唯一标识） | 不变、机器可读、全网唯一 | → WOWOK Personal 链上地址（~200 位） |
| 应用层 | display_name（呈现标识） | 可变、人类可读、可本地化 | 可因场景不同而不同（Section 0.10 一自多我） |

**达成共识**：
- agent_id 的本质是**协议层的身份锚点**，以后绑定链上地址后永不再改
- display_name 是**应用层的投影**——同一个身份在不同场景下可以有不同的呈现名
- V1 暂用简单字符串作为 agent_id，V2 接入 WOWOK 后迁移为链上地址
- 身份映射（ID → 呈现名）V2 应独立为模块，不是临时传参

### 讨论三：引擎的架构定位与兜底路径问题

**起因**：Bug 12-13（engine._call_center_llm() 既做编排又做内容，产生两条不一致的代码路径）。

**引擎在四层架构中的定位**：
- 引擎横跨**协议层**（状态机、状态转换规则）和**基础设施层**（调用 Skill、管理并发）
- 引擎是 Section 0.5"代码保障 > Prompt 保障"的执行者——用代码控制流程（状态机、等待屏障、轮次限制）
- 引擎**不是**能力层——它不应该写 prompt、定义 tool schema、构建 LLM 请求

**Bug 12-13 用架构语言说**：引擎（程序层）侵入了 Skill（能力层）的职责。它自己写了 prompt 和 tool schema，违反了 Section 0.2"本质与实现分离"——tool schema 是 Center Skill 的实现细节，引擎不该知道也不该复制。

**Phase 3.5 修复的不完整之处**：修复让主路径回归了 Skill，但保留了 `_call_center_llm()` 作为 `center_skill is None` 时的兜底。这违反了 Section 0.1"最小完整单元 ≠ MVP"——Center Skill 是协商单元的必要组件，没有 Center 就不是一个完整的协商。保留低质量兜底不是"最小完整"，是"砍掉最难的部分"。

**达成共识**：
- 删除 `engine._call_center_llm()` 兜底方法
- center_skill 从可选参数改为必须参数
- 没有 Center Skill 时直接报错（"大声失败"），不悄悄降级
- E2E 测试必须使用真实的 CenterCoordinatorSkill（配 mock LLM client），不绕过 Skill

### 讨论四：测试体系的架构级问题

**起因**：172 个测试全过，但真实联调发现 15 个 bug。

**问题诊断**（用架构原则语言）：

1. **违反 Section 0.1"最小完整单元"**：mock 组件不是"最小完整"的简化实现，而是"砍掉核心功能"的空壳。真实 Skill 会检查 context 键名、真实 LLM Client 会检查 tool schema 格式——mock 版本把这些全砍了。
2. **违反 Section 0.5"代码保障 > Prompt 保障"**：代码保障了流程（状态机、屏障），但没有保障数据传递的正确性。模块之间传递的数据格式/内容正确性也应该由代码保障。
3. **未覆盖架构核心机制**：反杜撰保障（Section 10.6）、观察遮蔽（Section 10.7）、共振匹配语义正确性（Section 6）在测试中完全缺失。

**达成共识**：
- 创建测试 Skill（`towow-eng-test/SKILL.md`）定义测试的本质原则
- 测试原则遵循"本质与实现分离"：定义原则和思维框架，不预设具体测什么
- 核心原则：契约测试（验证模块间数据约定）、mock 也是最小完整单元、从架构设计推导测试清单
- 信度（可重复性）和效度（测试通过真的意味着系统正确）是两个维度

### 执行计划

| 序号 | 事项 | 类型 |
|------|------|------|
| 1 | 删除 engine._call_center_llm()，center_skill 改为必须 | 代码修复 |
| 2 | 修 resonance_activated 事件中 display_name 残留 | 代码修复 |
| 3 | E2E 测试使用真实 CenterCoordinatorSkill | 测试改进 |
| 4 | 创建测试 Skill 定义 | 新 Skill |
| 5 | 更新 ENGINEERING_REFERENCE.md V2 改进点 | 文档 |

### 执行结果（Phase 3.6 完成）

全部 5 项执行完成，172 测试全过。

**1. engine._call_center_llm() 已删除**
- `center_skill` 从 `Optional[Skill] = None` 改为 `Skill`（必须参数）
- 删除 `_call_center_llm()` 方法（约 30 行）
- 删除所有 `if center_skill: ... else: _call_center_llm()` 分支
- `routes.py` 增加启动时校验：无 center_skill 则 RuntimeError

**2. resonance_activated display_name 残留已修**
- 事件中 display_name 现在使用 `self._agent_display_names.get(aid, aid)`

**3. E2E 测试使用真实 CenterCoordinatorSkill**
- `conftest.py` 新增 `center_skill` fixture（`CenterCoordinatorSkill()`）
- `test_engine.py`：全部 29 个测试更新，传入 `center_skill=center_skill`
- `test_e2e.py`：全部 6 个测试更新，内联创建 `CenterCoordinatorSkill()`
- 测试路径完整：Engine → CenterSkill → MockLLMClient → Engine 解析结果
- 172 测试全过（`pytest tests/towow/ -v` 16.44s）

**4. 测试 Skill 已创建**
- `.claude/skills/towow-eng-test/SKILL.md`
- 5 条核心原则：从架构推导测试清单、契约测试 > 行为测试、Mock 是简化的真实、测试应能发现真实 bug、代码保障的测试层面体现
- 测试分层：单元 → 契约 → 集成 → 架构验证
- 知识导航：一手来源（架构文档）、二手来源（pytest/Fowler）、三手来源（通用文章需批判审视）

**5. 文档已更新**
- DEV_LOG_V1.md 记录完整讨论和执行结果
- MEMORY.md 更新当前状态
