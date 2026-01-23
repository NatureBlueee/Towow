# ToWow 部署配置文档

> **文档路径**: `.ai/DEPLOYMENT-CONFIG.md`
>
> * 版本: v1.0
> * 状态: DRAFT
> * 创建日期: 2026-01-22
> * 最后更新: 2026-01-22

---

## 1. 部署架构概述

### 1.1 服务组件

ToWow 平台由以下核心服务组成：

| 组件 | 技术栈 | 端口 | 职责 |
|------|--------|------|------|
| **Frontend** | React 19 + Vite 7 + Zustand | 5173 (dev) / 80 (prod) | Web UI、SSE 订阅 |
| **Backend API** | FastAPI + Python 3.11 | 8000 | REST API、SSE 推送、Agent 协调 |
| **Database** | PostgreSQL 15 | 5432 | 持久化存储 |
| **LLM Service** | Anthropic Claude API | - | AI 决策（外部服务） |
| **OpenAgent** (可选) | Python + gRPC | 8600/8700 | 跨网络 Agent 协议 |

### 1.2 网络拓扑

```
                            ┌─────────────────────────────────────────┐
                            │              Cloud Server               │
                            │                                         │
  ┌─────────┐               │    ┌─────────────────────────────────┐  │
  │ Browser │◀──HTTPS──────▶│    │        Nginx (443/80)           │  │
  │  User   │               │    │   - SSL 终止                     │  │
  └─────────┘               │    │   - 静态文件服务                 │  │
                            │    │   - 反向代理                     │  │
                            │    └────────────┬────────────────────┘  │
                            │                 │                        │
                            │    ┌────────────┴────────────┐          │
                            │    │                         │          │
                            │    ▼                         ▼          │
                            │  ┌──────────┐         ┌──────────────┐  │
                            │  │ Frontend │         │ Backend API  │  │
                            │  │ (静态)    │         │ (FastAPI)    │  │
                            │  │ :80      │         │ :8000        │  │
                            │  └──────────┘         └──────┬───────┘  │
                            │                              │          │
                            │                 ┌────────────┴────┐     │
                            │                 ▼                 ▼     │
                            │          ┌──────────┐     ┌───────────┐ │
                            │          │ PostgreSQL │    │ Claude API │ │
                            │          │ :5432     │    │ (External) │ │
                            │          └──────────┘     └───────────┘ │
                            │                                         │
                            │         ┌──────────────────────────┐   │
                            │         │ OpenAgent (可选)         │   │
                            │         │ :8600 (gRPC) :8700 (HTTP)│   │
                            │         └──────────────────────────┘   │
                            └─────────────────────────────────────────┘
```

---

## 2. 本地开发环境

### 2.1 前置依赖

```bash
# Python 3.11+
python --version  # Python 3.11.x

# Node.js 20+
node --version  # v20.x.x

# PostgreSQL 15+ (可选，如果不用 Docker)
psql --version
```

### 2.2 快速启动

#### 方式 A: 使用启动脚本

```bash
# 从项目根目录运行
./start-dev.sh
```

脚本会提示在两个终端中分别运行后端和前端。

#### 方式 B: 手动启动

**终端 1 - 后端**:
```bash
cd /Users/nature/个人项目/Towow/towow
source venv/bin/activate
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 - 前端**:
```bash
cd /Users/nature/个人项目/Towow/towow-frontend
npm run dev
```

### 2.3 环境变量配置

复制 `.env.example` 到 `.env` 并配置：

```bash
# towow/.env

# ============ Application ============
APP_ENV=development
DEBUG=true
APP_PORT=8000

# ============ CORS ============
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# ============ Database ============
POSTGRES_USER=towow
POSTGRES_PASSWORD=password
POSTGRES_DB=towow
POSTGRES_PORT=5432
DATABASE_URL=postgresql://towow:password@localhost:5432/towow

# ============ LLM Providers ============
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_BASE_URL=https://api.anthropic.com  # 可选，支持代理

# ============ Admin API ============
ADMIN_API_KEY=your-secret-admin-key-here

# ============ Rate Limiting ============
ENABLE_RATE_LIMIT=false
RATE_LIMIT_MAX_CONCURRENT=100
RATE_LIMIT_USER_MAX=5

# ============ Negotiation Configuration ============
TOWOW_MAX_NEGOTIATION_ROUNDS=3
TOWOW_RESPONSE_TIMEOUT=300
TOWOW_FEEDBACK_TIMEOUT=120

# ============ OpenAgent (可选) ============
OPENAGENT_HOST=localhost
OPENAGENT_HTTP_PORT=8700
OPENAGENT_GRPC_PORT=8600
```

### 2.4 依赖安装

**后端依赖**:
```bash
cd towow
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**前端依赖**:
```bash
cd towow-frontend
npm install
```

### 2.5 访问地址

| 服务 | URL |
|------|-----|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

---

## 3. Docker 部署

### 3.1 项目 Dockerfile

**后端 Dockerfile** (`towow/Dockerfile`):

```dockerfile
# ToWow API Dockerfile
# Multi-stage build for smaller image size

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir asyncpg

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**前端 Dockerfile** (`towow-frontend/Dockerfile`) - 需创建:

```dockerfile
# ToWow Frontend Dockerfile
# Multi-stage build

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the production bundle
RUN npm run build

# Production stage - serve with nginx
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

### 3.2 Docker Compose 完整配置

创建 `docker-compose.prod.yml`:

```yaml
# ToWow Production Docker Compose
version: '3.8'

services:
  # Frontend (Nginx)
  frontend:
    build:
      context: ./towow-frontend
      dockerfile: Dockerfile
    container_name: towow-frontend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - towow-network

  # FastAPI Backend
  api:
    build:
      context: ./towow
      dockerfile: Dockerfile
    container_name: towow-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-towow}:${POSTGRES_PASSWORD:-password}@db:5432/${POSTGRES_DB:-towow}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-}
      - APP_ENV=production
      - DEBUG=false
      - CORS_ORIGINS=${CORS_ORIGINS:-https://your-domain.com}
      - ADMIN_API_KEY=${ADMIN_API_KEY}
      - ENABLE_RATE_LIMIT=true
      - RATE_LIMIT_MAX_CONCURRENT=${RATE_LIMIT_MAX_CONCURRENT:-100}
      - RATE_LIMIT_USER_MAX=${RATE_LIMIT_USER_MAX:-5}
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - towow-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    container_name: towow-db
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-towow}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
      - POSTGRES_DB=${POSTGRES_DB:-towow}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./towow/scripts/init_sql:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - towow-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-towow} -d ${POSTGRES_DB:-towow}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  # OpenAgent (可选 - 用于 OpenAgent 分支)
  openagent:
    build:
      context: ./openagents
      dockerfile: Dockerfile
    container_name: openagents-network
    ports:
      - "8700:8700"
      - "8600:8600"
    environment:
      - PYTHONUNBUFFERED=1
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - openagents_data:/app/data
    restart: unless-stopped
    networks:
      - towow-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8700/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    profiles:
      - openagent  # 只在指定 profile 时启动

networks:
  towow-network:
    driver: bridge

volumes:
  postgres_data:
    driver: local
  openagents_data:
    driver: local
```

### 3.3 镜像构建和推送

```bash
# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 推送到 Docker Registry (需要先登录)
docker tag towow-api:latest your-registry.com/towow-api:latest
docker tag towow-frontend:latest your-registry.com/towow-frontend:latest

docker push your-registry.com/towow-api:latest
docker push your-registry.com/towow-frontend:latest

# 或使用 GitHub Container Registry
docker tag towow-api:latest ghcr.io/your-org/towow-api:latest
docker push ghcr.io/your-org/towow-api:latest
```

### 3.4 启动服务

```bash
# 基础服务（不含 OpenAgent）
docker-compose -f docker-compose.prod.yml up -d

# 包含 OpenAgent
docker-compose -f docker-compose.prod.yml --profile openagent up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 停止服务
docker-compose -f docker-compose.prod.yml down
```

---

## 4. 云服务器部署

### 4.1 推荐配置

| 环境 | CPU | 内存 | 存储 | 带宽 |
|------|-----|------|------|------|
| **开发/测试** | 2 核 | 4 GB | 40 GB SSD | 5 Mbps |
| **生产（小规模）** | 4 核 | 8 GB | 100 GB SSD | 10 Mbps |
| **生产（中规模）** | 8 核 | 16 GB | 200 GB SSD | 20 Mbps |

**推荐云服务商**：
- 阿里云 ECS
- 腾讯云 CVM
- AWS EC2
- DigitalOcean Droplet

### 4.2 Nginx 反向代理配置

创建 `nginx/nginx.conf`:

```nginx
# Nginx 配置文件
upstream api_backend {
    server api:8000;
    keepalive 32;
}

# HTTP - 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Let's Encrypt 验证
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL 证书
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;

        # 缓存控制
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket / SSE 支持
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # SSE 特殊配置
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://api_backend/health;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # 健康检查 (前端)
    location = /health-fe {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

### 4.3 SSL 证书配置

**使用 Let's Encrypt (推荐)**:

```bash
# 安装 certbot
apt-get update
apt-get install certbot python3-certbot-nginx

# 获取证书
certbot --nginx -d your-domain.com -d www.your-domain.com

# 自动续期（添加到 crontab）
0 0 1 * * /usr/bin/certbot renew --quiet
```

**使用 Docker + Certbot**:

```yaml
# 在 docker-compose.prod.yml 中添加
  certbot:
    image: certbot/certbot
    container_name: certbot
    volumes:
      - ./nginx/ssl:/etc/letsencrypt
      - ./nginx/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

### 4.4 进程管理

#### 方式 A: 使用 Docker Compose (推荐)

Docker Compose 自带重启策略，配置 `restart: unless-stopped` 即可。

#### 方式 B: 使用 Supervisor (不用 Docker 时)

创建 `/etc/supervisor/conf.d/towow.conf`:

```ini
[program:towow-api]
command=/home/appuser/towow/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/home/appuser/towow
user=appuser
autostart=true
autorestart=true
stderr_logfile=/var/log/towow/api.err.log
stdout_logfile=/var/log/towow/api.out.log
environment=
    APP_ENV="production",
    DATABASE_URL="postgresql://...",
    ANTHROPIC_API_KEY="..."

[program:towow-frontend]
command=/usr/bin/npm run preview
directory=/home/appuser/towow-frontend
user=appuser
autostart=true
autorestart=true
stderr_logfile=/var/log/towow/frontend.err.log
stdout_logfile=/var/log/towow/frontend.out.log
```

```bash
# 启动
supervisorctl reread
supervisorctl update
supervisorctl start towow-api
supervisorctl start towow-frontend
```

#### 方式 C: 使用 PM2 (Node.js 生态)

```bash
# 安装 PM2
npm install -g pm2

# 启动后端 (通过 shell 脚本)
pm2 start "cd /home/appuser/towow && source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4" --name towow-api

# 启动前端
pm2 start "cd /home/appuser/towow-frontend && npm run preview" --name towow-frontend

# 保存配置
pm2 save
pm2 startup
```

---

## 5. 动态更新能力

### 5.1 零停机部署策略

#### Blue-Green 部署

```bash
# 创建 docker-compose.blue-green.yml
version: '3.8'

services:
  api-blue:
    build: ./towow
    container_name: towow-api-blue
    # ... 配置

  api-green:
    build: ./towow
    container_name: towow-api-green
    # ... 配置
```

```bash
# 部署新版本到 green
docker-compose -f docker-compose.blue-green.yml up -d api-green

# 健康检查通过后，切换 nginx upstream
# 修改 nginx.conf: upstream -> api-green

# 停止旧版本
docker-compose -f docker-compose.blue-green.yml stop api-blue
```

#### Rolling Update (Docker Swarm / K8s)

```bash
# Docker Swarm 模式
docker service update --image your-registry.com/towow-api:new-tag towow-api
```

### 5.2 配置热加载

#### 环境变量动态更新

ToWow 支持以下配置的运行时更新（无需重启）：

| 配置项 | 更新方式 | 说明 |
|--------|----------|------|
| `CORS_ORIGINS` | Admin API | 通过 `/admin/config` 更新 |
| `ENABLE_RATE_LIMIT` | Admin API | 启用/禁用限流 |
| `RATE_LIMIT_*` | Admin API | 调整限流参数 |

**通过 Admin API 更新配置**:

```bash
# 更新 CORS 配置
curl -X POST http://localhost:8000/admin/config \
  -H "X-Admin-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"cors_origins": ["https://new-domain.com"]}'
```

#### 使用配置文件 + inotify

对于需要重启才能生效的配置，可以使用文件监控：

```bash
# 使用 watchdog 监控配置文件变化
pip install watchdog

# 配置变化时自动重启
watchmedo auto-restart \
  --directory=./config \
  --pattern="*.yaml;*.json" \
  --recursive \
  -- uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 5.3 代码热更新

#### 开发环境

```bash
# uvicorn --reload 模式（仅开发）
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 生产环境替代方案

**Gunicorn + Uvicorn Workers**:

```bash
# gunicorn 支持 graceful reload
gunicorn api.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --graceful-timeout 30

# 优雅重载（不中断连接）
kill -HUP $(cat /var/run/gunicorn.pid)
```

**Docker Compose 滚动更新**:

```bash
# 使用 docker-compose up 的 --force-recreate
docker-compose -f docker-compose.prod.yml up -d --force-recreate --no-deps api
```

---

## 6. 两条分支的部署差异

### 6.1 分支对比

| 特性 | 本地实现分支 (fix/local-e2e) | OpenAgent 分支 (feature/openagent-migration) |
|------|------------------------------|---------------------------------------------|
| Agent 运行位置 | 同一进程内存 | 可分布式（gRPC） |
| 服务组件 | API + DB | API + DB + OpenAgent |
| 部署复杂度 | 低 | 中 |
| 网络要求 | 无特殊要求 | 需要 gRPC 端口 |
| 适用场景 | MVP 演示、小规模 | 跨网络协作、大规模 |

### 6.2 本地实现分支部署流程

```bash
# 1. 切换分支
git checkout fix/local-e2e

# 2. Docker 部署（不含 OpenAgent）
docker-compose -f docker-compose.prod.yml up -d

# 3. 验证
curl http://localhost:8000/health
```

**关键配置**:
- 不需要 `OPENAGENT_*` 环境变量
- Agent 通信通过内存队列
- 无需 8600/8700 端口

### 6.3 OpenAgent 分支部署流程

```bash
# 1. 切换分支
git checkout feature/openagent-migration

# 2. Docker 部署（含 OpenAgent）
docker-compose -f docker-compose.prod.yml --profile openagent up -d

# 3. 验证
curl http://localhost:8000/health
curl http://localhost:8700/api/health
```

**关键配置**:
```bash
# .env
OPENAGENT_HOST=openagent  # Docker 网络中的服务名
OPENAGENT_HTTP_PORT=8700
OPENAGENT_GRPC_PORT=8600
```

### 6.4 分支切换指南

#### 从本地分支切换到 OpenAgent 分支

```bash
# 1. 停止当前服务
docker-compose -f docker-compose.prod.yml down

# 2. 切换分支
git checkout feature/openagent-migration

# 3. 更新 .env
echo "OPENAGENT_HOST=openagent" >> .env
echo "OPENAGENT_HTTP_PORT=8700" >> .env
echo "OPENAGENT_GRPC_PORT=8600" >> .env

# 4. 重新构建并启动
docker-compose -f docker-compose.prod.yml --profile openagent up -d --build
```

#### 从 OpenAgent 分支切换回本地分支

```bash
# 1. 停止所有服务
docker-compose -f docker-compose.prod.yml --profile openagent down

# 2. 切换分支
git checkout fix/local-e2e

# 3. 启动（不含 OpenAgent）
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 7. 监控与日志

### 7.1 日志收集配置

#### Docker Logging Driver

```yaml
# docker-compose.prod.yml 中配置
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
```

#### 集中式日志（ELK / Loki）

```yaml
# 使用 Loki
services:
  api:
    logging:
      driver: loki
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        loki-batch-size: "400"
        loki-retries: "3"
```

### 7.2 健康检查端点

ToWow 提供以下健康检查端点：

| 端点 | 类型 | 用途 |
|------|------|------|
| `GET /health` | Liveness | 服务是否存活 |
| `GET /health/ready` | Readiness | 服务是否就绪（含 DB 检查） |

**响应示例**:

```json
// GET /health
{"status": "healthy"}

// GET /health/ready
{
  "status": "ready",
  "checks": {
    "database": "healthy"
  }
}
```

### 7.3 监控指标

#### 推荐监控项

| 指标 | 来源 | 告警阈值 |
|------|------|----------|
| `http_requests_total` | FastAPI | - |
| `http_request_duration_seconds` | FastAPI | P95 > 5s |
| `llm_call_success_rate` | 应用日志 | < 90% |
| `circuit_breaker_open` | 应用日志 | > 0 |
| `sse_active_connections` | 应用日志 | > 1000 |
| `negotiation_success_rate` | 应用日志 | < 70% |
| `container_cpu_usage` | Docker | > 80% |
| `container_memory_usage` | Docker | > 85% |

#### Prometheus 配置示例

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'towow-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'  # 需要集成 prometheus-fastapi-instrumentator
```

### 7.4 告警配置建议

**关键告警**:

```yaml
# alertmanager rules
groups:
  - name: towow
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "高错误率告警"

      - alert: LLMCircuitBreakerOpen
        expr: circuit_breaker_open > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "LLM 熔断器打开"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 响应延迟过高"
```

---

## 8. CI/CD 流水线

### 8.1 GitHub Actions 配置

创建 `.github/workflows/deploy.yml`:

```yaml
name: Build and Deploy

on:
  push:
    branches:
      - main
      - fix/local-e2e
      - feature/openagent-migration
    tags:
      - 'v*.*.*'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # 测试
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd towow
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Run tests
        run: |
          cd towow
          pytest tests/ -v

  # 构建
  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha,prefix=sha-

      # 构建后端镜像
      - name: Build and push API image
        uses: docker/build-push-action@v5
        with:
          context: ./towow
          file: ./towow/Dockerfile
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-api:${{ steps.meta.outputs.version }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # 构建前端镜像
      - name: Build and push Frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./towow-frontend
          file: ./towow-frontend/Dockerfile
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ steps.meta.outputs.version }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # 部署到 Staging
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'staging'
    environment: staging

    steps:
      - name: Deploy to Staging
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/towow
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d --force-recreate
            docker system prune -f

  # 部署到 Production
  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v') || github.event.inputs.environment == 'production'
    environment: production

    steps:
      - name: Deploy to Production
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/towow

            # Blue-Green 部署
            export DEPLOY_COLOR=$([ "$(docker ps --filter name=api-blue -q)" ] && echo "green" || echo "blue")

            # 拉取新镜像
            docker-compose -f docker-compose.blue-green.yml pull

            # 启动新版本
            docker-compose -f docker-compose.blue-green.yml up -d api-$DEPLOY_COLOR

            # 等待健康检查
            sleep 30
            curl -f http://localhost:8000/health || exit 1

            # 切换流量（更新 nginx 配置）
            sed -i "s/api-blue/api-$DEPLOY_COLOR/g" /etc/nginx/conf.d/towow.conf || \
            sed -i "s/api-green/api-$DEPLOY_COLOR/g" /etc/nginx/conf.d/towow.conf
            nginx -s reload

            # 停止旧版本
            OLD_COLOR=$([ "$DEPLOY_COLOR" = "blue" ] && echo "green" || echo "blue")
            docker-compose -f docker-compose.blue-green.yml stop api-$OLD_COLOR

            # 清理
            docker system prune -f
```

### 8.2 自动化部署触发条件

| 触发条件 | 部署环境 | 说明 |
|----------|----------|------|
| Push to `main` | Staging | 自动部署到测试环境 |
| Push to `fix/local-e2e` | - | 仅构建和测试 |
| Push to `feature/openagent-migration` | - | 仅构建和测试 |
| Tag `v*.*.*` | Production | 自动部署到生产环境 |
| Manual trigger | 可选 | 手动选择环境 |

### 8.3 回滚流程

```bash
# 1. 查看历史版本
docker images | grep towow

# 2. 回滚到指定版本
docker-compose -f docker-compose.prod.yml down
docker tag ghcr.io/your-org/towow-api:v1.0.0 towow-api:latest
docker-compose -f docker-compose.prod.yml up -d

# 3. 或使用 Git Tag 重新部署
git checkout v1.0.0
docker-compose -f docker-compose.prod.yml up -d --build
```

---

## 9. 快速参考

### 9.1 常用命令

```bash
# 本地开发
./start-dev.sh

# Docker 启动（不含 OpenAgent）
docker-compose -f docker-compose.prod.yml up -d

# Docker 启动（含 OpenAgent）
docker-compose -f docker-compose.prod.yml --profile openagent up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f api

# 重启服务
docker-compose -f docker-compose.prod.yml restart api

# 健康检查
curl http://localhost:8000/health
curl http://localhost:8000/health/ready

# 查看配置
docker-compose -f docker-compose.prod.yml config
```

### 9.2 端口清单

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Nginx | HTTP（重定向到 HTTPS） |
| 443 | Nginx | HTTPS |
| 5173 | Frontend (dev) | Vite 开发服务器 |
| 8000 | Backend API | FastAPI |
| 5432 | PostgreSQL | 数据库 |
| 8600 | OpenAgent | gRPC 端口 |
| 8700 | OpenAgent | HTTP 端口 |

### 9.3 环境变量完整清单

| 变量名 | 默认值 | 必填 | 说明 |
|--------|--------|------|------|
| `APP_ENV` | `development` | N | 环境标识 |
| `DEBUG` | `true` | N | 调试模式 |
| `APP_PORT` | `8000` | N | API 端口 |
| `DATABASE_URL` | - | Y | PostgreSQL 连接串 |
| `ANTHROPIC_API_KEY` | - | Y | Claude API Key |
| `ANTHROPIC_BASE_URL` | - | N | Claude API 代理地址 |
| `CORS_ORIGINS` | `localhost` | N | 允许的 CORS 源 |
| `ADMIN_API_KEY` | - | Y | Admin API 密钥 |
| `ENABLE_RATE_LIMIT` | `false` | N | 启用限流 |
| `OPENAGENT_HOST` | `localhost` | N | OpenAgent 主机 |
| `OPENAGENT_HTTP_PORT` | `8700` | N | OpenAgent HTTP 端口 |
| `OPENAGENT_GRPC_PORT` | `8600` | N | OpenAgent gRPC 端口 |

---

## 10. 变更记录

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-01-22 | Claude | 初版，覆盖完整部署配置 |
