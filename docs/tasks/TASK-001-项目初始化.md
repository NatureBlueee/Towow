# TASK-001：项目初始化

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-001 |
| 所属Phase | Phase 1：基础框架 |
| 依赖 | 无 |
| 预估工作量 | 0.5天 |
| 状态 | 待开始 |

---

## 任务描述

初始化ToWow项目结构，配置开发环境和依赖。

---

## 具体工作

### 1. 创建项目目录结构

```
towow/
├── openagents/              # OpenAgent相关代码
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py          # 基础Agent类
│   │   ├── coordinator.py
│   │   ├── channel_admin.py
│   │   └── user_agent.py
│   └── config.py
├── api/                     # FastAPI后端
│   ├── __init__.py
│   ├── main.py
│   ├── routers/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
├── database/
│   ├── __init__.py
│   ├── models.py
│   ├── connection.py
│   └── migrations/
├── prompts/                 # 提示词存储
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   └── conftest.py
├── scripts/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── README.md
```

### 2. 配置requirements.txt

```
# Core
openagents>=0.1.0
fastapi>=0.100.0
uvicorn>=0.23.0

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.12.0

# HTTP Client
aiohttp>=3.8.0
httpx>=0.25.0

# LLM
anthropic>=0.20.0

# Utils
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
```

### 3. 配置.env.example

```
# OpenAgent
OPENAGENT_HOST=localhost
OPENAGENT_HTTP_PORT=8700
OPENAGENT_GRPC_PORT=8600

# Database
DATABASE_URL=postgresql://towow:password@localhost:5432/towow

# LLM
ANTHROPIC_API_KEY=your_api_key_here

# App
APP_ENV=development
DEBUG=true
```

### 4. 配置pyproject.toml

```toml
[project]
name = "towow"
version = "0.1.0"
description = "ToWow - AI Agent Collaboration Network"
requires-python = ">=3.10"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py310"
```

---

## 验收标准

- [ ] 目录结构创建完成
- [ ] 所有配置文件就位
- [ ] `pip install -r requirements.txt` 成功
- [ ] Python import 不报错

---

## 产出物

- 完整的项目目录结构
- 配置文件（requirements.txt, .env.example, pyproject.toml）
- 基础的README.md

---

**创建时间**: 2026-01-21

> Beads 任务ID：`towow-9do`
