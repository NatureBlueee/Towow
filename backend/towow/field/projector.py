"""
SimHashProjector — float[input_dim] → binary[D] (packed as uint8[packed_dim])。

满足 Projector Protocol。
从 POC hdc.py 重写，改进：
- batch_project 返回 2D numpy 数组（支持向量化）
- popcount 查找表在 __init__ 预计算
- batch_similarity 全向量化（无 Python for 循环）
"""

from __future__ import annotations

import numpy as np

# Phase 1 实验锁定的参数
_DEFAULT_D = 10_000
_DEFAULT_SEED = 42


class SimHashProjector:
    """随机超平面投影 + Hamming 相似度。"""

    def __init__(
        self, input_dim: int = 768, D: int = _DEFAULT_D, seed: int = _DEFAULT_SEED
    ) -> None:
        self.D = D
        self._packed_size = (D + 7) // 8  # 1250 for D=10000
        # 确定性生成超平面矩阵（全网一致）
        rng = np.random.RandomState(seed)
        self._planes = rng.randn(D, input_dim).astype(np.float32)
        # popcount 查找表：byte → bit count
        self._popcount_lut = np.array(
            [bin(i).count("1") for i in range(256)], dtype=np.int32
        )

    def project(self, dense: np.ndarray) -> np.ndarray:
        """float32[dim] → packed uint8[packed_dim]。"""
        dense = np.asarray(dense, dtype=np.float32)
        dots = self._planes @ dense
        bits = (dots >= 0).astype(np.uint8)
        return np.packbits(bits)

    def batch_project(self, dense: np.ndarray) -> np.ndarray:
        """float32[N, dim] → uint8[N, packed_dim]。"""
        dense = np.asarray(dense, dtype=np.float32)
        if dense.ndim == 1:
            return self.project(dense).reshape(1, -1)
        # (N, dim) @ (dim, D) = (N, D)
        dots = dense @ self._planes.T
        bits = (dots >= 0).astype(np.uint8)
        return np.packbits(bits, axis=1)

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """两个 packed binary vector 的 Hamming 相似度 [0, 1]。"""
        xor = np.bitwise_xor(a, b)
        diff = self._popcount_lut[xor].sum()
        return 1.0 - diff / self.D

    def batch_similarity(
        self, query: np.ndarray, candidates: np.ndarray
    ) -> np.ndarray:
        """query (uint8[packed_dim]) vs candidates (uint8[N, packed_dim]) → float[N]。"""
        if candidates.ndim == 1:
            candidates = candidates.reshape(1, -1)
        # 向量化 XOR + popcount
        xor = np.bitwise_xor(query, candidates)  # (N, 1250)
        diff = self._popcount_lut[xor].sum(axis=1)  # (N,)
        return 1.0 - diff / self.D

    @property
    def packed_dim(self) -> int:
        return self._packed_size


def bundle_binary(
    vectors: list[np.ndarray], D: int = _DEFAULT_D, seed: int = 0
) -> np.ndarray:
    """
    多数投票 bundle: 多个 packed binary → 一个 packed binary。

    每个 bit 位置统计 1 的个数，过半 → 1。
    偶数输入时用 seed 随机打破平局。
    """
    if not vectors:
        raise ValueError("Cannot bundle empty list")
    if len(vectors) == 1:
        return vectors[0].copy()

    n = len(vectors)
    unpacked = np.array(
        [np.unpackbits(v)[:D] for v in vectors], dtype=np.int32
    )
    counts = unpacked.sum(axis=0)
    threshold = n / 2.0

    result_bits = np.zeros(D, dtype=np.uint8)
    result_bits[counts > threshold] = 1

    # 平局：偶数输入时 count == n/2
    ties = counts == threshold
    if ties.any():
        rng = np.random.RandomState(seed)
        result_bits[ties] = rng.randint(0, 2, size=ties.sum()).astype(np.uint8)

    return np.packbits(result_bits)
