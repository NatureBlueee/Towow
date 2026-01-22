"""
SSE Event Streaming Router

Provides Server-Sent Events endpoint for real-time event streaming.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from events.recorder import event_recorder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


async def event_generator(
    demand_id: str,
    request: Request,
    last_event_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    SSE event generator.

    Generates events for a specific demand_id with heartbeat support.

    Args:
        demand_id: Demand ID to filter events
        request: FastAPI request for disconnect detection
        last_event_id: Optional event ID for reconnection support
    """
    # Subscribe to events
    queue = event_recorder.subscribe()
    if queue is None:
        raise HTTPException(status_code=503, detail="Server at capacity, please retry later")

    try:
        # First send historical events
        channel_id = f"collab-{demand_id[:8]}" if len(demand_id) >= 8 else f"collab-{demand_id}"

        if last_event_id:
            # Reconnection: start from after specified event ID
            history = event_recorder.get_after(last_event_id)
        else:
            # Full history for this channel
            history = event_recorder.get_by_channel(channel_id)

        for event in history:
            yield f"data: {json.dumps(event)}\n\n"

        # Continuously send new events
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.debug(f"Client disconnected for demand {demand_id}")
                break

            try:
                # Wait for new event (5 second timeout for heartbeat)
                event = await asyncio.wait_for(queue.get(), timeout=5.0)

                # Filter to only send relevant events
                payload = event.get("payload", {})
                event_channel = payload.get("channel_id") or payload.get("channel")
                event_demand = payload.get("demand_id")

                # Match demand_id
                should_send = False
                if event_demand and event_demand == demand_id:
                    should_send = True
                elif event_channel:
                    # Check if channel_id is related to demand_id
                    if len(demand_id) >= 8 and demand_id[:8] in event_channel:
                        should_send = True
                    elif demand_id in event_channel:
                        should_send = True

                if should_send:
                    yield f"data: {json.dumps(event)}\n\n"

            except asyncio.TimeoutError:
                # Send heartbeat comment
                yield ": heartbeat\n\n"

    finally:
        event_recorder.unsubscribe(queue)
        logger.debug(f"Cleaned up SSE connection for demand {demand_id}")


def get_cors_origin_for_sse():
    """从环境变量获取 SSE CORS 源"""
    return os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")[0]


@router.get("/negotiations/{demand_id}/stream")
async def stream_events(
    demand_id: str,
    request: Request,
    last_event_id: Optional[str] = Query(None, description="Event ID for reconnection support")
):
    """
    SSE event stream endpoint.

    GET /api/v1/events/negotiations/{demand_id}/stream

    Streams events for a specific demand in real-time.
    Supports reconnection by providing last_event_id query parameter.

    Args:
        demand_id: Demand ID to stream events for
        request: FastAPI request
        last_event_id: Optional event ID for reconnection

    Returns:
        SSE stream response
    """
    return StreamingResponse(
        event_generator(demand_id, request, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Access-Control-Allow-Origin": get_cors_origin_for_sse(),
        }
    )


@router.get("/negotiations/{demand_id}/recent")
async def get_recent_events(
    demand_id: str,
    count: int = Query(50, ge=1, le=200, description="Number of events to return"),
    after: Optional[str] = Query(None, description="Event ID to start after")
):
    """
    Get recent events (polling fallback).

    GET /api/v1/events/negotiations/{demand_id}/recent?count=50&after=event_id

    Args:
        demand_id: Demand ID to get events for
        count: Number of events to return
        after: Optional event ID to start after

    Returns:
        List of recent events
    """
    channel_id = f"collab-{demand_id[:8]}" if len(demand_id) >= 8 else f"collab-{demand_id}"

    if after:
        events = event_recorder.get_after(after, count)
    else:
        events = event_recorder.get_by_channel(channel_id, count)

    return {
        "events": events,
        "count": len(events),
        "has_more": len(events) == count
    }


@router.get("/health")
async def events_health():
    """
    Event service health check.

    GET /api/v1/events/health

    Returns:
        Health status with subscriber and event counts
    """
    return {
        "status": "healthy",
        "subscribers": len(event_recorder.subscribers),
        "events_in_memory": len(event_recorder.events)
    }
