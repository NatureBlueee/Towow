"""Tests for the CosineResonanceDetector (V1 ResonanceDetector Protocol implementation).

Updated for PLAN-003: detect() now returns (activated, filtered) tuple
with min_score parameter for threshold-based filtering.
"""

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


# ============ Core behavior (tuple return) ============


class TestCosineResonanceDetector:

    @pytest.mark.asyncio
    async def test_returns_tuple(self, detector):
        """detect() must return a (activated, filtered) tuple."""
        demand = _normalized([1, 0, 0])
        agents = {"a": _normalized([1, 0, 0])}
        result = await detector.detect(demand, agents, k_star=1)
        assert isinstance(result, tuple)
        assert len(result) == 2
        activated, filtered = result
        assert isinstance(activated, list)
        assert isinstance(filtered, list)

    @pytest.mark.asyncio
    async def test_returns_k_star_activated(self, detector):
        """Activated list is capped at k_star."""
        demand = _normalized([1, 0, 0])
        agents = {
            "a": _normalized([1, 0, 0]),
            "b": _normalized([0.9, 0.1, 0]),
            "c": _normalized([0.8, 0.2, 0]),
        }
        activated, filtered = await detector.detect(demand, agents, k_star=2, min_score=0.0)
        assert len(activated) == 2

    @pytest.mark.asyncio
    async def test_sorted_descending(self, detector):
        """Activated results are sorted by score descending."""
        demand = _normalized([1, 0, 0])
        agents = {
            "low": _normalized([0, 1, 0]),
            "high": _normalized([1, 0, 0]),
            "mid": _normalized([1, 1, 0]),
        }
        activated, _ = await detector.detect(demand, agents, k_star=3, min_score=0.0)
        scores = [s for _, s in activated]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_perfect_match_score_one(self, detector):
        """Identical vectors should produce score ~1.0."""
        demand = _normalized([1, 2, 3])
        agents = {"match": _normalized([1, 2, 3])}
        activated, filtered = await detector.detect(demand, agents, k_star=1, min_score=0.0)
        assert len(activated) == 1
        assert activated[0][0] == "match"
        assert abs(activated[0][1] - 1.0) < 1e-5
        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_orthogonal_score_zero(self, detector):
        """Orthogonal vectors should produce score ~0.0."""
        demand = _normalized([1, 0, 0])
        agents = {"ortho": _normalized([0, 1, 0])}
        activated, filtered = await detector.detect(demand, agents, k_star=1, min_score=0.0)
        assert len(activated) == 1
        assert abs(activated[0][1]) < 1e-5

    @pytest.mark.asyncio
    async def test_correct_agent_ids_returned(self, detector):
        """Highest-scoring agent should be first in activated."""
        demand = _normalized([1, 0, 0])
        agents = {
            "alice": _normalized([1, 0.1, 0]),
            "bob": _normalized([0, 1, 0]),
        }
        activated, _ = await detector.detect(demand, agents, k_star=1, min_score=0.0)
        assert activated[0][0] == "alice"

    @pytest.mark.asyncio
    async def test_k_star_larger_than_agents(self, detector):
        """If k_star > agent count, activated has all agents."""
        demand = _normalized([1, 0, 0])
        agents = {
            "only_one": _normalized([1, 0, 0]),
        }
        activated, filtered = await detector.detect(demand, agents, k_star=10, min_score=0.0)
        assert len(activated) == 1
        assert len(filtered) == 0

    @pytest.mark.asyncio
    async def test_all_agents_returned_when_k_star_equals_count(self, detector):
        """When k_star == agent count and min_score=0, all are activated."""
        demand = _normalized([1, 0, 0])
        agents = {
            "a": _normalized([1, 0, 0]),
            "b": _normalized([0, 1, 0]),
            "c": _normalized([0, 0, 1]),
        }
        activated, filtered = await detector.detect(demand, agents, k_star=3, min_score=0.0)
        assert len(activated) == 3
        returned_ids = {r[0] for r in activated}
        assert returned_ids == {"a", "b", "c"}
        assert len(filtered) == 0


# ============ min_score filtering ============


class TestMinScoreFiltering:
    """Tests for the min_score threshold that splits activated/filtered."""

    @pytest.mark.asyncio
    async def test_min_score_zero_returns_all_in_activated(self, detector):
        """min_score=0.0 means everything goes to activated (backward-compatible)."""
        demand = _normalized([1, 0, 0])
        agents = {
            "high": _normalized([1, 0, 0]),      # score ~1.0
            "low": _normalized([0, 1, 0]),        # score ~0.0
            "neg": _normalized([-1, 0, 0]),       # score ~-1.0
        }
        activated, filtered = await detector.detect(demand, agents, k_star=10, min_score=0.0)
        # All agents with score >= 0.0 go to activated
        # The negative-score agent goes to filtered
        activated_ids = {aid for aid, _ in activated}
        filtered_ids = {aid for aid, _ in filtered}
        assert "high" in activated_ids
        assert "low" in activated_ids  # score 0.0 >= 0.0
        assert "neg" in filtered_ids   # score < 0.0

    @pytest.mark.asyncio
    async def test_min_score_splits_correctly(self, detector):
        """min_score=0.5 should split agents at the threshold."""
        demand = _normalized([1, 0, 0])
        agents = {
            "perfect": _normalized([1, 0, 0]),     # score ~1.0 -> activated
            "mid": _normalized([1, 1, 0]),          # score ~0.707 -> activated
            "low": _normalized([0, 1, 0]),           # score ~0.0 -> filtered
        }
        activated, filtered = await detector.detect(demand, agents, k_star=10, min_score=0.5)
        activated_ids = {aid for aid, _ in activated}
        filtered_ids = {aid for aid, _ in filtered}
        assert "perfect" in activated_ids
        assert "mid" in activated_ids
        assert "low" in filtered_ids

    @pytest.mark.asyncio
    async def test_min_score_one_filters_everything(self, detector):
        """min_score=1.0 filters all agents unless they are perfect matches."""
        demand = _normalized([1, 0, 0])
        agents = {
            "almost": _normalized([0.999, 0.001, 0]),  # score close to but not exactly 1.0
            "low": _normalized([0, 1, 0]),
        }
        activated, filtered = await detector.detect(demand, agents, k_star=10, min_score=1.0)
        # Both should be filtered since cosine sim < 1.0 for non-identical vectors
        assert len(activated) == 0
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_min_score_exact_match_at_one(self, detector):
        """A perfect score=1.0 agent passes min_score=1.0."""
        demand = _normalized([1, 2, 3])
        agents = {"exact": _normalized([1, 2, 3])}
        activated, filtered = await detector.detect(demand, agents, k_star=10, min_score=1.0)
        # Perfect match score is 1.0, should pass min_score=1.0
        assert len(activated) == 1
        assert activated[0][0] == "exact"
        assert abs(activated[0][1] - 1.0) < 1e-5

    @pytest.mark.asyncio
    async def test_k_star_limits_activated_count(self, detector):
        """k_star caps activated even when many agents pass min_score."""
        demand = _normalized([1, 0, 0])
        agents = {
            f"agent_{i}": _normalized([1, 0.01 * i, 0])  # All have high similarity
            for i in range(10)
        }
        activated, filtered = await detector.detect(demand, agents, k_star=3, min_score=0.0)
        assert len(activated) == 3
        # The rest go to... nowhere, they just don't make the k_star cut
        # But they are not "filtered" (score >= min_score), they're just above k_star limit
        # Per PLAN-003 semantics: activated is capped at k_star, overflow does NOT go to filtered

    @pytest.mark.asyncio
    async def test_k_star_plus_min_score_combination(self, detector):
        """k_star and min_score work together: min_score filters first, then k_star caps."""
        demand = _normalized([1, 0, 0])
        agents = {
            "a": _normalized([1, 0, 0]),           # score ~1.0 -> activated
            "b": _normalized([1, 1, 0]),            # score ~0.707 -> activated (but may be capped by k_star)
            "c": _normalized([0, 1, 0]),            # score ~0.0 -> filtered
            "d": _normalized([-1, 0, 0]),           # score ~-1.0 -> filtered
        }
        activated, filtered = await detector.detect(demand, agents, k_star=1, min_score=0.5)
        # Only 2 pass min_score (a and b), but k_star=1 caps at 1
        assert len(activated) == 1
        assert activated[0][0] == "a"  # highest score
        # filtered contains agents below min_score
        filtered_ids = {aid for aid, _ in filtered}
        assert "c" in filtered_ids
        assert "d" in filtered_ids

    @pytest.mark.asyncio
    async def test_filtered_sorted_descending(self, detector):
        """Filtered results are also sorted by score descending."""
        demand = _normalized([1, 0, 0])
        agents = {
            "f1": _normalized([0.3, 0.7, 0]),     # low positive sim
            "f2": _normalized([0, 1, 0]),           # ~0.0 sim
            "f3": _normalized([-0.5, 0.5, 0]),     # negative sim
        }
        activated, filtered = await detector.detect(demand, agents, k_star=10, min_score=0.9)
        # All should be filtered (none have score >= 0.9)
        assert len(activated) == 0
        assert len(filtered) == 3
        scores = [s for _, s in filtered]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_default_min_score_is_zero(self, detector):
        """Not passing min_score should default to 0.0 (backward-compatible)."""
        demand = _normalized([1, 0, 0])
        agents = {
            "a": _normalized([1, 0, 0]),
            "b": _normalized([0.5, 0.5, 0]),
        }
        # Call without min_score
        activated, filtered = await detector.detect(demand, agents, k_star=10)
        # All non-negative agents go to activated
        assert len(activated) == 2
        assert len(filtered) == 0


# ============ Edge cases ============


class TestEdgeCases:

    @pytest.mark.asyncio
    async def test_empty_agent_vectors(self, detector):
        demand = _normalized([1, 0, 0])
        activated, filtered = await detector.detect(demand, {}, k_star=5)
        assert activated == []
        assert filtered == []

    @pytest.mark.asyncio
    async def test_k_star_zero(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {"a": _normalized([1, 0, 0])}
        activated, filtered = await detector.detect(demand, agents, k_star=0)
        assert activated == []
        assert filtered == []

    @pytest.mark.asyncio
    async def test_k_star_negative(self, detector):
        demand = _normalized([1, 0, 0])
        agents = {"a": _normalized([1, 0, 0])}
        activated, filtered = await detector.detect(demand, agents, k_star=-1)
        assert activated == []
        assert filtered == []

    @pytest.mark.asyncio
    async def test_zero_demand_vector(self, detector):
        demand = np.zeros(3, dtype=np.float32)
        agents = {"a": _normalized([1, 0, 0])}
        activated, filtered = await detector.detect(demand, agents, k_star=1)
        assert activated == []
        assert filtered == []

    @pytest.mark.asyncio
    async def test_zero_agent_vector(self, detector):
        """Agent with zero vector gets score 0.0."""
        demand = _normalized([1, 0, 0])
        agents = {"zero_agent": np.zeros(3, dtype=np.float32)}
        activated, filtered = await detector.detect(demand, agents, k_star=1, min_score=0.0)
        assert len(activated) == 1
        assert activated[0][1] == 0.0

    @pytest.mark.asyncio
    async def test_zero_agent_vector_filtered_by_min_score(self, detector):
        """Agent with zero vector (score=0.0) is filtered when min_score > 0."""
        demand = _normalized([1, 0, 0])
        agents = {"zero_agent": np.zeros(3, dtype=np.float32)}
        activated, filtered = await detector.detect(demand, agents, k_star=1, min_score=0.5)
        assert len(activated) == 0
        assert len(filtered) == 1
        assert filtered[0][0] == "zero_agent"

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
        activated, filtered = await detector.detect(demand, agents, k_star=10, min_score=0.0)
        # activated contains agents with score >= min_score, capped at k_star
        # filtered contains agents with score < min_score
        # Agents above min_score but beyond k_star cap are in neither list (by design)
        assert len(activated) <= 10  # k_star cap
        assert len(activated) + len(filtered) <= 100
        # Activated scores are descending
        if activated:
            scores = [s for _, s in activated]
            assert scores == sorted(scores, reverse=True)
        # Filtered scores are descending
        if filtered:
            fscores = [s for _, s in filtered]
            assert fscores == sorted(fscores, reverse=True)
