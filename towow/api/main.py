"""ToWow FastAPI Application."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import admin, demand, events, health
from events.integration import setup_event_recording

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting ToWow API...")

    # Set up event recording integration
    setup_event_recording()
    logger.info("Event recording integration initialized")

    # Initialize demo mode service - TASK-020
    from services.demo_mode import init_demo_service
    init_demo_service()
    logger.info("Demo mode service initialized")

    # Initialize LLM service with fallback - TASK-020
    from services.llm import init_llm_service_with_fallback
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")  # 支持自定义 base_url
    init_llm_service_with_fallback(
        api_key=api_key,
        base_url=base_url,
        timeout=10.0,
        failure_threshold=3,
        recovery_timeout=30.0
    )
    logger.info("LLM service with fallback initialized")

    yield

    # Shutdown
    logger.info("Shutting down ToWow API...")


app = FastAPI(
    title="ToWow API",
    description="AI Agent Collaboration Network API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
def get_cors_origins():
    """从环境变量获取允许的 CORS 源"""
    origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limit middleware - TASK-020
# Only enable in production or when explicitly requested
ENABLE_RATE_LIMIT = os.getenv("ENABLE_RATE_LIMIT", "false").lower() == "true"
if ENABLE_RATE_LIMIT:
    from middleware.rate_limiter import RateLimitMiddleware, RateLimitConfig
    rate_limit_config = RateLimitConfig(
        global_max_concurrent=int(os.getenv("RATE_LIMIT_MAX_CONCURRENT", "100")),
        user_max_requests=int(os.getenv("RATE_LIMIT_USER_MAX", "5")),
        global_queue_size=int(os.getenv("RATE_LIMIT_QUEUE_SIZE", "50")),
    )
    app.add_middleware(RateLimitMiddleware, config=rate_limit_config)
    logger.info("Rate limit middleware enabled")

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(demand.router)
app.include_router(events.router)
app.include_router(admin.router)  # TASK-020: Admin API


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to ToWow API", "version": "0.1.0"}
