"""
ReflectionSelectorSkill — extracts text features from profile for vector encoding.

Client-side Skill: uses ProfileDataSource adapter.
Architecture ref: Section 10.5
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..core.errors import SkillError
from .base import BaseSkill

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are a profile analyst. Your task is to extract the key capability features \
from an agent's profile data for encoding into a searchable vector representation.

Extract a list of concise text descriptions, each describing one distinct capability, \
experience, or characteristic. These will be used for matching against demands.

Rules:
1. Each feature should be a short, self-contained description (1-2 sentences max).
2. Cover different dimensions: skills, experience, domain knowledge, soft skills.
3. Be specific — "3 years of React development" is better than "frontend skills".
4. Do not invent or embellish — only describe what's in the profile.

Output in JSON format:
{{"features": ["feature 1", "feature 2", ...]}}
"""


class ReflectionSelectorSkill(BaseSkill):
    """
    Extracts text features from an agent's profile for vector encoding.

    Uses the client-side adapter (ProfileDataSource) to call the user's own model.
    """

    @property
    def name(self) -> str:
        return "reflection_selector"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        agent_id = context.get("agent_id")
        adapter = context.get("adapter")

        if not agent_id:
            raise SkillError("agent_id is required")
        if adapter is None:
            raise SkillError("adapter (ProfileDataSource) is required")

        profile_data = context.get("profile_data")
        if profile_data is None:
            profile_data = await adapter.get_profile(agent_id)

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
        profile_str = json.dumps(profile_data, ensure_ascii=False, indent=2) if profile_data else "(no profile data)"

        messages = [
            {"role": "user", "content": f"Extract capability features from this profile:\n{profile_str}"}
        ]
        return SYSTEM_PROMPT, messages

    def _validate_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_output)
            features = parsed.get("features", [])
        except (json.JSONDecodeError, TypeError):
            # Lenient: split by newlines and filter
            lines = [line.strip().lstrip("- ").strip() for line in raw_output.strip().split("\n")]
            features = [line for line in lines if line]

        if not isinstance(features, list):
            raise SkillError("ReflectionSelectorSkill: features must be a list")

        # Ensure all features are strings
        features = [str(f) for f in features if f]

        if not features:
            raise SkillError("ReflectionSelectorSkill: no features extracted")

        return {"features": features}
