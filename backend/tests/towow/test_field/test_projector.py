"""
Tests for SimHashProjector and bundle_binary.

Pure numpy, no model loading.
"""

import numpy as np
import pytest

from towow.field.projector import SimHashProjector, bundle_binary


class TestSimHashProjector:

    def setup_method(self):
        self.proj = SimHashProjector(input_dim=768, D=10_000, seed=42)

    def test_project_output_shape(self):
        dense = np.random.randn(768).astype(np.float32)
        packed = self.proj.project(dense)
        assert packed.dtype == np.uint8
        assert packed.shape == (1250,)  # (10000+7)//8

    def test_project_deterministic(self):
        dense = np.random.randn(768).astype(np.float32)
        a = self.proj.project(dense)
        b = self.proj.project(dense)
        np.testing.assert_array_equal(a, b)

    def test_project_different_inputs_differ(self):
        a = self.proj.project(np.ones(768, dtype=np.float32))
        b = self.proj.project(-np.ones(768, dtype=np.float32))
        assert not np.array_equal(a, b)

    def test_batch_project_output_shape(self):
        dense = np.random.randn(5, 768).astype(np.float32)
        packed = self.proj.batch_project(dense)
        assert packed.dtype == np.uint8
        assert packed.shape == (5, 1250)

    def test_batch_project_matches_single(self):
        """batch_project should produce same results as repeated project."""
        dense = np.random.randn(3, 768).astype(np.float32)
        batch_result = self.proj.batch_project(dense)
        for i in range(3):
            single = self.proj.project(dense[i])
            np.testing.assert_array_equal(batch_result[i], single)

    def test_batch_project_1d_input(self):
        """1D input to batch_project should return (1, packed_dim)."""
        dense = np.random.randn(768).astype(np.float32)
        result = self.proj.batch_project(dense)
        assert result.shape == (1, 1250)

    def test_similarity_self_is_one(self):
        dense = np.random.randn(768).astype(np.float32)
        packed = self.proj.project(dense)
        assert self.proj.similarity(packed, packed) == pytest.approx(1.0)

    def test_similarity_range(self):
        a = self.proj.project(np.random.randn(768).astype(np.float32))
        b = self.proj.project(np.random.randn(768).astype(np.float32))
        sim = self.proj.similarity(a, b)
        assert 0.0 <= sim <= 1.0

    def test_batch_similarity_shape(self):
        query = self.proj.project(np.random.randn(768).astype(np.float32))
        candidates = self.proj.batch_project(np.random.randn(5, 768).astype(np.float32))
        scores = self.proj.batch_similarity(query, candidates)
        assert scores.shape == (5,)

    def test_batch_similarity_matches_single(self):
        """batch_similarity should match repeated similarity calls."""
        query = self.proj.project(np.random.randn(768).astype(np.float32))
        vecs = [self.proj.project(np.random.randn(768).astype(np.float32)) for _ in range(3)]
        candidates = np.array(vecs, dtype=np.uint8)
        batch_scores = self.proj.batch_similarity(query, candidates)
        for i in range(3):
            single = self.proj.similarity(query, vecs[i])
            assert batch_scores[i] == pytest.approx(single)

    def test_batch_similarity_1d_candidate(self):
        """Single candidate (1D) should work."""
        query = self.proj.project(np.random.randn(768).astype(np.float32))
        candidate = self.proj.project(np.random.randn(768).astype(np.float32))
        scores = self.proj.batch_similarity(query, candidate)
        assert scores.shape == (1,)

    def test_packed_dim_property(self):
        assert self.proj.packed_dim == 1250

    def test_different_D(self):
        proj = SimHashProjector(input_dim=768, D=8000, seed=99)
        assert proj.packed_dim == 1000  # (8000+7)//8
        packed = proj.project(np.random.randn(768).astype(np.float32))
        assert packed.shape == (1000,)

    def test_different_seed_different_planes(self):
        proj_a = SimHashProjector(input_dim=768, D=10_000, seed=1)
        proj_b = SimHashProjector(input_dim=768, D=10_000, seed=2)
        dense = np.random.randn(768).astype(np.float32)
        a = proj_a.project(dense)
        b = proj_b.project(dense)
        assert not np.array_equal(a, b)


class TestBundleBinary:

    def test_single_vector_returns_copy(self):
        v = np.array([0xFF, 0x00, 0xAA], dtype=np.uint8)
        result = bundle_binary([v], D=24)
        np.testing.assert_array_equal(result, v)
        # Should be a copy, not same object
        assert result is not v

    def test_identical_vectors_returns_same(self):
        v = np.array([0xFF, 0x00], dtype=np.uint8)
        result = bundle_binary([v, v, v], D=16)
        np.testing.assert_array_equal(result, v)

    def test_majority_vote(self):
        """3 vectors, majority should win at each bit position."""
        # All 1s
        v1 = np.array([0xFF], dtype=np.uint8)
        # All 0s
        v0 = np.array([0x00], dtype=np.uint8)
        # 2 ones vs 1 zero → result should be all 1s
        result = bundle_binary([v1, v1, v0], D=8)
        np.testing.assert_array_equal(result, v1)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            bundle_binary([], D=8)

    def test_even_count_tiebreak_with_seed(self):
        """Even number of vectors: ties broken deterministically by seed."""
        v1 = np.array([0xFF], dtype=np.uint8)  # all 1s
        v0 = np.array([0x00], dtype=np.uint8)  # all 0s
        # 1 vs 1 → tie at every bit → seed determines
        result_a = bundle_binary([v1, v0], D=8, seed=42)
        result_b = bundle_binary([v1, v0], D=8, seed=42)
        # Same seed → same result
        np.testing.assert_array_equal(result_a, result_b)
        # Different seed → likely different result
        result_c = bundle_binary([v1, v0], D=8, seed=99)
        # Not guaranteed different for 8 bits, but very likely
        # Just check it doesn't crash
        assert result_c.dtype == np.uint8
