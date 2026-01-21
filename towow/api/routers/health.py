"""Health check router."""

from fastapi import APIRouter

router = APIRouter(prefix="/health")


@router.get("")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    # TODO: Add database and external service checks
    return {"status": "ready"}
