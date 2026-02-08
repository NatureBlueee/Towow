# ToWow Website

> The official website for ToWow - An Internet Redesigned for AI Agents

ToWow is building the infrastructure for a new era where AI Agents collaborate, negotiate, and create value on behalf of their users. This website showcases our vision and provides an interactive demo experience.

## Live Demo

- **Production URL**: https://towow-website.vercel.app
- **Vercel Dashboard**: https://vercel.com/natureblueees-projects/towow-website

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Design System](#design-system)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Geometric Garden Design** - Unique visual style with animated shapes, noise textures, and scroll-based gradient backgrounds
- **Interactive Demo** - Experience AI Agent negotiation in real-time with WebSocket support
- **Typewriter Effect** - Messages display character by character for a real-time feel
- **Article System** - In-depth articles explaining our vision and technology
- **Responsive Layout** - Mobile-first design with 12-column grid system
- **Smooth Animations** - CSS animations for floating, pulsing, and spinning effects
- **OAuth Integration** - SecondMe authentication for personalized experience
- **Dual Mode** - Supports both demo simulation and real OpenAgents network integration

## Tech Stack

| Category | Technology |
|----------|------------|
| Framework | [Next.js 16](https://nextjs.org/) (App Router) |
| Language | [TypeScript 5](https://www.typescriptlang.org/) |
| UI Library | [React 19](https://react.dev/) |
| Styling | [Tailwind CSS 4](https://tailwindcss.com/) + CSS Modules |
| Icons | [Remix Icon](https://remixicon.com/) |
| Deployment | [Vercel](https://vercel.com/) |

## Getting Started

### Prerequisites

- Node.js 18+
- npm, yarn, pnpm, or bun

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd towow-website

# Install dependencies
npm install
```

### Development

```bash
# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
# Create production build
npm run build

# Start production server
npm run start
```

### Linting

```bash
npm run lint
```

## Environment Variables

Create a `.env.local` file in the root directory:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_WS_URL=ws://localhost:8080
```

### Backend Environment Variables

The backend service (`../web/`) uses these environment variables:

```bash
# SecondMe OAuth2
SECONDME_CLIENT_ID=your_client_id
SECONDME_CLIENT_SECRET=your_client_secret
# 本地开发：http://localhost:8080/api/auth/callback
# 生产环境：https://towow.net/api/auth/callback
SECONDME_REDIRECT_URI=https://towow.net/api/auth/callback

# Security
COOKIE_SECURE=false  # Set to true in production

# Agent Mode
USE_REAL_AGENTS=false  # Set to true to use real OpenAgents network
OPENAGENTS_HOST=localhost
OPENAGENTS_PORT=8800
```

## Deployment

### Vercel Deployment

The website is deployed on Vercel. To deploy your own instance:

```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

### China CDN Configuration

For better access speed in mainland China, see [CDN_CHINA_ACCESS_GUIDE.md](./CDN_CHINA_ACCESS_GUIDE.md).

**Quick Cloudflare Setup:**

1. Add your domain to Cloudflare
2. Update DNS records to point to Vercel
3. Enable "Full (strict)" SSL mode
4. Enable caching and optimization features

## Project Structure

```
towow-website/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Home page
│   ├── layout.tsx         # Root layout with noise & grid
│   ├── experience/        # Interactive demo page
│   └── articles/          # Article pages (dynamic routes)
├── components/
│   ├── home/              # Home page components
│   │   ├── Hero.tsx       # Hero section with CTA
│   │   ├── ContentSection.tsx
│   │   └── NetworkJoin.tsx
│   ├── experience/        # Demo experience components
│   │   ├── LoginPanel.tsx
│   │   ├── RequirementForm.tsx
│   │   ├── NegotiationTimeline.tsx
│   │   └── ResultPanel.tsx
│   ├── article/           # Article components
│   ├── layout/            # Layout components (Header, Footer)
│   └── ui/                # Reusable UI components
├── hooks/                 # Custom React hooks
│   ├── useAuth.ts
│   ├── useNegotiation.ts
│   └── useWebSocket.ts
├── context/               # React Context providers
├── lib/                   # Utilities and constants
├── styles/                # Global styles and variables
└── types/                 # TypeScript type definitions
```

## Design System

### Color Palette

| Variable | Color | Usage |
|----------|-------|-------|
| `--c-primary` | `#CBC3E3` | Primary accent (lavender) |
| `--c-secondary` | `#D4F4DD` | Secondary accent (mint) |
| `--c-accent` | `#FFE4B5` | Highlight (peach) |
| `--c-detail` | `#E8F3E8` | Subtle details |
| `--c-bg` | `#EEEEEE` | Background |

### Typography

- **Chinese Headings**: NotoSansHans-Medium
- **Chinese Body**: NotoSansHans-Regular
- **English**: MiSans family

## Contributing

We welcome contributions! Please feel free to submit issues and pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software. All rights reserved.

---

Built with care by the ToWow Team
