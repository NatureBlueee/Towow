# ToWow 官方网站

> ToWow - 为 AI Agent 重新设计的互联网

ToWow 正在构建一个全新时代的基础设施，让 AI Agent 能够代表用户进行协作、协商和价值创造。本网站展示了我们的愿景，并提供交互式演示体验。

## 目录

- [核心特性](#-核心特性)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [项目结构](#-项目结构)
- [设计系统](#-设计系统)
- [参与贡献](#-参与贡献)
- [许可证](#-许可证)

## 核心特性

- **几何花园设计** - 独特的视觉风格，包含动态几何图形、噪点纹理和网格叠加效果
- **交互式演示** - 通过 WebSocket 实时体验 AI Agent 协商过程
- **文章系统** - 深度文章阐述我们的愿景和技术理念
- **响应式布局** - 移动优先设计，采用 12 列栅格系统
- **流畅动画** - CSS 动画实现浮动、脉冲和旋转效果
- **OAuth 集成** - SecondMe 认证，提供个性化体验

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | [Next.js 16](https://nextjs.org/) (App Router) |
| 语言 | [TypeScript 5](https://www.typescriptlang.org/) |
| UI 库 | [React 19](https://react.dev/) |
| 样式 | [Tailwind CSS 4](https://tailwindcss.com/) + CSS Modules |
| 图标 | [Remix Icon](https://remixicon.com/) |

## 快速开始

### 环境要求

- Node.js 18+
- npm、yarn、pnpm 或 bun

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd towow-website

# 安装依赖
npm install
```

### 开发

```bash
# 启动开发服务器
npm run dev
```

在浏览器中打开 [http://localhost:3000](http://localhost:3000) 查看效果。

### 构建

```bash
# 创建生产构建
npm run build

# 启动生产服务器
npm run start
```

### 代码检查

```bash
npm run lint
```

## 项目结构

```
towow-website/
├── app/                    # Next.js App Router 页面
│   ├── page.tsx           # 首页
│   ├── layout.tsx         # 根布局（噪点和网格）
│   ├── experience/        # 交互演示页面
│   └── articles/          # 文章页面（动态路由）
├── components/
│   ├── home/              # 首页组件
│   │   ├── Hero.tsx       # 主视觉区域
│   │   ├── ContentSection.tsx
│   │   └── NetworkJoin.tsx
│   ├── experience/        # 演示体验组件
│   │   ├── LoginPanel.tsx
│   │   ├── RequirementForm.tsx
│   │   ├── NegotiationTimeline.tsx
│   │   └── ResultPanel.tsx
│   ├── article/           # 文章组件
│   ├── layout/            # 布局组件（Header、Footer）
│   └── ui/                # 可复用 UI 组件
├── hooks/                 # 自定义 React Hooks
│   ├── useAuth.ts
│   ├── useNegotiation.ts
│   └── useWebSocket.ts
├── context/               # React Context 提供者
├── lib/                   # 工具函数和常量
├── styles/                # 全局样式和变量
└── types/                 # TypeScript 类型定义
```

## 设计系统

### 色彩系统

| 变量 | 颜色值 | 用途 |
|------|--------|------|
| `--c-primary` | `#CBC3E3` | 主色调（薰衣草紫） |
| `--c-secondary` | `#D4F4DD` | 次要色（薄荷绿） |
| `--c-accent` | `#FFE4B5` | 强调色（蜜桃橙） |
| `--c-detail` | `#E8F3E8` | 细节色 |
| `--c-bg` | `#EEEEEE` | 背景色 |

### 字体系统

- **中文标题**: NotoSansHans-Medium
- **中文正文**: NotoSansHans-Regular
- **英文**: MiSans 字体家族

## 参与贡献

我们欢迎各种形式的贡献！请随时提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m '添加某个特性'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

## 许可证

本项目为专有软件，保留所有权利。

---

由 ToWow 团队用心打造
