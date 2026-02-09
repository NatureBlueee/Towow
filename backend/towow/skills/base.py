"""
Skill base class — shared infrastructure for all 6 Skills.

Skills are the capability layer: they provide intelligence via LLM calls.
The protocol layer (engine) provides determinism via code control.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """
    Abstract base class for all Skills.

    Subclasses must implement name, execute(), and _build_prompt().
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill name identifier (e.g., 'demand_formulation')."""
        ...

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the skill with the given context."""
        ...

    @abstractmethod
    def _build_prompt(self, context: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        """Build system prompt and messages for LLM call."""
        ...

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """Strip markdown code fences (```json ... ```) from LLM output.

        Real LLMs frequently wrap JSON in code fences even when prompted not to.
        Code guarantee > prompt guarantee (Section 0.5).
        """
        stripped = text.strip()
        match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?\s*```$", stripped, re.DOTALL)
        if match:
            return match.group(1).strip()
        return stripped

    def _validate_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and parse LLM output. Override for structured output.
        Code guarantee > prompt guarantee.
        """
        return {"content": raw_output}
