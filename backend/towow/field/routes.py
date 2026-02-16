"""
V2 Intent Field HTTP API — deposit intents, match by text, get stats.

Endpoints:
  POST /field/api/deposit  — deposit text into the field
  POST /field/api/match    — match text against the field (Intent level)
  POST /field/api/match-owners — match text against the field (Owner level)
  GET  /field/api/stats    — field statistics

Depends on app.state.field (V2 MemoryField, handles encoding internally).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

field_router = APIRouter(prefix="/field/api", tags=["field"])


# ── Request / Response schemas ──────────────────────────

class DepositRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Intent text to deposit")
    owner: str = Field(..., min_length=1, description="Owner identifier")
    metadata: dict[str, Any] = Field(default_factory=dict)


class DepositResponse(BaseModel):
    intent_id: str
    message: str


class MatchRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Query text to match")
    k: int = Field(default=10, ge=1, le=100)


class MatchResultItem(BaseModel):
    intent_id: str
    score: float
    owner: str
    text: str
    metadata: dict[str, Any]


class OwnerMatchItem(BaseModel):
    owner: str
    score: float
    top_intents: list[MatchResultItem]


class MatchResponse(BaseModel):
    results: list[MatchResultItem]
    query_time_ms: float
    total_intents: int


class OwnerMatchResponse(BaseModel):
    results: list[OwnerMatchItem]
    query_time_ms: float
    total_intents: int
    total_owners: int


class StatsResponse(BaseModel):
    intent_count: int
    owner_count: int


# ── Helpers ─────────────────────────────────────────────

def _get_field(request: Request):
    field = getattr(request.app.state, "field", None)
    if field is None:
        raise HTTPException(status_code=503, detail="Intent field not initialized")
    return field


# ── Endpoints ───────────────────────────────────────────

@field_router.post("/deposit", response_model=DepositResponse)
async def deposit_intent(req: DepositRequest, request: Request):
    """Deposit an intent into the field."""
    field = _get_field(request)
    intent_id = await field.deposit(req.text, req.owner, req.metadata)
    return DepositResponse(
        intent_id=intent_id,
        message=f"Deposited intent for owner '{req.owner}'",
    )


@field_router.post("/match", response_model=MatchResponse)
async def match_intents(req: MatchRequest, request: Request):
    """Match text against the field, return Intent-level results."""
    field = _get_field(request)
    t0 = time.time()
    results = await field.match(req.text, req.k)
    query_time_ms = (time.time() - t0) * 1000
    total = await field.count()

    return MatchResponse(
        results=[
            MatchResultItem(
                intent_id=r.intent_id, score=r.score,
                owner=r.owner, text=r.text, metadata=r.metadata,
            )
            for r in results
        ],
        query_time_ms=round(query_time_ms, 2),
        total_intents=total,
    )


@field_router.post("/match-owners", response_model=OwnerMatchResponse)
async def match_owners(req: MatchRequest, request: Request):
    """Match text against the field, return Owner-level aggregated results."""
    field = _get_field(request)
    t0 = time.time()
    results = await field.match_owners(req.text, req.k)
    query_time_ms = (time.time() - t0) * 1000
    total_intents = await field.count()
    total_owners = await field.count_owners()

    return OwnerMatchResponse(
        results=[
            OwnerMatchItem(
                owner=r.owner, score=r.score,
                top_intents=[
                    MatchResultItem(
                        intent_id=i.intent_id, score=i.score,
                        owner=i.owner, text=i.text, metadata=i.metadata,
                    )
                    for i in r.intents
                ],
            )
            for r in results
        ],
        query_time_ms=round(query_time_ms, 2),
        total_intents=total_intents,
        total_owners=total_owners,
    )


@field_router.get("/stats", response_model=StatsResponse)
async def field_stats(request: Request):
    """Return field statistics."""
    field = _get_field(request)
    return StatsResponse(
        intent_count=await field.count(),
        owner_count=await field.count_owners(),
    )


class LoadProfilesResponse(BaseModel):
    loaded: int
    total_intents: int
    total_owners: int
    message: str


@field_router.post("/load-profiles", response_model=LoadProfilesResponse)
async def load_profiles(request: Request):
    """Batch-load agent profiles from JSON files into the field."""
    from towow.field.profile_loader import load_all_profiles

    field = _get_field(request)

    existing = await field.count()
    if existing > 0:
        return LoadProfilesResponse(
            loaded=0,
            total_intents=existing,
            total_owners=await field.count_owners(),
            message=f"Field already has {existing} intents, skipped loading",
        )

    profiles = load_all_profiles()
    loaded = 0
    for owner, text in profiles.items():
        try:
            await field.deposit(text, owner)
            loaded += 1
        except ValueError:
            continue

    logger.info("Loaded %d profiles into field", loaded)
    return LoadProfilesResponse(
        loaded=loaded,
        total_intents=await field.count(),
        total_owners=await field.count_owners(),
        message=f"Loaded {loaded} agent profiles",
    )
