"""
Projector implementations for V2 Intent Field.

All projectors satisfy the Projector Protocol: float[dim] → packed uint8[packed_dim].

Available projectors:
- SimHashProjector: Random hyperplane projection (D=10000, 1250 bytes) — Phase 1 baseline
- MrlBqlProjector: Binary Quantization (sign→packbits, 64 bytes for 512d) — ADR-012 upgrade
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


class MrlBqlProjector:
    """MRL + Binary Quantization: sign(x) → packbits。

    与 SimHash 的区别：
    - 无需随机超平面矩阵（SimHash 需要 D×input_dim float32）
    - 每个 float 维度直接映射为 1 bit：>0 → 1, ≤0 → 0
    - D = input_dim（512 维 → 512 bits = 64 bytes，vs SimHash 1250 bytes）
    - 要求编码器支持 MRL（如 BgeM3Encoder(truncate_dim=512)）

    MRL 保证前 N 维本身就是最优 N 维表示，截断后归一化即可。
    BQL 进一步压缩为 binary，论文报告保留 ≥93% 原始精度。
    """

    def __init__(self, input_dim: int = 512) -> None:
        self.D = input_dim
        self._packed_size = (input_dim + 7) // 8  # 64 for D=512
        # popcount 查找表：byte → bit count
        self._popcount_lut = np.array(
            [bin(i).count("1") for i in range(256)], dtype=np.int32
        )

    def project(self, dense: np.ndarray) -> np.ndarray:
        """float32[dim] → packed uint8[packed_dim]。"""
        dense = np.asarray(dense, dtype=np.float32)
        bits = (dense > 0).astype(np.uint8)
        return np.packbits(bits)

    def batch_project(self, dense: np.ndarray) -> np.ndarray:
        """float32[N, dim] → uint8[N, packed_dim]。"""
        dense = np.asarray(dense, dtype=np.float32)
        if dense.ndim == 1:
            return self.project(dense).reshape(1, -1)
        bits = (dense > 0).astype(np.uint8)
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
        xor = np.bitwise_xor(query, candidates)
        diff = self._popcount_lut[xor].sum(axis=1)
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
