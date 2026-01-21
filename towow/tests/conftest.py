"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_message():
    """Sample message fixture for testing agents."""
    return {
        "type": "test",
        "content": "Hello, Agent!",
        "metadata": {"source": "test"},
    }
