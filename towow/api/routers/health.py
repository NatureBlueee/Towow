"""Health check router."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db

router = APIRouter(prefix="/health")


@router.get("")
async def health_check():
    """Health check endpoint (liveness probe)."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check endpoint (readiness probe).

    Checks database connectivity.
    """
    checks = {
        "database": "unknown",
    }

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"

    # Determine overall status
    all_healthy = all(
        v == "healthy" for v in checks.values()
    )

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
    }
