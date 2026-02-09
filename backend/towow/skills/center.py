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


# ============ Tool Definitions (Claude API format) ============

TOOL_OUTPUT_PLAN = {
    "name": "output_plan",
    "description": "Output a text plan (suggestion, analysis, recommendation). This terminates the negotiation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan_text": {
                "type": "string",
                "description": "The complete plan text including resource allocation, coordination approach, and expected outcomes.",
            }
        },
        "required": ["plan_text"],
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

SYSTEM_PROMPT = """\
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
- Use output_plan when you have enough information to propose a plan.
- Use ask_agent when you need more information from a specific participant.
- Use start_discovery when two participants might have hidden complementarities.
- Use create_sub_demand when there's a gap that current participants cannot fill.
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

        messages = [{"role": "user", "content": user_content}]
        return SYSTEM_PROMPT, messages

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
