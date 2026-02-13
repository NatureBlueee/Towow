"""Towow MCP Server — 5 tools for interacting with the Towow network."""

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from .client import TowowClient
from .config import get_agent_id, save_agent, save_last_negotiation, get_last_negotiation_id

mcp = FastMCP("towow")


def _get_client() -> TowowClient:
    return TowowClient()


@mcp.tool()
async def towow_scenes() -> str:
    """列出通爻网络中的所有场景。返回每个场景的 ID、名称、描述和 Agent 数量。"""
    client = _get_client()
    try:
        scenes = await client.get_scenes()
    finally:
        await client.close()

    if not scenes:
        return "当前没有可用的场景。"

    lines = [f"通爻网络共 {len(scenes)} 个场景：\n"]
    for s in scenes:
        agent_count = s.get("agent_count", 0)
        lines.append(
            f"- **{s.get('name', s['scene_id'])}** (`{s['scene_id']}`)"
            f" — {s.get('description', '无描述')}"
            f" · {agent_count} 个 Agent"
        )
    return "\n".join(lines)


@mcp.tool()
async def towow_agents(scope: str = "all") -> str:
    """列出通爻网络中的 Agent。

    Args:
        scope: 过滤范围，如 "all"（全部）或 "scene:hackathon"（指定场景）。
    """
    client = _get_client()
    try:
        agents = await client.get_agents(scope)
    finally:
        await client.close()

    if not agents:
        return f"范围 `{scope}` 下没有 Agent。"

    lines = [f"共 {len(agents)} 个 Agent（scope: {scope}）：\n"]
    for a in agents[:30]:  # Cap display at 30
        bio = a.get("bio", "")
        bio_preview = (bio[:60] + "...") if len(bio) > 60 else bio
        source = a.get("source", "")
        lines.append(
            f"- **{a.get('display_name', a['agent_id'])}**"
            f" ({source})"
            f"{f' — {bio_preview}' if bio_preview else ''}"
        )
    if len(agents) > 30:
        lines.append(f"\n... 还有 {len(agents) - 30} 个 Agent")
    return "\n".join(lines)


@mcp.tool()
async def towow_join(email: str, display_name: str, raw_text: str, scene_id: str = "") -> str:
    """加入通爻网络。注册后你的 Agent 会出现在网络中，可以参与协商。

    Args:
        email: 你的邮箱地址。
        display_name: 你想在网络中显示的名字。
        raw_text: 关于你的介绍——简历、技能、兴趣，任何能代表你的文字。越具体，共振越精准。
        scene_id: 想加入的场景 ID（可选，留空则加入全部场景）。
    """
    client = _get_client()
    try:
        result = await client.quick_register(email, display_name, raw_text, scene_id)
    finally:
        await client.close()

    agent_id = result.get("agent_id", "")
    name = result.get("display_name", display_name)

    if agent_id:
        save_agent(agent_id, name)

    return (
        f"加入成功！\n\n"
        f"- Agent ID: `{agent_id}`\n"
        f"- 名字: {name}\n"
        f"- {result.get('message', '')}\n\n"
        f"你的身份已保存到本地配置。现在可以使用 `towow_demand` 提交需求了。"
    )


@mcp.tool()
async def towow_demand(intent: str, scope: str = "all") -> str:
    """向通爻网络提交需求，发起协商。网络中的 Agent 会通过共振响应你的需求。

    需要先使用 towow_join 注册。

    Args:
        intent: 你的需求描述（自然语言）。
        scope: 协商范围，如 "all"（全网络）或 "scene:hackathon"（指定场景）。
    """
    agent_id = get_agent_id()
    if not agent_id:
        return (
            "你还没有加入通爻网络。请先使用 `towow_join` 注册。\n\n"
            "示例：towow_join(email='you@example.com', display_name='你的名字', "
            "raw_text='你的自我介绍...')"
        )

    client = _get_client()
    try:
        # Submit the demand
        result = await client.negotiate(intent, scope, agent_id)
        negotiation_id = result.get("negotiation_id", "")

        if not negotiation_id:
            return f"提交失败：{json.dumps(result, ensure_ascii=False)}"

        save_last_negotiation(negotiation_id)

        # Poll for completion (3s interval, max 120s)
        status = result.get("state", "pending")
        progress_lines = [
            f"协商已发起 (`{negotiation_id}`)\n",
            f"初始状态: {status}",
        ]

        for _ in range(40):  # 40 * 3s = 120s max
            if status in ("completed", "failed"):
                break
            await asyncio.sleep(3)
            try:
                poll = await client.get_negotiation(negotiation_id)
            except Exception:
                continue  # Transient error — retry on next iteration
            new_status = poll.get("state", status)
            if new_status != status:
                status = new_status
                progress_lines.append(f"状态更新: {status}")
            if status in ("completed", "failed"):
                result = poll
                break

        # Format final result
        if status == "completed":
            plan = result.get("plan_output", "")
            agent_count = result.get("agent_count", 0)
            progress_lines.append(f"\n协商完成！{agent_count} 个 Agent 参与。\n")
            if plan:
                progress_lines.append(f"## 方案\n\n{plan}")
            else:
                plan_json = result.get("plan_json")
                if plan_json:
                    progress_lines.append(
                        f"## 方案\n\n```json\n"
                        f"{json.dumps(plan_json, ensure_ascii=False, indent=2)}\n```"
                    )
                else:
                    progress_lines.append("方案正在生成中，请稍后使用 `towow_status` 查看。")
        elif status == "failed":
            progress_lines.append(f"\n协商失败：{result.get('error', '未知错误')}")
        else:
            progress_lines.append(
                f"\n协商仍在进行中（当前状态: {status}）。"
                f"使用 `towow_status` 查看最新结果。"
            )

        return "\n".join(progress_lines)
    finally:
        await client.close()


@mcp.tool()
async def towow_status(negotiation_id: str = "") -> str:
    """查看协商状态和结果。

    Args:
        negotiation_id: 协商 ID。留空则查看最近一次协商。
    """
    neg_id = negotiation_id or get_last_negotiation_id()
    if not neg_id:
        return "没有找到协商记录。请先使用 `towow_demand` 提交需求。"

    client = _get_client()
    try:
        data = await client.get_negotiation(neg_id)
    finally:
        await client.close()

    status = data.get("state", "unknown")
    agent_count = data.get("agent_count", 0)

    lines = [
        f"## 协商状态\n",
        f"- ID: `{neg_id}`",
        f"- 状态: {status}",
        f"- 参与 Agent: {agent_count}",
    ]

    if data.get("demand_text"):
        lines.append(f"- 需求: {data['demand_text'][:100]}")

    if status == "completed":
        plan = data.get("plan_output", "")
        if plan:
            lines.append(f"\n## 方案\n\n{plan}")
        else:
            plan_json = data.get("plan_json")
            if plan_json:
                lines.append(
                    f"\n## 方案\n\n```json\n"
                    f"{json.dumps(plan_json, ensure_ascii=False, indent=2)}\n```"
                )
    elif status == "failed":
        lines.append(f"\n协商失败：{data.get('error', '未知错误')}")

    return "\n".join(lines)


def main():
    """Entry point for the towow-mcp command."""
    mcp.run()


if __name__ == "__main__":
    main()
