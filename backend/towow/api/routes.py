"""
API endpoints for the Towow V1 negotiation system.

5 call APIs + 1 WebSocket endpoint.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from towow.core.models import (
    AgentIdentity,
    AgentState,
    DemandSnapshot,
    NegotiationSession,
    NegotiationState,
    SceneDefinition,
    SourceType,
    TraceChain,
    generate_id,
)

from .schemas import (
    AgentResponse,
    ConfirmFormulationRequest,
    CreateSceneRequest,
    NegotiationResponse,
    RegisterAgentRequest,
    SceneResponse,
    SubmitDemandRequest,
    UserActionRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")
ws_router = APIRouter()


# ============ Scene Endpoints ============

@router.post("/scenes", response_model=SceneResponse, status_code=201)
async def create_scene(req: CreateSceneRequest, request: Request):
    state = request.app.state
    scene_id = generate_id("scene")
    scene = SceneDefinition(
        scene_id=scene_id,
        name=req.name,
        description=req.description,
        organizer_id=req.organizer_id,
        expected_responders=req.expected_responders,
        access_policy=req.access_policy,
    )
    state.scenes[scene_id] = scene

    return SceneResponse(
        scene_id=scene.scene_id,
        name=scene.name,
        description=scene.description,
        organizer_id=scene.organizer_id,
        expected_responders=scene.expected_responders,
        access_policy=scene.access_policy.value if hasattr(scene.access_policy, "value") else scene.access_policy,
        status=scene.status.value if hasattr(scene.status, "value") else scene.status,
        agent_ids=scene.agent_ids,
    )


@router.post("/scenes/{scene_id}/agents", response_model=AgentResponse, status_code=201)
async def register_agent(scene_id: str, req: RegisterAgentRequest, request: Request):
    state = request.app.state
    scene = state.scenes.get(scene_id)
    if not scene:
        raise HTTPException(404, f"Scene {scene_id} not found")

    if req.agent_id in scene.agent_ids:
        raise HTTPException(409, f"Agent {req.agent_id} already registered in scene")

    try:
        source = SourceType(req.source_type)
    except ValueError:
        source = SourceType.CUSTOM

    identity = AgentIdentity(
        agent_id=req.agent_id,
        display_name=req.display_name,
        source_type=source,
        scene_id=scene_id,
        metadata=req.profile_data,
    )
    state.agents[req.agent_id] = identity
    state.profiles[req.agent_id] = req.profile_data
    scene.agent_ids.append(req.agent_id)

    return AgentResponse(
        agent_id=req.agent_id,
        display_name=req.display_name,
        scene_id=scene_id,
    )


# ============ Negotiation Endpoints ============

@router.post("/negotiations/submit", response_model=NegotiationResponse, status_code=201)
async def submit_demand(req: SubmitDemandRequest, request: Request):
    state = request.app.state
    scene = state.scenes.get(req.scene_id)
    if not scene:
        raise HTTPException(404, f"Scene {req.scene_id} not found")

    negotiation_id = generate_id("neg")
    demand = DemandSnapshot(
        raw_intent=req.intent,
        user_id=req.user_id,
        scene_id=req.scene_id,
    )
    session = NegotiationSession(
        negotiation_id=negotiation_id,
        demand=demand,
        trace=TraceChain(negotiation_id=negotiation_id),
    )
    state.sessions[negotiation_id] = session

    # Start negotiation as background task
    task = asyncio.create_task(
        _run_negotiation(state, session, scene)
    )
    state.tasks[negotiation_id] = task

    return _session_to_response(session)


@router.post("/negotiations/{negotiation_id}/confirm", response_model=NegotiationResponse)
async def confirm_formulation(
    negotiation_id: str, req: ConfirmFormulationRequest, request: Request,
):
    state = request.app.state
    session = state.sessions.get(negotiation_id)
    if not session:
        raise HTTPException(404, f"Negotiation {negotiation_id} not found")

    if session.state != NegotiationState.FORMULATED:
        raise HTTPException(
            409,
            f"Cannot confirm: negotiation is in state {session.state.value}, expected 'formulated'",
        )

    session.demand.formulated_text = req.confirmed_text
    return _session_to_response(session)


@router.post("/negotiations/{negotiation_id}/action", response_model=NegotiationResponse)
async def user_action(
    negotiation_id: str, req: UserActionRequest, request: Request,
):
    state = request.app.state
    session = state.sessions.get(negotiation_id)
    if not session:
        raise HTTPException(404, f"Negotiation {negotiation_id} not found")

    if req.action == "cancel":
        if session.state == NegotiationState.COMPLETED:
            raise HTTPException(409, "Negotiation already completed")
        session.state = NegotiationState.COMPLETED
        session.metadata["cancelled"] = True
        # Cancel the running background task if any
        task = state.tasks.get(negotiation_id)
        if task and not task.done():
            task.cancel()
    else:
        raise HTTPException(400, f"Unknown action: {req.action}")

    return _session_to_response(session)


@router.get("/negotiations/{negotiation_id}", response_model=NegotiationResponse)
async def get_negotiation(negotiation_id: str, request: Request):
    state = request.app.state
    session = state.sessions.get(negotiation_id)
    if not session:
        raise HTTPException(404, f"Negotiation {negotiation_id} not found")

    return _session_to_response(session)


# ============ WebSocket ============

@ws_router.websocket("/ws/negotiation/{negotiation_id}")
async def negotiation_ws(websocket: WebSocket, negotiation_id: str):
    state = websocket.app.state

    session = state.sessions.get(negotiation_id)
    if not session:
        await websocket.close(code=4004, reason="Negotiation not found")
        return

    ws_manager = state.ws_manager
    agent_id = f"ws_client_{negotiation_id}"
    connected = await ws_manager.connect(websocket, agent_id)
    if not connected:
        return

    channel = f"negotiation:{negotiation_id}"
    await ws_manager.subscribe_channel(agent_id, channel)

    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(agent_id)


# ============ Helpers ============

def _session_to_response(session: NegotiationSession) -> NegotiationResponse:
    participants = []
    for p in session.participants:
        entry = {
            "agent_id": p.agent_id,
            "display_name": p.display_name,
            "resonance_score": p.resonance_score,
            "state": p.state.value,
        }
        if p.offer:
            entry["offer_content"] = p.offer.content
            entry["offer_capabilities"] = p.offer.capabilities
        participants.append(entry)

    return NegotiationResponse(
        negotiation_id=session.negotiation_id,
        state=session.state.value,
        demand_raw=session.demand.raw_intent,
        demand_formulated=session.demand.formulated_text,
        participants=participants,
        plan_output=session.plan_output,
        center_rounds=session.center_rounds,
    )


async def _run_negotiation(
    state: Any,
    session: NegotiationSession,
    scene: SceneDefinition,
) -> None:
    """Run the full negotiation pipeline as a background task."""
    try:
        engine = state.engine
        adapter = state.adapter
        llm_client = state.llm_client

        agent_vectors = {}
        if state.encoder and scene.agent_ids:
            for agent_id in scene.agent_ids:
                profile = state.profiles.get(agent_id, {})
                text_parts = []
                if profile.get("skills"):
                    text_parts.append(", ".join(profile["skills"]))
                if profile.get("bio"):
                    text_parts.append(profile["bio"])
                if profile.get("description"):
                    text_parts.append(profile["description"])
                text = " ".join(text_parts) if text_parts else agent_id
                try:
                    vec = await state.encoder.encode(text)
                    agent_vectors[agent_id] = vec
                except Exception as e:
                    logger.warning(f"Failed to encode agent {agent_id}: {e}")

        await engine.start_negotiation(
            session=session,
            adapter=adapter,
            llm_client=llm_client,
            formulation_skill=state.skills.get("formulation"),
            offer_skill=state.skills.get("offer"),
            center_skill=state.skills.get("center"),
            agent_vectors=agent_vectors or None,
            k_star=scene.expected_responders,
        )

    except Exception as e:
        logger.error(f"Negotiation {session.negotiation_id} failed: {e}", exc_info=True)
        session.metadata["error"] = str(e)
        if session.state != NegotiationState.COMPLETED:
            session.state = NegotiationState.COMPLETED
