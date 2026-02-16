"""
Encoder implementations for V2 Intent Field.

All encoders satisfy the Encoder Protocol: text -> float32[dim].
Model loaded once in __init__, reused for all subsequent calls.

Available encoders:
- MpnetEncoder: paraphrase-multilingual-mpnet-base-v2 (768d) — Phase 1 baseline
- BgeM3Encoder: BAAI/bge-m3 (1024d, MRL-native) — ADR-012 upgrade
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Phase 1 baseline
_MPNET_MODEL = "paraphrase-multilingual-mpnet-base-v2"

# ADR-012: 2024 SOTA, native multilingual, MRL support
_BGE_M3_MODEL = "BAAI/bge-m3"


class MpnetEncoder:
    """paraphrase-multilingual-mpnet-base-v2 (768d) 编码器。Phase 1 基线。"""

    def __init__(self, model_name: str = _MPNET_MODEL) -> None:
        logger.info("Loading encoder model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_sentence_embedding_dimension()
        logger.info("Encoder ready: dim=%d", self._dim)

    def encode(self, text: str) -> np.ndarray:
        """单条文本 → float32[768]。已归一化。"""
        vec = self._model.encode(text, normalize_embeddings=True)
        return np.asarray(vec, dtype=np.float32)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """批量编码 → float32[N, 768]。已归一化。"""
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)

    @property
    def dim(self) -> int:
        return self._dim


class BgeM3Encoder:
    """BAAI/bge-m3 (1024d, MRL-native) 编码器。

    MRL (Matryoshka Representation Learning) 支持：前 N 维本身就是
    最优 N 维表示，截断后重新归一化即可。truncate_dim 参数在
    EXP-006 (MRL+BQL) 中使用。
    """

    # 本地缓存路径（实验时下载，避免重复下载）
    _LOCAL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "bge-m3"

    def __init__(
        self, model_path: str | None = None, truncate_dim: int | None = None
    ) -> None:
        if model_path is None and self._LOCAL_PATH.exists():
            model_name = str(self._LOCAL_PATH)
        else:
            model_name = model_path or _BGE_M3_MODEL
        logger.info(
            "Loading encoder model: %s (truncate_dim=%s)", model_name, truncate_dim
        )
        self._model = SentenceTransformer(model_name)
        self._full_dim = self._model.get_sentence_embedding_dimension()
        self._truncate_dim = truncate_dim
        self._dim = truncate_dim if truncate_dim else self._full_dim
        logger.info("Encoder ready: full_dim=%d, output_dim=%d", self._full_dim, self._dim)

    def encode(self, text: str) -> np.ndarray:
        """单条文本 → float32[dim]。已归一化。"""
        vec = self._model.encode(text, normalize_embeddings=True)
        vec = np.asarray(vec, dtype=np.float32)
        if self._truncate_dim:
            vec = vec[: self._truncate_dim]
            vec /= np.linalg.norm(vec)
        return vec

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """批量编码 → float32[N, dim]。已归一化。"""
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)
        vecs = self._model.encode(texts, normalize_embeddings=True)
        vecs = np.asarray(vecs, dtype=np.float32)
        if self._truncate_dim:
            vecs = vecs[:, : self._truncate_dim]
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            vecs /= norms
        return vecs

    @property
    def dim(self) -> int:
        return self._dim
