"""
Tests for EncodingPipeline — the Encoder + Projector + Chunker composition.

Uses a stub Encoder and the real SimHashProjector (no model loading).
"""

import numpy as np
import pytest

from towow.field.pipeline import EncodingPipeline
from towow.field.projector import SimHashProjector


class StubEncoder:
    """Deterministic encoder for tests. Returns normalized random vectors
    seeded by text hash. Satisfies the Encoder Protocol without loading models."""

    def __init__(self, dim: int = 768) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def encode(self, text: str) -> np.ndarray:
        seed = int.from_bytes(text.encode()[:4].ljust(4, b'\0'), "big")
        rng = np.random.RandomState(seed)
        vec = rng.randn(self._dim).astype(np.float32)
        vec /= np.linalg.norm(vec)
        return vec

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        return np.array([self.encode(t) for t in texts], dtype=np.float32)


class TestEncodingPipeline:

    def setup_method(self):
        self.encoder = StubEncoder(dim=768)
        self.projector = SimHashProjector(input_dim=768, D=10_000, seed=42)
        self.pipeline = EncodingPipeline(self.encoder, self.projector)

    def test_encode_text_output_shape(self):
        vec = self.pipeline.encode_text("hello world")
        assert vec.dtype == np.uint8
        assert vec.shape == (1250,)

    def test_encode_text_deterministic(self):
        a = self.pipeline.encode_text("test input")
        b = self.pipeline.encode_text("test input")
        np.testing.assert_array_equal(a, b)

    def test_encode_text_different_inputs(self):
        a = self.pipeline.encode_text("hello")
        b = self.pipeline.encode_text("world")
        assert not np.array_equal(a, b)

    def test_encode_text_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.pipeline.encode_text("")

    def test_encode_text_whitespace_raises(self):
        with pytest.raises(ValueError, match="empty"):
            self.pipeline.encode_text("   ")

    def test_encode_texts_multiple(self):
        texts = ["alpha", "beta", "gamma"]
        results = self.pipeline.encode_texts(texts)
        assert len(results) == 3
        for vec in results:
            assert vec.dtype == np.uint8
            assert vec.shape == (1250,)

    def test_encode_texts_matches_single(self):
        """encode_texts should produce same vectors as individual encode_text."""
        texts = ["foo", "bar"]
        batch = self.pipeline.encode_texts(texts)
        for i, t in enumerate(texts):
            single = self.pipeline.encode_text(t)
            np.testing.assert_array_equal(batch[i], single)

    def test_similarity_self_is_one(self):
        vec = self.pipeline.encode_text("test")
        assert self.pipeline.similarity(vec, vec) == pytest.approx(1.0)

    def test_batch_similarity_shape(self):
        query = self.pipeline.encode_text("query")
        candidates = np.array(
            [self.pipeline.encode_text(f"doc {i}") for i in range(5)],
            dtype=np.uint8,
        )
        scores = self.pipeline.batch_similarity(query, candidates)
        assert scores.shape == (5,)

    def test_packed_dim(self):
        assert self.pipeline.packed_dim == 1250

    def test_long_text_uses_chunking(self):
        """Text longer than max_chars should be chunked and bundled."""
        # Create text with sentence boundaries exceeding default 256 chars
        long_text = ". ".join(f"Sentence number {i} with some content" for i in range(20))
        assert len(long_text) > 256
        vec = self.pipeline.encode_text(long_text)
        assert vec.dtype == np.uint8
        assert vec.shape == (1250,)

    def test_long_text_deterministic(self):
        long_text = ". ".join(f"Part {i}" for i in range(30))
        a = self.pipeline.encode_text(long_text)
        b = self.pipeline.encode_text(long_text)
        np.testing.assert_array_equal(a, b)
