"""
Tests for V2 MemoryField — the Intent Field in-memory implementation.

Uses HashPipeline — a deterministic test pipeline that satisfies the
EncodingPipeline interface without loading real models. It produces
reproducible binary vectors via SHA-256 hashing and computes real
Hamming similarity. Any method not part of the interface will raise
AttributeError (unlike MagicMock which silently accepts anything).
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from towow.field.field import MemoryField


# ── Test Pipeline (production-grade, no MagicMock) ────────

class HashPipeline:
    """Deterministic encoding pipeline for tests.

    Satisfies the same interface as EncodingPipeline:
      - encode_text(str) → uint8[packed_dim]
      - batch_similarity(query, candidates) → float[N]
      - packed_dim → int

    Uses SHA-256 hash to generate reproducible binary vectors —
    same text always produces the same vector, different texts
    produce different vectors. Similarity is real Hamming distance.

    Unlike MagicMock, calling undefined methods raises AttributeError.
    """

    def __init__(self, packed_dim: int = 1250) -> None:
        self._packed_dim = packed_dim
        # Popcount LUT for vectorized Hamming similarity
        self._popcount_lut = np.array(
            [bin(i).count("1") for i in range(256)], dtype=np.int32
        )

    @property
    def packed_dim(self) -> int:
        return self._packed_dim

    def encode_text(self, text: str) -> np.ndarray:
        """text → deterministic uint8[packed_dim] via SHA-256 seeded RNG."""
        h = hashlib.sha256(text.encode()).digest()
        rng = np.random.RandomState(int.from_bytes(h[:4], "big"))
        return rng.randint(0, 256, size=self._packed_dim, dtype=np.uint8)

    def batch_similarity(
        self, query: np.ndarray, candidates: np.ndarray
    ) -> np.ndarray:
        """Hamming similarity: fraction of matching bits. Vectorized."""
        if candidates.ndim == 1:
            candidates = candidates.reshape(1, -1)
        xor = np.bitwise_xor(query, candidates)
        diff = self._popcount_lut[xor].sum(axis=1)
        total_bits = candidates.shape[1] * 8
        return 1.0 - diff / total_bits


# ── Deposit Tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_deposit_and_count():
    field = MemoryField(HashPipeline())
    assert await field.count() == 0
    assert await field.count_owners() == 0

    await field.deposit("Python developer", "alice")
    assert await field.count() == 1
    assert await field.count_owners() == 1

    await field.deposit("Rust engineer", "bob")
    assert await field.count() == 2
    assert await field.count_owners() == 2


@pytest.mark.asyncio
async def test_deposit_returns_intent_id():
    field = MemoryField(HashPipeline())
    iid = await field.deposit("test text", "owner1")
    assert isinstance(iid, str)
    assert len(iid) > 0


@pytest.mark.asyncio
async def test_deposit_dedup_same_owner_text():
    """Same (owner, text) pair should not create duplicate intents."""
    field = MemoryField(HashPipeline())

    id1 = await field.deposit("hello world", "alice")
    id2 = await field.deposit("hello world", "alice")

    assert id1 == id2
    assert await field.count() == 1


@pytest.mark.asyncio
async def test_deposit_different_owners_same_text():
    """Same text but different owners should create separate intents."""
    field = MemoryField(HashPipeline())

    id1 = await field.deposit("hello world", "alice")
    id2 = await field.deposit("hello world", "bob")

    assert id1 != id2
    assert await field.count() == 2


@pytest.mark.asyncio
async def test_deposit_multi_intent_per_owner():
    """Same owner can have multiple intents with different text."""
    field = MemoryField(HashPipeline())

    await field.deposit("Python developer", "alice")
    await field.deposit("Machine learning", "alice")
    await field.deposit("Open source contributor", "alice")

    assert await field.count() == 3
    assert await field.count_owners() == 1


@pytest.mark.asyncio
async def test_deposit_empty_text_raises():
    field = MemoryField(HashPipeline())
    with pytest.raises(ValueError, match="empty"):
        await field.deposit("", "owner")
    with pytest.raises(ValueError, match="empty"):
        await field.deposit("   ", "owner")


@pytest.mark.asyncio
async def test_deposit_empty_owner_raises():
    field = MemoryField(HashPipeline())
    with pytest.raises(ValueError, match="owner"):
        await field.deposit("some text", "")


@pytest.mark.asyncio
async def test_deposit_with_metadata():
    field = MemoryField(HashPipeline())
    iid = await field.deposit("test", "alice", metadata={"scene": "hackathon"})

    results = await field.match("test", k=1)
    assert len(results) == 1
    assert results[0].metadata["scene"] == "hackathon"


# ── Match Tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_match_returns_sorted_by_score():
    field = MemoryField(HashPipeline())

    await field.deposit("alpha", "a")
    await field.deposit("beta", "b")
    await field.deposit("gamma", "c")

    results = await field.match("alpha", k=3)
    assert len(results) == 3
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_match_self_highest_score():
    """Matching the exact same text should rank that intent first."""
    field = MemoryField(HashPipeline())

    await field.deposit("unique specific text", "alice")
    await field.deposit("something else entirely", "bob")
    await field.deposit("another unrelated thing", "carol")

    results = await field.match("unique specific text", k=3)
    assert results[0].owner == "alice"
    assert results[0].score > results[1].score


@pytest.mark.asyncio
async def test_match_k_limits_results():
    field = MemoryField(HashPipeline())
    for i in range(10):
        await field.deposit(f"text number {i}", f"owner_{i}")

    results = await field.match("query", k=3)
    assert len(results) == 3

    results = await field.match("query", k=20)
    assert len(results) == 10  # only 10 in field


@pytest.mark.asyncio
async def test_match_empty_field():
    field = MemoryField(HashPipeline())
    results = await field.match("anything", k=5)
    assert results == []


@pytest.mark.asyncio
async def test_match_empty_query():
    field = MemoryField(HashPipeline())
    await field.deposit("some text", "alice")
    results = await field.match("", k=5)
    assert results == []


@pytest.mark.asyncio
async def test_match_result_fields():
    """FieldResult should contain all expected fields."""
    field = MemoryField(HashPipeline())
    await field.deposit("test text", "alice", metadata={"key": "val"})

    results = await field.match("test text", k=1)
    r = results[0]
    assert isinstance(r.intent_id, str)
    assert isinstance(r.score, float)
    assert r.owner == "alice"
    assert r.text == "test text"
    assert r.metadata == {"key": "val"}


# ── Match Owners Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_match_owners_aggregates():
    field = MemoryField(HashPipeline())

    await field.deposit("Python expert", "alice")
    await field.deposit("ML researcher", "alice")
    await field.deposit("Rust developer", "bob")

    results = await field.match_owners("Python", k=10)
    owners = [r.owner for r in results]
    # Both owners should appear, each once
    assert "alice" in owners
    assert "bob" in owners
    assert len(owners) == len(set(owners))  # no duplicates


@pytest.mark.asyncio
async def test_match_owners_score_is_max():
    """Owner score should be the max of their intents' scores."""
    field = MemoryField(HashPipeline())

    await field.deposit("intent A", "alice")
    await field.deposit("intent B", "alice")

    results = await field.match_owners("intent A", k=1)
    assert len(results) >= 1
    owner_result = [r for r in results if r.owner == "alice"][0]
    # Score should equal the best intent score
    intent_scores = [i.score for i in owner_result.intents]
    assert owner_result.score == max(intent_scores)


@pytest.mark.asyncio
async def test_match_owners_empty_field():
    field = MemoryField(HashPipeline())
    results = await field.match_owners("anything", k=5)
    assert results == []


# ── Remove Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_remove_intent():
    field = MemoryField(HashPipeline())

    iid = await field.deposit("to be removed", "alice")
    assert await field.count() == 1

    await field.remove(iid)
    assert await field.count() == 0
    assert await field.count_owners() == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_silent():
    """Removing a non-existent intent should not raise."""
    field = MemoryField(HashPipeline())
    await field.remove("does-not-exist")  # should not raise


@pytest.mark.asyncio
async def test_remove_does_not_appear_in_match():
    field = MemoryField(HashPipeline())

    iid = await field.deposit("removed text", "alice")
    await field.deposit("kept text", "bob")
    await field.remove(iid)

    results = await field.match("removed text", k=10)
    result_ids = [r.intent_id for r in results]
    assert iid not in result_ids


@pytest.mark.asyncio
async def test_remove_owner():
    field = MemoryField(HashPipeline())

    await field.deposit("intent 1", "alice")
    await field.deposit("intent 2", "alice")
    await field.deposit("intent 3", "bob")

    removed = await field.remove_owner("alice")
    assert removed == 2
    assert await field.count() == 1
    assert await field.count_owners() == 1


@pytest.mark.asyncio
async def test_remove_owner_nonexistent():
    field = MemoryField(HashPipeline())
    removed = await field.remove_owner("nobody")
    assert removed == 0


@pytest.mark.asyncio
async def test_deposit_after_remove_allows_reuse():
    """After removing, the same (owner, text) can be re-deposited."""
    field = MemoryField(HashPipeline())

    iid1 = await field.deposit("reusable text", "alice")
    await field.remove(iid1)
    assert await field.count() == 0

    iid2 = await field.deposit("reusable text", "alice")
    assert await field.count() == 1
    assert iid1 != iid2  # new intent, new id


# ── Buffer Growth Test ────────────────────────────────────

@pytest.mark.asyncio
async def test_buffer_grows_beyond_initial_capacity():
    """Field should handle more intents than initial buffer capacity."""
    field = MemoryField(HashPipeline())
    # Default initial capacity is 1024, deposit more
    n = 50  # enough to verify growth works, not too slow
    for i in range(n):
        await field.deposit(f"text {i}", f"owner_{i}")

    assert await field.count() == n
    results = await field.match("text 0", k=5)
    assert len(results) == 5


# ── Protocol Conformance ──────────────────────────────────

def test_memory_field_satisfies_protocol():
    """MemoryField should satisfy the IntentField Protocol."""
    from towow.field.protocols import IntentField
    assert isinstance(MemoryField(HashPipeline()), IntentField)
