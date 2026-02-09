#!/usr/bin/env python3
"""
Towow SDK — Custom Center Tool Example

Shows how to register a custom tool that Center can use during negotiation.
In this example, we add a "search_knowledge_base" tool that Center can
call to look up domain-specific information.

Usage:
    python examples/custom_tool.py
"""

from __future__ import annotations

from typing import Any

from towow import (
    CenterCoordinatorSkill,
    NegotiationSession,
)


# ---------------------------------------------------------------------------
# 1. Define a CenterToolHandler
# ---------------------------------------------------------------------------
class KnowledgeBaseSearchHandler:
    """
    Custom Center tool that searches a knowledge base.

    Center can call this during synthesis when it needs domain-specific
    information to make better decisions.
    """

    @property
    def tool_name(self) -> str:
        return "search_knowledge_base"

    async def handle(
        self,
        session: NegotiationSession,
        tool_args: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle the search request.

        Args:
            tool_args: {"query": str, "max_results": int}
            context: Engine-provided deps (adapter, llm_client, etc.)

        Returns:
            Search results dict (stored in Center's history).
        """
        query = tool_args.get("query", "")
        max_results = tool_args.get("max_results", 5)

        # In production, this would call your actual knowledge base
        results = await _fake_search(query, max_results)

        return {
            "query": query,
            "results": results,
            "total_found": len(results),
        }


async def _fake_search(query: str, max_results: int) -> list[dict]:
    """Fake search — replace with your real implementation."""
    return [
        {"title": f"Result for '{query}'", "relevance": 0.95},
        {"title": f"Related to '{query}'", "relevance": 0.82},
    ][:max_results]


# ---------------------------------------------------------------------------
# 2. Extend CenterCoordinatorSkill to include the new tool
# ---------------------------------------------------------------------------
class MyCenterSkill(CenterCoordinatorSkill):
    """Center skill with an extra search_knowledge_base tool."""

    def _get_tools(self) -> list[dict]:
        """Add our custom tool to Center's tool schema."""
        # Get the default 5 tools
        tools = super()._get_tools()

        # Add our custom tool
        tools.append({
            "name": "search_knowledge_base",
            "description": (
                "Search the domain knowledge base for relevant information. "
                "Use this when you need specific domain knowledge to evaluate "
                "agent capabilities or make better coordination decisions."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        })
        return tools


# ---------------------------------------------------------------------------
# 3. Register with the engine
# ---------------------------------------------------------------------------
def setup_engine_with_custom_tools():
    """
    Example: build an engine with the custom tool registered.

    In production, combine with EngineBuilder:

        engine, defaults = (
            EngineBuilder()
            .with_adapter(my_adapter)
            .with_llm_client(my_llm)
            .with_center_skill(MyCenterSkill())
            .with_tool_handler(KnowledgeBaseSearchHandler())
            .build()
        )
    """
    from towow import EngineBuilder, NullEventPusher
    from unittest.mock import MagicMock

    engine, defaults = (
        EngineBuilder()
        .with_encoder(MagicMock())
        .with_resonance_detector(MagicMock())
        .with_center_skill(MyCenterSkill())
        .with_tool_handler(KnowledgeBaseSearchHandler())
        .with_event_pusher(NullEventPusher())
        .build()
    )

    print(f"Engine created with custom tools: {list(engine._tool_handlers.keys())}")
    print("Center skill: MyCenterSkill (includes search_knowledge_base)")
    return engine, defaults


if __name__ == "__main__":
    setup_engine_with_custom_tools()
