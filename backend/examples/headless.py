#!/usr/bin/env python3
"""
Towow SDK — Headless Example

Run a full negotiation without any web server.
This is the simplest possible usage of the SDK.

Usage:
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... python examples/headless.py

Requirements:
    pip install towow-sdk[claude,embeddings]
"""

import asyncio
import os
import sys

# ---------------------------------------------------------------------------
# 1. Import everything from the SDK top-level
# ---------------------------------------------------------------------------
from towow import (
    CenterCoordinatorSkill,
    DemandFormulationSkill,
    DemandSnapshot,
    EngineBuilder,
    LoggingEventPusher,
    NegotiationSession,
    OfferGenerationSkill,
    SubNegotiationSkill,
    GapRecursionSkill,
)
from towow.adapters.claude_adapter import ClaudeAdapter
from towow.infra.llm_client import ClaudePlatformClient


async def main() -> None:
    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY")
    if not api_key:
        print("Set TOWOW_ANTHROPIC_API_KEY to run this example.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Define agents (in production these come from your database)
    # ------------------------------------------------------------------
    agent_profiles = {
        "alice": {
            "name": "Alice",
            "role": "Machine Learning Engineer",
            "skills": ["Python", "PyTorch", "NLP", "Recommendation Systems"],
            "bio": "ML engineer with 5 years experience in NLP and RecSys.",
        },
        "bob": {
            "name": "Bob",
            "role": "Full-Stack Developer",
            "skills": ["TypeScript", "React", "Node.js", "PostgreSQL"],
            "bio": "Full-stack developer specializing in web applications.",
        },
    }

    # ------------------------------------------------------------------
    # 3. Build the engine — one line, all defaults
    # ------------------------------------------------------------------
    adapter = ClaudeAdapter(
        api_key=api_key,
        agent_profiles=agent_profiles,
    )
    llm_client = ClaudePlatformClient(api_key=api_key)

    engine, defaults = (
        EngineBuilder()
        .with_adapter(adapter)
        .with_llm_client(llm_client)
        .with_center_skill(CenterCoordinatorSkill())
        .with_formulation_skill(DemandFormulationSkill())
        .with_offer_skill(OfferGenerationSkill())
        .with_sub_negotiation_skill(SubNegotiationSkill())
        .with_gap_recursion_skill(GapRecursionSkill())
        .with_event_pusher(LoggingEventPusher())  # prints events to console
        .with_display_names({aid: p["name"] for aid, p in agent_profiles.items()})
        .build()
    )

    # ------------------------------------------------------------------
    # 4. Create a session and run
    # ------------------------------------------------------------------
    session = NegotiationSession(
        negotiation_id="example-001",
        demand=DemandSnapshot(
            raw_intent="I need a technical co-founder who can build an AI-powered SaaS product",
            user_id="user_demo",
            scene_id="scene_default",
        ),
    )

    print(f"\n{'='*60}")
    print(f"  Demand: {session.demand.raw_intent}")
    print(f"  Agents: {', '.join(agent_profiles.keys())}")
    print(f"{'='*60}\n")

    # Auto-confirm formulation (in production, user confirms via UI)
    async def auto_confirm():
        """Wait for formulation, then auto-confirm."""
        for _ in range(60):
            await asyncio.sleep(1)
            if engine.is_awaiting_confirmation(session.negotiation_id):
                engine.confirm_formulation(session.negotiation_id)
                print("[auto-confirm] Formulation confirmed.\n")
                return

    confirm_task = asyncio.create_task(auto_confirm())

    # Run the negotiation
    result = await engine.start_negotiation(session=session, **defaults)

    confirm_task.cancel()

    # ------------------------------------------------------------------
    # 5. Print results
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"  State: {result.state.value}")
    print(f"  Center rounds: {result.center_rounds}")
    print(f"  Participants: {len(result.participants)}")
    print(f"{'='*60}")

    if result.demand.formulated_text:
        print(f"\n--- Formulated Demand ---\n{result.demand.formulated_text[:500]}")

    for p in result.participants:
        print(f"\n--- {p.display_name} ({p.state.value}) ---")
        if p.offer:
            print(p.offer.content[:300])

    if result.plan_output:
        print(f"\n--- Plan Output ---\n{result.plan_output[:1000]}")

    print(f"\nDone. Events: {len(result.event_history)}")


if __name__ == "__main__":
    asyncio.run(main())
