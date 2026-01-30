# TASK-EXP-003: LoginPanel 组件

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-003 |
| 状态 | TODO |
| 优先级 | P0 |
| 预估工时 | 3h |
| Beads ID | `towow-qzu` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

实现登录面板组件，展示 SecondMe 登录入口和登录说明。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 5.1.1 节 LoginPanel 设计
- 现有 Button 组件
- 现有 ContentCard 组件

## 3. 输出

- `/components/experience/LoginPanel.tsx` - 登录面板组件
- `/components/experience/LoginPanel.module.css` - 样式文件

## 4. 验收标准

- [ ] 显示 SecondMe 登录按钮
- [ ] 显示登录说明文案
- [ ] 支持 loading 状态（按钮禁用 + 加载动画）
- [ ] 点击按钮触发 onLoginClick 回调
- [ ] 样式符合设计规范（使用 CSS Variables）
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：
- TASK-EXP-002（认证 Context 与 Hooks）- 需要 useAuth Hook

**接口依赖**：无

## 6. 实现要点

```typescript
// components/experience/LoginPanel.tsx
interface LoginPanelProps {
  onLoginClick: () => void;
  isLoading?: boolean;
}

export function LoginPanel({ onLoginClick, isLoading }: LoginPanelProps) {
  return (
    <ContentCard className={styles.loginPanel}>
      <h2>体验 ToWow Agent 协作</h2>
      <p>通过 SecondMe 登录，提交您的协作需求</p>
      <Button
        variant="primary"
        onClick={onLoginClick}
        isLoading={isLoading}
        disabled={isLoading}
      >
        使用 SecondMe 登录
      </Button>
    </ContentCard>
  );
}
```

## 7. 测试要点

- 默认状态渲染测试
- loading 状态渲染测试
- 点击事件触发测试
- 样式一致性测试

---

## 实现记录

> 开发完成后填写

### 实现说明

（待填写）

### 测试结果

（待填写）

### 变更记录

| 时间 | 变更内容 | 变更人 |
|------|----------|--------|
| 2026-01-29 | 创建任务 | proj |
