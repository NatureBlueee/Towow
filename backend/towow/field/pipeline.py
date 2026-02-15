"""
编码流水线 — text → packed binary vector。

组合 Encoder + Projector + Chunker：
1. split_chunks(text) → list[str]
2. encoder.encode_batch(chunks) → float[N, 768]
3. projector.batch_project(dense) → uint8[N, 1250]
4. bundle_binary(binaries) → uint8[1250]
"""

from __future__ import annotations

import hashlib
import logging

import numpy as np

from towow.field.chunker import split_chunks
from towow.field.protocols import Encoder, Projector
from towow.field.projector import bundle_binary

logger = logging.getLogger(__name__)


class EncodingPipeline:
    """组合 Encoder + Projector + Chunker 为统一编码流水线。"""

    def __init__(self, encoder: Encoder, projector: Projector) -> None:
        self._encoder = encoder
        self._projector = projector

    def encode_text(self, text: str) -> np.ndarray:
        """
        text → packed binary vector (uint8[1250])。

        短文本直接编码。长文本切分后逐块编码再 bundle。
        """
        chunks = split_chunks(text)
        if not chunks:
            raise ValueError("Cannot encode empty text")

        if len(chunks) == 1:
            dense = self._encoder.encode(chunks[0])
            return self._projector.project(dense)

        # 多 chunk: batch encode → batch project → bundle
        dense_vecs = self._encoder.encode_batch(chunks)
        binary_vecs = self._projector.batch_project(dense_vecs)
        # bundle 的 seed 基于文本 hash，确保确定性
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        return bundle_binary(list(binary_vecs), seed=seed)

    def encode_texts(self, texts: list[str]) -> list[np.ndarray]:
        """批量编码多段文本。每段独立走 chunk+bundle 流水线。"""
        return [self.encode_text(t) for t in texts]

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """代理到 projector.similarity。"""
        return self._projector.similarity(a, b)

    def batch_similarity(
        self, query: np.ndarray, candidates: np.ndarray
    ) -> np.ndarray:
        """代理到 projector.batch_similarity。"""
        return self._projector.batch_similarity(query, candidates)

    @property
    def packed_dim(self) -> int:
        """投影后 packed uint8 向量的长度。"""
        return self._projector.packed_dim
