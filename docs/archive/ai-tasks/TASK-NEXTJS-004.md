# TASK-NEXTJS-004: 动画系统

## 任务元信息

- **任务 ID**: TASK-NEXTJS-004
- **Beads ID**: `towow-537`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 1 小时
- **状态**: TODO

---

## 1. 目标

建立完整的 CSS 动画系统，包括关键帧定义和动画工具类。

---

## 2. 输入

- `ToWow - 几何花园 V1.html` 第 294-309 行的动画关键帧
- TECH-NEXTJS-MIGRATION-v5.md 第 5.3 节的动画规范

---

## 3. 输出

- `styles/animations.css` - 动画关键帧和工具类

---

## 4. 验收标准

### 4.1 关键帧完整性

- [ ] `@keyframes growUp` - 从下往上生长动画
- [ ] `@keyframes float` - 上下浮动动画
- [ ] `@keyframes spin` - 旋转动画
- [ ] `@keyframes pulse` - 脉冲缩放动画

### 4.2 工具类完整性

- [ ] `.animate-float` - 浮动动画类
- [ ] `.animate-pulse` - 脉冲动画类
- [ ] `.animate-spin` - 旋转动画类
- [ ] `.animate-grow-up` - 生长动画类

### 4.3 视觉验收

- [ ] Hero 区域背景动画正常
- [ ] 网络节点浮动动画正常
- [ ] 几何图形脉冲动画正常
- [ ] 旋转动画流畅无卡顿

---

## 5. 实现步骤

### 5.1 创建 animations.css

```css
/* styles/animations.css */

/* === 关键帧定义 === */

/* 从下往上生长 - 用于 Hero 背景 */
@keyframes growUp {
  0% {
    transform: translateY(100px) scale(0);
    opacity: 0;
  }
  100% {
    transform: translateY(0) scale(1);
    opacity: 0.6;
  }
}

/* 上下浮动 - 用于网络节点 */
@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

/* 旋转 - 用于装饰图形 */
@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* 脉冲缩放 - 用于几何图形 */
@keyframes pulse {
  0%, 100% {
    opacity: 0.4;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.05);
  }
}

/* === 动画工具类 === */

.animate-float {
  animation: float 6s ease-in-out infinite;
}

.animate-pulse {
  animation: pulse 6s infinite;
}

.animate-spin {
  animation: spin 60s linear infinite;
}

.animate-grow-up {
  animation: growUp 1.5s ease-out forwards;
}

/* === 动画延迟工具类 === */

.animation-delay-300 {
  animation-delay: 0.3s;
}

.animation-delay-500 {
  animation-delay: 0.5s;
}

.animation-delay-1000 {
  animation-delay: 1s;
}

.animation-delay-1500 {
  animation-delay: 1.5s;
}

.animation-delay-2000 {
  animation-delay: 2s;
}

/* === 动画时长工具类 === */

.animation-duration-6s {
  animation-duration: 6s;
}

.animation-duration-7s {
  animation-duration: 7s;
}

.animation-duration-8s {
  animation-duration: 8s;
}

/* === 性能优化 === */

.will-change-transform {
  will-change: transform;
}

.will-change-opacity {
  will-change: opacity;
}
```

### 5.2 更新 globals.css

确保 animations.css 被正确导入：

```css
@import '../styles/fonts.css';
@import '../styles/variables.css';
@import '../styles/typography.css';
@import '../styles/animations.css';
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

### 7.1 动画性能优化

- 只对 `transform` 和 `opacity` 做动画（GPU 加速）
- 避免对 `width`、`height`、`margin` 等属性做动画
- 使用 `will-change` 提示浏览器优化

### 7.2 动画时长设计

| 动画 | 时长 | 说明 |
|------|------|------|
| growUp | 1.5s | 一次性动画，快速完成 |
| float | 6-8s | 循环动画，缓慢自然 |
| pulse | 6s | 循环动画，缓慢呼吸感 |
| spin | 60s | 循环动画，极慢旋转 |

### 7.3 动画曲线

- `ease-out` - 快进慢出，适合入场动画
- `ease-in-out` - 慢进慢出，适合循环动画
- `linear` - 匀速，适合旋转动画
- `cubic-bezier(0.165, 0.84, 0.44, 1)` - 自定义曲线，更有弹性

---

## 8. 注意事项

- 动画参数必须与原 HTML 完全一致
- 注意 `animation-fill-mode: forwards` 的使用（growUp 需要）
- 测试时注意不同浏览器的动画表现
- 移动端可能需要降低动画复杂度（本项目暂不考虑）
