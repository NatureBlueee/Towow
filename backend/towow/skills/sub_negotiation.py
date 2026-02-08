"""
SubNegotiationSkill — discovery dialogue between two agents.

Platform-side Skill: uses PlatformLLMClient.
Architecture ref: Section 10.8

V1: third-party synthesis (one LLM call analyzing both agents).
Future: direct agent-to-agent dialogue.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..core.errors import SkillError
from .base import BaseSkill

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are a resource discovery specialist. Two participants have each given their responses, \
but their profiles may contain relevant capabilities not mentioned in their offers. \
Your task is to discover complementarities and potential collaboration value between them.

Rules:
1. Focus on parts of the profile NOT covered in the offer.
2. Look for unexpected complementarities and combinations.
3. If there's conflict, find coordination paths acceptable to both parties.

Output in JSON format:
{{
  "discovery_report": {{
    "new_associations": ["association 1", "association 2"],
    "coordination": "coordination approach or null if not needed",
    "additional_contributions": {{
      "agent_a": ["potential contribution 1"],
      "agent_b": ["potential contribution 1"]
    }},
    "summary": "brief summary of discoveries"
  }}
}}
"""


class SubNegotiationSkill(BaseSkill):
    """
    Discovers hidden complementarities between two agents' profiles.

    V1 implementation: single LLM call analyzing both agents (third-party synthesis).
    """

    @property
    def name(self) -> str:
        return "sub_negotiation"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        agent_a = context.get("agent_a")
        agent_b = context.get("agent_b")
        reason = context.get("reason")
        llm_client = context.get("llm_client")

        if agent_a is None:
            raise SkillError("agent_a is required")
        if agent_b is None:
            raise SkillError("agent_b is required")
        if not reason:
            raise SkillError("reason is required")
        if llm_client is None:
            raise SkillError("llm_client (PlatformLLMClient) is required")

        system_prompt, messages = self._build_prompt(context)

        response = await llm_client.chat(
            messages=messages,
            system_prompt=system_prompt,
        )

        raw_output = response.get("content", "")
        return self._validate_output(raw_output, context)

    def _build_prompt(self, context: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        agent_a = context["agent_a"]
        agent_b = context["agent_b"]
        reason = context["reason"]

        a_name = agent_a.get("display_name", agent_a.get("agent_id", "Agent A"))
        b_name = agent_b.get("display_name", agent_b.get("agent_id", "Agent B"))

        a_offer = agent_a.get("offer", "(no offer)")
        a_profile = json.dumps(agent_a.get("profile", {}), ensure_ascii=False, indent=2)

        b_offer = agent_b.get("offer", "(no offer)")
        b_profile = json.dumps(agent_b.get("profile", {}), ensure_ascii=False, indent=2)

        user_content = (
            f"## Trigger Reason\n{reason}\n\n"
            f"## Participant A: {a_name}\nOffer: {a_offer}\nProfile:\n{a_profile}\n\n"
            f"## Participant B: {b_name}\nOffer: {b_offer}\nProfile:\n{b_profile}"
        )

        messages = [{"role": "user", "content": user_content}]
        return SYSTEM_PROMPT, messages

    def _validate_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_output)
            report = parsed.get("discovery_report", parsed)
        except (json.JSONDecodeError, TypeError):
            # Lenient: treat entire output as summary
            report = {
                "new_associations": [],
                "coordination": None,
                "additional_contributions": {},
                "summary": raw_output.strip(),
            }

        # Ensure required fields
        if not isinstance(report, dict):
            raise SkillError("SubNegotiationSkill: discovery_report must be a dict")

        report.setdefault("new_associations", [])
        report.setdefault("coordination", None)
        report.setdefault("additional_contributions", {})
        report.setdefault("summary", "")

        if not report["summary"] and not report["new_associations"]:
            raise SkillError("SubNegotiationSkill: discovery_report has no content")

        return {"discovery_report": report}
