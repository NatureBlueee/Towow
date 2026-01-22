# ToWow 项目启动与测试指南

> 完整的开发环境配置、启动和测试流程

---

## 📋 目录

- [项目概览](#项目概览)
- [环境准备](#环境准备)
- [后端启动与测试](#后端启动与测试)
- [前端启动与测试](#前端启动与测试)
- [OpenAgents 网络测试](#openagents-网络测试)
- [Docker 部署测试](#docker-部署测试)
- [常见问题](#常见问题)

---

## 项目概览

ToWow 是一个基于 OpenAgents 的 AI Agent 协作平台,包含以下组件:

```
Towow/
├── towow/              # 后端 (FastAPI + PostgreSQL + OpenAgents)
├── towow-frontend/     # 前端 (React + Vite + TypeScript)
└── openagents/         # OpenAgents 框架
```

**技术栈**:
- **后端**: Python 3.10+, FastAPI, PostgreSQL, SQLAlchemy, OpenAgents
- **前端**: React 19, TypeScript, Vite, Ant Design, TailwindCSS
- **AI**: Anthropic Claude API

---

## 环境准备

### 1. 系统要求

- **Python**: 3.10 或更高版本
- **Node.js**: 18.0 或更高版本
- **PostgreSQL**: 14 或更高版本 (可选,可使用 Docker)
- **Git**: 最新版本

### 2. 检查环境

```bash
# 检查 Python 版本
python3 --version

# 检查 Node.js 和 npm 版本
node --version
npm --version

# 检查 PostgreSQL (如果本地安装)
psql --version

# 检查 Docker (可选)
docker --version
docker-compose --version
```

### 3. 克隆项目 (如果还未克隆)

```bash
cd /Users/nature/个人项目
git clone <repository-url> Towow
cd Towow
```

---

## 后端启动与测试

### 方法一: 本地开发环境 (推荐用于开发)

#### 1. 创建虚拟环境

```bash
cd /Users/nature/个人项目/Towow/towow

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

#### 2. 安装依赖

```bash
# 安装生产依赖
pip install -r requirements.txt

# 安装开发依赖 (包含测试工具)
pip install -r requirements-dev.txt
```

#### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

**必须配置的环境变量**:
```bash
# 应用配置
APP_ENV=development
DEBUG=true
APP_PORT=8000

# 数据库配置 (如果使用本地 PostgreSQL)
DATABASE_URL=postgresql://towow:password@localhost:5432/towow

# LLM API Key
ANTHROPIC_API_KEY=your_actual_api_key_here

# OpenAgent 配置
OPENAGENT_HOST=localhost
OPENAGENT_HTTP_PORT=8700
OPENAGENT_GRPC_PORT=8600
```

#### 4. 设置数据库

**选项 A: 使用本地 PostgreSQL**

```bash
# 创建数据库
createdb towow

# 或使用 psql
psql -U postgres
CREATE DATABASE towow;
CREATE USER towow WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE towow TO towow;
\q
```

**选项 B: 使用 Docker PostgreSQL**

```bash
# 仅启动数据库服务
docker-compose up -d db

# 查看数据库日志
docker-compose logs -f db
```

#### 5. 运行数据库迁移

```bash
# 确保在 towow 目录下且虚拟环境已激活
cd /Users/nature/个人项目/Towow/towow

# 运行迁移
alembic upgrade head
```

#### 6. 启动后端服务

```bash
# 开发模式 (带热重载)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 或者使用指定的端口
uvicorn api.main:app --reload --port 8000
```

**验证后端启动**:
- 访问 http://localhost:8000
- 访问 http://localhost:8000/docs (FastAPI Swagger 文档)
- 访问 http://localhost:8000/health (健康检查)

#### 7. 运行后端测试

```bash
# 运行所有测试
pytest

# 运行测试并显示覆盖率
pytest --cov=api --cov=services --cov=database

# 运行特定测试文件
pytest tests/test_api.py

# 运行并显示详细输出
pytest -v

# 运行异步测试
pytest -v tests/test_async.py
```

#### 8. 代码质量检查

```bash
# 运行 Ruff 检查代码风格
ruff check .

# 自动修复可修复的问题
ruff check . --fix

# 运行类型检查
mypy .
```

---

### 方法二: Docker 部署 (推荐用于生产环境测试)

#### 1. 配置环境变量

```bash
cd /Users/nature/个人项目/Towow/towow

# 复制并编辑 .env
cp .env.example .env
nano .env
```

#### 2. 启动所有服务

```bash
# 构建并启动所有服务
docker-compose up --build

# 或在后台运行
docker-compose up -d --build
```

#### 3. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f db
```

#### 4. 验证服务

```bash
# 检查服务状态
docker-compose ps

# 测试 API
curl http://localhost:8000/health
```

#### 5. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷 (清空数据库)
docker-compose down -v
```

---

## 前端启动与测试

### 1. 安装依赖

```bash
cd /Users/nature/个人项目/Towow/towow-frontend

# 安装 npm 依赖
npm install
```

### 2. 配置环境变量 (可选)

创建 `.env.local` 文件:

```bash
# 创建环境变量文件
cat > .env.local << EOF
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=ToWow
EOF
```

### 3. 启动开发服务器

```bash
# 启动 Vite 开发服务器
npm run dev
```

**默认访问地址**: http://localhost:5173

### 4. 构建生产版本

```bash
# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

### 5. 代码检查

```bash
# 运行 ESLint
npm run lint
```

### 6. 前端测试 (如果有测试配置)

```bash
# 如果项目配置了测试
npm test

# 或运行特定测试
npm run test:unit
```

---

## OpenAgents 网络测试

### 1. 启动 OpenAgents 网络

```bash
cd /Users/nature/个人项目/Towow/openagents

# 启动网络 (交互式设置)
python3 -m openagents.cli network start

# 或使用已有配置
openagents network start
```

### 2. 查看帮助

```bash
# 查看所有命令
python3 -m openagents.cli --help

# 查看网络命令
python3 -m openagents.cli network --help
```

### 3. 启动示例 Agent

```bash
# 进入示例目录
cd demos/00_hello_world

# 启动网络
openagents network start

# 在另一个终端启动 Agent
openagents agent start agents/charlie.yaml
```

### 4. 验证 OpenAgents 端口

```bash
# 检查端口是否在监听
lsof -i :8700  # HTTP transport
lsof -i :8600  # gRPC transport
lsof -i :8800  # MCP transport
```

---

## 完整的端到端测试流程

### 1. 启动后端

```bash
# 终端 1: 启动后端
cd /Users/nature/个人项目/Towow/towow
source venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

### 2. 启动前端

```bash
# 终端 2: 启动前端
cd /Users/nature/个人项目/Towow/towow-frontend
npm run dev
```

### 3. 启动 OpenAgents (可选)

```bash
# 终端 3: 启动 OpenAgents 网络
cd /Users/nature/个人项目/Towow/openagents
python3 -m openagents.cli network start
```

### 4. 验证所有服务

打开浏览器访问:
- **前端**: http://localhost:5173
- **后端 API**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **OpenAgents HTTP**: http://localhost:8700 (如果启动)

---

## 常见问题

### 1. 数据库连接失败

**问题**: `could not connect to server: Connection refused`

**解决方案**:
```bash
# 检查 PostgreSQL 是否运行
pg_isready

# 或启动 Docker 数据库
docker-compose up -d db

# 检查 .env 中的 DATABASE_URL 是否正确
```

### 2. 端口已被占用

**问题**: `Address already in use`

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000  # 后端端口
lsof -i :5173  # 前端端口

# 杀死进程
kill -9 <PID>

# 或使用不同的端口
uvicorn api.main:app --reload --port 8001
```

### 3. Python 依赖安装失败

**问题**: `pip install` 失败

**解决方案**:
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 单独安装失败的包
pip install <package-name> --no-cache-dir
```

### 4. npm 依赖安装失败

**问题**: `npm install` 失败

**解决方案**:
```bash
# 清除 npm 缓存
npm cache clean --force

# 删除 node_modules 和 package-lock.json
rm -rf node_modules package-lock.json

# 重新安装
npm install

# 或使用 yarn
yarn install
```

### 5. Alembic 迁移失败

**问题**: 数据库迁移错误

**解决方案**:
```bash
# 查看当前迁移状态
alembic current

# 查看迁移历史
alembic history

# 回滚到上一个版本
alembic downgrade -1

# 重新运行迁移
alembic upgrade head

# 如果需要重置数据库
dropdb towow
createdb towow
alembic upgrade head
```

### 6. OpenAgents 启动失败

**问题**: OpenAgents 网络无法启动

**解决方案**:
```bash
# 检查 Python 版本 (需要 3.10+)
python3 --version

# 重新安装 OpenAgents
pip install --upgrade openagents

# 检查端口是否被占用
lsof -i :8700
lsof -i :8600

# 查看详细错误日志
python3 -m openagents.cli network start --log-level DEBUG
```

### 7. API Key 未配置

**问题**: `ANTHROPIC_API_KEY not found`

**解决方案**:
```bash
# 编辑 .env 文件
nano /Users/nature/个人项目/Towow/towow/.env

# 添加你的 API Key
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

# 或临时设置环境变量
export ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

---

## 快速启动脚本

创建一个快速启动脚本 `start_dev.sh`:

```bash
#!/bin/bash

# ToWow 开发环境快速启动脚本

echo "🚀 启动 ToWow 开发环境..."

# 启动后端
echo "📦 启动后端服务..."
cd /Users/nature/个人项目/Towow/towow
source venv/bin/activate
uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端
echo "🎨 启动前端服务..."
cd /Users/nature/个人项目/Towow/towow-frontend
npm run dev &
FRONTEND_PID=$!

echo "✅ 服务已启动!"
echo "   后端: http://localhost:8000"
echo "   前端: http://localhost:5173"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
```

使用方法:
```bash
chmod +x start_dev.sh
./start_dev.sh
```

---

## 测试检查清单

### 后端测试 ✓
- [ ] 数据库连接成功
- [ ] 数据库迁移完成
- [ ] API 服务启动 (http://localhost:8000)
- [ ] Swagger 文档可访问 (/docs)
- [ ] 健康检查通过 (/health)
- [ ] 单元测试通过 (`pytest`)
- [ ] 代码质量检查通过 (`ruff`, `mypy`)

### 前端测试 ✓
- [ ] npm 依赖安装成功
- [ ] 开发服务器启动 (http://localhost:5173)
- [ ] 页面正常加载
- [ ] API 调用成功
- [ ] ESLint 检查通过

### OpenAgents 测试 ✓
- [ ] 网络启动成功
- [ ] HTTP 端口监听 (8700)
- [ ] gRPC 端口监听 (8600)
- [ ] Agent 可以连接网络
- [ ] 事件系统正常工作

### Docker 测试 ✓
- [ ] Docker 镜像构建成功
- [ ] 所有容器启动成功
- [ ] 容器健康检查通过
- [ ] 服务间通信正常
- [ ] 数据持久化正常

---

## 获取帮助

- **项目文档**: 查看 `/docs` 目录
- **OpenAgents 文档**: https://openagents.org/docs/
- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **React 文档**: https://react.dev/

---

**最后更新**: 2026-01-22
**版本**: 1.0.0
