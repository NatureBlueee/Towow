"""
OfferGenerationSkill — generates an offer from an agent's profile in response to a demand.

Client-side Skill: uses ProfileDataSource adapter.
Architecture ref: Section 10.6

Anti-fabrication: the prompt only receives the agent's OWN profile data.
This is enforced by code (information source restriction), not by prompt alone.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..core.errors import SkillError
from .base import BaseSkill

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You represent a real person/service. Your task is to honestly respond to this demand \
based on your actual background.

Rules:
1. Only describe capabilities and experiences recorded in your profile.
2. If the demand is partially relevant, clearly state what's relevant and what's not.
3. If completely irrelevant, say "I can't help with this."
4. Think: in the context of this demand, which of your experiences might have unexpected value?

Your profile:
{profile_data}

Output in JSON format:
{{
  "content": "your response to the demand",
  "capabilities": ["relevant capability 1", "relevant capability 2"],
  "confidence": 0.0 to 1.0
}}
"""


class OfferGenerationSkill(BaseSkill):
    """
    Generates an offer from an agent in response to a demand.

    Anti-fabrication guarantee: only the agent's OWN profile data is in the prompt.
    This is enforced by code (this class controls what goes into the prompt).
    """

    @property
    def name(self) -> str:
        return "offer_generation"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        agent_id = context.get("agent_id")
        demand_text = context.get("demand_text")
        adapter = context.get("adapter")

        if not agent_id:
            raise SkillError("agent_id is required")
        if not demand_text:
            raise SkillError("demand_text is required")
        if adapter is None:
            raise SkillError("adapter (ProfileDataSource) is required")

        # Anti-fabrication: get only THIS agent's profile
        profile_data = context.get("profile_data", {})

        system_prompt, messages = self._build_prompt(
            {**context, "profile_data": profile_data}
        )

        raw_output = await adapter.chat(
            agent_id=agent_id,
            messages=messages,
            system_prompt=system_prompt,
        )

        return self._validate_output(raw_output, context)

    def _build_prompt(self, context: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        profile_data = context.get("profile_data", {})
        demand_text = context["demand_text"]

        profile_str = json.dumps(profile_data, ensure_ascii=False, indent=2) if profile_data else "(no profile data)"
        system = SYSTEM_PROMPT.format(profile_data=profile_str)

        messages = [
            {"role": "user", "content": f"Demand: {demand_text}\nPlease give your response."}
        ]
        return system, messages

    def _validate_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        # Strip markdown code fences (real LLMs wrap JSON in ```json blocks)
        cleaned = self._strip_code_fence(raw_output)
        try:
            parsed = json.loads(cleaned)
            content = parsed.get("content", "")
            capabilities = parsed.get("capabilities", [])
            confidence = parsed.get("confidence", 0.0)
        except (json.JSONDecodeError, TypeError):
            # Lenient: treat entire output as content
            content = cleaned.strip()
            capabilities = []
            confidence = 0.5

        if not content:
            raise SkillError("OfferGenerationSkill: content is empty")

        # Clamp confidence to [0, 1]
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        if not isinstance(capabilities, list):
            capabilities = []
        capabilities = [str(c) for c in capabilities]

        return {
            "content": content,
            "capabilities": capabilities,
            "confidence": confidence,
        }
