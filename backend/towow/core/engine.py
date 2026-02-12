"""
Negotiation orchestration engine — the state machine that drives
the complete negotiation lifecycle from demand submission to plan output.

This is the protocol layer's core: it provides determinism via code control
while delegating intelligence to Skills via LLM calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .errors import AdapterError, EngineError
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
DEFAULT_FORMULATION_TIMEOUT_S = 30.0


class NegotiationEngine:
    """
    Orchestrates the full negotiation lifecycle.

    Drives a NegotiationSession through its state machine:
    CREATED -> FORMULATING -> FORMULATED -> ENCODING -> OFFERING ->
    BARRIER_WAITING -> SYNTHESIZING -> COMPLETED

    The engine provides determinism (state transitions, barriers, round limits)
    while Skills provide intelligence (LLM calls).
    """

    # Timeout for user confirmation before auto-proceeding with original text
    DEFAULT_CONFIRMATION_TIMEOUT_S = 300.0

    def __init__(
        self,
        encoder: Encoder,
        resonance_detector: ResonanceDetector,
        event_pusher: EventPusher,
        offer_timeout_s: float = DEFAULT_OFFER_TIMEOUT_S,
        confirmation_timeout_s: float = DEFAULT_CONFIRMATION_TIMEOUT_S,
        formulation_timeout_s: float = DEFAULT_FORMULATION_TIMEOUT_S,
    ):
        self._encoder = encoder
        self._resonance_detector = resonance_detector
        self._event_pusher = event_pusher
        self._offer_timeout_s = offer_timeout_s
        self._confirmation_timeout_s = confirmation_timeout_s
        self._formulation_timeout_s = formulation_timeout_s
        self._confirmation_events: dict[str, asyncio.Event] = {}
        self._confirmed_texts: dict[str, str | None] = {}
        self._neg_contexts: dict[str, dict[str, Any]] = {}
        # SDK: custom Center tool handler registry
        self._tool_handlers: dict[str, Any] = {}

    # ============ SDK: Tool Handler Registry ============

    def register_tool_handler(self, handler: Any) -> None:
        """Register a custom CenterToolHandler.

        The handler must have ``tool_name`` (str property) and
        ``handle(session, tool_args, context)`` async method.

        ``output_plan`` cannot be overridden — it triggers state transition.
        """
        name = handler.tool_name
        if name == TOOL_OUTPUT_PLAN:
            raise ValueError("output_plan is built-in and cannot be overridden.")
        self._tool_handlers[name] = handler
        logger.info("Registered custom Center tool handler: %s", name)

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

    def _display_names(self, session: NegotiationSession) -> dict[str, str]:
        """Get agent display names for a negotiation from its stored context."""
        ctx = self._neg_contexts.get(session.negotiation_id, {})
        return ctx.get("agent_display_names", {})

    # ============ Event Storage + Push ============

    async def _push_event(
        self, session: NegotiationSession, event: Any,
    ) -> None:
        """Store event on session for replay, then push to subscribers."""
        session.event_history.append(event.to_dict())
        await self._event_pusher.push(event)

    # ============ Confirmation API ============

    def confirm_formulation(
        self, negotiation_id: str, confirmed_text: str | None = None,
    ) -> bool:
        """Signal that the user has confirmed the formulation.

        Called by the API layer when user POSTs to /confirm.
        Returns False if engine is not waiting (already timed out or completed).
        """
        event = self._confirmation_events.get(negotiation_id)
        if event is None:
            return False
        if confirmed_text is not None:
            self._confirmed_texts[negotiation_id] = confirmed_text
        event.set()
        return True

    def is_awaiting_confirmation(self, negotiation_id: str) -> bool:
        """Check if engine is waiting for user confirmation on this negotiation."""
        return negotiation_id in self._confirmation_events

    # ============ Main Flow ============

    async def start_negotiation(
        self,
        session: NegotiationSession,
        adapter: ProfileDataSource,
        llm_client: PlatformLLMClient,
        center_skill: Skill,
        formulation_skill: Optional[Skill] = None,
        offer_skill: Optional[Skill] = None,
        agent_vectors: Optional[dict[str, Vector]] = None,
        k_star: int = 5,
        min_score: float = 0.5,
        agent_display_names: Optional[dict[str, str]] = None,
        sub_negotiation_skill: Optional[Skill] = None,
        gap_recursion_skill: Optional[Skill] = None,
        register_session: Optional[Callable[[NegotiationSession], None]] = None,
        scene_context: Optional[dict] = None,
    ) -> NegotiationSession:
        """
        Drive a negotiation from CREATED to COMPLETED.

        This is the top-level entry point. It runs the full pipeline:
        formulation -> encoding -> offering -> barrier -> synthesis -> plan.

        center_skill is required — Center is a necessary component of the
        negotiation unit (Section 0.1: minimum complete unit, not MVP).
        """
        if session.trace is None:
            session.trace = TraceChain(negotiation_id=session.negotiation_id)

        # Store context for sub-negotiation reuse (and per-session display names)
        self._neg_contexts[session.negotiation_id] = {
            "adapter": adapter,
            "llm_client": llm_client,
            "center_skill": center_skill,
            "formulation_skill": formulation_skill,
            "offer_skill": offer_skill,
            "agent_vectors": agent_vectors,
            "k_star": k_star,
            "min_score": min_score,
            "agent_display_names": agent_display_names or {},
            "sub_negotiation_skill": sub_negotiation_skill,
            "gap_recursion_skill": gap_recursion_skill,
            "register_session": register_session,
            "scene_context": scene_context,
        }

        try:
            # Step 1: Formulation
            await self._run_formulation(session, adapter, formulation_skill)

            # Step 2: Encoding + resonance detection
            await self._run_encoding(session, agent_vectors, k_star, min_score)

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
        finally:
            self._neg_contexts.pop(session.negotiation_id, None)

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

        degraded = False
        degraded_reason = ""

        if formulation_skill:
            user_id = session.demand.user_id or "user"

            # Step 1: Fetch profile (aligns with offer stage pattern)
            try:
                profile_data = await adapter.get_profile(user_id)
            except Exception as e:
                logger.warning("Profile fetch failed for %s: %s", user_id, e)
                profile_data = {}

            # Step 2: Execute formulation with timeout
            try:
                result = await asyncio.wait_for(
                    formulation_skill.execute({
                        "raw_intent": session.demand.raw_intent,
                        "agent_id": user_id,
                        "adapter": adapter,
                        "profile_data": profile_data,
                    }),
                    timeout=self._formulation_timeout_s,
                )
                formulated_text = result.get("formulated_text", session.demand.raw_intent)
            except asyncio.TimeoutError:
                logger.warning("Formulation timed out for %s", session.negotiation_id)
                formulated_text = session.demand.raw_intent
                degraded = True
                degraded_reason = "formulation_timeout"
            except AdapterError as e:
                err_str = str(e).lower()
                if "401" in err_str or "403" in err_str or "token" in err_str:
                    degraded_reason = "token_expired"
                else:
                    degraded_reason = "adapter_error"
                degraded = True
                formulated_text = session.demand.raw_intent
                logger.warning("Formulation adapter error for %s: %s", session.negotiation_id, e)
            except Exception as e:
                logger.warning(
                    "Formulation failed for %s, using raw intent: %s",
                    session.negotiation_id, e,
                )
                formulated_text = session.demand.raw_intent
                degraded = True
                degraded_reason = "formulation_error"
        else:
            # No formulation skill — use raw intent directly
            formulated_text = session.demand.raw_intent

        session.demand.formulated_text = formulated_text
        self._transition(session, NegotiationState.FORMULATED)

        logger.info(
            "🔵 [%s] formulation done (%.1fs): degraded=%s reason=%s text='%s'",
            session.negotiation_id, time.monotonic() - t0,
            degraded, degraded_reason, formulated_text[:100],
        )

        await self._push_event(
            session,
            formulation_ready(
                negotiation_id=session.negotiation_id,
                raw_intent=session.demand.raw_intent,
                formulated_text=formulated_text,
                degraded=degraded,
                degraded_reason=degraded_reason,
            ),
        )

        # Protocol layer required step: wait for user confirmation (Section 10.2)
        confirm_event = asyncio.Event()
        self._confirmation_events[session.negotiation_id] = confirm_event
        logger.info("🔵 [%s] waiting for confirmation (timeout=%.0fs)...", session.negotiation_id, self._confirmation_timeout_s)

        # Sub-negotiations: Center (the initiator) auto-confirms — "谁发起谁确认"
        if session.depth > 0:
            self.confirm_formulation(session.negotiation_id)

        try:
            await asyncio.wait_for(
                confirm_event.wait(), timeout=self._confirmation_timeout_s,
            )
            logger.info("🔵 [%s] confirmation received", session.negotiation_id)
        except asyncio.TimeoutError:
            logger.warning(
                "🟡 [%s] confirmation timeout (%.0fs), auto-confirming with original text",
                session.negotiation_id,
                self._confirmation_timeout_s,
            )
        finally:
            # Apply confirmed text if user modified it
            confirmed = self._confirmed_texts.pop(session.negotiation_id, None)
            if confirmed is not None:
                session.demand.formulated_text = confirmed
            self._confirmation_events.pop(session.negotiation_id, None)

        self._trace(
            session,
            "formulation",
            t0,
            input_summary=session.demand.raw_intent,
            output_summary=session.demand.formulated_text,
        )

    # ============ Step 2: Encoding + Resonance ============

    async def _run_encoding(
        self,
        session: NegotiationSession,
        agent_vectors: Optional[dict[str, Vector]],
        k_star: int,
        min_score: float = 0.5,
    ) -> None:
        t0 = time.monotonic()
        self._transition(session, NegotiationState.ENCODING)

        demand_text = session.demand.formulated_text or session.demand.raw_intent
        logger.info(
            "🔵 [%s] encoding: demand='%s' agent_vectors=%s k_star=%d min_score=%.2f",
            session.negotiation_id, demand_text[:80],
            len(agent_vectors) if agent_vectors else 0, k_star, min_score,
        )

        if not agent_vectors:
            # No agent vectors provided — skip resonance, move forward with empty participants
            logger.warning("🟡 [%s] encoding: NO agent vectors, skipping resonance", session.negotiation_id)
            self._transition(session, NegotiationState.OFFERING)
            self._trace(session, "encoding", t0, output_summary="no agent vectors")
            return

        # Exclude demand submitter from resonance candidates (self-resonance is meaningless)
        submitter_id = session.demand.user_id
        candidate_vectors = {
            aid: vec for aid, vec in agent_vectors.items() if aid != submitter_id
        }
        logger.info(
            "🔵 [%s] encoding: submitter=%s excluded, candidates=%d (from %d)",
            session.negotiation_id, submitter_id, len(candidate_vectors), len(agent_vectors),
        )
        if not candidate_vectors:
            logger.warning("🟡 [%s] encoding: 0 candidates after excluding submitter", session.negotiation_id)
            self._transition(session, NegotiationState.OFFERING)
            self._trace(session, "encoding", t0, output_summary="no candidates after excluding submitter")
            return

        # Encode demand AFTER confirming we have candidate vectors to compare against
        try:
            demand_vector = await self._encoder.encode(demand_text)
            logger.info("🔵 [%s] encoding: demand_vector dim=%d", session.negotiation_id, len(demand_vector))
        except Exception as enc_err:
            # Encoding failed (API auth, network, etc.) — degrade to all candidates
            logger.warning(
                "🟡 [%s] encoding: demand encode failed (%s), degrading to all %d candidates",
                session.negotiation_id, enc_err, len(candidate_vectors),
            )
            for agent_id in list(candidate_vectors.keys())[:k_star]:
                session.participants.append(
                    AgentParticipant(
                        agent_id=agent_id,
                        display_name=self._display_names(session).get(agent_id, agent_id),
                        resonance_score=0.0,
                        state=AgentState.ACTIVE,
                    )
                )
            self._transition(session, NegotiationState.OFFERING)
            self._trace(session, "encoding", t0, output_summary=f"degraded: {len(session.participants)} agents (encode failed)")
            return

        # detect() returns (activated, filtered) tuple per PLAN-003
        activated, filtered = await self._resonance_detector.detect(
            demand_vector=demand_vector,
            agent_vectors=candidate_vectors,
            k_star=k_star,
            min_score=min_score,
        )
        # Log top scores for debugging
        all_scores = activated + filtered
        top5 = sorted(all_scores, key=lambda x: x[1], reverse=True)[:5]
        logger.info(
            "🔵 [%s] resonance: activated=%d filtered=%d top5=%s",
            session.negotiation_id, len(activated), len(filtered),
            [(aid[:20], f"{s:.3f}") for aid, s in top5],
        )

        # Only activated agents (>= min_score, up to k_star) become participants
        for agent_id, score in activated:
            session.participants.append(
                AgentParticipant(
                    agent_id=agent_id,
                    display_name=self._display_names(session).get(agent_id, agent_id),
                    resonance_score=score,
                    state=AgentState.ACTIVE,
                )
            )

        self._transition(session, NegotiationState.OFFERING)

        await self._push_event(
            session,
            resonance_activated(
                negotiation_id=session.negotiation_id,
                activated_count=len(activated),
                agents=[
                    {
                        "agent_id": aid,
                        "display_name": self._display_names(session).get(aid, aid),
                        "resonance_score": score,
                    }
                    for aid, score in activated
                ],
                filtered_agents=[
                    {
                        "agent_id": aid,
                        "display_name": self._display_names(session).get(aid, aid),
                        "resonance_score": score,
                    }
                    for aid, score in filtered
                ],
            ),
        )

        logger.info(
            "Negotiation %s: resonance detection complete — %d activated, %d filtered (min_score=%.2f, k_star=%d)",
            session.negotiation_id,
            len(activated),
            len(filtered),
            min_score,
            k_star,
        )

        self._trace(
            session,
            "encoding_resonance",
            t0,
            input_summary=demand_text[:100],
            output_summary=f"{len(activated)} activated, {len(filtered)} filtered",
        )

    # ============ Step 3: Parallel Offers + Barrier ============

    async def _run_offers(
        self,
        session: NegotiationSession,
        adapter: ProfileDataSource,
        offer_skill: Optional[Skill],
    ) -> None:
        t0 = time.monotonic()
        logger.info(
            "🔵 [%s] offers START: %d participants, offer_skill=%s",
            session.negotiation_id, len(session.participants),
            type(offer_skill).__name__ if offer_skill else "None",
        )

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

                await self._push_event(
                    session,
                    offer_received(
                        negotiation_id=session.negotiation_id,
                        agent_id=participant.agent_id,
                        display_name=participant.display_name,
                        content=content,
                        capabilities=capabilities,
                    ),
                )

            except asyncio.TimeoutError:
                logger.warning(
                    "Agent %s timed out during offer generation (%.0fs). "
                    "adapter=%s, offer_skill=%s",
                    participant.agent_id, self._offer_timeout_s,
                    type(adapter).__name__, type(offer_skill).__name__ if offer_skill else "None",
                )
                participant.state = AgentState.EXITED
            except Exception as exc:
                logger.warning(
                    "Agent %s failed during offer generation: %s (type=%s)",
                    participant.agent_id,
                    exc, type(exc).__name__,
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

        await self._push_event(
            session,
            barrier_complete(
                negotiation_id=session.negotiation_id,
                total_participants=len(session.participants),
                offers_received=offers_count,
                exited_count=exited_count,
            ),
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
        center_skill: Skill,
    ) -> None:
        """
        Run the Center synthesis loop.

        Center Skill is required — it provides the prompt, tool schema,
        and observation masking that are essential for quality synthesis.
        Engine only orchestrates; Skill provides intelligence (Section 0.5).

        The Center makes tool calls:
        - output_plan: ends the negotiation
        - ask_agent: asks an agent a follow-up question, result feeds back
        - start_discovery: runs a sub-negotiation skill
        - create_sub_demand: spawns a recursive negotiation
        """
        t0 = time.monotonic()
        history: list[dict[str, Any]] = []
        offers_count = sum(1 for p in session.participants if p.offer)
        exited_count = sum(1 for p in session.participants if p.state == AgentState.EXITED)
        # WARNING level to ensure visibility in Railway logs
        logger.warning(
            "🔵 [%s] synthesis START: %d participants, %d offers, %d exited, llm=%s",
            session.negotiation_id, len(session.participants), offers_count, exited_count,
            type(llm_client).__name__ if llm_client else "None",
        )

        while True:
            round_t0 = time.monotonic()
            session.center_rounds += 1

            # Build context for Center
            neg_ctx = self._neg_contexts.get(session.negotiation_id, {})
            context: dict[str, Any] = {
                "demand": session.demand,
                "offers": session.collected_offers,
                "participants": session.participants,
                "history": history,
                "round": session.center_rounds,
                "round_number": session.center_rounds,
                "tools_restricted": session.tools_restricted,
                "llm_client": llm_client,
                "scene_context": neg_ctx.get("scene_context"),
            }

            try:
                result = await asyncio.wait_for(
                    center_skill.execute(context),
                    timeout=90.0,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "🟡 [%s] Center synthesis round %d timed out (90s), forcing plan from session data",
                    session.negotiation_id, session.center_rounds,
                )
                # Construct plan from existing session data rather than hanging
                demand_text = session.demand.formulated_text or session.demand.raw_intent
                offer_summaries = []
                for p in session.participants:
                    if p.offer:
                        name = p.display_name or p.agent_id
                        offer_summaries.append(f"- {name}: {p.offer.content[:200]}")
                offers_text = "\n".join(offer_summaries) if offer_summaries else "(无响应)"
                fallback_plan = (
                    f"## 协商方案（Center 超时，基于已收集信息生成）\n\n"
                    f"**需求**: {demand_text}\n\n"
                    f"**参与者响应**:\n{offers_text}\n"
                )
                await self._finish_with_plan(session, fallback_plan, t0)
                return

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

                await self._push_event(
                    session,
                    center_tool_call(
                        negotiation_id=session.negotiation_id,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        round_number=session.center_rounds,
                    ),
                )

                if tool_name == TOOL_OUTPUT_PLAN:
                    # Always built-in: triggers state transition to COMPLETED
                    plan_text = tool_args.get("plan_text", "")
                    plan_json = tool_args.get("plan_json")
                    await self._finish_with_plan(session, plan_text, t0, plan_json=plan_json)
                    return

                # SDK: check custom handler registry first
                elif tool_name in self._tool_handlers:
                    handler = self._tool_handlers[tool_name]
                    handler_ctx = {
                        "adapter": adapter,
                        "llm_client": llm_client,
                        "display_names": self._display_names(session),
                        "neg_context": self._neg_contexts.get(session.negotiation_id, {}),
                        "engine": self,
                    }
                    result = await handler.handle(session, tool_args, handler_ctx)
                    if result is not None:
                        history.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result,
                        })

                # Built-in tool handlers (fallback when no custom handler registered)
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
                    discovery_result = await self._handle_start_discovery(
                        session, adapter, llm_client, tool_args,
                    )
                    history.append({
                        "tool": TOOL_START_DISCOVERY,
                        "args": tool_args,
                        "result": discovery_result,
                    })

                elif tool_name == TOOL_CREATE_SUB_DEMAND:
                    sub_result = await self._handle_create_sub_demand(
                        session, llm_client, tool_args,
                    )
                    history.append({
                        "tool": TOOL_CREATE_SUB_DEMAND,
                        "args": tool_args,
                        "result": sub_result,
                    })

                else:
                    logger.warning(
                        "Negotiation %s: unknown Center tool '%s', skipping",
                        session.negotiation_id, tool_name,
                    )

                self._trace(
                    session,
                    f"center_tool_{tool_name}",
                    round_t0,
                    input_summary=str(tool_args)[:200],
                    round=session.center_rounds,
                )

            # After processing tools: if tools_restricted, force output_plan next round
            if session.tools_restricted:
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
                try:
                    result = await asyncio.wait_for(
                        center_skill.execute(forced_context),
                        timeout=90.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "🟡 [%s] Center forced round timed out (90s)",
                        session.negotiation_id,
                    )
                    result = {"tool_calls": [], "content": ""}

                plan_calls = result.get("tool_calls", [])
                forced_plan_json = None
                plan_text = None
                for pc in plan_calls:
                    if pc["name"] == TOOL_OUTPUT_PLAN:
                        plan_text = pc.get("arguments", {}).get("plan_text")
                        forced_plan_json = pc.get("arguments", {}).get("plan_json")
                        break

                # Fallback: if LLM didn't call output_plan, synthesize from session data
                if not plan_text:
                    content = result.get("content", "")
                    if content and len(content) > 20:
                        # LLM returned text content instead of tool call — use it
                        plan_text = content
                    else:
                        # Code guarantee: construct meaningful plan from session data
                        demand_text = session.demand.formulated_text or session.demand.raw_intent
                        offer_summaries = []
                        for p in session.participants:
                            if p.offer:
                                name = p.display_name or p.agent_id
                                offer_summaries.append(f"- {name}: {p.offer.content[:150]}")
                        offers_text = "\n".join(offer_summaries) if offer_summaries else "(无响应)"
                        plan_text = (
                            f"## 协商方案\n\n"
                            f"**需求**: {demand_text}\n\n"
                            f"**参与者响应**:\n{offers_text}\n\n"
                            f"基于以上 {len(session.participants)} 位参与者的响应，"
                            f"建议按各自专长分工协作，共同推进需求的实现。"
                        )

                await self._finish_with_plan(session, plan_text, t0, plan_json=forced_plan_json)
                return

            # Loop back: Center will be called again with updated history
            # Transition SYNTHESIZING -> SYNTHESIZING (self-loop)
            self._transition(session, NegotiationState.SYNTHESIZING)

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

    async def _handle_start_discovery(
        self,
        session: NegotiationSession,
        adapter: ProfileDataSource,
        llm_client: PlatformLLMClient,
        tool_args: dict[str, Any],
    ) -> dict[str, Any]:
        """Run SubNegotiationSkill to discover complementarities between two agents."""
        ctx = self._neg_contexts.get(session.negotiation_id, {})
        sub_neg_skill = ctx.get("sub_negotiation_skill")

        agent_a_id = tool_args.get("agent_a", "")
        agent_b_id = tool_args.get("agent_b", "")
        reason = tool_args.get("reason", tool_args.get("topic", ""))

        if not sub_neg_skill:
            return {"discovery_report": {"summary": f"Discovery requested for {agent_a_id} and {agent_b_id}, but SubNegotiationSkill not available."}}

        # Build agent context: profile + offer from participants
        def _agent_context(aid: str) -> dict[str, Any]:
            participant = next((p for p in session.participants if p.agent_id == aid), None)
            offer_text = participant.offer.content if participant and participant.offer else "(no offer)"
            profile = {}
            # Profile will be fetched asynchronously below
            return {"agent_id": aid, "offer": offer_text, "profile": profile}

        agent_a_ctx = _agent_context(agent_a_id)
        agent_b_ctx = _agent_context(agent_b_id)

        # Fetch profiles asynchronously
        try:
            agent_a_ctx["profile"] = await adapter.get_profile(agent_a_id)
        except Exception:
            agent_a_ctx["profile"] = {}
        try:
            agent_b_ctx["profile"] = await adapter.get_profile(agent_b_id)
        except Exception:
            agent_b_ctx["profile"] = {}

        # Add display names
        agent_a_ctx["display_name"] = self._display_names(session).get(agent_a_id, agent_a_id)
        agent_b_ctx["display_name"] = self._display_names(session).get(agent_b_id, agent_b_id)

        try:
            result = await sub_neg_skill.execute({
                "agent_a": agent_a_ctx,
                "agent_b": agent_b_ctx,
                "reason": reason or "Discover complementarities",
                "llm_client": llm_client,
            })
            return result
        except Exception as exc:
            logger.warning("start_discovery failed: %s", exc)
            return {"discovery_report": {"summary": f"Discovery failed: {exc}"}}

    async def _handle_create_sub_demand(
        self,
        session: NegotiationSession,
        llm_client: PlatformLLMClient,
        tool_args: dict[str, Any],
    ) -> dict[str, Any]:
        """Create and run a recursive sub-negotiation for a gap."""
        ctx = self._neg_contexts.get(session.negotiation_id, {})
        gap_recursion_skill = ctx.get("gap_recursion_skill")
        gap_description = tool_args.get("gap_description", "")

        # Depth limit check
        if session.depth >= 1:
            msg = f"Max recursion depth reached (depth={session.depth}). Cannot create sub-negotiation."
            logger.info("Negotiation %s: %s", session.negotiation_id, msg)
            return {"status": "max_depth_reached", "message": msg}

        # Generate sub-demand text via GapRecursionSkill
        if gap_recursion_skill:
            try:
                gap_result = await gap_recursion_skill.execute({
                    "gap_description": gap_description,
                    "demand_context": session.demand.formulated_text or session.demand.raw_intent,
                    "llm_client": llm_client,
                })
                sub_demand_text = gap_result.get("sub_demand_text", gap_description)
            except Exception as exc:
                logger.warning("GapRecursionSkill failed: %s", exc)
                sub_demand_text = gap_description
        else:
            sub_demand_text = gap_description

        # Create sub-session
        sub_id = generate_id("neg")
        sub_session = NegotiationSession(
            negotiation_id=sub_id,
            demand=DemandSnapshot(
                raw_intent=sub_demand_text,
                user_id=session.demand.user_id,
                scene_id=session.demand.scene_id,
            ),
            parent_negotiation_id=session.negotiation_id,
            depth=session.depth + 1,
            trace=TraceChain(negotiation_id=sub_id),
        )

        # Push sub_negotiation_started event to parent channel
        await self._push_event(
            session,
            sub_negotiation_started(
                negotiation_id=session.negotiation_id,
                sub_negotiation_id=sub_id,
                gap_description=gap_description,
            ),
        )

        # Register sub-session so frontend can access it
        register_session = ctx.get("register_session")
        if register_session:
            register_session(sub_session)

        # Record sub-session ID on parent
        session.sub_session_ids.append(sub_id)

        # Run sub-negotiation recursively (reusing parent context)
        try:
            await self.start_negotiation(
                session=sub_session,
                adapter=ctx.get("adapter"),
                llm_client=ctx.get("llm_client"),
                center_skill=ctx.get("center_skill"),
                formulation_skill=ctx.get("formulation_skill"),
                offer_skill=ctx.get("offer_skill"),
                agent_vectors=ctx.get("agent_vectors"),
                k_star=ctx.get("k_star", 5),
                min_score=ctx.get("min_score", 0.5),
                agent_display_names=ctx.get("agent_display_names"),
                sub_negotiation_skill=ctx.get("sub_negotiation_skill"),
                gap_recursion_skill=ctx.get("gap_recursion_skill"),
                register_session=register_session,
            )
        except Exception as exc:
            logger.warning("Sub-negotiation %s failed: %s", sub_id, exc)
            sub_session.metadata["error"] = str(exc)

        # Return full sub-session data to parent Center
        return self._serialize_sub_session(sub_session)

    @staticmethod
    def _serialize_sub_session(sub: NegotiationSession) -> dict[str, Any]:
        """Serialize a sub-session's full data for return to parent Center."""
        return {
            "sub_negotiation_id": sub.negotiation_id,
            "state": sub.state.value,
            "depth": sub.depth,
            "demand": sub.demand.formulated_text or sub.demand.raw_intent,
            "plan_output": sub.plan_output,
            "participants": [
                {
                    "agent_id": p.agent_id,
                    "display_name": p.display_name,
                    "state": p.state.value,
                    "offer": p.offer.content if p.offer else None,
                }
                for p in sub.participants
            ],
            "center_rounds": sub.center_rounds,
            "event_count": len(sub.event_history),
            "error": sub.metadata.get("error"),
        }

    async def _finish_with_plan(
        self,
        session: NegotiationSession,
        plan_text: str,
        start_time: float,
        plan_json: Optional[dict] = None,
    ) -> None:
        """Finalize the negotiation with a plan output.

        Three-layer defense ensures plan_json is never None:
        1. Use plan_json from LLM if valid (has tasks[])
        2. Extract JSON from plan_text if plan_json missing
        3. Construct minimal plan_json from session data
        """
        # --- Three-layer defense: guarantee plan_json ---
        if not self._is_valid_plan_json(plan_json):
            extracted = self._extract_plan_json(plan_text)
            if self._is_valid_plan_json(extracted):
                plan_json = extracted
                logger.info("plan_json: extracted from plan_text")

        if not self._is_valid_plan_json(plan_json):
            plan_json = self._build_minimal_plan_json(session)
            logger.info("plan_json: constructed from session data (%d tasks)", len(plan_json.get("tasks", [])))

        # Code guarantee: auto-generate topology.edges from prerequisites
        # LLM may fill prerequisites but forget edges (代码保障 > Prompt 保障)
        if plan_json and isinstance(plan_json.get("tasks"), list):
            edges = (plan_json.get("topology") or {}).get("edges", [])
            if not edges:
                # Build valid task ID set to filter hallucinated prerequisites
                valid_ids = {t.get("id", "") for t in plan_json["tasks"] if t.get("id")}
                generated_edges = []
                for task in plan_json["tasks"]:
                    task_id = task.get("id", "")
                    if not task_id or task_id not in valid_ids:
                        continue
                    for prereq in task.get("prerequisites", []):
                        if prereq and prereq in valid_ids:
                            generated_edges.append({"from": prereq, "to": task_id})
                if generated_edges:
                    if "topology" not in plan_json:
                        plan_json["topology"] = {}
                    plan_json["topology"]["edges"] = generated_edges
                    logger.info(
                        "plan_json: auto-generated %d topology edges from prerequisites",
                        len(generated_edges),
                    )

        session.plan_output = plan_text
        session.plan_json = plan_json
        self._transition(session, NegotiationState.COMPLETED)
        session.completed_at = datetime.now(timezone.utc)
        if session.trace:
            session.trace.completed_at = session.completed_at

        await self._push_event(
            session,
            plan_ready(
                negotiation_id=session.negotiation_id,
                plan_text=plan_text,
                center_rounds=session.center_rounds,
                participating_agents=[
                    p.agent_id
                    for p in session.participants
                    if p.state == AgentState.REPLIED
                ],
                plan_json=plan_json,
            ),
        )

        self._trace(
            session,
            "synthesis_complete",
            start_time,
            output_summary=plan_text[:200],
        )

    @staticmethod
    def _is_valid_plan_json(plan_json: Optional[dict]) -> bool:
        """Check if plan_json has the minimum structure for TopologyView."""
        if not plan_json or not isinstance(plan_json, dict):
            return False
        tasks = plan_json.get("tasks")
        return isinstance(tasks, list) and len(tasks) > 0

    @staticmethod
    def _extract_plan_json(plan_text: str) -> Optional[dict]:
        """Try to extract a plan_json object from plan_text.

        LLM may embed JSON in its text output. We find the largest valid
        JSON object that looks like a plan (has tasks[] and participants[]).
        """
        if not plan_text:
            return None
        # Find all JSON-like blocks: outermost { ... }
        candidates = []
        for m in re.finditer(r'\{', plan_text):
            start = m.start()
            depth = 0
            for i in range(start, len(plan_text)):
                if plan_text[i] == '{':
                    depth += 1
                elif plan_text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        candidates.append(plan_text[start:i + 1])
                        break
        # Try candidates from longest to shortest
        candidates.sort(key=len, reverse=True)
        for candidate in candidates:
            try:
                obj = json.loads(candidate)
                if (
                    isinstance(obj, dict)
                    and isinstance(obj.get("tasks"), list)
                    and len(obj["tasks"]) > 0
                ):
                    return obj
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    @staticmethod
    def _build_minimal_plan_json(session: "NegotiationSession") -> dict:
        """Construct a minimal but valid plan_json from session data.

        Every participant who replied gets one task. All tasks are parallel
        (no dependencies). This is the last-resort fallback so TopologyView
        always has something to render.
        """
        participants = []
        tasks = []
        for i, p in enumerate(session.participants):
            if p.state == AgentState.REPLIED:
                participants.append({
                    "agent_id": p.agent_id,
                    "display_name": p.display_name,
                    "role_in_plan": "参与者",
                })
                offer_desc = ""
                if p.offer and p.offer.content:
                    offer_desc = p.offer.content[:100]
                    if len(p.offer.content) > 100:
                        offer_desc += "..."
                tasks.append({
                    "id": f"task_{i + 1}",
                    "title": f"{p.display_name} 的贡献",
                    "description": offer_desc,
                    "assignee_id": p.agent_id,
                    "prerequisites": [],
                    "status": "pending",
                })
        return {
            "summary": (
                session.demand.formulated_text
                or session.demand.raw_intent
                or "协商方案"
            ),
            "participants": participants,
            "tasks": tasks or [{"id": "task_1", "title": "待分配", "description": "", "assignee_id": "unknown", "prerequisites": [], "status": "pending"}],
            "topology": {"edges": []},
        }
