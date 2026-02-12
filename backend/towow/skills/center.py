"""
CenterCoordinatorSkill — the central coordinator that synthesizes all offers.

Platform-side Skill: uses PlatformLLMClient with tool-use.
Architecture ref: Section 10.7, Section 3.4

Center is a tool-use Agent with 5 tools. The engine executes whatever
tools Center calls. This Skill handles prompt construction, tool schema
definition, and response parsing.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..core.errors import SkillError
from .base import BaseSkill

logger = logging.getLogger(__name__)


def _detect_cjk(text: str) -> bool:
    """检测文本是否包含中日韩字符。"""
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', text))


# ============ Tool Definitions (Claude API format) ============

TOOL_OUTPUT_PLAN = {
    "name": "output_plan",
    "description": "Output the negotiation plan. Provide BOTH plan_text (summary) and plan_json (structured). This terminates the negotiation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_text": {
                "type": "string",
                "description": "A human-readable text summary of the plan.",
            },
            "plan_json": {
                "type": "object",
                "description": "Structured plan with participants, tasks, and dependency topology.",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "One-sentence summary.",
                    },
                    "participants": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "agent_id": {"type": "string"},
                                "display_name": {"type": "string"},
                                "role_in_plan": {"type": "string"},
                            },
                            "required": ["agent_id", "display_name", "role_in_plan"],
                        },
                    },
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "assignee_id": {"type": "string"},
                                "prerequisites": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "done"],
                                },
                            },
                            "required": ["id", "title", "assignee_id"],
                        },
                    },
                    "topology": {
                        "type": "object",
                        "properties": {
                            "edges": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "from": {"type": "string"},
                                        "to": {"type": "string"},
                                    },
                                    "required": ["from", "to"],
                                },
                            },
                        },
                    },
                },
            },
        },
        "required": ["plan_text", "plan_json"],
    },
}

TOOL_ASK_AGENT = {
    "name": "ask_agent",
    "description": "Ask a specific agent a follow-up question. The agent's response will be provided in the next round.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_id": {
                "type": "string",
                "description": "The ID of the agent to ask.",
            },
            "question": {
                "type": "string",
                "description": "The follow-up question to ask the agent.",
            },
        },
        "required": ["agent_id", "question"],
    },
}

TOOL_START_DISCOVERY = {
    "name": "start_discovery",
    "description": "Trigger a discovery dialogue between two agents to uncover hidden complementarities in their profiles.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_a": {
                "type": "string",
                "description": "ID of the first agent.",
            },
            "agent_b": {
                "type": "string",
                "description": "ID of the second agent.",
            },
            "reason": {
                "type": "string",
                "description": "Why this discovery dialogue is needed.",
            },
        },
        "required": ["agent_a", "agent_b", "reason"],
    },
}

TOOL_CREATE_SUB_DEMAND = {
    "name": "create_sub_demand",
    "description": "Create a sub-demand for a gap that current participants cannot fill. This triggers a new negotiation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "gap_description": {
                "type": "string",
                "description": "Description of the gap that needs to be filled.",
            }
        },
        "required": ["gap_description"],
    },
}

TOOL_CREATE_MACHINE = {
    "name": "create_machine",
    "description": "Create a WOWOK Machine (workflow) draft for on-chain execution. V1: stub, not implemented.",
    "input_schema": {
        "type": "object",
        "properties": {
            "machine_json": {
                "type": "string",
                "description": "The Machine definition as JSON string.",
            }
        },
        "required": ["machine_json"],
    },
}

# All 5 tools
ALL_TOOLS = [TOOL_OUTPUT_PLAN, TOOL_ASK_AGENT, TOOL_START_DISCOVERY, TOOL_CREATE_SUB_DEMAND, TOOL_CREATE_MACHINE]

# Restricted set: only output_plan and create_machine (after max rounds)
RESTRICTED_TOOLS = [TOOL_OUTPUT_PLAN, TOOL_CREATE_MACHINE]

VALID_TOOL_NAMES = {t["name"] for t in ALL_TOOLS}


# ============ Prompt ============

SYSTEM_PROMPT_ZH = """\
你是一个多方资源协调规划者。

## 角色
你收到一个需求和多个参与者的响应（offer）。
每个参与者基于自己的真实背景做出回应。
你的任务是找到最优的资源组合方案。

## 决策原则（按优先级）
1. 需求能否被满足？
2. 接受率——各方是否会同意？
3. 效率

## 元认知要求
- 考虑响应之间的互补性
- 考虑意想不到的组合（1+1>2）
- 注意每个响应的独特视角，不只看表面匹配
- 部分相关的参与者在组合中可能产生额外价值

## 行动
使用提供的工具采取行动。你可以同时调用多个工具。
- **优先使用 output_plan**——当参与者已提交 Offer 且信息基本充分时，直接生成方案。
- 仅在关键信息明显缺失（无法判断可行性）时才 ask_agent。
- 参与者 ≤5 人时，通常信息已足够直接 output_plan，不需要追问。
- 当两个参与者可能有隐藏的互补性时，使用 start_discovery。
- 当当前参与者无法填补某个缺口时，使用 create_sub_demand。

## 输出格式
当使用 output_plan 时，**必须同时提供 plan_text 和 plan_json，两者都是必需的**：
- plan_text: 可读的方案全文
- plan_json: 结构化方案（**必须提供，不可省略**），包含：
  - summary: 一句话总结
  - participants: 每个参与者的 {agent_id, display_name, role_in_plan}
  - tasks: 任务列表，**必须体现工作流的先后依赖关系**：
    - id 用 "task_1", "task_2" ... 格式
    - **先思考任务之间的自然顺序**：哪些必须先完成，后续才能开始？哪些可以并行？
    - prerequisites 填入**必须先完成**的任务 id 数组
    - **禁止所有任务都设为并行（全部 prerequisites: []）**——真实协作一定有先后依赖
    - 典型模式：调研→设计→实现→交付；或有分叉：设计→[前端开发, 后端开发]→集成
    - status 统一为 "pending"
  - topology.edges: 从 prerequisites 展平得到的 {from, to} 边列表

## 依赖示例（仅供参考格式，实际内容根据需求生成）
```json
{
  "tasks": [
    {"id": "task_1", "title": "需求调研", "assignee_id": "a1", "prerequisites": [], "status": "pending"},
    {"id": "task_2", "title": "方案设计", "assignee_id": "a2", "prerequisites": ["task_1"], "status": "pending"},
    {"id": "task_3", "title": "核心开发", "assignee_id": "a3", "prerequisites": ["task_2"], "status": "pending"},
    {"id": "task_4", "title": "内容制作", "assignee_id": "a4", "prerequisites": ["task_2"], "status": "pending"},
    {"id": "task_5", "title": "整合交付", "assignee_id": "a1", "prerequisites": ["task_3", "task_4"], "status": "pending"}
  ],
  "topology": {"edges": [{"from":"task_1","to":"task_2"},{"from":"task_2","to":"task_3"},{"from":"task_2","to":"task_4"},{"from":"task_3","to":"task_5"},{"from":"task_4","to":"task_5"}]}
}
```

agent_id 和 display_name 必须与上面 Participant Responses 中给出的完全一致。

## 语言
用中文输出方案。
"""

SYSTEM_PROMPT_EN = """\
You are a multi-party resource coordination planner.

## Role
You receive a demand and responses (offers) from multiple participants.
Each participant responded based on their real background.
Your task is to find the optimal resource combination plan.

## Decision Principles (by priority)
1. Can the demand be satisfied?
2. Acceptance rate — will each party agree?
3. Efficiency

## Metacognition Requirements
- Consider complementarities between responses
- Consider unexpected combinations (1+1>2)
- Notice each response's unique perspective, don't just look at surface matching
- Partially relevant participants may add value in combination

## Actions
Use the provided tools to take action. You may call multiple tools at once.
- **Prefer output_plan** — when participants have submitted offers and information is mostly sufficient, generate a plan directly.
- Only use ask_agent when critical information is clearly missing (cannot judge feasibility).
- When there are ≤5 participants, information is usually sufficient for output_plan without follow-up questions.
- Use start_discovery when two participants might have hidden complementarities.
- Use create_sub_demand when there's a gap that current participants cannot fill.

## Output Format
When using output_plan, **you MUST provide both plan_text and plan_json. Both are required**:
- plan_text: A human-readable full plan text
- plan_json: A structured plan (**required, do not omit**) containing:
  - summary: One-sentence summary
  - participants: Each participant's {agent_id, display_name, role_in_plan}
  - tasks: Task list that **MUST reflect workflow dependencies**:
    - id uses "task_1", "task_2" ... format
    - **Think about task ordering first**: which tasks must finish before others can start? Which can run in parallel?
    - prerequisites lists prerequisite task id array
    - **DO NOT make all tasks parallel (all prerequisites: [])**—real collaboration always has sequential dependencies
    - Common patterns: research→design→implement→deliver; or branching: design→[frontend, backend]→integration
    - status should be "pending"
  - topology.edges: Flattened {from, to} edge list derived from prerequisites

## Dependency Example (format reference only, generate actual content based on demand)
```json
{
  "tasks": [
    {"id": "task_1", "title": "Research", "assignee_id": "a1", "prerequisites": [], "status": "pending"},
    {"id": "task_2", "title": "Design", "assignee_id": "a2", "prerequisites": ["task_1"], "status": "pending"},
    {"id": "task_3", "title": "Backend Dev", "assignee_id": "a3", "prerequisites": ["task_2"], "status": "pending"},
    {"id": "task_4", "title": "Frontend Dev", "assignee_id": "a4", "prerequisites": ["task_2"], "status": "pending"},
    {"id": "task_5", "title": "Integration", "assignee_id": "a1", "prerequisites": ["task_3", "task_4"], "status": "pending"}
  ],
  "topology": {"edges": [{"from":"task_1","to":"task_2"},{"from":"task_2","to":"task_3"},{"from":"task_2","to":"task_4"},{"from":"task_3","to":"task_5"},{"from":"task_4","to":"task_5"}]}
}
```

agent_id and display_name must exactly match those in the Participant Responses above.
"""


class CenterCoordinatorSkill(BaseSkill):
    """
    The central coordinator — synthesizes offers and drives negotiation via tool-use.

    Uses PlatformLLMClient (our own Claude API calls).
    """

    @property
    def name(self) -> str:
        return "center_coordinator"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        demand = context.get("demand")
        offers = context.get("offers")
        llm_client = context.get("llm_client")

        if demand is None:
            raise SkillError("demand (DemandSnapshot) is required")
        if offers is None:
            raise SkillError("offers list is required")
        if llm_client is None:
            raise SkillError("llm_client (PlatformLLMClient) is required")

        tools_restricted = context.get("tools_restricted", False)
        round_number = context.get("round_number", 1)
        history = context.get("history")
        participants = context.get("participants", [])

        system_prompt, messages = self._build_prompt(context)
        tools = self._get_restricted_tools() if tools_restricted else self._get_tools()

        response = await llm_client.chat(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
        )

        return self._validate_output(response, context)

    def _get_tools(self) -> list[dict[str, Any]]:
        """Return the full tool schema list. Override to add custom tools."""
        return list(ALL_TOOLS)

    def _get_restricted_tools(self) -> list[dict[str, Any]]:
        """Return the restricted tool schema (after max rounds). Override to customize."""
        return list(RESTRICTED_TOOLS)

    def _build_prompt(self, context: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        demand = context["demand"]
        offers = context["offers"]
        participants = context.get("participants", [])
        round_number = context.get("round_number", 1)
        history = context.get("history")

        # Build demand section
        demand_text = demand.formulated_text or demand.raw_intent

        # Build offers section with observation masking
        if round_number > 1 and history:
            # Observation masking: mask original offers, show previous reasoning
            offer_section = self._build_masked_offers(offers, participants, history)
        else:
            offer_section = self._build_offers(offers, participants)

        user_content = f"## Demand\n{demand_text}\n\n{offer_section}"

        if history:
            history_section = self._build_history(history, round_number)
            user_content += f"\n\n{history_section}"

        # Forced instruction: when tools_restricted, LLM MUST call output_plan
        if context.get("tools_restricted"):
            user_content += (
                "\n\n## 重要：最后一轮 / IMPORTANT: Final Round\n"
                "这是最后一轮。你**必须立即**调用 output_plan 输出方案。"
                "基于已有信息给出最佳方案，不要再使用其他工具。\n"
                "This is the final round. You **MUST** call output_plan now. "
                "Produce the best plan based on available information. Do not use any other tools."
            )

        system = SYSTEM_PROMPT_ZH if _detect_cjk(demand_text) else SYSTEM_PROMPT_EN

        # Scene context injection (B1): append scene-specific guidance to system prompt
        scene_context = context.get("scene_context")
        if scene_context and isinstance(scene_context, dict):
            priority = scene_context.get("priority_strategy", "")
            domain = scene_context.get("domain_context", "通用")
            system += f"\n\n## 场景上下文\n优先策略：{priority}\n领域：{domain}"

        messages = [{"role": "user", "content": user_content}]
        return system, messages

    def _build_offers(self, offers: list, participants: list) -> str:
        """Build full offers section (round 1)."""
        participant_map = {p.agent_id: p for p in participants} if participants else {}
        lines = [f"## Participant Responses ({len(offers)} total)"]
        for i, offer in enumerate(offers, 1):
            name = participant_map.get(offer.agent_id, None)
            display = name.display_name if name else offer.agent_id
            lines.append(f"\n### Participant {i}: {display} (ID: {offer.agent_id})")
            lines.append(f"Response: {offer.content}")
            if offer.capabilities:
                lines.append(f"Capabilities: {', '.join(offer.capabilities)}")
            lines.append(f"Confidence: {offer.confidence}")
        return "\n".join(lines)

    def _build_masked_offers(self, offers: list, participants: list, history: list) -> str:
        """Build masked offers section (round > 1). Original offers are masked to summary."""
        agent_names = []
        for offer in offers:
            agent_names.append(offer.agent_id)

        mask_summary = (
            f"## Participant Responses (masked)\n"
            f"Received {len(offers)} offers from: {', '.join(agent_names)}.\n"
            f"(Original offer details have been masked. See previous round reasoning for analysis.)"
        )

        # Include new replies if any exist in history
        new_replies = [h for h in history if h.get("type") == "agent_reply"]
        if new_replies:
            mask_summary += "\n\n## New Replies This Round"
            for reply in new_replies:
                mask_summary += f"\n### {reply.get('agent_id', 'unknown')}\n{reply.get('content', '')}"

        return mask_summary

    def _build_history(self, history: list, round_number: int) -> str:
        """Build history section preserving reasoning AND tool results from previous rounds."""
        lines = ["## History from Previous Rounds"]
        for entry in history:
            entry_type = entry.get("type", "unknown")
            if entry_type == "center_reasoning":
                lines.append(f"\n### Round {entry.get('round', '?')} Reasoning")
                lines.append(entry.get("content", ""))
            elif entry_type == "center_decision":
                lines.append(f"\n### Round {entry.get('round', '?')} Decision")
                lines.append(entry.get("content", ""))
            elif "tool" in entry:
                # Tool call results (ask_agent, start_discovery, create_sub_demand)
                tool_name = entry["tool"]
                tool_args = entry.get("args", {})
                tool_result = entry.get("result")
                lines.append(f"\n### Tool Result: {tool_name}")
                lines.append(f"Arguments: {json.dumps(tool_args, ensure_ascii=False, default=str)}")
                if tool_result is not None:
                    if isinstance(tool_result, dict):
                        lines.append(f"Result:\n```json\n{json.dumps(tool_result, ensure_ascii=False, indent=2, default=str)}\n```")
                    else:
                        lines.append(f"Result: {tool_result}")
        return "\n".join(lines)

    @staticmethod
    def _strip_think_tags(text: str) -> str:
        """Strip <think>...</think> blocks that LLMs sometimes output as plain text."""
        return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)

    def _validate_output(self, response: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate tool calls from LLM response."""
        tool_calls = response.get("tool_calls")

        if not tool_calls:
            # No tool calls — LLM responded with text. This is a format error.
            content = self._strip_think_tags(response.get("content", "")).strip()
            if content:
                # Degrade gracefully: wrap text content as output_plan
                logger.warning("Center responded with text instead of tool call, degrading to output_plan")
                return {
                    "tool_calls": [{"name": "output_plan", "arguments": {"plan_text": content}}],
                }
            raise SkillError("CenterCoordinatorSkill: no tool calls and no content in response")

        # Validate each tool call
        # Build valid names from current tool list (supports custom tools)
        valid_names = {t["name"] for t in self._get_tools()}

        validated = []
        for tc in tool_calls:
            tool_name = tc.get("name")
            if tool_name not in valid_names:
                raise SkillError(f"CenterCoordinatorSkill: invalid tool name '{tool_name}'")

            arguments = tc.get("arguments", {})
            if not isinstance(arguments, dict):
                raise SkillError(
                    f"CenterCoordinatorSkill: tool '{tool_name}' arguments must be a dict, got {type(arguments)}"
                )

            validated.append({"name": tool_name, "arguments": arguments})

        # Strip think tags from content passed back to engine for history
        content = response.get("content")
        result: dict[str, Any] = {"tool_calls": validated}
        if content:
            result["content"] = self._strip_think_tags(content).strip() or None
        return result
