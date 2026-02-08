"""Tests for the EmbeddingEncoder (V1 Encoder Protocol implementation)."""

from __future__ import annotations

import numpy as np
import pytest

from towow.core.errors import EncodingError
from towow.core.protocols import Encoder
from towow.hdc.encoder import EmbeddingEncoder


# ============ Protocol compliance tests (use MockEncoder pattern) ============


class TestEmbeddingEncoderProtocol:
    """Verify EmbeddingEncoder satisfies the Encoder Protocol."""

    def test_is_encoder_protocol(self):
        encoder = EmbeddingEncoder.__new__(EmbeddingEncoder)
        assert isinstance(encoder, Encoder)


# ============ Unit tests with real model ============


@pytest.mark.slow
class TestEmbeddingEncoderReal:
    """Tests that require the actual sentence-transformers model."""

    @pytest.fixture(scope="class")
    def encoder(self):
        return EmbeddingEncoder()

    @pytest.mark.asyncio
    async def test_encode_returns_normalized_vector(self, encoder):
        vec = await encoder.encode("machine learning engineer")
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 1e-5, f"Expected unit norm, got {norm}"

    @pytest.mark.asyncio
    async def test_encode_returns_float32(self, encoder):
        vec = await encoder.encode("data scientist")
        assert vec.dtype == np.float32

    @pytest.mark.asyncio
    async def test_encode_deterministic(self, encoder):
        v1 = await encoder.encode("python developer")
        v2 = await encoder.encode("python developer")
        np.testing.assert_array_equal(v1, v2)

    @pytest.mark.asyncio
    async def test_similar_texts_high_similarity(self, encoder):
        v1 = await encoder.encode("machine learning engineer")
        v2 = await encoder.encode("deep learning researcher")
        sim = float(np.dot(v1, v2))
        assert sim > 0.5, f"Similar texts should have high similarity, got {sim}"

    @pytest.mark.asyncio
    async def test_unrelated_texts_low_similarity(self, encoder):
        v1 = await encoder.encode("machine learning engineer")
        v2 = await encoder.encode("professional pastry chef")
        sim = float(np.dot(v1, v2))
        assert sim < 0.5, f"Unrelated texts should have low similarity, got {sim}"

    @pytest.mark.asyncio
    async def test_batch_encode(self, encoder):
        texts = ["data scientist", "frontend developer", "product manager"]
        vecs = await encoder.batch_encode(texts)
        assert len(vecs) == 3
        for v in vecs:
            assert abs(np.linalg.norm(v) - 1.0) < 1e-5

    @pytest.mark.asyncio
    async def test_batch_encode_matches_single(self, encoder):
        texts = ["data scientist", "frontend developer"]
        batch = await encoder.batch_encode(texts)
        singles = [await encoder.encode(t) for t in texts]
        for b, s in zip(batch, singles):
            np.testing.assert_allclose(b, s, atol=1e-5)

    @pytest.mark.asyncio
    async def test_batch_encode_empty(self, encoder):
        result = await encoder.batch_encode([])
        assert result == []

    @pytest.mark.asyncio
    async def test_bundle_preserves_semantics(self, encoder):
        v_ml = await encoder.encode("machine learning")
        v_py = await encoder.encode("python programming")
        v_data = await encoder.encode("data analysis")
        bundled = await encoder.bundle([v_ml, v_py, v_data])

        assert abs(np.linalg.norm(bundled) - 1.0) < 1e-5

        v_query = await encoder.encode("python machine learning data scientist")
        sim = float(np.dot(bundled, v_query))
        assert sim > 0.4, f"Bundle should be semantically close to combined query, got {sim}"

    @pytest.mark.asyncio
    async def test_multilingual(self, encoder):
        v_en = await encoder.encode("machine learning engineer")
        v_zh = await encoder.encode("机器学习工程师")
        sim = float(np.dot(v_en, v_zh))
        assert sim > 0.5, f"Multilingual model should align EN/ZH, got {sim}"


# ============ Error handling tests ============


class TestEmbeddingEncoderErrors:
    """Error handling tests (don't need model)."""

    @pytest.mark.asyncio
    async def test_encode_empty_string_raises(self):
        encoder = EmbeddingEncoder()
        with pytest.raises(EncodingError, match="empty text"):
            await encoder.encode("")

    @pytest.mark.asyncio
    async def test_encode_whitespace_only_raises(self):
        encoder = EmbeddingEncoder()
        with pytest.raises(EncodingError, match="empty text"):
            await encoder.encode("   ")

    @pytest.mark.asyncio
    async def test_batch_encode_with_empty_string_raises(self):
        encoder = EmbeddingEncoder()
        with pytest.raises(EncodingError, match="empty text"):
            await encoder.batch_encode(["valid", ""])

    @pytest.mark.asyncio
    async def test_bundle_empty_list_raises(self):
        encoder = EmbeddingEncoder()
        with pytest.raises(EncodingError, match="empty vector list"):
            await encoder.bundle([])

    @pytest.mark.asyncio
    async def test_bundle_zero_vectors_raises(self):
        encoder = EmbeddingEncoder()
        zero = np.zeros(10, dtype=np.float32)
        with pytest.raises(EncodingError, match="zero vector"):
            await encoder.bundle([zero, -zero])

    def test_invalid_model_raises(self):
        encoder = EmbeddingEncoder(model_name="nonexistent-model-xyz")
        with pytest.raises(EncodingError, match="Failed to load"):
            _ = encoder.model
