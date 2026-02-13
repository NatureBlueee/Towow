"""
CenterCoordinatorSkill — the central coordinator that synthesizes all offers.

Platform-side Skill: uses PlatformLLMClient with tool-use.
Architecture ref: Section 10.7, Section 3.4

Center is a tool-use Agent with 3 tools (output_plan, create_sub_demand,
create_machine). Single-round: directly synthesizes offers into a task
assignment plan. No multi-round ask/discovery.
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

# All tools: direct synthesis (no multi-round ask/discovery)
ALL_TOOLS = [TOOL_OUTPUT_PLAN, TOOL_CREATE_SUB_DEMAND, TOOL_CREATE_MACHINE]

# Restricted set: only output_plan and create_machine (after max rounds)
RESTRICTED_TOOLS = [TOOL_OUTPUT_PLAN, TOOL_CREATE_MACHINE]

VALID_TOOL_NAMES = {t["name"] for t in ALL_TOOLS}


# ============ Prompt ============

SYSTEM_PROMPT_ZH = """\
你是一个分工协调者。

你收到一个需求和多个参与者的响应（offer）。直接根据这些信息输出分工方案。

## 你要做的
分析每个参与者能贡献什么，然后调用 output_plan 输出分工方案。一步到位，不需要追问。

## 分工原则
1. 谁能做什么？——从 offer 中提取每个人的实际能力
2. 谁和谁搭配？——互补的人放在相关任务上
3. 什么顺序？——先后依赖要合理，不要全部并行

## output_plan 格式
**必须同时提供 plan_text 和 plan_json**：
- plan_text: 方案说明（为什么这样分工、为什么这个顺序）
- plan_json: 结构化方案，包含：
  - summary: 一句话总结
  - participants: 每个参与者的 {agent_id, display_name, role_in_plan}
  - tasks: 任务列表，体现先后依赖：
    - id 用 "task_1", "task_2" ... 格式
    - prerequisites 填入必须先完成的任务 id
    - **禁止全部并行**——真实协作一定有先后依赖
    - status 统一为 "pending"
  - topology.edges: {from, to} 边列表

## 示例
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

agent_id 和 display_name 必须与 Participant Responses 中给出的完全一致。
用中文输出。
"""

SYSTEM_PROMPT_EN = """\
You are a task assignment coordinator.

You receive a demand and responses (offers) from multiple participants. Directly produce a task assignment plan based on this information.

## What to do
Analyze what each participant can contribute, then call output_plan with the assignment. One step, no follow-up questions needed.

## Assignment Principles
1. Who can do what? — extract actual capabilities from each offer
2. Who pairs well? — put complementary people on related tasks
3. What order? — dependencies must be logical, not everything in parallel

## output_plan Format
**You MUST provide both plan_text and plan_json**:
- plan_text: Explanation of why this assignment and this ordering
- plan_json: Structured plan containing:
  - summary: One-sentence summary
  - participants: Each participant's {agent_id, display_name, role_in_plan}
  - tasks: Task list reflecting dependencies:
    - id uses "task_1", "task_2" ... format
    - prerequisites lists prerequisite task ids
    - **DO NOT make all tasks parallel** — real collaboration has sequential dependencies
    - status should be "pending"
  - topology.edges: {from, to} edge list

## Example
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

agent_id and display_name must exactly match those in Participant Responses above.
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

        demand_text = demand.formulated_text or demand.raw_intent
        offer_section = self._build_offers(offers, participants)

        user_content = f"## Demand\n{demand_text}\n\n{offer_section}"

        system = SYSTEM_PROMPT_ZH if _detect_cjk(demand_text) else SYSTEM_PROMPT_EN

        # Scene context injection
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

    @staticmethod
    def _try_extract_plan_json(text: str) -> dict[str, Any] | None:
        """Try to extract a plan_json object from free-form text.

        LLM may embed JSON in markdown code blocks or inline.
        Returns None if no valid plan_json found.
        """
        # Try markdown code blocks first
        code_blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        for block in code_blocks:
            try:
                parsed = json.loads(block)
                if isinstance(parsed.get("tasks"), list) and len(parsed["tasks"]) > 0:
                    return parsed
            except (json.JSONDecodeError, TypeError):
                continue

        # Try finding bare JSON objects
        for m in re.finditer(r'\{', text):
            start = m.start()
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            parsed = json.loads(text[start:i + 1])
                            if isinstance(parsed.get("tasks"), list) and len(parsed["tasks"]) > 0:
                                return parsed
                        except (json.JSONDecodeError, TypeError):
                            pass
                        break
        return None

    def _validate_output(self, response: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Parse and validate tool calls from LLM response."""
        tool_calls = response.get("tool_calls")

        if not tool_calls:
            # No tool calls — LLM responded with text. This is a format error.
            content = self._strip_think_tags(response.get("content", "")).strip()
            if content:
                # Degrade gracefully: wrap text content as output_plan
                # Try to extract plan_json from the text (LLM may have embedded JSON)
                logger.warning("Center responded with text instead of tool call, degrading to output_plan")
                plan_json = self._try_extract_plan_json(content)
                args: dict[str, Any] = {"plan_text": content}
                if plan_json:
                    args["plan_json"] = plan_json
                    logger.info("Center text degradation: extracted plan_json with %d tasks",
                                len(plan_json.get("tasks", [])))
                return {
                    "tool_calls": [{"name": "output_plan", "arguments": args}],
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
