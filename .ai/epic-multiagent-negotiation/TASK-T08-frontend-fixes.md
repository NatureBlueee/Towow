# T08: 前端修复（SSE 事件适配）

> **任务 ID**: T08
> **所属 Story**: STORY-07
> **优先级**: P1
> **预估工时**: 4h
> **依赖**: 接口依赖 T01, T05（契约先行，可并行开发）
> **Beads ID**: `towow-ibw`
> **状态**: DOING (等待 Review)

---

## 1. 任务目标

适配 v4 版本新增的 SSE 事件类型，确保前端能够正确展示：
1. 多轮协商进度（5轮）
2. 强制终结状态
3. 反馈评估结果
4. 状态恢复提示

---

## 2. 实现内容

### 2.1 新增 SSE 事件处理

```typescript
// v4 新增事件类型
type V4EventType =
  | "towow.feedback.evaluated"        // 反馈评估结果
  | "towow.negotiation.force_finalized"  // 强制终结
  | "towow.negotiation.round_started";   // 新一轮开始

// eventStore.ts 新增处理
case "towow.feedback.evaluated":
  // 展示反馈评估：Agent X 的反馈被评估为 accept/negotiate
  break;

case "towow.negotiation.force_finalized":
  // 展示强制终结：协商已达最大轮次，自动生成妥协方案
  break;

case "towow.negotiation.round_started":
  // 展示轮次进度：第 N/5 轮协商开始
  break;
```

### 2.2 UI 组件更新

1. **协商进度条**
   - 显示当前轮次：`第 N / 5 轮`
   - 第 5 轮特殊标记："最终轮"

2. **状态卡片**
   - `FORCE_FINALIZED` 状态：显示橙色警告
   - 妥协方案标注："部分 Agent 未完全接受"

3. **反馈评估展示**
   - 实时显示每个 Agent 的反馈结果
   - 区分 `offer` 和 `negotiate` 响应

### 2.3 错误处理增强

```typescript
// 状态恢复提示
case "towow.state.recovered":
  showNotification({
    type: "info",
    message: "检测到连接中断，已自动恢复协商状态"
  });
  break;
```

---

## 3. 验收标准

| 标准 | 验证方法 | 状态 |
|------|----------|------|
| 5 轮协商进度正确展示 | 手动触发 5 轮协商，观察进度条 | [ ] 待验证 |
| 强制终结状态显示正确 | 模拟 5 轮后自动终结 | [ ] 待验证 |
| 反馈评估实时更新 | 观察 Agent 反馈展示 | [ ] 待验证 |
| SSE 断线重连正常 | 模拟网络中断后恢复 | [ ] 待验证 |

---

## 4. 接口契约（来自 T01, T05）

### SSE 事件格式

```typescript
interface SSEEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, any>;
}
```

### 关键 Payload 结构

```typescript
// towow.negotiation.round_started
interface RoundStartedPayload {
  round: number;
  max_rounds: number;  // 固定为 5
  participants: string[];
}

// towow.negotiation.force_finalized
interface ForceFinalizedPayload {
  accepted_agents: string[];
  pending_agents: string[];
  compromise_proposal: ProposalContent;
}

// towow.feedback.evaluated
interface FeedbackEvaluatedPayload {
  agent_id: string;
  response_type: "offer" | "negotiate";
  evaluation: "accept" | "reject" | "conditional";
}
```

---

## 5. 关联文档

| 文档 | 路径 |
|------|------|
| 技术方案 v4 | `.ai/epic-multiagent-negotiation/TECH-multiagent-negotiation-v4.md` |
| 前端代码 | `towow-frontend/src/stores/eventStore.ts` |
| SSE 页面 | `towow-frontend/src/pages/Negotiation.tsx` |

---

## 6. 实现记录

### 6.1 修改的文件

| 文件 | 修改说明 |
|------|----------|
| `towow-frontend/src/types/index.ts` | 新增 v4 类型定义：`FeedbackResult`、`ForceFinalizationInfo`、`ForceFinalizationPayload`、`FeedbackEvaluatedPayload`、`RoundStartedPayload`；扩展 `NegotiationState` 增加 `maxRounds`、`isForceFinalized`、`forceFinalizationInfo`、`feedbackResults` 字段 |
| `towow-frontend/src/stores/eventStore.ts` | 新增 v4 事件处理：`towow.negotiation.force_finalized`、增强 `towow.feedback.evaluated`（支持单个 Agent 反馈）、增强 `towow.negotiation.round_started`（更新 maxRounds）；新增 setter：`setMaxRounds`、`setForceFinalized`、`addFeedbackResult` |
| `towow-frontend/src/pages/Negotiation.tsx` | 新增 UI 组件：`NegotiationProgressBar`（协商进度条）、`ForceFinalizationCard`（强制终结警告卡片）、`FeedbackResultsCard`（反馈评估展示）；更新主组件以展示新状态 |

### 6.2 关键实现说明

#### 协商进度条 (`NegotiationProgressBar`)
- 显示当前轮次和最大轮次
- 使用进度条和轮次标记可视化进度
- 最终轮（第 5 轮）使用橙色样式并显示"最终轮"标签
- 进度条颜色：普通轮次为紫色渐变，最终轮为橙红色渐变

#### 强制终结卡片 (`ForceFinalizationCard`)
- 显示橙色警告边框
- 展示接受/未完全接受的 Agent 数量
- 列出未完全接受的 Agent ID

#### 反馈评估展示 (`FeedbackResultsCard`)
- 列表展示每个 Agent 的反馈结果
- 区分 offer 和 negotiate 响应类型
- 底部显示统计摘要（接受/有条件/拒绝数量）

#### 事件处理增强
- `towow.feedback.evaluated` 支持两种格式：
  - 单个 Agent 反馈（包含 `agent_id`）
  - 批量评估结果（包含 `accepts`/`rejects`/`negotiates`）
- `towow.negotiation.round_started` 自动更新 `maxRounds`
- `towow.negotiation.force_finalized` 设置强制终结状态并记录相关信息

### 6.3 构建验证

```bash
# TypeScript 检查通过
npx tsc --noEmit  # 无错误

# Vite 构建成功
npx vite build
# dist/index.html                   0.46 kB
# dist/assets/index-DdqnsIL3.css   62.01 kB
# dist/assets/index-CCP3DYgP.js   924.09 kB

# ESLint 检查（修改的文件无错误）
npx eslint src/stores/eventStore.ts src/pages/Negotiation.tsx src/types/index.ts  # 无错误
```

### 6.4 待办事项

- [ ] 等待 Tech Review
- [ ] 手动测试 5 轮协商流程
- [ ] 测试强制终结场景
- [ ] 测试 SSE 断线重连
