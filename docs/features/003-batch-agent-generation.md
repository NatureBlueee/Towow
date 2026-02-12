# Feature 003: 批量 Agent 画像生成 + 排序优化

**日期**: 2026-02-12
**Commit**: `6b42304`

## 背景

App Store 4 个场景原有各 8 个模板化 Agent，缺乏个性和多样性。用户体验像看假数据。

## 目标

每个场景至少 100 个独特、个性化的 Agent：
- 独特网名（互联网昵称风格，不是真名）
- 口语化 bio（像真人打字，有棱角，不是官方腔）
- 技能/背景高度多样化
- 每批不同风格种子确保风格差异

## 实现

### 1. 生成脚本: `scripts/generate_agents.py`

通过 Anthropic API（Claude Sonnet）批量生成：

- **10 种风格种子**：极客老炮、文艺青年、学生党、跨界人才、海外华人、资深从业者、小众专家、反叛者、LGBTQ+技术人才、非一线实干派
- **每场景 10 批 × 10 个**，5 个 API key 轮巡
- **去重机制**：按 agent_id 去重
- **`--supplement` 模式**：加载已有数据，只补足到 100+，减少浪费
- **温度 1.0**：最大多样性
- **JSON 自修复**：清理 markdown 代码块包裹

### 2. 最终数据

| 场景 | 数量 | 文件 |
|------|------|------|
| hackathon | 118 | `apps/S1_hackathon/data/agents.json` |
| skill_exchange | 107 | `apps/S2_skill_exchange/data/agents.json` |
| recruitment | 114 | `apps/R1_recruitment/data/agents.json` |
| matchmaking | 108 | `apps/M1_matchmaking/data/agents.json` |
| **总计** | **447** | |

### 3. SecondMe 用户优先排序

`apps/app_store/backend/app.py` — `list_agents` 端点新增排序：
```python
agents.sort(key=lambda a: (0 if "secondme" in (a.get("source") or "").lower() else 1))
```

SecondMe 注册的真人用户排在前面，JSON 文件生成的 agent 排后面。

## 质量示例

```
赛博和尚: 打 CTF 打了八年，拿过几次前三...
sudo rm -rf 心动: 白天拆解闭源软件，晚上在暗网电台放后朋克...
量子厨子: 从业20年的专业厨师，后来发现自己更喜欢量子计算...
摸鱼大师: 95后老程序员，18岁开始接外包养活自己...
```

## 失败处理

LLM 偶尔输出非法 JSON（bio 中含未转义引号）。10 批中约 1-2 批失败。
通过 `--supplement` 补充模式弥补缺口。

## 改动文件

| 文件 | 操作 |
|------|------|
| `scripts/generate_agents.py` | **新建** — 批量生成脚本 |
| `apps/*/data/agents.json` × 4 | **重写** — 100+ agents/场景 |
| `apps/app_store/backend/app.py` | **修改** — SecondMe 优先排序 |
