"""
DemandFormulationSkill — enriches user's raw intent using their profile.

Client-side Skill: uses ProfileDataSource adapter for LLM calls.
Architecture ref: Section 10.4
"""

from __future__ import annotations

import json
import logging
from typing import Any

import re

from ..core.errors import SkillError
from .base import BaseSkill

logger = logging.getLogger(__name__)


def _detect_cjk(text: str) -> bool:
    """检测文本是否包含中日韩字符。"""
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', text))


SYSTEM_PROMPT_ZH = """\
你代表一个真实的人。你的任务是理解用户真正需要什么，\
并基于你对他们的了解，帮助他们更准确、完整地表达需求。

规则：
1. 区分"需要"和"要求"——具体的要求可能只是满足真实需要的一种方式。
2. 从用户画像中补充相关上下文，让响应者能更好地理解。
3. 不要替换用户的原始意图——丰富和补充它。
4. 保留用户的偏好，但标注哪些是硬约束、哪些是可协商的。

用户画像：
{profile_data}

以 JSON 格式输出：
{{
  "formulated_text": "丰富后的需求文本",
  "enrichments": {{
    "hard_constraints": ["..."],
    "negotiable_preferences": ["..."],
    "context_added": ["..."]
  }}
}}
"""

SYSTEM_PROMPT_EN = """\
You represent a real person. Your task is to understand what the user truly needs \
and help them express it more accurately and completely, based on your knowledge of them.

Rules:
1. Distinguish "needs" from "requirements" — the specific ask may be just one way to satisfy the real need.
2. Supplement with relevant context from the user's profile so responders understand better.
3. Do not replace the user's original intent — enrich and supplement it.
4. Preserve the user's preferences, but mark which are hard constraints and which are negotiable.

The user's profile:
{profile_data}

Output in JSON format:
{{
  "formulated_text": "the enriched demand text",
  "enrichments": {{
    "hard_constraints": ["..."],
    "negotiable_preferences": ["..."],
    "context_added": ["..."]
  }}
}}
"""


class DemandFormulationSkill(BaseSkill):
    """
    Enriches a user's raw intent using their profile data.

    Uses the client-side adapter (ProfileDataSource) to call the user's own model.
    """

    @property
    def name(self) -> str:
        return "demand_formulation"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        raw_intent = context.get("raw_intent")
        agent_id = context.get("agent_id")
        adapter = context.get("adapter")

        if not raw_intent:
            raise SkillError("raw_intent is required")
        if not agent_id:
            raise SkillError("agent_id is required")
        if adapter is None:
            raise SkillError("adapter (ProfileDataSource) is required")

        system_prompt, messages = self._build_prompt(context)

        raw_output = await adapter.chat(
            agent_id=agent_id,
            messages=messages,
            system_prompt=system_prompt,
        )

        return self._validate_output(raw_output, context)

    def _build_prompt(self, context: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        profile_data = context.get("profile_data", {})
        raw_intent = context["raw_intent"]

        profile_str = json.dumps(profile_data, ensure_ascii=False, indent=2) if profile_data else "(no profile data)"

        if _detect_cjk(raw_intent):
            system = SYSTEM_PROMPT_ZH.format(profile_data=profile_str)
            messages = [
                {"role": "user", "content": f"用户说：{raw_intent}\n请生成丰富后的需求表述。"}
            ]
        else:
            system = SYSTEM_PROMPT_EN.format(profile_data=profile_str)
            messages = [
                {"role": "user", "content": f"The user says: {raw_intent}\nPlease generate an enriched demand expression."}
            ]
        return system, messages

    def _validate_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        # Strip markdown code fences (real LLMs wrap JSON in ```json blocks)
        cleaned = self._strip_code_fence(raw_output)
        try:
            parsed = json.loads(cleaned)
            formulated = parsed.get("formulated_text", "")
            enrichments = parsed.get("enrichments", {})
        except (json.JSONDecodeError, TypeError):
            # Detect common LLM error patterns before treating as formulated text
            cleaned_lower = cleaned.strip().lower()
            error_patterns = [
                "rate limit", "too many requests", "overloaded",
                "internal server error", "service unavailable",
                "i cannot", "i'm unable", "as an ai",
            ]
            if any(pat in cleaned_lower for pat in error_patterns):
                raise SkillError(
                    f"DemandFormulationSkill: LLM returned error instead of formulation: "
                    f"{cleaned[:100]}"
                )
            # Lenient: treat entire output as the formulated text
            formulated = cleaned.strip()
            enrichments = {}

        if not formulated:
            raise SkillError("DemandFormulationSkill: formulated_text is empty")

        return {
            "formulated_text": formulated,
            "enrichments": enrichments,
        }
