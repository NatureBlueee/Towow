# TASK-NEXTJS-003: 字体配置

## 任务元信息

- **任务 ID**: TASK-NEXTJS-003
- **Beads ID**: `towow-jb6`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 1 小时
- **状态**: TODO

---

## 1. 目标

配置项目所需的所有字体，包括中文字体和英文字体，确保与原 HTML 视觉效果一致。

---

## 2. 输入

- `ToWow - 几何花园 V1.html` 第 14-17 行的 @font-face 定义
- `从注意力到价值 - ToWow深度阅读.html` 第 9-20 行的 @font-face 定义

---

## 3. 输出

- `styles/fonts.css` - 字体定义文件
- 或在 `app/layout.tsx` 中使用 next/font 配置

---

## 4. 验收标准

### 4.1 字体加载验收

- [ ] `NotoSansHans-Regular` 正常加载
- [ ] `NotoSansHans-Medium` 正常加载
- [ ] `MiSans-Regular` 正常加载
- [ ] `MiSans-Demibold` 正常加载
- [ ] `NotoSerifCJKsc-Bold` 正常加载（文章页专用）

### 4.2 视觉验收

- [ ] 首页标题字体正确
- [ ] 首页正文字体正确
- [ ] 英文字体正确
- [ ] 文章页标题字体正确（衬线体）

### 4.3 性能验收

- [ ] 字体加载不阻塞首屏渲染
- [ ] 配置了合适的 fallback 字体
- [ ] 无 FOUT（Flash of Unstyled Text）或 FOIT（Flash of Invisible Text）

---

## 5. 实现步骤

### 5.1 方案 A：使用 CDN（推荐，与原 HTML 一致）

创建 `styles/fonts.css`：

```css
/* styles/fonts.css */

@font-face {
  font-family: 'MiSans-Regular';
  src: url('https://assets-persist.lovart.ai/agent-static-assets/MiSans-Regular.ttf');
  font-display: swap;
}

@font-face {
  font-family: 'MiSans-Demibold';
  src: url('https://assets-persist.lovart.ai/agent-static-assets/MiSans-Demibold.ttf');
  font-display: swap;
}

@font-face {
  font-family: 'NotoSansHans-Regular';
  src: url('https://assets-persist.lovart.ai/agent-static-assets/NotoSansHans-Regular.otf');
  font-display: swap;
}

@font-face {
  font-family: 'NotoSansHans-Medium';
  src: url('https://assets-persist.lovart.ai/agent-static-assets/NotoSansHans-Medium.otf');
  font-display: swap;
}

@font-face {
  font-family: 'NotoSerifCJKsc-Bold';
  src: url('https://assets-persist.lovart.ai/agent-static-assets/NotoSerifCJKsc-Bold.otf');
  font-display: swap;
}
```

### 5.2 更新 globals.css

```css
/* app/globals.css */

@import '../styles/fonts.css';
@import '../styles/variables.css';
@import '../styles/typography.css';
@import '../styles/animations.css';

/* ... 其他样式 ... */
```

### 5.3 方案 B：使用本地字体（可选，性能更好）

1. 下载字体文件到 `public/fonts/`
2. 更新 @font-face 的 src 路径

```css
@font-face {
  font-family: 'NotoSansHans-Regular';
  src: url('/fonts/NotoSansHans-Regular.otf');
  font-display: swap;
}
```

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-001: 项目初始化

### 6.2 接口依赖

无

### 6.3 被依赖

- TASK-NEXTJS-005: 布局组件（接口依赖）
- TASK-NEXTJS-006: UI 原子组件（接口依赖）

---

## 7. 技术说明

### 7.1 font-display: swap

- 使用 `swap` 策略：先显示 fallback 字体，字体加载完成后替换
- 避免 FOIT（文字不可见）
- 可能有轻微的 FOUT（字体闪烁），但用户体验更好

### 7.2 字体文件格式

- `.ttf` - TrueType Font，兼容性好
- `.otf` - OpenType Font，功能更丰富
- 两种格式现代浏览器都支持

### 7.3 Fallback 字体策略

```css
--f-cn-head: 'NotoSansHans-Medium', 'PingFang SC', 'Microsoft YaHei', sans-serif;
--f-cn-body: 'NotoSansHans-Regular', 'PingFang SC', 'Microsoft YaHei', sans-serif;
```

---

## 8. 注意事项

- CDN 字体可能有跨域问题，需确认 CORS 配置
- 字体文件较大（中文字体通常 > 5MB），注意加载性能
- 如果 CDN 不稳定，考虑使用本地字体
- 测试时注意清除浏览器缓存
