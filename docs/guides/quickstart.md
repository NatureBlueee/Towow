# 快速上手 (Quickstart)

5 分钟跑通本地开发环境。

## 前置条件

- Python 3.11+
- Node.js 18+
- npm

## 1. 后端

```bash
cd backend

# 创建虚拟环境（首次）
python -m venv venv

# 激活
source venv/bin/activate

# 安装依赖（首次）
pip install -r requirements.txt

# 配置环境变量
# 复制 .env.example 或手动创建 .env:
#   TOWOW_ANTHROPIC_API_KEY=sk-ant-...  (必需，V1 Engine + V2 多视角查询)

# 启动
uvicorn server:app --reload --port 8080
```

后端启动后：
- `http://localhost:8080/health` — 健康检查
- `http://localhost:8080/field/api/stats` — V2 Field 状态
- `http://localhost:8080/store/` — App Store 面板

## 2. 前端

```bash
cd website
npm install    # 首次
npm run dev    # 启动 (port 3000)
```

前端启动后：
- `http://localhost:3000/field` — V2 Field 体验页
- `http://localhost:3000/playground` — V1 开放注册 + 协商

## 3. 测试

```bash
cd backend
source venv/bin/activate
python -m pytest tests/towow/ -v    # 332 tests
```

## 4. V2 Field 体验流程

1. 打开 `http://localhost:3000/field`
2. 点击「加载示例数据」— 批量导入 Agent Profile
3. 切到 Match 标签 — 输入查询（如"Rust 后端开发"）
4. 切到 Match Owners — 看到 Owner 级聚合结果
5. 切到 Multi-Perspective — 看到共振/互补/干涉三区展示

## 5. 目录结构速览

```
backend/towow/core/    — V1 协商引擎 (协议层)
backend/towow/field/   — V2 意图场 (编码、匹配、多视角)
website/app/field/     — V2 前端体验页
website/app/playground/— V1 前端 Playground
docs/                  — 架构、设计日志、决策记录
```

详见 [README.md](../../README.md) 和 [CLAUDE.md](../../CLAUDE.md)。
