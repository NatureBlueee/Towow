# Issue 007: Agent 数据展示与 SecondMe 用户持久化

**日期**: 2026-02-12
**状态**: 已修复
**Commit**: (本次提交)

## 问题描述

Feature 003 批量生成 447 个 Agent 后，暴露出三个关联问题：

### 问题 1: 前端字段映射断裂 — `tags.map is not a function`

**现象**: AI相亲（matchmaking）场景打开即报错 `TypeError: tags.map is not a function`。

**根因**: 批量生成脚本使用的 agent 数据字段名与前端 `AgentScroll.tsx` 中硬编码的字段名不匹配。

| 场景 | 前端读的字段 | 实际数据字段 |
|------|-------------|-------------|
| matchmaking | `values` (期望数组) | `values` (字符串), `interests` (数组) |
| matchmaking | `personality`, `location` | `occupation` |
| recruitment | `experience_years`, `expected_salary` | `experience`, `salary_range`, `work_style` |
| skill_exchange | `price_range`, `teaching_style` | `style` |

matchmaking 的 `tagSource` 对字符串类型的 `values` 调用 `.slice(0,3)` 得到 3 个字符的字符串，再 `.map()` 就崩了。

### 问题 2: "通向惊喜"永远推荐同一个 Agent（"故障少女"）

**现象**: SecondMe 分身辅助的 system prompt 里，网络参与者列表永远是同一批人。

**根因**: `_build_agent_summaries()` 用 `get_agents_by_scope()[:10]` 取前 10 个 agent。dict 插入顺序固定 → 永远是 JSON 文件中排最前面的那批。几百个 agent 中只有固定的 10 个被 SecondMe 看到。

### 问题 3: SecondMe 用户数据重启后消失

**现象**: ~50 个通过 SecondMe 登录的用户，后端每次重启后全部丢失。只剩 JSON 文件里的 agent。

**根因**: `AgentRegistry._agents` 是纯内存 dict，无持久化。SecondMe 用户的注册信息（profile、scene_ids）、access_token、向量编码全部在进程内存中。后端重启 = 全部清零。

## 修复方案

### 问题 1 修复: 字段映射对齐

`website/components/store/AgentScroll.tsx` — 按实际数据 schema 更新 `SCENE_DISPLAY` 配置：

- **matchmaking**: `tagSource` 改为读 `interests` 数组（`Array.isArray` 防御），`highlight` 用 `occupation`
- **recruitment**: `highlight` 改为 `experience` / `salary_range` / `work_style`
- **skill_exchange**: `highlight` 改为 `availability` / `style`

### 问题 2 修复: 随机抽样

`apps/app_store/backend/routers.py` — `_build_agent_summaries()`:

```python
# 之前: 固定取前 10 个
agent_ids = composite.get_agents_by_scope(scope)[:max_agents]

# 之后: 随机抽 5 个
all_ids = composite.get_agents_by_scope(scope)
agent_ids = random.sample(all_ids, min(max_agents, len(all_ids)))
```

每次调用随机抽取，SecondMe 每次看到不同的网络参与者。`max_agents` 从 10 降到 5（够提供上下文，不撑 token）。

### 问题 3 修复: 每人一个 JSON 文件

**写入**（`backend/routers/auth.py`）:
- 新增 `_persist_secondme_user()`：登录时写 `data/secondme_users/{agent_id}.json`
- 重复登录 → 覆盖更新
- 写入失败不阻断登录（try/except 包裹）

**恢复**（`backend/server.py`）:
- 新增 `_restore_secondme_users()`：启动时扫描 `data/secondme_users/*.json`，注册回 AgentRegistry
- token 不持久化 → 画像可见但需重新登录才能 chat

**adapter=None 防御**（`backend/towow/infra/agent_registry.py`）:
- `AgentEntry.adapter` 和 `register_agent()` 改为 `Optional`
- `get_profile()`: adapter=None 时直接返回 `profile_data`
- `chat()` / `chat_stream()`: adapter=None 时抛 `AdapterError("会话已过期")`

## 教训

1. **LLM 生成的数据 schema 是隐性契约** — prompt 定义了字段名，前端依赖字段名，但中间没有共享的 schema 定义。改了 prompt 不会有编译报错，必须人工验证消费端对齐。

2. **固定排序 + 截断 = 永远同一批** — `dict[:N]` 在确定性排序下是陷阱。涉及"展示多样性"的场景必须引入随机性。

3. **纯内存状态 = 重启归零** — 只要数据重要到用户会注意到丢失，就必须持久化。最简方案（JSON 文件）足以应对小规模场景。

## 改动文件

| 文件 | 操作 |
|------|------|
| `website/components/store/AgentScroll.tsx` | **修改** — 4 个场景字段映射对齐 |
| `apps/app_store/backend/routers.py` | **修改** — random.sample + max_agents=5 |
| `backend/routers/auth.py` | **修改** — 新增持久化函数 |
| `backend/server.py` | **修改** — 新增启动恢复函数 |
| `backend/towow/infra/agent_registry.py` | **修改** — adapter Optional + null checks |
