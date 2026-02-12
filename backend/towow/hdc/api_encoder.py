"""
Lightweight embedding encoder using HuggingFace Inference API.

No torch, no sentence-transformers — just HTTP calls to the same model.
Used in production to avoid loading a ~300MB ML framework into memory.

Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
  - Same model as the local EmbeddingEncoder
  - Vectors are compatible (same 384-dim space)
  - Free tier: sufficient for typical usage
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
import numpy as np

from towow.core.errors import EncodingError
from towow.core.protocols import Vector

logger = logging.getLogger(__name__)

HF_API_URL = "https://router.huggingface.co/pipeline/feature-extraction/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class HuggingFaceAPIEncoder:
    """
    Encoder using HuggingFace Inference API.

    Satisfies the same Encoder Protocol as EmbeddingEncoder.
    Produces identical vectors (same model on HF servers).
    """

    def __init__(self, api_token: Optional[str] = None):
        self._headers = {}
        if api_token:
            self._headers["Authorization"] = f"Bearer {api_token}"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def encode(self, text: str) -> Vector:
        """Encode a single text into a normalized vector via HF API."""
        if not text or not text.strip():
            raise EncodingError("Cannot encode empty text")
        try:
            response = await self._client.post(
                HF_API_URL,
                json={"inputs": text, "options": {"wait_for_model": True}},
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()

            # HF returns [[token_embeddings...]] for feature-extraction
            # We need to mean-pool and normalize (same as sentence-transformers)
            token_embeddings = np.array(data, dtype=np.float32)
            if token_embeddings.ndim == 3:
                # Shape: (1, seq_len, hidden_dim) -> mean pool -> (hidden_dim,)
                vec = token_embeddings[0].mean(axis=0)
            elif token_embeddings.ndim == 2:
                # Shape: (seq_len, hidden_dim) -> mean pool
                vec = token_embeddings.mean(axis=0)
            elif token_embeddings.ndim == 1:
                vec = token_embeddings
            else:
                raise EncodingError(f"Unexpected embedding shape: {token_embeddings.shape}")

            # Normalize
            norm = np.linalg.norm(vec)
            if norm < 1e-10:
                raise EncodingError("Encoding resulted in zero vector")
            return (vec / norm).astype(np.float32)

        except EncodingError:
            raise
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                # Model loading — retry once after waiting
                logger.warning("HF API: model loading, retrying in 5s...")
                import asyncio
                await asyncio.sleep(5)
                return await self.encode(text)
            raise EncodingError(f"HF API error: {e.response.status_code} {e.response.text[:200]}") from e
        except Exception as e:
            raise EncodingError(f"HF API encoding failed: {e}") from e

    async def batch_encode(self, texts: list[str]) -> list[Vector]:
        """Encode multiple texts. Uses single encode per text (API limitation)."""
        if not texts:
            return []
        results = []
        for text in texts:
            vec = await self.encode(text)
            results.append(vec)
        return results

    async def bundle(self, vectors: list[Vector]) -> Vector:
        """Bundle multiple vectors into one by averaging and normalizing."""
        if not vectors:
            raise EncodingError("Cannot bundle empty vector list")
        stacked = np.stack(vectors)
        avg = stacked.mean(axis=0)
        norm = np.linalg.norm(avg)
        if norm < 1e-10:
            raise EncodingError("Bundle resulted in zero vector")
        return (avg / norm).astype(np.float32)
