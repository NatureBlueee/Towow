"""
Cosine resonance detector — V1 implementation of the ResonanceDetector Protocol.

Uses cosine similarity to rank agents by resonance with a demand vector.
Implements the k* mechanism: returns top-k* agents sorted by score.
"""

from __future__ import annotations

import numpy as np

from towow.core.protocols import Vector


class CosineResonanceDetector:
    """
    V1 ResonanceDetector: cosine similarity ranking.

    Satisfies the ResonanceDetector Protocol defined in core/protocols.py.
    Stateless — pure function from (demand_vector, agent_vectors, k*) to results.
    """

    async def detect(
        self,
        demand_vector: Vector,
        agent_vectors: dict[str, Vector],
        k_star: int,
        min_score: float = 0.0,
    ) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        """
        Detect resonance between demand and agents.

        Returns (activated, filtered):
        - activated: agents with score >= min_score, sorted descending, max k_star
        - filtered: agents with score < min_score, sorted descending

        When min_score=0.0 (default), all agents go to activated (backward-compatible).
        """
        if k_star <= 0 or not agent_vectors:
            return ([], [])

        demand_norm = np.linalg.norm(demand_vector)
        if demand_norm < 1e-10:
            return ([], [])

        results: list[tuple[str, float]] = []
        for agent_id, agent_vec in agent_vectors.items():
            agent_norm = np.linalg.norm(agent_vec)
            if agent_norm < 1e-10:
                results.append((agent_id, 0.0))
                continue
            sim = float(
                np.dot(demand_vector, agent_vec) / (demand_norm * agent_norm)
            )
            results.append((agent_id, sim))

        results.sort(key=lambda x: x[1], reverse=True)

        activated = [(aid, score) for aid, score in results if score >= min_score][:k_star]
        filtered = [(aid, score) for aid, score in results if score < min_score]

        return (activated, filtered)
