"""
GapRecursionSkill — converts a gap into a well-formed sub-demand.

Platform-side Skill: uses PlatformLLMClient.
Architecture ref: Section 10.9

The sub-demand enters the same negotiation flow recursively.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..core.errors import SkillError
from .base import BaseSkill

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You need to convert a resource gap into an independent demand. \
This demand will be broadcast to the network for other participants to respond to.

Rules:
1. The sub-demand should be more specific than the original demand.
2. The sub-demand should be self-contained — readers should not need to know the parent demand's details.
3. But preserve enough context for responders to understand the background.

Output in JSON format:
{{
  "sub_demand_text": "the independent sub-demand",
  "context": "relevant background context from the parent demand"
}}
"""


class GapRecursionSkill(BaseSkill):
    """
    Converts a gap description into a well-formed sub-demand for recursive negotiation.
    """

    @property
    def name(self) -> str:
        return "gap_recursion"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        gap_description = context.get("gap_description")
        demand_context = context.get("demand_context")
        llm_client = context.get("llm_client")

        if not gap_description:
            raise SkillError("gap_description is required")
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
        gap_description = context["gap_description"]
        demand_context = context.get("demand_context", "(no parent context)")

        user_content = (
            f"## Original Demand\n{demand_context}\n\n"
            f"## Identified Gap\n{gap_description}\n\n"
            f"Please generate an independent sub-demand."
        )

        messages = [{"role": "user", "content": user_content}]
        return SYSTEM_PROMPT, messages

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Strip markdown code fences (```json ... ```) wrapping JSON output."""
        stripped = text.strip()
        if stripped.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
            stripped = stripped[first_newline + 1:]
            # Remove closing fence
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3].rstrip()
        return stripped

    def _validate_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        cleaned = self._strip_markdown_fences(raw_output)
        try:
            parsed = json.loads(cleaned)
            sub_demand_text = parsed.get("sub_demand_text", "")
            sub_context = parsed.get("context", "")
        except (json.JSONDecodeError, TypeError):
            # Lenient: treat entire output as the sub-demand
            sub_demand_text = cleaned.strip()
            sub_context = context.get("demand_context", "")

        if not sub_demand_text:
            raise SkillError("GapRecursionSkill: sub_demand_text is empty")

        return {
            "sub_demand_text": sub_demand_text,
            "context": sub_context,
        }
