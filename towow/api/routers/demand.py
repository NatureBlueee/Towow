"""
Demand API Router

Handles demand submission and status queries.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from events.recorder import event_recorder

logger = logging.getLogger(__name__)

# 存储活跃任务的集合
_active_tasks: Set[asyncio.Task] = set()


def _task_done_callback(task: asyncio.Task):
    """任务完成回调，处理异常和清理"""
    _active_tasks.discard(task)
    if task.cancelled():
        logger.info(f"Task {task.get_name()} was cancelled")
    elif task.exception():
        logger.error(f"Task {task.get_name()} failed with exception: {task.exception()}")

router = APIRouter(prefix="/api/v1/demand", tags=["demand"])


class DemandSubmitRequest(BaseModel):
    """Request model for demand submission."""
    raw_input: str
    user_id: Optional[str] = "anonymous"


class DemandSubmitResponse(BaseModel):
    """Response model for demand submission."""
    demand_id: str
    channel_id: str
    status: str
    understanding: Dict[str, Any]


# In-memory demand storage
_demands: Dict[str, Dict] = {}


@router.post("/submit", response_model=DemandSubmitResponse)
async def submit_demand(request: DemandSubmitRequest):
    """
    Submit a new demand.

    POST /api/v1/demand/submit

    Args:
        request: Demand submission request with raw_input and optional user_id

    Returns:
        Demand ID, channel ID, status, and initial understanding
    """
    try:
        # Generate demand_id
        demand_id = f"d-{uuid4().hex[:8]}"
        channel_id = f"collab-{demand_id[2:]}"

        # Store demand
        _demands[demand_id] = {
            "demand_id": demand_id,
            "channel_id": channel_id,
            "raw_input": request.raw_input,
            "user_id": request.user_id,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat()
        }

        # Simple demand understanding (MVP stage)
        understanding = {
            "surface_demand": request.raw_input,
            "confidence": "high"
        }

        # Record demand understood event
        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.demand.understood",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "demand_id": demand_id,
                "channel_id": channel_id,
                "surface_demand": understanding["surface_demand"],
                "confidence": understanding["confidence"]
            }
        })

        # Trigger mock negotiation flow asynchronously
        task = asyncio.create_task(
            trigger_mock_negotiation(demand_id, channel_id, request.raw_input),
            name=f"negotiation-{demand_id}"
        )
        task.add_done_callback(_task_done_callback)
        _active_tasks.add(task)

        return DemandSubmitResponse(
            demand_id=demand_id,
            channel_id=channel_id,
            status="processing",
            understanding=understanding
        )

    except Exception as e:
        logger.error(f"Failed to submit demand: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def trigger_mock_negotiation(demand_id: str, channel_id: str, raw_input: str):
    """
    Trigger mock negotiation flow (for demo purposes).

    In MVP stage, simulates the full negotiation flow with events.

    Args:
        demand_id: Demand ID
        channel_id: Channel ID
        raw_input: Original demand text
    """
    try:
        # Wait 2 seconds to simulate filtering
        await asyncio.sleep(2)

        # Filter completed event
        candidates = [
            {"agent_id": "user_agent_bob", "reason": "venue resources"},
            {"agent_id": "user_agent_alice", "reason": "technical expertise"},
            {"agent_id": "user_agent_charlie", "reason": "event planning"},
        ]

        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.filter.completed",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "demand_id": demand_id,
                "channel_id": channel_id,
                "candidates": candidates
            }
        })

        # Wait 1 second, simulate response collection
        await asyncio.sleep(1)

        # Send offer events
        for candidate in candidates:
            await asyncio.sleep(1)
            await event_recorder.record({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": "towow.offer.submitted",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "channel_id": channel_id,
                    "demand_id": demand_id,
                    "agent_id": candidate["agent_id"],
                    "decision": "participate",
                    "contribution": f"Willing to contribute {candidate['reason']}"
                }
            })

        # Wait 1 second, generate proposal
        await asyncio.sleep(1)

        summary_text = raw_input[:30] + "..." if len(raw_input) > 30 else raw_input
        proposal = {
            "summary": f"Collaboration plan for '{summary_text}'",
            "assignments": [
                {"agent_id": "user_agent_bob", "role": "Venue Provider", "responsibility": "Provide meeting room for 30 people"},
                {"agent_id": "user_agent_alice", "role": "Tech Speaker", "responsibility": "30-minute AI technology sharing"},
                {"agent_id": "user_agent_charlie", "role": "Event Planner", "responsibility": "Event flow design"},
            ],
            "timeline": "To be determined",
            "confidence": "high"
        }

        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.proposal.distributed",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "channel_id": channel_id,
                "demand_id": demand_id,
                "proposal": proposal,
                "round": 1
            }
        })

        # Wait 2 seconds, negotiation complete
        await asyncio.sleep(2)

        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.proposal.finalized",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "channel_id": channel_id,
                "demand_id": demand_id,
                "proposal": proposal,
                "participants": ["user_agent_bob", "user_agent_alice", "user_agent_charlie"],
                "rounds": 1
            }
        })

        # Update status
        if demand_id in _demands:
            _demands[demand_id]["status"] = "completed"

        logger.info(f"Mock negotiation completed for demand {demand_id}")

    except Exception as e:
        logger.error(f"Mock negotiation error: {e}")


@router.get("/{demand_id}")
async def get_demand(demand_id: str):
    """
    Get demand details.

    GET /api/v1/demand/{demand_id}

    Args:
        demand_id: Demand ID to retrieve

    Returns:
        Demand details
    """
    if demand_id not in _demands:
        raise HTTPException(status_code=404, detail="Demand not found")

    return _demands[demand_id]


@router.get("/{demand_id}/status")
async def get_demand_status(demand_id: str):
    """
    Get demand status.

    GET /api/v1/demand/{demand_id}/status

    Args:
        demand_id: Demand ID to check status

    Returns:
        Status information
    """
    if demand_id not in _demands:
        raise HTTPException(status_code=404, detail="Demand not found")

    demand = _demands[demand_id]
    return {
        "demand_id": demand_id,
        "status": demand.get("status", "unknown"),
        "current_round": 1
    }


async def cleanup_tasks():
    """清理所有活跃任务（在 shutdown 时调用）"""
    if not _active_tasks:
        return

    logger.info(f"Cleaning up {len(_active_tasks)} active tasks")
    for task in _active_tasks:
        task.cancel()
    await asyncio.gather(*_active_tasks, return_exceptions=True)
    _active_tasks.clear()
    logger.info("All tasks cleaned up")
