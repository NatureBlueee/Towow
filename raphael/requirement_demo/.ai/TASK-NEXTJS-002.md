# TASK-NEXTJS-002: CSS 变量系统

## 任务元信息

- **任务 ID**: TASK-NEXTJS-002
- **Beads ID**: `towow-0k2`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 1 小时
- **状态**: TODO

---

## 1. 目标

建立完整的 CSS 变量系统，包括颜色、字体、栅格、间距、圆角、阴影、过渡和 z-index 层级。

---

## 2. 输入

- `ToWow - 几何花园 V1.html` 第 19-40 行的 CSS 变量定义
- TECH-NEXTJS-MIGRATION-v5.md 第 5.1 节的变量规范

---

## 3. 输出

- `styles/variables.css` - CSS 变量定义文件
- `styles/typography.css` - 排版样式文件
- `app/globals.css` - 全局样式入口（导入变量文件）

---

## 4. 验收标准

### 4.1 变量完整性

- [ ] 颜色系统：7 个颜色变量
- [ ] 字体系统：5 个字体变量
- [ ] 栅格系统：4 个栅格变量
- [ ] 间距系统：8 个间距变量
- [ ] 圆角系统：4 个圆角变量
- [ ] 阴影系统：3 个阴影变量
- [ ] 过渡系统：3 个过渡变量
- [ ] Z-Index 系统：6 个层级变量

### 4.2 排版类完整性

- [ ] `.text-h1` - 66px 标题
- [ ] `.text-h2` - 38px 标题
- [ ] `.text-h3` - 32px 标题
- [ ] `.text-body` - 19px 正文
- [ ] `.text-body-lg` - 22px 大正文
- [ ] `.text-caption` - 14px 说明文字
- [ ] `.en-font` - 英文字体
- [ ] `.article-title` - 72px 文章标题
- [ ] `.article-body` - 文章正文（含 strong 高亮）

### 4.3 全局样式验收

- [ ] `globals.css` 正确导入变量文件
- [ ] 基础重置样式（box-sizing, margin, padding）
- [ ] body 基础样式（width: 1920px, font-family, font-size）

---

## 5. 实现步骤

### 5.1 创建 variables.css

```css
/* styles/variables.css */

:root {
  /* === 颜色系统 === */
  --c-primary: #CBC3E3;
  --c-secondary: #D4F4DD;
  --c-accent: #FFE4B5;
  --c-detail: #E8F3E8;
  --c-bg: #EEEEEE;
  --c-text-main: #1A1A1A;
  --c-text-sec: #555555;
  --c-text-gray: #666666;
  --c-text-dark: #222222;

  /* === 字体系统 === */
  --f-cn-head: 'NotoSansHans-Medium', sans-serif;
  --f-cn-body: 'NotoSansHans-Regular', sans-serif;
  --f-en-head: 'MiSans-Demibold', sans-serif;
  --f-en-body: 'MiSans-Regular', sans-serif;
  --f-serif: 'NotoSerifCJKsc-Bold', serif;

  /* === 栅格系统 === */
  --grid-cols: 12;
  --grid-gap: 24px;
  --page-width: 1920px;
  --container-width: 1680px;

  /* === 间距系统 === */
  --spacing-xs: 8px;
  --spacing-sm: 16px;
  --spacing-md: 24px;
  --spacing-lg: 32px;
  --spacing-xl: 48px;
  --spacing-2xl: 64px;
  --spacing-3xl: 80px;
  --spacing-section: 240px;

  /* === 圆角 === */
  --radius-sm: 4px;
  --radius-md: 12px;
  --radius-lg: 24px;
  --radius-full: 50px;

  /* === 阴影 === */
  --shadow-sm: 0 5px 15px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 10px 30px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 20px 40px rgba(0, 0, 0, 0.1);

  /* === 过渡 === */
  --transition-fast: 0.2s ease;
  --transition-normal: 0.3s ease;
  --transition-slow: 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);

  /* === Z-Index 层级 === */
  --z-base: 1;
  --z-content: 5;
  --z-header: 100;
  --z-modal: 500;
  --z-noise: 999;
  --z-tooltip: 1000;
}
```

### 5.2 创建 typography.css

参考 TECH 文档第 5.2 节。

### 5.3 更新 globals.css

```css
/* app/globals.css */

@import '../styles/variables.css';
@import '../styles/typography.css';
@import '../styles/animations.css';

/* === 全局重置 === */
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

/* === Body 基础样式 === */
body {
  width: var(--page-width);
  margin: 0 auto;
  background-color: var(--c-bg);
  color: var(--c-text-main);
  font-family: var(--f-cn-body);
  font-size: 19px;
  line-height: 1.75;
  overflow-x: hidden;
  -webkit-font-smoothing: antialiased;
}

/* === 标题重置 === */
h1, h2, h3, h4, h5, h6 {
  font-family: var(--f-cn-head);
  margin: 0;
  font-weight: normal;
}

/* === 链接重置 === */
a {
  color: inherit;
  text-decoration: none;
}
```

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-001: 项目初始化（需要项目目录结构）

### 6.2 接口依赖

无

### 6.3 被依赖

- TASK-NEXTJS-005: 布局组件
- TASK-NEXTJS-006: UI 原子组件

---

## 7. 技术说明

### 7.1 CSS 变量命名规范

- 颜色：`--c-` 前缀
- 字体：`--f-` 前缀
- 间距：`--spacing-` 前缀
- 圆角：`--radius-` 前缀
- 阴影：`--shadow-` 前缀
- 过渡：`--transition-` 前缀
- 层级：`--z-` 前缀

### 7.2 为什么使用 CSS 变量而非 SCSS 变量

- 运行时可修改（支持主题切换）
- 浏览器原生支持
- 无需编译步骤
- 与原 HTML 保持一致

---

## 8. 注意事项

- 变量值必须与原 HTML 完全一致
- 注意字体 fallback 设置
- 确保 `@import` 顺序正确（variables 在最前）
