# TASK-EXP-001: 页面路由与布局

## 文档元信息

| 字段 | 值 |
|------|-----|
| TASK_ID | TASK-EXP-001 |
| 状态 | TODO |
| 优先级 | P0 |
| 预估工时 | 2h |
| Beads ID | `towow-sv4` |
| 关联文档 | TECH-PRODUCT-PAGE-v5.md |

---

## 1. 任务目标

创建产品体验页的路由结构和基础布局，为后续组件开发提供页面框架。

## 2. 输入

- TECH-PRODUCT-PAGE-v5.md 第 3 节页面设计
- 现有 towow-website 项目结构
- 现有布局组件（NoiseTexture, GridLines）

## 3. 输出

- `/app/experience/page.tsx` - 体验页主页面
- `/app/experience/layout.tsx` - 体验页布局
- 基础页面结构（Header 占位、主内容区、Footer 占位）

## 4. 验收标准

- [ ] 访问 `/experience` 路由正常显示页面
- [ ] 布局包含 NoiseTexture 和 GridLines 背景
- [ ] 页面结构符合设计（Header + Main + Footer）
- [ ] 响应式布局基础支持（桌面端优先）
- [ ] 无 TypeScript 编译错误

## 5. 依赖关系

**硬依赖**：无

**接口依赖**：无

## 6. 实现要点

```typescript
// app/experience/layout.tsx
export default function ExperienceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className={styles.experienceLayout}>
      <NoiseTexture />
      <GridLines />
      <main className={styles.main}>{children}</main>
    </div>
  );
}
```

## 7. 测试要点

- 路由访问测试
- 布局渲染测试
- 背景组件加载测试

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
