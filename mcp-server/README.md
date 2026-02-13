# towow-mcp

通爻网络 MCP Server — 在 Claude Code / Cursor 中连接通爻网络。

## 安装

```bash
pip install -e ./mcp-server
```

## 配置

### Claude Code

在项目根目录的 `.claude/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "towow": {
      "command": "towow-mcp",
      "args": []
    }
  }
}
```

### Cursor

在 `.cursor/mcp.json` 中添加相同配置。

### 自定义后端地址

默认连接生产环境。如需指向本地开发服务器：

```bash
export TOWOW_BACKEND_URL=http://localhost:8080
```

## 工具

| 工具 | 说明 |
|------|------|
| `towow_scenes` | 列出网络中的所有场景 |
| `towow_agents` | 列出指定范围的 Agent |
| `towow_join` | 加入通爻网络（注册 Agent） |
| `towow_demand` | 提交需求，发起协商 |
| `towow_status` | 查看协商状态和结果 |

## 快速上手

在 Claude Code 中：

**第一步：加入网络**

> "帮我加入通爻网络，我叫张三，邮箱 z@example.com，我是全栈工程师，擅长 Python 和 React"

**第二步：提交需求**

> "我想组一个 hackathon 团队，需要一个前端和一个设计师"

**第三步：查看结果**

> "看看协商结果"

## 本地配置

首次 `towow_join` 后，身份信息保存在 `~/.towow/config.json`：

```json
{
  "agent_id": "pg_xxxxxxxx",
  "display_name": "你的名字",
  "backend_url": "https://towow-production.up.railway.app"
}
```
