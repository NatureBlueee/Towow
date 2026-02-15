"""
V2 Intent Field Protocol 定义。

三个 Protocol：
- IntentField: 场的核心操作（deposit, match, match_owners）
- Encoder: 文本 → 密集向量（内部接口）
- Projector: 密集向量 → 二进制超向量（内部接口）

Protocol 定义 WHAT，不定义 HOW。实现可替换。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from towow.field.types import FieldResult, OwnerMatch


@runtime_checkable
class IntentField(Protocol):
    """V2 Intent Field — 意图的持久场。Genome §3 协议边界内的核心。"""

    async def deposit(
        self, text: str, owner: str, metadata: dict | None = None
    ) -> str:
        """Intent 进入场。返回 intent_id。"""
        ...

    async def match(self, text: str, k: int = 10) -> list[FieldResult]:
        """在场中找到与 text 最相关的 Intent。按 score 降序。"""
        ...

    async def match_owners(
        self, text: str, k: int = 10, max_intents: int = 3
    ) -> list[OwnerMatch]:
        """在场中找到与 text 最相关的 Owner（按 owner 聚合）。"""
        ...

    async def remove(self, intent_id: str) -> None:
        """移除单个 Intent。不存在时静默。"""
        ...

    async def remove_owner(self, owner: str) -> int:
        """移除 owner 的所有 Intent。返回移除数量。"""
        ...

    async def count(self) -> int:
        """场中 Intent 总数。"""
        ...

    async def count_owners(self) -> int:
        """场中 Owner 总数。"""
        ...


@runtime_checkable
class Encoder(Protocol):
    """文本 → 密集向量。Field 的内部依赖。"""

    def encode(self, text: str) -> np.ndarray:
        """单条文本编码。返回 float32[dim]。"""
        ...

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """批量编码。返回 float32[N, dim]。"""
        ...

    @property
    def dim(self) -> int:
        """向量维度。"""
        ...


@runtime_checkable
class Projector(Protocol):
    """密集向量 → 二进制超向量。Field 的内部依赖。"""

    def project(self, dense: np.ndarray) -> np.ndarray:
        """float[dim] → packed uint8。"""
        ...

    def batch_project(self, dense: np.ndarray) -> np.ndarray:
        """float[N, dim] → uint8[N, packed_size]。"""
        ...

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """两个投影向量的相似度 [0, 1]。"""
        ...

    def batch_similarity(
        self, query: np.ndarray, candidates: np.ndarray
    ) -> np.ndarray:
        """query vs N candidates。返回 float[N]。"""
        ...

    @property
    def packed_dim(self) -> int:
        """投影后 packed uint8 向量的长度。"""
        ...
