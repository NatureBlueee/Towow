"""Tests for the CosineResonanceDetector (V1 ResonanceDetector Protocol implementation)."""

from __future__ import annotations

import numpy as np
import pytest

from towow.core.protocols import ResonanceDetector
from towow.hdc.resonance import CosineResonanceDetector


def _normalized(vec: list[float]) -> np.ndarray:
    """Helper: create a normalized float32 vector."""
    v = np.array(vec, dtype=np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def detector() -> CosineResonanceDetector:
    return CosineResonanceDetector()


# ============ Protocol compliance ============


class TestProtocolCompliance:
    def test_is_resonance_detector_protocol(self):
        d = CosineResonanceDetector()
        assert isinstance(d, ResonanceDetector)


# ============ Core behavior ============


class TestCosineResonanceDetector:

    @pytest.mark.asyncio
    async def test_returns_k_star_results(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {
            "a": _normalized([1, 0, 0]),
            "b": _normalized([0, 1, 0]),
            "c": _normalized([0, 0, 1]),
        }
        results = await detector.detect(demand, agents, k_star=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_sorted_descending(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {
            "low": _normalized([0, 1, 0]),
            "high": _normalized([1, 0, 0]),
            "mid": _normalized([1, 1, 0]),
        }
        results = await detector.detect(demand, agents, k_star=3)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_perfect_match_score_one(self, detector):
        demand = _normalized([1, 2, 3])
        agents = {"match": _normalized([1, 2, 3])}
        results = await detector.detect(demand, agents, k_star=1)
        assert len(results) == 1
        assert results[0][0] == "match"
        assert abs(results[0][1] - 1.0) < 1e-5

    @pytest.mark.asyncio
    async def test_orthogonal_score_zero(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {"ortho": _normalized([0, 1, 0])}
        results = await detector.detect(demand, agents, k_star=1)
        assert len(results) == 1
        assert abs(results[0][1]) < 1e-5

    @pytest.mark.asyncio
    async def test_correct_agent_ids_returned(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {
            "alice": _normalized([1, 0.1, 0]),
            "bob": _normalized([0, 1, 0]),
        }
        results = await detector.detect(demand, agents, k_star=1)
        assert results[0][0] == "alice"

    @pytest.mark.asyncio
    async def test_k_star_larger_than_agents(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {
            "only_one": _normalized([1, 0, 0]),
        }
        results = await detector.detect(demand, agents, k_star=10)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_all_agents_returned_when_k_star_equals_count(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {
            "a": _normalized([1, 0, 0]),
            "b": _normalized([0, 1, 0]),
            "c": _normalized([0, 0, 1]),
        }
        results = await detector.detect(demand, agents, k_star=3)
        assert len(results) == 3
        returned_ids = {r[0] for r in results}
        assert returned_ids == {"a", "b", "c"}


# ============ Edge cases ============


class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_empty_agent_vectors(self, detector):
        demand = _normalized([1, 0, 0])
        results = await detector.detect(demand, {}, k_star=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_k_star_zero(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {"a": _normalized([1, 0, 0])}
        results = await detector.detect(demand, agents, k_star=0)
        assert results == []

    @pytest.mark.asyncio
    async def test_k_star_negative(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {"a": _normalized([1, 0, 0])}
        results = await detector.detect(demand, agents, k_star=-1)
        assert results == []

    @pytest.mark.asyncio
    async def test_zero_demand_vector(self, detector):
        demand = np.zeros(3, dtype=np.float32)
        agents = {"a": _normalized([1, 0, 0])}
        results = await detector.detect(demand, agents, k_star=1)
        assert results == []

    @pytest.mark.asyncio
    async def test_zero_agent_vector(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {"zero_agent": np.zeros(3, dtype=np.float32)}
        results = await detector.detect(demand, agents, k_star=1)
        assert len(results) == 1
        assert results[0][1] == 0.0

    @pytest.mark.asyncio
    async def test_high_dimensional_vectors(self, detector):
        rng = np.random.RandomState(42)
        demand = rng.randn(384).astype(np.float32)
        demand /= np.linalg.norm(demand)
        agents = {}
        for i in range(100):
            v = rng.randn(384).astype(np.float32)
            v /= np.linalg.norm(v)
            agents[f"agent_{i}"] = v
        results = await detector.detect(demand, agents, k_star=10)
        assert len(results) == 10
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)
