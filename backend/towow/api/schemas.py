"""
Pydantic request/response models for the Towow V1 API.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ============ Scene ============

class CreateSceneRequest(BaseModel):
    name: str
    description: str
    organizer_id: str
    expected_responders: int = 10
    access_policy: str = "open"


class SceneResponse(BaseModel):
    scene_id: str
    name: str
    description: str
    organizer_id: str
    expected_responders: int
    access_policy: str
    status: str
    agent_ids: list[str]


# ============ Agent ============

class RegisterAgentRequest(BaseModel):
    agent_id: str
    display_name: str
    source_type: str = "claude"
    profile_data: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    agent_id: str
    display_name: str
    scene_id: str


# ============ Negotiation ============

class SubmitDemandRequest(BaseModel):
    scene_id: str
    user_id: str
    intent: str
    k_star: Optional[int] = None
    min_score: Optional[float] = None


class ConfirmFormulationRequest(BaseModel):
    confirmed_text: Optional[str] = None


class UserActionRequest(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class NegotiationResponse(BaseModel):
    negotiation_id: str
    state: str
    demand_raw: str
    demand_formulated: Optional[str] = None
    participants: list[dict[str, Any]] = Field(default_factory=list)
    plan_output: Optional[str] = None
    center_rounds: int = 0
    parent_negotiation_id: Optional[str] = None
    sub_session_ids: list[str] = Field(default_factory=list)
    depth: int = 0


class PlanResponse(BaseModel):
    negotiation_id: str
    plan_text: str
    plan_json: Optional[dict] = None
    center_rounds: int
    participating_agents: list[str]
