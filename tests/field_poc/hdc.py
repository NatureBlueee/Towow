"""
HDC (Hyperdimensional Computing) 原语 — SimHash + Bundle + Hamming

对应架构设计文档 Section 6.1.4 的三步编码流程：
  步骤一: 文本 → 语义嵌入（外部完成，本模块不关心）
  步骤二: 浮点向量 → 二进制超向量（SimHash 投影）
  步骤三: 超向量绑定（bundle = 多数投票叠加）

参数：
  D = 10,000 维二进制超向量
  SimHash: D 个随机超平面，全网共享（固定 seed）
  Bundle: 多数投票，奇数输入直接投票，偶数输入随机打破平局

存储：
  np.packbits → 10,000 bit = 1,250 bytes per vector
"""

from __future__ import annotations

import numpy as np


class SimHash:
    """
    随机超平面投影: float[input_dim] → binary[D]

    原理: 选 D 个随机超平面，每个超平面把空间分成正负两半。
    一个浮点向量与每个超平面法向量做点积，正 → 1，负 → 0。
    语义接近的浮点向量，投影后 Hamming 距离也小。
    """

    def __init__(self, input_dim: int, D: int = 10_000, seed: int = 42):
        self.input_dim = input_dim
        self.D = D
        self.seed = seed
        # 生成 D 个随机超平面法向量 (D × input_dim)
        rng = np.random.RandomState(seed)
        self._planes = rng.randn(D, input_dim).astype(np.float32)

    def project(self, vec: np.ndarray) -> np.ndarray:
        """
        单个浮点向量 → 二进制超向量（packed uint8）

        输入: float32[input_dim]
        输出: uint8[ceil(D/8)] — packed bits
        """
        vec = np.asarray(vec, dtype=np.float32)
        # 点积 → 符号 → 二进制
        dots = self._planes @ vec  # shape: (D,)
        bits = (dots >= 0).astype(np.uint8)  # shape: (D,)
        return np.packbits(bits)

    def batch_project(self, vecs: np.ndarray) -> list[np.ndarray]:
        """
        批量投影: float32[N, input_dim] → list of packed binary vectors

        输入: float32[N, input_dim]
        输出: list of uint8[ceil(D/8)]
        """
        vecs = np.asarray(vecs, dtype=np.float32)
        # (N, input_dim) @ (input_dim, D) = (N, D)
        dots = vecs @ self._planes.T
        bits = (dots >= 0).astype(np.uint8)  # (N, D)
        return [np.packbits(row) for row in bits]


def hamming_similarity(a: np.ndarray, b: np.ndarray, D: int = 10_000) -> float:
    """
    两个 packed binary vector 的 Hamming 相似度 [0, 1]

    Hamming similarity = 1 - (hamming_distance / D)
    = (matching bits) / D
    """
    # XOR → popcount
    xor = np.bitwise_xor(a, b)
    diff_bits = sum(bin(byte).count("1") for byte in xor)
    return 1.0 - diff_bits / D


def batch_hamming_similarity(
    query: np.ndarray, candidates: list[np.ndarray], D: int = 10_000
) -> np.ndarray:
    """
    一个 query 和多个 candidate 的 Hamming 相似度

    返回: float[N] 相似度数组
    """
    # 使用查找表加速 popcount
    lookup = np.array([bin(i).count("1") for i in range(256)], dtype=np.int32)

    sims = np.empty(len(candidates), dtype=np.float64)
    for i, cand in enumerate(candidates):
        xor = np.bitwise_xor(query, cand)
        diff = lookup[xor].sum()
        sims[i] = 1.0 - diff / D
    return sims


def bundle_binary(vectors: list[np.ndarray], D: int = 10_000, seed: int = 0) -> np.ndarray:
    """
    多数投票 bundle: 多个 packed binary vectors → 一个 packed binary vector

    原理: 每个 bit 位置，统计 1 的个数。过半 → 1，否则 → 0。
    偶数个向量时，使用随机 tie-breaking。

    输入: list of uint8[ceil(D/8)] (packed bits)
    输出: uint8[ceil(D/8)] (packed bits)
    """
    if not vectors:
        raise ValueError("Cannot bundle empty list")
    if len(vectors) == 1:
        return vectors[0].copy()

    n = len(vectors)
    # 解包所有向量为 bit 数组
    unpacked = np.array([np.unpackbits(v)[:D] for v in vectors], dtype=np.int32)
    # 每个 bit 位置的 1 的计数
    counts = unpacked.sum(axis=0)  # shape: (D,)
    threshold = n / 2.0

    result_bits = np.zeros(D, dtype=np.uint8)
    result_bits[counts > threshold] = 1

    # 平局处理（偶数输入时 count == n/2）
    ties = counts == threshold
    if ties.any():
        rng = np.random.RandomState(seed)
        result_bits[ties] = rng.randint(0, 2, size=ties.sum()).astype(np.uint8)

    return np.packbits(result_bits)


def bundle_dense(vectors: list[np.ndarray]) -> np.ndarray:
    """
    Dense vector bundle: 平均 + 归一化（现有 encoder.bundle 的等价实现）

    用于对比：dense bundle vs binary bundle
    """
    if not vectors:
        raise ValueError("Cannot bundle empty list")
    stacked = np.stack(vectors)
    avg = stacked.mean(axis=0)
    norm = np.linalg.norm(avg)
    if norm < 1e-10:
        raise ValueError("Bundle resulted in zero vector")
    return (avg / norm).astype(np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Dense vector cosine similarity."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
