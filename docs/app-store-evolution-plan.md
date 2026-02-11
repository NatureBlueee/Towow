# App Store 产品进化方案 — 工程规划（定稿）

> 2026-02-11 基于 Arch + Eng 双线分析，经决策确认后的工程规划。
> 源报告：`docs/arch-report.md` + `docs/eng-report.md`

---

## 零、决策记录

| # | 决策点 | 选择 | 理由 |
|---|--------|------|------|
| 1 | P1-P4 执行方式 | **全做，三轨并行** | 前端/后端/算法互相独立 |
| 2 | 4 场景深度 | **黑客松深做，其他 3 个浅做** | 标杆场景做到位再复制 |
| 3 | App Store 技术栈 | **迁移到 Next.js** | 路由、组件复用、SSR 长期更优 |
| 4 | /store/ 首页形态 | **全网模式**（需求输入 + 所有 Agent + 场景切换入口） | 进来就能用 |
| 5 | Schema 命名 | **task-centric（plan_json）** | 一 task 一 assignee 更自然 |
| 6 | 拓扑布局 | **层级/Sugiyama（左→右 DAG）** | 流程图心智模型 |
| 7 | Store i18n 路由 | **不走 locale 路由** | 产品页非内容页，用 useTranslations 做翻译 |

---

## 一、核心契约变更（唯一的跨系统变更）

### Vercel rewrite 规则

```
# Before (全量转发)
/store/:path*  →  Railway

# After (仅 API + WebSocket 转发)
/store/api/:path*  →  Railway
/store/ws/:path*   →  Railway
# /store/ 和 /store/[scene] 由 Next.js 服务
```

**涉及文件**：
- `website/next.config.ts` — 拆分 rewrite 规则
- `backend/server.py` — 删除 `mount_store_static()`（停止服务 HTML/CSS/JS）

**验证**：改完后确认 `/store/api/info` 可达、`/store/` 返回 Next.js 页面。

### 后端 API 路由

**零改动**。`/store/api/*` 全部保持原样。

---

## 二、三轨并行工作计划

```
Track A (前端迁移+场景)     Track B (后端结构化)      Track C (拓扑算法)
─────────────────────     ──────────────────────    ─────────────────
A1. 契约变更               B1. P2 Center context     C1. topo sort +
    next.config.ts              center.py                 层级布局
    server.py                   _build_prompt             (纯函数)
         │                       │
A2. 组件骨架               B2. P3 plan_json          C2. mock 数据
    layout + page               7 文件 ~80 行             验证算法
    hooks 基础                   │
         │                       │
A3. 功能迁移               B3. 跑真实协商            C3. React 组件
    39 函数 → React             验证 JSON 质量            TopologyView
    DemandInput                  │                         │
    AgentScroll                  │                         │
    Progress/Plan                │                         │
    Developer Panel              │                         │
         │                       │                         │
A4. 黑客松深做                   └──────────┬──────────────┘
    主题/叙事/卡片                          │
    方案展示模板                   集成：真实 plan_json
         │                      + 拓扑渲染 + 回退测试
         │                              │
A5. 其他 3 场景浅做           端到端验证
    主题色 + Hero 文案        (全链路走通)
```

### 依赖关系

- **A1 → A2 → A3 → A4 → A5**（串行，前端基础设施逐步搭建）
- **B1 → B2 → B3**（串行，后端 P2 先于 P3）
- **C1 → C2**（算法验证后才进入 React）
- **C3 依赖 A3**（需要组件骨架）
- **集成 依赖 A3 + B2 + C2**（三轨汇合）
- **A4/A5 与集成可并行**（场景差异化和拓扑是独立的产品维度）

---

## 三、Track A — Next.js 迁移 + 场景

### A1. 契约变更

| 文件 | 改动 |
|------|------|
| `website/next.config.ts` | `/store/:path*` 拆为 `/store/api/:path*` + `/store/ws/:path*` |
| `backend/server.py` | 删除 `mount_store_static(application, prefix="/store")` |

### A2. 组件骨架

```
website/app/store/
├── layout.tsx                  # Store 共享布局（不走 i18n 路由）
├── page.tsx                    # /store/ 全网模式首页
└── [scene]/
    └── page.tsx                # /store/hackathon 等场景页

website/components/store/
├── StoreHeader.tsx             # 标题 + 登录/用户信息
├── DemandInput.tsx             # 需求输入（textarea + chips + scope + submit）
├── AgentScroll.tsx             # 横向 Agent 列表
├── SceneTabs.tsx               # 场景切换标签栏
├── NegotiationProgress.tsx     # 进度（timeline + graph 切换）
├── PlanOutput.tsx              # 方案展示（文本 or 拓扑）
├── TopologyView.tsx            # SVG DAG 拓扑图（Track C）
├── DeveloperPanel.tsx          # 开发者模式
├── StateMachineView.tsx        # 状态机可视化
├── ApiPlayground.tsx           # API 测试区
└── EventLog.tsx                # 事件流监视器

website/hooks/
├── useStoreNegotiation.ts      # 协商状态（submit, poll, events → reducer）
├── useStoreWebSocket.ts        # WebSocket 连接 + 断线重连
└── useStoreAuth.ts             # 登录状态（cookie session）

website/lib/
├── store-api.ts                # /store/api/* fetch 封装
├── store-scenes.ts             # 场景配置（主题色、叙事、卡片模板）
└── topology-layout.ts          # 拓扑排序 + 层级布局（Track C 产物）
```

### A3. 功能迁移（app.js 39 函数 → React）

原 `app.js` 函数按组件归属拆分：

| 原函数 | 归属组件/Hook |
|--------|-------------|
| `switchMode`, `switchScope` | `StoreHeader` / `SceneTabs` |
| `fillDemand`, `submitDemand` | `DemandInput` |
| `renderAgents`, `getInitial`, `getAvatarColor` | `AgentScroll` |
| `pollStatus`, `handleEvent` | `useStoreNegotiation` |
| `connectWebSocket` | `useStoreWebSocket` |
| `showPlan`, `renderGraphView` | `PlanOutput` / `NegotiationProgress` |
| `updateStateMachine` | `StateMachineView` |
| `addEventLog` | `EventLog` |
| `submitCreateScene`, `submitListScenes`, `submitListAgents` | `ApiPlayground` |
| `switchProgressView` | `NegotiationProgress` |
| `loginWithSecondMe`, `checkAuth` | `useStoreAuth` |
| `renderScenes`, `fillSceneTemplate`, `togglePlayground` | 各自组件 |
| `escapeHtml`, `getSceneConfig` | `lib/` 工具函数 |

### A4. 黑客松场景深做

5 个维度全部独立设计：

| 维度 | 实现方式 |
|------|---------|
| **主题** | CSS 变量 `--scene-primary: #F9A87C` 等，`[scene]/page.tsx` 设置 |
| **Hero 叙事** | "48小时，你需要什么队友？" + 场景描述段 |
| **Agent 卡片** | `AgentScroll` 接受 `cardTemplate` prop，黑客松版强调技术栈/经历 |
| **需求输入** | `DemandInput` 的 placeholder 和 chips 按场景切换 |
| **方案展示** | `PlanOutput` 接受 `planTemplate` prop，黑客松版渲染团队阵容 |

### A5. 其他 3 场景浅做

仅 CSS 主题色 + Hero 文案 + placeholder。卡片和方案展示用通用模板。

```typescript
// lib/store-scenes.ts
export const SCENES = {
  hackathon: {
    id: 'hackathon',
    name: '黑客松组队',
    primary: '#F9A87C',
    bg: '#FFF8F0',
    hero: '48小时，你需要什么队友？',
    placeholder: '例如：需要一个擅长 React Native 的移动端开发...',
    chips: ['前端开发', '后端工程师', 'UI设计师', '产品经理'],
    centerContext: '技术互补性优先',
    cardTemplate: 'hackathon',  // 深做
    planTemplate: 'team',       // 深做
  },
  'skill-exchange': {
    id: 'skill-exchange',
    name: '技能交换',
    primary: '#FFE4B5',
    bg: '#FFFDF5',
    hero: '你能教什么？想学什么？',
    placeholder: '例如：我会弹吉他，想学摄影...',
    chips: ['编程', '设计', '音乐', '语言'],
    centerContext: '双向匹配度优先',
    cardTemplate: 'default',    // 浅做
    planTemplate: 'default',    // 浅做
  },
  recruit: {
    id: 'recruit',
    name: '智能招聘',
    primary: '#8FD5A3',
    bg: '#F0FFF4',
    hero: '你在找什么样的人？',
    placeholder: '例如：需要 3 年以上经验的全栈工程师...',
    chips: ['工程师', '设计师', '产品经理', '运营'],
    centerContext: '经验与岗位匹配优先',
    cardTemplate: 'default',
    planTemplate: 'default',
  },
  matchmaking: {
    id: 'matchmaking',
    name: 'AI 相亲',
    primary: '#D4B8D9',
    bg: '#FDF5FF',
    hero: '描述你理想中的...',
    placeholder: '例如：希望找到一个喜欢户外运动、热爱阅读的人...',
    chips: ['运动', '艺术', '旅行', '美食'],
    centerContext: '价值观契合度优先',
    cardTemplate: 'default',
    planTemplate: 'default',
  },
} as const;
```

---

## 四、Track B — 后端结构化输出

### B1. Center 场景上下文注入（P2）

**1 文件改动**：`backend/towow/skills/center.py`

`_build_prompt()` 增加 `scene_context: dict | None` 参数：
```python
def _build_prompt(self, ..., scene_context: dict | None = None) -> str:
    prompt = SYSTEM_PROMPT_ZH  # or EN
    if scene_context:
        prompt += f"\n\n## 场景上下文\n优先策略：{scene_context['priority_strategy']}\n领域：{scene_context.get('domain_context', '通用')}"
    return prompt
```

App Store 后端在调用 engine 时从 `SAMPLE_APPS` 取出 `scene_context` 传入。

### B2. plan_json 双轨输出（P3）

**7 文件，~80 行，全 additive**（详见 `docs/eng-report.md` Section A）：

| # | 文件 | 改动 |
|---|------|------|
| 1 | `skills/center.py` L34-47 | `TOOL_OUTPUT_PLAN` 增加 `plan_json` object schema |
| 2 | `skills/center.py` L132-187 | System prompt 增加结构化输出指导段 |
| 3 | `core/events.py` L142-156 | `plan_ready()` 增加 `plan_json: dict | None = None` |
| 4 | `core/engine.py` L905-937 | `_finish_with_plan()` 接收传递 `plan_json` |
| 5 | `core/engine.py` L614-617 | output_plan 分支提取 `plan_json` |
| 6 | `api/schemas.py` L78-83 | `PlanResponse` 增加 `plan_json: Optional[dict] = None` |
| 7 | `core/models.py` L161 | `NegotiationSession` 增加 `plan_json: Optional[dict] = None` |

### B3. 验证

跑 2-3 次真实协商，检查 Claude 输出的 `plan_json` 结构质量。如不稳定，在 `center.py` 加校验逻辑。

---

## 五、Track C — 拓扑可视化

### C1. 算法（纯函数，无 React 依赖）

`website/lib/topology-layout.ts`：

```typescript
interface TaskNode {
  id: string;
  title: string;
  assigneeId: string;
  prerequisites: string[];
}

interface LayoutNode extends TaskNode {
  layer: number;
  x: number;
  y: number;
}

interface LayoutEdge {
  from: string;
  to: string;
}

interface TopologyLayout {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  width: number;
  height: number;
}

export function computeTopologyLayout(
  tasks: TaskNode[],
  layerWidth = 200,
  nodeHeight = 100
): TopologyLayout { ... }
```

算法：Kahn 拓扑排序 → 层内按 assignee 分组 → 坐标计算。~50 行。含环路检测（发现环 → 返回 null → 触发回退）。

### C2. Mock 数据验证

写 3-5 个不同拓扑结构的 mock plan_json（线性、扇出、钻石依赖），验证布局算法正确性。

### C3. React 组件

`website/components/store/TopologyView.tsx`：
- 消费 `computeTopologyLayout()` 输出
- SVG `<path>` 贝塞尔曲线连线
- DOM 节点（头像 + task title + assignee name）
- 点击交互：高亮节点和相关边，显示 task 详情面板
- ~100 行 TSX

`PlanOutput.tsx` 整合：
```typescript
if (planJson?.tasks?.length > 0) {
  return <TopologyView planJson={planJson} participants={participants} />;
}
return <PlanText text={planText} />;
```

---

## 六、Machine JSON Schema（定稿）

```json
{
  "summary": "一句话总结协商结果",
  "participants": [
    {
      "agent_id": "agent_abc123",
      "display_name": "Alice",
      "role_in_plan": "前端开发 - 负责 React Native 移动端实现"
    }
  ],
  "tasks": [
    {
      "id": "task_1",
      "title": "搭建移动端框架",
      "description": "使用 React Native 搭建 App 基本框架",
      "assignee_id": "agent_abc123",
      "prerequisites": [],
      "status": "pending"
    }
  ],
  "topology": {
    "edges": [
      { "from": "task_1", "to": "task_3" }
    ]
  }
}
```

- `plan_text` required + `plan_json` optional
- `participants` 去重声明
- `tasks.prerequisites[]` → DAG
- `topology.edges` → DAG 冗余展平
- `status` 枚举 `pending | in_progress | done`

---

## 七、风险矩阵

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Vercel rewrite 变更导致 API 断裂 | 中 | 高 | 改后先验证 `/store/api/info` |
| 迁移过程中 Store 不可用 | 中 | 中 | 保留旧 static mount 作 fallback，新路由就绪后再删 |
| LLM plan_json 不符合 schema | 中 | 低 | tool-use schema + 前端回退 |
| WebSocket 在 Next.js 集成 | 中 | 中 | Client Component + useEffect，已有参考 |
| 39 函数迁移遗漏 | 低 | 中 | 逐函数对照清单迁移 |
| 破坏 190 个测试 | 极低 | 高 | 全 additive，默认 None |

---

## 八、不做的事（V1）

- 不改协议层（状态机、事件语义、Center 工具集）
- 不做 WOWOK 集成（V2+）
- 不做场景即 Agent / HDC 空间投影（V2+）
- 不做 Store i18n 路由（用 useTranslations 翻译文案即可）
- 不引入第三方图库（纯 SVG + DOM）
