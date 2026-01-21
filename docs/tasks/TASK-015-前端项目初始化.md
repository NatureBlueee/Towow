# TASK-015：前端项目初始化

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-015 |
| 所属Phase | Phase 5：前端开发 |
| 硬依赖 | - |
| 接口依赖 | - |
| 可并行 | TASK-001~007（与后端并行） |
| 预估工作量 | 0.5天 |
| 状态 | 待开始 |

---

## 任务描述

初始化React前端项目，配置基础依赖和项目结构。

---

## 具体工作

### 1. 创建项目

```bash
npx create-react-app towow-frontend --template typescript
cd towow-frontend
```

### 2. 安装依赖

```bash
# UI组件
npm install antd @ant-design/icons

# 状态管理
npm install zustand

# 动画
npm install framer-motion

# HTTP请求
npm install axios

# 路由
npm install react-router-dom

# 工具
npm install dayjs lodash-es
npm install -D @types/lodash-es
```

### 3. 项目结构

```
towow-frontend/
├── src/
│   ├── api/                 # API调用
│   │   ├── client.ts        # axios实例配置
│   │   ├── demand.ts        # 需求相关API
│   │   └── events.ts        # 事件相关API
│   ├── components/          # 通用组件
│   │   ├── common/
│   │   │   └── Loading.tsx
│   │   └── layout/
│   │       └── MainLayout.tsx
│   ├── features/            # 功能模块
│   │   ├── demand/          # 需求提交
│   │   │   └── DemandSubmitPage.tsx
│   │   ├── negotiation/     # 协商展示
│   │   │   └── NegotiationPage.tsx
│   │   └── dashboard/       # 大屏展示
│   │       └── DashboardPage.tsx
│   ├── hooks/               # 自定义Hooks
│   │   └── useSSE.ts        # SSE连接Hook
│   ├── stores/              # 状态管理
│   │   ├── demandStore.ts
│   │   └── eventStore.ts
│   ├── types/               # 类型定义
│   │   └── index.ts
│   ├── utils/               # 工具函数
│   │   └── format.ts
│   ├── App.tsx
│   └── index.tsx
├── public/
└── package.json
```

### 4. 基础配置

#### 4.1 API客户端

`src/api/client.ts`:

```typescript
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 统一错误处理
    if (error.response?.status === 401) {
      // 未授权处理
    }
    return Promise.reject(error);
  }
);

// SSE连接创建函数
export const createSSEConnection = (endpoint: string): EventSource => {
  return new EventSource(`${API_BASE}${endpoint}`);
};
```

#### 4.2 类型定义

`src/types/index.ts`:

```typescript
// 需求相关
export interface DemandSubmitRequest {
  raw_input: string;
  user_id?: string;
}

export interface DemandSubmitResponse {
  demand_id: string;
  channel_id: string;
  status: string;
  understanding: {
    surface_demand: string;
    confidence: string;
  };
}

// 协商相关
export interface Participant {
  agent_id: string;
  name: string;
  role?: string;
  status: 'pending' | 'accepted' | 'declined' | 'negotiating';
  contribution?: string;
}

export interface Proposal {
  version: number;
  summary: string;
  assignments: Array<{
    agent_id: string;
    role: string;
    responsibility: string;
  }>;
  timeline?: string;
  open_questions?: string[];
  confidence: 'high' | 'medium' | 'low';
}

// 事件相关
export interface TimelineEvent {
  id: string;
  type: string;
  timestamp: string;
  title: string;
  description?: string;
  status: 'done' | 'active' | 'pending';
}

export interface SSEEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, any>;
}
```

#### 4.3 状态管理

`src/stores/demandStore.ts`:

```typescript
import { create } from 'zustand';
import { DemandSubmitResponse } from '../types';

interface DemandState {
  currentDemand: DemandSubmitResponse | null;
  loading: boolean;
  error: string | null;
  setCurrentDemand: (demand: DemandSubmitResponse) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useDemandStore = create<DemandState>((set) => ({
  currentDemand: null,
  loading: false,
  error: null,
  setCurrentDemand: (demand) => set({ currentDemand: demand }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({ currentDemand: null, loading: false, error: null }),
}));
```

#### 4.4 路由配置

`src/App.tsx`:

```tsx
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { MainLayout } from './components/layout/MainLayout';
import { DemandSubmitPage } from './features/demand/DemandSubmitPage';
import { NegotiationPage } from './features/negotiation/NegotiationPage';

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <MainLayout>
          <Routes>
            <Route path="/" element={<DemandSubmitPage />} />
            <Route path="/negotiation/:demandId" element={<NegotiationPage />} />
          </Routes>
        </MainLayout>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
```

#### 4.5 环境变量配置

`.env.development`:

```
REACT_APP_API_URL=http://localhost:8000
```

`.env.production`:

```
REACT_APP_API_URL=https://api.towow.example.com
```

---

## 验收标准

- [ ] 项目可以正常启动（npm start）
- [ ] 所有依赖安装完成，无报错
- [ ] 目录结构创建完成
- [ ] TypeScript配置正确，无类型错误
- [ ] 基础路由配置完成
- [ ] API客户端配置完成
- [ ] 状态管理配置完成
- [ ] Antd组件库可正常使用

---

## 产出物

- `towow-frontend/` 目录
- 项目基础结构
- 基础配置文件
- 类型定义文件

---

## 技术选型说明

| 项目 | 选型 | 理由 |
|------|------|------|
| 框架 | React 18 + TypeScript | 生态成熟、团队熟悉、类型安全 |
| UI库 | Ant Design | 组件丰富、快速开发、中文友好 |
| 状态管理 | Zustand | 轻量、简单、无样板代码 |
| 动画 | Framer Motion | 流畅的过渡动画、声明式API |
| HTTP | Axios | 成熟稳定、拦截器支持好 |

---

**创建时间**: 2026-01-21
**来源**: supplement-03-frontend.md
