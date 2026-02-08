# PROJ-NEXTJS-MIGRATION-v5: ToWow 静态页面 Next.js 迁移项目计划

## 文档元信息

- **文档类型**: 项目计划 (PROJ)
- **版本**: v5
- **状态**: ACTIVE
- **创建日期**: 2026-01-29 19:01 CST
- **关联 TECH**: `.ai/TECH-NEXTJS-MIGRATION-v5.md`
- **关联 TASK**: `.ai/TASK-NEXTJS-001.md` 至 `.ai/TASK-NEXTJS-011.md`

---

## 1. 项目概述

### 1.1 项目目标

将 ToWow 现有的静态 HTML 页面迁移到 Next.js 项目，实现：

1. **组件化**: 将重复的 UI 元素抽象为可复用组件
2. **模块化**: CSS 样式模块化，避免全局污染
3. **可维护性**: 清晰的目录结构和代码组织
4. **视觉一致性**: 100% 还原原有设计，不改变任何视觉效果

### 1.2 成功标准

- [ ] 所有页面视觉效果与原 HTML 100% 一致
- [ ] 组件复用率 > 60%
- [ ] 无 CSS 全局污染
- [ ] Lighthouse 性能分数 > 80

### 1.3 范围边界

| 范围内 | 范围外 |
|--------|--------|
| 首页（几何花园）迁移 | 响应式设计（保持 1920px 固定宽度） |
| 6 篇文章页面迁移 | CMS 集成 |
| CSS 变量系统建立 | 国际化 (i18n) |
| 组件库搭建 | SEO 优化（后续迭代） |
| 静态数据管理 | 用户认证系统 |

---

## 2. 里程碑计划

### 2.1 里程碑概览

| 里程碑 | 目标 | 预计完成 | 状态 |
|--------|------|----------|------|
| M1 | 项目初始化 + 基础设施 | Day 1 | TODO |
| M2 | UI 组件库完成 | Day 2 | TODO |
| M3 | 页面组件完成 | Day 3 | TODO |
| M4 | 页面集成完成 | Day 4 | TODO |
| M5 | 视觉 QA 与上线 | Day 5 | TODO |

### 2.2 里程碑完成定义 (DoD)

#### M1: 项目初始化 + 基础设施
- [ ] Next.js 项目可正常启动 (`npm run dev`)
- [ ] 目录结构符合 TECH 文档规范
- [ ] CSS 变量系统完整（36 个变量）
- [ ] 字体加载正常
- [ ] 动画关键帧定义完成

#### M2: UI 组件库完成
- [ ] 布局组件：NoiseTexture、GridLines、Header、Footer
- [ ] UI 原子组件：Button、Shape、ContentCard、LinkArrow、NodeItem、QuoteBlock、Divider
- [ ] 所有组件有对应的 CSS Module

#### M3: 页面组件完成
- [ ] 首页组件：Hero、ContentSection、NetworkJoin
- [ ] 文章组件：ArticleHero、TableOfContents、ArticleContent、RelatedArticles、CTABox
- [ ] 组件 Props 接口符合 TECH 文档定义

#### M4: 页面集成完成
- [ ] 首页可正常访问 (`/`)
- [ ] 6 篇文章页可正常访问 (`/articles/[slug]`)
- [ ] 文章数据结构完整

#### M5: 视觉 QA 与上线
- [ ] 与原 HTML 视觉对比无差异
- [ ] Lighthouse 性能分数 > 80
- [ ] 代码清理完成

---

## 3. 任务清单与状态

### 3.1 任务依赖图

```
Phase 1: 项目初始化
├── TASK-001: 创建 Next.js 项目 (towow-gyx)
│
Phase 2: 基础设施 (可并行)
├── TASK-002: CSS 变量系统 (towow-0k2) ──────────────────┐
├── TASK-003: 字体配置 (towow-jb6) ─────────────────────┤
└── TASK-004: 动画系统 (towow-537) ─────────────────────┤
                                                         │
Phase 3: UI 组件 (可并行)                                │
├── TASK-005: 布局组件 (towow-dxw) ◄────────────────────┤
│   ├── NoiseTexture                                     │
│   ├── GridLines                                        │
│   └── Footer                                           │
│                                                        │
├── TASK-006: UI 原子组件 (towow-13g) ◄─────────────────┘
│   ├── Button
│   ├── Shape
│   ├── ContentCard
│   ├── LinkArrow
│   └── Divider
│
Phase 4: 页面组件 (可并行)
├── TASK-007: 首页组件 (towow-0cg) ◄──── TASK-005, TASK-006
│   ├── Hero
│   ├── ContentSection
│   └── NetworkJoin
│
├── TASK-008: 文章组件 (towow-4us) ◄──── TASK-005, TASK-006
│   ├── Header
│   ├── ArticleHero
│   ├── TableOfContents
│   ├── ArticleContent
│   ├── RelatedArticles
│   └── CTABox
│
Phase 5: 页面集成 (可并行)
├── TASK-009: 首页集成 (towow-75y) ◄──── TASK-007
├── TASK-010: 文章页集成 (towow-agu) ◄── TASK-008
│
Phase 6: 测试与优化
└── TASK-011: 视觉 QA 与优化 (towow-hsi) ◄── TASK-009, TASK-010
```

### 3.2 执行进度表

| TASK ID | 任务名称 | Beads ID | 优先级 | 预估工时 | 状态 | Owner | 阻塞项 |
|---------|----------|----------|--------|----------|------|-------|--------|
| TASK-NEXTJS-001 | 项目初始化 | towow-gyx | P0 | 2h | TODO | - | 无 |
| TASK-NEXTJS-002 | CSS 变量系统 | towow-0k2 | P0 | 1h | TODO | - | TASK-001 |
| TASK-NEXTJS-003 | 字体配置 | towow-jb6 | P0 | 1h | TODO | - | TASK-001 |
| TASK-NEXTJS-004 | 动画系统 | towow-537 | P0 | 1h | TODO | - | TASK-001 |
| TASK-NEXTJS-005 | 布局组件 | towow-dxw | P0 | 3h | TODO | - | TASK-002 |
| TASK-NEXTJS-006 | UI 原子组件 | towow-13g | P0 | 4h | TODO | - | TASK-002 |
| TASK-NEXTJS-007 | 首页组件 | towow-0cg | P0 | 4h | TODO | - | TASK-005, TASK-006 |
| TASK-NEXTJS-008 | 文章组件 | towow-4us | P0 | 5h | TODO | - | TASK-005, TASK-006 |
| TASK-NEXTJS-009 | 首页集成 | towow-75y | P0 | 3h | TODO | - | TASK-007 |
| TASK-NEXTJS-010 | 文章页集成 | towow-agu | P0 | 4h | TODO | - | TASK-008 |
| TASK-NEXTJS-011 | 视觉 QA 与优化 | towow-hsi | P0 | 4h | TODO | - | TASK-009, TASK-010 |

**总预估工时**: 32 小时

### 3.3 接口依赖验证约定

根据 TECH 文档，以下任务存在接口依赖（非硬依赖），采用契约先行策略：

| TASK_ID | 接口依赖任务 | 验证时间点 | 验证方式 |
|---------|-------------|-----------|---------|
| TASK-005 | TASK-003 (字体) | TASK-003 完成后 | 字体渲染验证 |
| TASK-005 | TASK-004 (动画) | TASK-004 完成后 | 动画效果验证 |
| TASK-006 | TASK-004 (动画) | TASK-004 完成后 | 动画效果验证 |

**说明**: 接口依赖不设置 beads 依赖，允许并行开发。但必须在被依赖任务完成后进行联调验证。

---

## 4. 关键路径分析

### 4.1 关键路径

```
TASK-001 → TASK-002 → TASK-005 → TASK-007 → TASK-009 → TASK-011
                    ↘ TASK-006 ↗         ↘ TASK-008 → TASK-010 ↗
```

### 4.2 时间估算

| 路径 | 任务序列 | 总工时 |
|------|----------|--------|
| 关键路径 A | 001→002→005→007→009→011 | 2+1+3+4+3+4 = 17h |
| 关键路径 B | 001→002→006→008→010→011 | 2+1+4+5+4+4 = 20h |

**关键路径**: B 路径（20 小时）

### 4.3 并行优化

- Phase 2 的三个任务可完全并行（节省 2h）
- Phase 3 的两个任务可完全并行（节省 3h）
- Phase 4 的两个任务可完全并行（节省 4h）
- Phase 5 的两个任务可完全并行（节省 3h）

**优化后总时长**: 约 3-4 个工作日

---

## 5. 执行计划（无限 AI Dev 场景）

### 5.1 批次执行计划

#### 第一批（立即可并行）
- **TASK-001**: 项目初始化 (towow-gyx)
  - 无依赖，可立即启动

#### 第二批（等第一批完成后启动）
- **TASK-002**: CSS 变量系统 (towow-0k2)
- **TASK-003**: 字体配置 (towow-jb6)
- **TASK-004**: 动画系统 (towow-537)
- 三个任务可完全并行

#### 第三批（等第二批完成后启动）
- **TASK-005**: 布局组件 (towow-dxw)
- **TASK-006**: UI 原子组件 (towow-13g)
- 两个任务可完全并行

#### 第四批（等第三批完成后启动）
- **TASK-007**: 首页组件 (towow-0cg)
- **TASK-008**: 文章组件 (towow-4us)
- 两个任务可完全并行

#### 第五批（等第四批完成后启动）
- **TASK-009**: 首页集成 (towow-75y)
- **TASK-010**: 文章页集成 (towow-agu)
- 两个任务可完全并行

#### 第六批（等第五批完成后启动）
- **TASK-011**: 视觉 QA 与优化 (towow-hsi)

### 5.2 beads 依赖设置清单

```bash
# 已执行的依赖设置命令
# Phase 2 依赖 Phase 1
bd dep add towow-0k2 towow-gyx  # TASK-002 依赖 TASK-001
bd dep add towow-jb6 towow-gyx  # TASK-003 依赖 TASK-001
bd dep add towow-537 towow-gyx  # TASK-004 依赖 TASK-001

# Phase 3 依赖 Phase 2
bd dep add towow-dxw towow-0k2  # TASK-005 依赖 TASK-002
bd dep add towow-13g towow-0k2  # TASK-006 依赖 TASK-002

# Phase 4 依赖 Phase 3
bd dep add towow-0cg towow-dxw  # TASK-007 依赖 TASK-005
bd dep add towow-0cg towow-13g  # TASK-007 依赖 TASK-006
bd dep add towow-4us towow-dxw  # TASK-008 依赖 TASK-005
bd dep add towow-4us towow-13g  # TASK-008 依赖 TASK-006

# Phase 5 依赖 Phase 4
bd dep add towow-75y towow-0cg  # TASK-009 依赖 TASK-007
bd dep add towow-agu towow-4us  # TASK-010 依赖 TASK-008

# Phase 6 依赖 Phase 5
bd dep add towow-hsi towow-75y  # TASK-011 依赖 TASK-009
bd dep add towow-hsi towow-agu  # TASK-011 依赖 TASK-010
```

---

## 6. 风险与预案

| 风险 | 影响 | 概率 | 预案 |
|------|------|------|------|
| 字体加载失败 | 视觉不一致 | 低 | 配置 fallback 字体 |
| CSS 变量浏览器兼容 | 样式异常 | 低 | 使用 PostCSS 编译 |
| 动画性能问题 | 页面卡顿 | 中 | 使用 `will-change` 优化 |
| 图片加载慢 | 首屏体验差 | 中 | 使用 Next.js Image 优化 |
| 组件接口不匹配 | 集成困难 | 中 | 严格按 TECH 文档接口契约开发 |

---

## 7. Gate 检查点

### Gate A（进入实现前）- 已通过

- [x] TECH 文档完成 (TECH-NEXTJS-MIGRATION-v5.md)
- [x] 任务拆解完成 (11 个 TASK)
- [x] 组件接口契约定义完成
- [x] 依赖关系分析完成

### Gate B（P0 Task 进入 DONE 前）

每个 TASK 完成时必须验证：
- [ ] 对应 AC 的测试用例与结果
- [ ] 代码符合 TECH 文档规范
- [ ] CSS Module 无全局污染
- [ ] 组件 Props 接口符合契约

### Gate C（视觉 QA 前）

- [ ] 所有页面可正常访问
- [ ] 与原 HTML 视觉对比无差异
- [ ] Lighthouse 性能分数 > 80

---

## 8. 验收检查点（禁止 Mock）

- [ ] 前端是否使用真实数据结构？（如果是 Mock = 不通过）
- [ ] 组件是否按 TECH 文档接口实现？（如果接口不匹配 = 不通过）
- [ ] 是否进行了视觉对比验证？（如果没有 = 不通过）

---

## 9. 未决项

| 编号 | 问题 | 状态 | 负责人 |
|------|------|------|--------|
| [OPEN-1] | 是否需要响应式设计？ | 待决策 | - |
| [OPEN-2] | 文章内容是否需要 MDX 支持？ | 待决策 | - |
| [OPEN-3] | 是否需要 SEO 优化（meta tags）？ | 待决策 | - |
| [TBD-1] | 部署平台选择（Vercel/其他） | 待决策 | - |

---

## 10. 变更记录

| 日期 | 版本 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 2026-01-29 | v5 | 初始版本，基于 TECH-NEXTJS-MIGRATION-v5 创建 | proj |

---

## 附录 A: beads 任务 ID 映射表

| TASK ID | Beads ID | 文档路径 |
|---------|----------|----------|
| TASK-NEXTJS-001 | towow-gyx | `.ai/TASK-NEXTJS-001.md` |
| TASK-NEXTJS-002 | towow-0k2 | `.ai/TASK-NEXTJS-002.md` |
| TASK-NEXTJS-003 | towow-jb6 | `.ai/TASK-NEXTJS-003.md` |
| TASK-NEXTJS-004 | towow-537 | `.ai/TASK-NEXTJS-004.md` |
| TASK-NEXTJS-005 | towow-dxw | `.ai/TASK-NEXTJS-005.md` |
| TASK-NEXTJS-006 | towow-13g | `.ai/TASK-NEXTJS-006.md` |
| TASK-NEXTJS-007 | towow-0cg | `.ai/TASK-NEXTJS-007.md` |
| TASK-NEXTJS-008 | towow-4us | `.ai/TASK-NEXTJS-008.md` |
| TASK-NEXTJS-009 | towow-75y | `.ai/TASK-NEXTJS-009.md` |
| TASK-NEXTJS-010 | towow-agu | `.ai/TASK-NEXTJS-010.md` |
| TASK-NEXTJS-011 | towow-hsi | `.ai/TASK-NEXTJS-011.md` |

## 附录 B: 常用 beads 命令

```bash
# 查看可立即开始的任务
bd ready -l NEXTJS-MIGRATION

# 查看所有任务
bd list -l NEXTJS-MIGRATION

# 查看任务详情
bd show <beads_id>

# 更新任务状态
bd update <beads_id> -s "doing"   # 开始
bd update <beads_id> -s "done"    # 完成

# 查看依赖关系
bd dep list <beads_id>
```
