# Issue 005: 静默失败模式 (Silent Failure Patterns)

**日期**: 2026-02-12
**状态**: 已修复
**共同模式**: 未被强制的契约假设

---

## Bug 1: 场景页按钮消失

### 现象

`/store/[scene]` 页面的"通向惊喜"和"让分身润色"按钮不显示。

### 根因

`DemandInput` 新增了 `isAuthenticated` prop 控制按钮可见性，但只更新了主页消费方（`/store/page.tsx`），遗漏了场景页（`/store/[scene]/page.tsx`）。

### 为什么没发现

`isAuthenticated?: boolean` — 可选 prop，TypeScript 不报错。`undefined` 被 `{isAuthenticated && ...}` 当 `false` 处理，按钮静默消失。没有编译错误、没有运行时异常、没有控制台警告，纯粹的静默降级。

### 修复

补传 auth props 给场景页的 `DemandInput`。

---

## Bug 2: SSE 换行符丢失

### 现象

流式输出中所有 `\n` 字符被静默丢弃，段落和列表变成一坨文字。

### 根因

```python
yield f"data: {chunk}\n\n"
```

`chunk` 内的 `\n` 被 SSE 协议当作帧分隔符，截断了 `data` 行。SSE 规范要求每个 `data:` 行不能包含换行符，换行符会被解释为消息边界。

### 为什么没发现

之前测试用短文本无换行。V4 prompt 引入结构化输出（段落、列表）后才触发。

### 修复

```python
yield f"data: {json.dumps(chunk)}\n\n"
```

`json.dumps()` 将 `\n` 编码为 `\\n`，避免被 SSE 协议误解析。

---

## 共同模式：未被强制的契约假设

两个 bug 的本质相同：**存在一个隐含假设，但没有代码强制执行它**。

| | Bug 1 | Bug 2 |
|---|---|---|
| 隐含假设 | 所有消费方都会传 `isAuthenticated` | chunk 内容不含 `\n` |
| 违反方式 | 新消费方漏传 | prompt 改版引入结构化输出 |
| 失败模式 | 按钮消失，无报错 | 文本断裂，无报错 |
| 检测难度 | 高 — TypeScript 不报错 | 高 — 短文本测试不触发 |

**对应架构原则 0.5**：代码保障 > Prompt 保障。假设没有被代码强制 = 迟早会被违反。

---

## 教训

### 教训 1: Optional prop 不等于无关紧要

控制核心功能可见性的 prop 如果是 `Optional`，任何新消费方漏传就是静默降级。**改共享组件接口时必须搜索所有消费方**。

防御措施：
- 控制核心功能的 prop 应该是 required，或者有安全的默认值
- 改组件接口后，用 `grep` 搜索所有 `<ComponentName` 确认每个消费方

### 教训 2: 协议帧字符 = 保留字符

任何用特定字符做分隔的协议（SSE 的 `\n`、CSV 的 `,`、URL 的 `&`），内容中出现该字符就会破坏帧。**必须有编码/转义层**。

防御措施：
- SSE: `json.dumps()` 编码 data 内容
- CSV: 引号包裹 + 引号转义
- URL: `encodeURIComponent()`
- 通用原则：协议层和内容层之间必须有编码边界
