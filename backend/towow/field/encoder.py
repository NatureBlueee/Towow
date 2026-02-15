"""
MpnetEncoder — paraphrase-multilingual-mpnet-base-v2 (768d)。

满足 Encoder Protocol：text → float32[768]。
模型在 __init__ 加载一次，后续复用。
"""

from __future__ import annotations

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Phase 1 实验锁定的模型
_DEFAULT_MODEL = "paraphrase-multilingual-mpnet-base-v2"


class MpnetEncoder:
    """paraphrase-multilingual-mpnet-base-v2 (768d) 编码器。"""

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
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
