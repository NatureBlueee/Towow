"""
Negotiation orchestration engine — the state machine that drives
the complete negotiation lifecycle from demand submission to plan output.

This is the protocol layer's core: it provides determinism via code control
while delegating intelligence to Skills via LLM calls.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from .errors import EngineError
from .events import (
    barrier_complete,
    center_tool_call,
    formulation_ready,
    offer_received,
    plan_ready,
    resonance_activated,
    sub_negotiation_started,
)
from .models import (
    AgentParticipant,
    AgentState,
    DemandSnapshot,
    NegotiationSession,
    NegotiationState,
    Offer,
    TraceChain,
    generate_id,
)
from .protocols import (
    Encoder,
    EventPusher,
    PlatformLLMClient,
    ProfileDataSource,
    ResonanceDetector,
    Skill,
    Vector,
)

logger = logging.getLogger(__name__)

# ============ State Machine ============

# Valid state transitions. Key = current state, value = set of allowed next states.
VALID_TRANSITIONS: dict[NegotiationState, set[NegotiationState]] = {
    NegotiationState.CREATED: {NegotiationState.FORMULATING, NegotiationState.COMPLETED},
    NegotiationState.FORMULATING: {NegotiationState.FORMULATED, NegotiationState.COMPLETED},
    NegotiationState.FORMULATED: {NegotiationState.ENCODING, NegotiationState.COMPLETED},
    NegotiationState.ENCODING: {NegotiationState.OFFERING, NegotiationState.COMPLETED},
    NegotiationState.OFFERING: {NegotiationState.BARRIER_WAITING, NegotiationState.COMPLETED},
    NegotiationState.BARRIER_WAITING: {NegotiationState.SYNTHESIZING, NegotiationState.COMPLETED},
    NegotiationState.SYNTHESIZING: {NegotiationState.SYNTHESIZING, NegotiationState.COMPLETED},
    NegotiationState.COMPLETED: set(),  # Terminal state
}

# Center tool names
TOOL_OUTPUT_PLAN = "output_plan"
TOOL_ASK_AGENT = "ask_agent"
TOOL_START_DISCOVERY = "start_discovery"
TOOL_CREATE_SUB_DEMAND = "create_sub_demand"

# Default timeouts
DEFAULT_OFFER_TIMEOUT_S = 30.0


class NegotiationEngine:
    """
    Orchestrates the full negotiation lifecycle.

    Drives a NegotiationSession through its state machine:
    CREATED -> FORMULATING -> FORMULATED -> ENCODING -> OFFERING ->
    BARRIER_WAITING -> SYNTHESIZING -> COMPLETED

    The engine provides determinism (state transitions, barriers, round limits)
    while Skills provide intelligence (LLM calls).
    """

    def __init__(
        self,
        encoder: Encoder,
        resonance_detector: ResonanceDetector,
        event_pusher: EventPusher,
        offer_timeout_s: float = DEFAULT_OFFER_TIMEOUT_S,
    ):
        self._encoder = encoder
        self._resonance_detector = resonance_detector
        self._event_pusher = event_pusher
        self._offer_timeout_s = offer_timeout_s

    # ============ State Transition ============

    def _transition(
        self, session: NegotiationSession, new_state: NegotiationState
    ) -> None:
        """
        Transition the session to a new state.

        Raises EngineError if the transition is not valid.
        """
        current = session.state
        allowed = VALID_TRANSITIONS.get(current, set())
        if new_state not in allowed:
            raise EngineError(
                f"Invalid state transition: {current.value} -> {new_state.value}"
            )
        logger.info(
            "Negotiation %s: %s -> %s",
            session.negotiation_id,
            current.value,
            new_state.value,
        )
        session.state = new_state

    # ============ Trace Helpers ============

    @staticmethod
    def _trace(
        session: NegotiationSession,
        step: str,
        start_time: float,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
        **metadata: Any,
    ) -> None:
        """Record a trace entry with timing."""
        if session.trace is None:
            return
        duration_ms = (time.monotonic() - start_time) * 1000
        session.trace.add_entry(
            step=step,
            duration_ms=round(duration_ms, 2),
            input_summary=input_summary,
            output_summary=output_summary,
            metadata=metadata,
        )

    # ============ Main Flow ============

    async def start_negotiation(
        self,
        session: NegotiationSession,
        adapter: ProfileDataSource,
        llm_client: PlatformLLMClient,
        formulation_skill: Optional[Skill] = None,
        offer_skill: Optional[Skill] = None,
        center_skill: Optional[Skill] = None,
        agent_vectors: Optional[dict[str, Vector]] = None,
        k_star: int = 5,
        agent_display_names: Optional[dict[str, str]] = None,
    ) -> NegotiationSession:
        """
        Drive a negotiation from CREATED to COMPLETED.

        This is the top-level entry point. It runs the full pipeline:
        formulation -> encoding -> offering -> barrier -> synthesis -> plan.
        """
        if session.trace is None:
            session.trace = TraceChain(negotiation_id=session.negotiation_id)

        self._agent_display_names = agent_display_names or {}

        try:
            # Step 1: Formulation
            await self._run_formulation(session, adapter, formulation_skill)

            # Step 2: Encoding + resonance detection
            await self._run_encoding(session, agent_vectors, k_star)

            # Step 3: Parallel offer generation + barrier
            await self._run_offers(session, adapter, offer_skill)

            # Step 4: Center synthesis loop
            await self._run_synthesis(session, adapter, llm_client, center_skill)

        except EngineError:
            raise
        except Exception as exc:
            logger.error(
                "Negotiation %s failed: %s",
                session.negotiation_id,
                exc,
                exc_info=True,
            )
            # Graceful degradation: move to COMPLETED on unrecoverable error
            if session.state != NegotiationState.COMPLETED:
                self._transition(session, NegotiationState.COMPLETED)
                session.completed_at = datetime.now(timezone.utc)
                if session.trace:
                    session.trace.completed_at = session.completed_at
                session.metadata["error"] = str(exc)
            raise EngineError(f"Negotiation failed: {exc}") from exc

        return session

    # ============ Step 1: Formulation ============

    async def _run_formulation(
        self,
        session: NegotiationSession,
        adapter: ProfileDataSource,
        formulation_skill: Optional[Skill],
    ) -> None:
        t0 = time.monotonic()
        self._transition(session, NegotiationState.FORMULATING)

        if formulation_skill:
            result = await formulation_skill.execute({
                "raw_intent": session.demand.raw_intent,
                "agent_id": session.demand.user_id or "user",
                "adapter": adapter,
            })
            formulated_text = result.get("formulated_text", session.demand.raw_intent)
        else:
            # No formulation skill — use raw intent directly
            formulated_text = session.demand.raw_intent

        session.demand.formulated_text = formulated_text
        self._transition(session, NegotiationState.FORMULATED)

        await self._event_pusher.push(
            formulation_ready(
                negotiation_id=session.negotiation_id,
                raw_intent=session.demand.raw_intent,
                formulated_text=formulated_text,
            )
        )

        self._trace(
            session,
            "formulation",
            t0,
            input_summary=session.demand.raw_intent,
            output_summary=formulated_text,
        )

    # ============ Step 2: Encoding + Resonance ============

    async def _run_encoding(
        self,
        session: NegotiationSession,
        agent_vectors: Optional[dict[str, Vector]],
        k_star: int,
    ) -> None:
        t0 = time.monotonic()
        self._transition(session, NegotiationState.ENCODING)

        demand_text = session.demand.formulated_text or session.demand.raw_intent
        demand_vector = await self._encoder.encode(demand_text)

        if not agent_vectors:
            # No agent vectors provided — skip resonance, move forward with empty participants
            self._transition(session, NegotiationState.OFFERING)
            self._trace(session, "encoding", t0, output_summary="no agent vectors")
            return

        results = await self._resonance_detector.detect(
            demand_vector=demand_vector,
            agent_vectors=agent_vectors,
            k_star=k_star,
        )

        for agent_id, score in results:
            session.participants.append(
                AgentParticipant(
                    agent_id=agent_id,
                    display_name=self._agent_display_names.get(agent_id, agent_id),
                    resonance_score=score,
                    state=AgentState.ACTIVE,
                )
            )

        self._transition(session, NegotiationState.OFFERING)

        await self._event_pusher.push(
            resonance_activated(
                negotiation_id=session.negotiation_id,
                activated_count=len(results),
                agents=[
                    {
                        "agent_id": aid,
                        "display_name": aid,
                        "resonance_score": score,
                    }
                    for aid, score in results
                ],
            )
        )

        self._trace(
            session,
            "encoding_resonance",
            t0,
            input_summary=demand_text[:100],
            output_summary=f"{len(results)} agents activated",
        )

    # ============ Step 3: Parallel Offers + Barrier ============

    async def _run_offers(
        self,
        session: NegotiationSession,
        adapter: ProfileDataSource,
        offer_skill: Optional[Skill],
    ) -> None:
        t0 = time.monotonic()

        if not session.participants:
            # No participants — go straight to barrier
            self._transition(session, NegotiationState.BARRIER_WAITING)
            self._transition(session, NegotiationState.SYNTHESIZING)
            self._trace(session, "offers", t0, output_summary="no participants")
            return

        # Generate offers in parallel
        async def _generate_one_offer(participant: AgentParticipant) -> None:
            try:
                if offer_skill:
                    # Fetch profile data for anti-fabrication guarantee
                    try:
                        profile_data = await adapter.get_profile(participant.agent_id)
                    except Exception:
                        profile_data = {}

                    result = await asyncio.wait_for(
                        offer_skill.execute({
                            "agent_id": participant.agent_id,
                            "demand_text": session.demand.formulated_text or session.demand.raw_intent,
                            "adapter": adapter,
                            "profile_data": profile_data,
                        }),
                        timeout=self._offer_timeout_s,
                    )
                    content = result.get("content", "")
                    capabilities = result.get("capabilities", [])
                else:
                    # No offer skill — use adapter chat directly
                    content = await asyncio.wait_for(
                        adapter.chat(
                            agent_id=participant.agent_id,
                            messages=[{
                                "role": "user",
                                "content": f"Please respond to this demand: {session.demand.formulated_text or session.demand.raw_intent}",
                            }],
                        ),
                        timeout=self._offer_timeout_s,
                    )
                    capabilities = []

                participant.offer = Offer(
                    agent_id=participant.agent_id,
                    content=content,
                    capabilities=capabilities,
                    confidence=result.get("confidence", 0.0) if offer_skill else 0.0,
                )
                participant.state = AgentState.REPLIED

                await self._event_pusher.push(
                    offer_received(
                        negotiation_id=session.negotiation_id,
                        agent_id=participant.agent_id,
                        display_name=participant.display_name,
                        content=content,
                        capabilities=capabilities,
                    )
                )

            except asyncio.TimeoutError:
                logger.warning(
                    "Agent %s timed out during offer generation",
                    participant.agent_id,
                )
                participant.state = AgentState.EXITED
            except Exception as exc:
                logger.warning(
                    "Agent %s failed during offer generation: %s",
                    participant.agent_id,
                    exc,
                )
                participant.state = AgentState.EXITED

        # Run all offer generations in parallel (gather works on Python 3.9+)
        await asyncio.gather(
            *(_generate_one_offer(p) for p in session.participants),
            return_exceptions=True,
        )

        # Barrier: all agents have replied or exited at this point
        self._transition(session, NegotiationState.BARRIER_WAITING)

        offers_count = len(session.collected_offers)
        exited_count = sum(1 for p in session.participants if p.state == AgentState.EXITED)

        await self._event_pusher.push(
            barrier_complete(
                negotiation_id=session.negotiation_id,
                total_participants=len(session.participants),
                offers_received=offers_count,
                exited_count=exited_count,
            )
        )

        self._trace(
            session,
            "offers_barrier",
            t0,
            output_summary=f"{offers_count} offers, {exited_count} exited",
        )

        self._transition(session, NegotiationState.SYNTHESIZING)

    # ============ Step 4: Center Synthesis Loop ============

    async def _run_synthesis(
        self,
        session: NegotiationSession,
        adapter: ProfileDataSource,
        llm_client: PlatformLLMClient,
        center_skill: Optional[Skill],
    ) -> None:
        """
        Run the Center synthesis loop.

        The Center receives all offers and the demand, then makes tool calls:
        - output_plan: ends the negotiation
        - ask_agent: asks an agent a follow-up question, result feeds back
        - start_discovery: runs a sub-negotiation skill
        - create_sub_demand: spawns a recursive negotiation
        """
        t0 = time.monotonic()
        history: list[dict[str, Any]] = []

        while True:
            round_t0 = time.monotonic()
            session.center_rounds += 1

            # Build context for Center
            context: dict[str, Any] = {
                "demand": session.demand,
                "offers": session.collected_offers,
                "participants": session.participants,
                "history": history,
                "round": session.center_rounds,
                "round_number": session.center_rounds,
                "tools_restricted": session.tools_restricted,
                "llm_client": llm_client,
            }

            if center_skill:
                result = await center_skill.execute(context)
            else:
                # No center skill — call LLM directly
                result = await self._call_center_llm(
                    session, llm_client, history
                )

            tool_calls = result.get("tool_calls")

            # Preserve Center's reasoning text in history for subsequent rounds
            center_reasoning = result.get("content")
            if center_reasoning:
                history.append({
                    "type": "center_reasoning",
                    "round": session.center_rounds,
                    "content": center_reasoning,
                })

            if not tool_calls:
                # No tool calls — treat text response as the plan
                plan_text = center_reasoning or "No plan generated."
                await self._finish_with_plan(session, plan_text, t0)
                return

            # Process each tool call
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("arguments", {})

                await self._event_pusher.push(
                    center_tool_call(
                        negotiation_id=session.negotiation_id,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        round_number=session.center_rounds,
                    )
                )

                if tool_name == TOOL_OUTPUT_PLAN:
                    plan_text = tool_args.get("plan_text", "")
                    await self._finish_with_plan(session, plan_text, t0)
                    return

                elif tool_name == TOOL_ASK_AGENT:
                    agent_reply = await self._handle_ask_agent(
                        session, adapter, tool_args
                    )
                    history.append({
                        "tool": TOOL_ASK_AGENT,
                        "args": tool_args,
                        "result": agent_reply,
                    })

                elif tool_name == TOOL_START_DISCOVERY:
                    discovery_result = tool_args.get("result", "Discovery completed.")
                    history.append({
                        "tool": TOOL_START_DISCOVERY,
                        "args": tool_args,
                        "result": discovery_result,
                    })

                elif tool_name == TOOL_CREATE_SUB_DEMAND:
                    sub_id = generate_id("neg")
                    await self._event_pusher.push(
                        sub_negotiation_started(
                            negotiation_id=session.negotiation_id,
                            sub_negotiation_id=sub_id,
                            gap_description=tool_args.get("gap_description", ""),
                        )
                    )
                    history.append({
                        "tool": TOOL_CREATE_SUB_DEMAND,
                        "args": tool_args,
                        "result": f"Sub-negotiation {sub_id} started.",
                    })

                self._trace(
                    session,
                    f"center_tool_{tool_name}",
                    round_t0,
                    input_summary=str(tool_args)[:200],
                    round=session.center_rounds,
                )

            # After processing tools: if tools_restricted, force output_plan next round
            if session.tools_restricted:
                # Force a final call — still through center_skill for consistent prompting
                forced_context = {
                    "demand": session.demand,
                    "offers": session.collected_offers,
                    "participants": session.participants,
                    "history": history,
                    "round": session.center_rounds + 1,
                    "round_number": session.center_rounds + 1,
                    "tools_restricted": True,
                    "llm_client": llm_client,
                }
                if center_skill:
                    result = await center_skill.execute(forced_context)
                else:
                    result = await self._call_center_llm(
                        session, llm_client, history, force_plan=True
                    )

                plan_calls = result.get("tool_calls", [])
                plan_text = "Plan could not be generated (round limit reached)."
                for pc in plan_calls:
                    if pc["name"] == TOOL_OUTPUT_PLAN:
                        plan_text = pc.get("arguments", {}).get("plan_text", plan_text)
                        break
                else:
                    # LLM returned text content instead of tool call
                    plan_text = result.get("content", plan_text)

                await self._finish_with_plan(session, plan_text, t0)
                return

            # Loop back: Center will be called again with updated history
            # Transition SYNTHESIZING -> SYNTHESIZING (self-loop)
            self._transition(session, NegotiationState.SYNTHESIZING)

    async def _call_center_llm(
        self,
        session: NegotiationSession,
        llm_client: PlatformLLMClient,
        history: list[dict[str, Any]],
        force_plan: bool = False,
    ) -> dict[str, Any]:
        """Call the platform LLM for Center synthesis."""
        # Build messages
        offers_text = "\n".join(
            f"- {o.agent_id}: {o.content}" for o in session.collected_offers
        )
        demand_text = session.demand.formulated_text or session.demand.raw_intent

        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    f"Demand: {demand_text}\n\n"
                    f"Offers:\n{offers_text}\n\n"
                    f"History: {history}\n\n"
                    f"Round: {session.center_rounds}"
                ),
            },
        ]

        # Build tools list — reuse canonical schemas from center skill
        from towow.skills.center import ALL_TOOLS, RESTRICTED_TOOLS
        if force_plan or session.tools_restricted:
            tools = RESTRICTED_TOOLS
        else:
            tools = ALL_TOOLS

        return await llm_client.chat(
            messages=messages,
            system_prompt="You are the Center coordinator.",
            tools=tools,
        )

    async def _handle_ask_agent(
        self,
        session: NegotiationSession,
        adapter: ProfileDataSource,
        tool_args: dict[str, Any],
    ) -> str:
        """Forward a question to an agent and return their reply."""
        agent_id = tool_args.get("agent_id", "")
        question = tool_args.get("question", "")

        if not question.strip():
            return f"Agent {agent_id}: no question provided."

        try:
            reply = await asyncio.wait_for(
                adapter.chat(
                    agent_id=agent_id,
                    messages=[{"role": "user", "content": question}],
                ),
                timeout=self._offer_timeout_s,
            )
            return reply
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("ask_agent failed for %s: %s", agent_id, exc)
            return f"Agent {agent_id} did not respond."

    async def _finish_with_plan(
        self,
        session: NegotiationSession,
        plan_text: str,
        start_time: float,
    ) -> None:
        """Finalize the negotiation with a plan output."""
        session.plan_output = plan_text
        self._transition(session, NegotiationState.COMPLETED)
        session.completed_at = datetime.now(timezone.utc)
        if session.trace:
            session.trace.completed_at = session.completed_at

        await self._event_pusher.push(
            plan_ready(
                negotiation_id=session.negotiation_id,
                plan_text=plan_text,
                center_rounds=session.center_rounds,
                participating_agents=[
                    p.agent_id
                    for p in session.participants
                    if p.state == AgentState.REPLIED
                ],
            )
        )

        self._trace(
            session,
            "synthesis_complete",
            start_time,
            output_summary=plan_text[:200],
        )
