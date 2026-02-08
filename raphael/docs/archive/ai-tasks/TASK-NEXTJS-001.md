# TASK-NEXTJS-001: 项目初始化

## 任务元信息

- **任务 ID**: TASK-NEXTJS-001
- **Beads ID**: `towow-gyx`
- **所属 TECH**: TECH-NEXTJS-MIGRATION-v5
- **优先级**: P0
- **预估工时**: 2 小时
- **状态**: TODO

---

## 1. 目标

创建 Next.js 14 项目，配置基础开发环境，建立标准目录结构。

---

## 2. 输入

- Next.js 14 官方文档
- TECH-NEXTJS-MIGRATION-v5.md 中的目录结构设计

---

## 3. 输出

- 可运行的 Next.js 项目
- 完整的目录结构
- 基础配置文件

---

## 4. 验收标准

### 4.1 功能验收

- [ ] `npm run dev` 可正常启动开发服务器
- [ ] 访问 `http://localhost:3000` 显示默认页面
- [ ] TypeScript 编译无错误
- [ ] 目录结构符合 TECH 文档规范

### 4.2 目录结构验收

```
towow-website/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   └── articles/
│       └── [slug]/
│           └── page.tsx
├── components/
│   ├── layout/
│   ├── home/
│   ├── article/
│   └── ui/
├── lib/
├── styles/
├── public/
├── next.config.js
├── tsconfig.json
└── package.json
```

### 4.3 配置验收

- [ ] `next.config.js` 配置正确
- [ ] `tsconfig.json` 路径别名配置（@/）
- [ ] CSS Modules 支持已启用

---

## 5. 实现步骤

### 5.1 创建项目

```bash
npx create-next-app@latest towow-website --typescript --app --src-dir=false --tailwind=false --eslint
```

### 5.2 创建目录结构

```bash
cd towow-website

# 创建组件目录
mkdir -p components/layout
mkdir -p components/home
mkdir -p components/article
mkdir -p components/ui

# 创建其他目录
mkdir -p lib
mkdir -p styles
mkdir -p public/fonts

# 创建文章路由
mkdir -p app/articles/\[slug\]
touch app/articles/\[slug\]/page.tsx
```

### 5.3 配置 TypeScript 路径别名

编辑 `tsconfig.json`：

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### 5.4 清理默认文件

- 删除 `app/page.tsx` 中的默认内容
- 删除 `app/globals.css` 中的默认样式
- 删除 `public/` 中的默认图片

---

## 6. 依赖关系

### 6.1 硬依赖

无

### 6.2 被依赖

- TASK-NEXTJS-002: CSS 变量系统
- TASK-NEXTJS-003: 字体配置
- TASK-NEXTJS-004: 动画系统

---

## 7. 技术说明

### 7.1 为什么选择 App Router

- Next.js 14 官方推荐
- 支持 Server Components
- 更好的数据获取模式
- 支持 `generateStaticParams` 用于 SSG

### 7.2 为什么不用 Tailwind

- 原 HTML 的 CSS 结构清晰，可直接复用
- 复杂动画和几何图形用 Tailwind 会很冗长
- 避免引入额外学习成本

---

## 8. 注意事项

- 确保 Node.js 版本 >= 18.17
- 使用 npm 而非 yarn/pnpm（保持一致性）
- 不要提交 `node_modules` 目录
