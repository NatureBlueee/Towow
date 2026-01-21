"""ToWow FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting ToWow API...")
    yield
    # Shutdown
    print("Shutting down ToWow API...")


app = FastAPI(
    title="ToWow API",
    description="AI Agent Collaboration Network API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to ToWow API", "version": "0.1.0"}
