"""
Embedding encoder — V1 implementation of the Encoder Protocol.

Uses sentence-transformers for dense embedding cosine similarity.
Model: paraphrase-multilingual-MiniLM-L12-v2
  - 384 dimensions, fast inference
  - Strong multilingual support (Chinese + English)
  - Good semantic quality for paraphrase/similarity tasks
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Optional

import numpy as np

from towow.core.errors import EncodingError
from towow.core.protocols import Vector


def _get_model(model_name: str):
    """Lazy-load sentence-transformers model (cached singleton)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


class EmbeddingEncoder:
    """
    V1 Encoder: dense embedding via sentence-transformers.

    Satisfies the Encoder Protocol defined in core/protocols.py.
    Stateless per call — the model is loaded once and reused.
    """

    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model_name: Optional[str] = None):
        # Fail-fast: check dependency at construction, not at first encode()
        try:
            import sentence_transformers  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for EmbeddingEncoder. "
                "Install with: pip install sentence-transformers"
            ) from e
        self._model_name = model_name or self.DEFAULT_MODEL
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                self._model = _get_model(self._model_name)
            except Exception as e:
                raise EncodingError(
                    f"Failed to load model '{self._model_name}': {e}"
                ) from e
        return self._model

    async def encode(self, text: str) -> Vector:
        """Encode a single text into a normalized vector."""
        if not text or not text.strip():
            raise EncodingError("Cannot encode empty text")
        try:
            loop = asyncio.get_running_loop()
            vec = await loop.run_in_executor(
                None, lambda: self.model.encode(text, normalize_embeddings=True)
            )
            return np.asarray(vec, dtype=np.float32)
        except EncodingError:
            raise
        except Exception as e:
            raise EncodingError(f"Encoding failed: {e}") from e

    async def batch_encode(self, texts: list[str]) -> list[Vector]:
        """Encode multiple texts into normalized vectors."""
        if not texts:
            return []
        for i, t in enumerate(texts):
            if not t or not t.strip():
                raise EncodingError(f"Cannot encode empty text at index {i}")
        try:
            loop = asyncio.get_running_loop()
            vecs = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts, normalize_embeddings=True),
            )
            return [np.asarray(v, dtype=np.float32) for v in vecs]
        except EncodingError:
            raise
        except Exception as e:
            raise EncodingError(f"Batch encoding failed: {e}") from e

    async def bundle(self, vectors: list[Vector]) -> Vector:
        """
        Bundle multiple vectors into one by averaging and normalizing.

        Used to create an Agent profile vector from multiple text descriptions
        (skills, experience, preferences, etc.). This is the HDC "bundle"
        operation approximated with dense vectors.
        """
        if not vectors:
            raise EncodingError("Cannot bundle empty vector list")
        stacked = np.stack(vectors)
        avg = stacked.mean(axis=0)
        norm = np.linalg.norm(avg)
        if norm < 1e-10:
            raise EncodingError("Bundle resulted in zero vector")
        return (avg / norm).astype(np.float32)
