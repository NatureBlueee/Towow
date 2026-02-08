# TASK-NEXTJS-011: 视觉 QA 与优化

## 任务元信息

- **任务 ID**: TASK-NEXTJS-011
- **Beads ID**: `towow-hsi`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 4 小时
- **状态**: TODO

---

## 1. 目标

对迁移后的 Next.js 项目进行全面的视觉 QA，确保与原 HTML 100% 一致，并进行性能优化。

---

## 2. 输入

- 原 HTML 文件（7 个）
- 迁移后的 Next.js 项目
- TASK-NEXTJS-009 和 TASK-NEXTJS-010 的产出

---

## 3. 输出

- 视觉 QA 报告
- 修复后的代码
- 性能优化后的代码

---

## 4. 验收标准

### 4.1 视觉一致性验收

- [ ] 首页与原 HTML 视觉 100% 一致
- [ ] 6 篇文章页与原 HTML 视觉 100% 一致
- [ ] 所有颜色值正确
- [ ] 所有字体正确
- [ ] 所有间距正确
- [ ] 所有动画正确

### 4.2 交互验收

- [ ] 所有 hover 效果正常
- [ ] 所有链接可点击
- [ ] TOC 滚动高亮正常
- [ ] 阅读进度条正常
- [ ] 按钮动画正常

### 4.3 性能验收

- [ ] Lighthouse Performance > 80
- [ ] Lighthouse Accessibility > 90
- [ ] Lighthouse Best Practices > 90
- [ ] 首屏加载时间 < 3s
- [ ] 无明显卡顿

---

## 5. 实现步骤

### 5.1 视觉 QA 检查清单

#### 首页检查

| 区域 | 检查项 | 状态 |
|------|--------|------|
| Hero | 标题字体大小 66px | [ ] |
| Hero | 副标题字体大小 22px | [ ] |
| Hero | 按钮间距 24px | [ ] |
| Hero | 背景圆形颜色 #CBC3E3 | [ ] |
| Hero | 背景方形颜色 #D4F4DD | [ ] |
| Hero | growUp 动画正常 | [ ] |
| Section 1 | 卡片位置 grid-column: 2/7 | [ ] |
| Section 1 | 装饰图形位置正确 | [ ] |
| Section 2 | 卡片位置 grid-column: 7/12 | [ ] |
| ... | ... | [ ] |
| NetworkJoin | SVG 连线正确 | [ ] |
| NetworkJoin | 节点位置正确 | [ ] |
| NetworkJoin | float 动画正常 | [ ] |
| Footer | 二维码区域 | [ ] |
| Footer | 联系方式 | [ ] |

#### 文章页检查

| 区域 | 检查项 | 状态 |
|------|--------|------|
| Header | 高度 80px | [ ] |
| Header | 毛玻璃效果 | [ ] |
| Header | 进度条颜色 #CBC3E3 | [ ] |
| Hero | 标题字体 72px 衬线体 | [ ] |
| Hero | 装饰图片位置 | [ ] |
| TOC | sticky 定位 | [ ] |
| TOC | 高亮效果 | [ ] |
| Content | 首字母装饰 | [ ] |
| Content | strong 渐变背景 | [ ] |
| Content | 引用块样式 | [ ] |
| CTA | 渐变背景 | [ ] |
| Related | 卡片 hover 效果 | [ ] |
| Footer | 深色背景 | [ ] |

### 5.2 视觉对比方法

1. **并排对比**：在两个浏览器窗口中分别打开原 HTML 和 Next.js 页面
2. **截图对比**：使用工具对比截图差异
3. **像素级对比**：使用 Pixelmatch 等工具

### 5.3 性能优化

#### 图片优化

```typescript
// 使用 Next.js Image 组件
import Image from 'next/image';

<Image
  src={heroImages.right}
  alt=""
  width={150}
  height={150}
  priority
/>
```

#### 字体优化

```typescript
// 使用 next/font 预加载字体
import localFont from 'next/font/local';

const notoSans = localFont({
  src: '../public/fonts/NotoSansHans-Regular.otf',
  display: 'swap',
});
```

#### 动画优化

```css
/* 使用 will-change 提示浏览器 */
.animate-float {
  will-change: transform;
}

/* 使用 transform 而非 top/left */
.shape {
  transform: translate(var(--x), var(--y));
}
```

### 5.4 常见问题修复

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 字体不一致 | 字体加载失败 | 检查 CDN 可用性，添加 fallback |
| 间距不一致 | CSS 变量未生效 | 检查变量导入顺序 |
| 动画卡顿 | 触发重排 | 使用 transform 替代 |
| 颜色偏差 | 颜色值错误 | 对比原 HTML 颜色值 |
| hover 失效 | z-index 问题 | 检查层级关系 |

---

## 6. 依赖关系

### 6.1 硬依赖

- TASK-NEXTJS-009: 首页集成
- TASK-NEXTJS-010: 文章页集成

### 6.2 接口依赖

无

### 6.3 被依赖

无（最终任务）

---

## 7. 技术说明

### 7.1 Lighthouse 测试

```bash
# 使用 Chrome DevTools
1. 打开 Chrome DevTools
2. 切换到 Lighthouse 面板
3. 选择 Performance, Accessibility, Best Practices
4. 点击 Generate report

# 使用 CLI
npx lighthouse http://localhost:3000 --output html --output-path ./lighthouse-report.html
```

### 7.2 视觉回归测试工具

- **Percy**: 自动化视觉测试
- **Chromatic**: Storybook 集成
- **Pixelmatch**: 像素级对比

### 7.3 性能指标

| 指标 | 目标 | 说明 |
|------|------|------|
| FCP | < 1.8s | First Contentful Paint |
| LCP | < 2.5s | Largest Contentful Paint |
| CLS | < 0.1 | Cumulative Layout Shift |
| TBT | < 200ms | Total Blocking Time |

---

## 8. 注意事项

- 视觉 QA 需要在 1920px 宽度下进行
- 测试时清除浏览器缓存
- 注意不同浏览器的渲染差异
- 性能测试需要在生产构建下进行（`npm run build && npm start`）
- 记录所有发现的问题和修复方案

---

## 9. QA 报告模板

```markdown
# 视觉 QA 报告

## 测试环境
- 浏览器: Chrome 120
- 分辨率: 1920x1080
- 日期: 2026-01-XX

## 首页

### 通过项
- [ ] Hero 区域
- [ ] Section 1-6
- [ ] NetworkJoin
- [ ] Footer

### 问题项
| 问题 | 严重程度 | 状态 |
|------|----------|------|
| ... | ... | ... |

## 文章页

### 通过项
- [ ] Header
- [ ] Hero
- [ ] TOC
- [ ] Content
- [ ] CTA
- [ ] Related
- [ ] Footer

### 问题项
| 问题 | 严重程度 | 状态 |
|------|----------|------|
| ... | ... | ... |

## 性能报告

| 指标 | 得分 | 目标 | 状态 |
|------|------|------|------|
| Performance | XX | >80 | ... |
| Accessibility | XX | >90 | ... |
| Best Practices | XX | >90 | ... |

## 总结
...
```
