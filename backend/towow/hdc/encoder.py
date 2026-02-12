"""
Embedding encoder — V1 implementation of the Encoder Protocol.

Uses sentence-transformers for dense embedding cosine similarity.
Model: paraphrase-multilingual-MiniLM-L12-v2
  - 384 dimensions, fast inference
  - Strong multilingual support (Chinese + English)
  - Good semantic quality for paraphrase/similarity tasks

Supports two backends:
  - PyTorch (default on dev machines with torch installed)
  - ONNX Runtime (production — lighter, no torch dependency)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import numpy as np

from towow.core.errors import EncodingError
from towow.core.protocols import Vector

logger = logging.getLogger(__name__)


def _detect_backend() -> str:
    """Detect the best available backend.

    Priority: TOWOW_ENCODER_BACKEND env > onnx > torch.
    ONNX uses ~50MB RAM vs torch's ~300MB, critical for Railway.
    """
    import os
    forced = os.environ.get("TOWOW_ENCODER_BACKEND", "").lower()
    if forced in ("onnx", "torch"):
        logger.info("Encoder backend forced by env: %s", forced)
        return forced
    try:
        import onnxruntime  # noqa: F401
        return "onnx"
    except ImportError:
        pass
    try:
        import torch  # noqa: F401
        return "torch"
    except ImportError:
        pass
    raise ImportError(
        "EmbeddingEncoder requires either 'onnxruntime' or 'torch'. "
        "Install one: pip install onnxruntime  OR  pip install torch"
    )


def _get_model(model_name: str, backend: str):
    """Load sentence-transformers model with the given backend."""
    from sentence_transformers import SentenceTransformer
    logger.info("Loading embedding model '%s' (backend=%s)...", model_name, backend)
    if backend == "onnx":
        model = SentenceTransformer(model_name, backend="onnx")
    else:
        model = SentenceTransformer(model_name)
    logger.info("Embedding model loaded: %s (%s)", model_name, backend)
    return model


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
        self._backend = _detect_backend()
        self._model_name = model_name or self.DEFAULT_MODEL
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                self._model = _get_model(self._model_name, self._backend)
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
