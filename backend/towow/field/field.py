"""
MemoryField — V2 IntentField 的内存实现。

持久内存场：Intent deposit 后持续存在，不随请求销毁。
支持 Intent 级匹配（match）和 Owner 级聚合（match_owners）。

存储结构：
- _intents: dict[intent_id → Intent]
- _vectors: uint8[N, packed_dim] 紧凑矩阵（packed_dim 从 pipeline 获取）
- _id_index: list[intent_id]（行号 → id 映射）
- _pos_index: dict[intent_id → int]（id → 行号反向索引，O(1) 删除）
- _owner_index: dict[owner → set[intent_id]]
- _dedup: set[hash]（去重键）
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from collections import defaultdict

import numpy as np

from towow.field.pipeline import EncodingPipeline
from towow.field.types import FieldResult, Intent, OwnerMatch

logger = logging.getLogger(__name__)

_INITIAL_CAPACITY = 1024


class MemoryField:
    """内存持久场。满足 IntentField Protocol。"""

    def __init__(self, pipeline: EncodingPipeline) -> None:
        self._pipeline = pipeline
        self._packed_dim = pipeline.packed_dim
        self._lock = asyncio.Lock()

        # 核心存储
        self._intents: dict[str, Intent] = {}
        self._vectors: np.ndarray = np.empty(
            (0, self._packed_dim), dtype=np.uint8
        )
        self._id_index: list[str] = []
        self._pos_index: dict[str, int] = {}  # intent_id → row position
        self._owner_index: defaultdict[str, set[str]] = defaultdict(set)
        self._dedup: set[str] = set()

        # 容量管理
        self._capacity = _INITIAL_CAPACITY
        self._vector_buf: np.ndarray = np.zeros(
            (_INITIAL_CAPACITY, self._packed_dim), dtype=np.uint8
        )
        self._active_count = 0

    async def deposit(
        self, text: str, owner: str, metadata: dict | None = None
    ) -> str:
        """Intent 进入场。幂等：同一 (owner, text) 不重复存储。"""
        if not text or not text.strip():
            raise ValueError("Cannot deposit empty text")
        if not owner or not owner.strip():
            raise ValueError("Cannot deposit without owner")

        # 去重
        dedup_key = hashlib.sha256(f"{owner}|{text}".encode()).hexdigest()
        async with self._lock:
            if dedup_key in self._dedup:
                # 找到已存在的 intent_id 并返回
                for iid, intent in self._intents.items():
                    if intent.owner == owner and intent.text == text:
                        return iid
                # dedup 集合和 intents 不一致，清理并继续
                self._dedup.discard(dedup_key)

            intent_id = str(uuid.uuid4())
            intent = Intent(
                id=intent_id,
                owner=owner,
                text=text.strip(),
                metadata=metadata or {},
            )

            # 编码（在锁外做会更好，但简单起见先在锁内）
            binary_vec = self._pipeline.encode_text(intent.text)

            # 存储
            self._intents[intent_id] = intent
            self._dedup.add(dedup_key)
            self._owner_index[owner].add(intent_id)

            # 向量矩阵追加
            if self._active_count >= self._capacity:
                self._grow_buffer()
            self._vector_buf[self._active_count] = binary_vec
            self._id_index.append(intent_id)
            self._pos_index[intent_id] = self._active_count
            self._active_count += 1
            # 更新活跃视图
            self._vectors = self._vector_buf[: self._active_count]

        logger.debug(
            "Deposited intent %s for owner %s (%d chars)",
            intent_id[:8], owner, len(text),
        )
        return intent_id

    async def match(self, text: str, k: int = 10) -> list[FieldResult]:
        """在场中找到与 text 最相关的 Intent。"""
        if not text or not text.strip():
            return []
        if self._active_count == 0:
            return []

        query_vec = self._pipeline.encode_text(text.strip())
        scores = self._pipeline.batch_similarity(query_vec, self._vectors)

        # top-k
        actual_k = min(k, self._active_count)
        if actual_k >= self._active_count:
            top_indices = np.argsort(scores)[::-1]
        else:
            top_indices = np.argpartition(scores, -actual_k)[-actual_k:]
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        results: list[FieldResult] = []
        for idx in top_indices:
            iid = self._id_index[idx]
            intent = self._intents[iid]
            results.append(
                FieldResult(
                    intent_id=iid,
                    score=float(scores[idx]),
                    owner=intent.owner,
                    text=intent.text,
                    metadata=intent.metadata,
                )
            )
        return results

    async def match_owners(
        self, text: str, k: int = 10, max_intents: int = 3
    ) -> list[OwnerMatch]:
        """在场中找到与 text 最相关的 Owner。按 owner 聚合。"""
        # 取足够多的 Intent 级结果用于聚合
        raw_k = min(k * max_intents * 2, self._active_count)
        if raw_k == 0:
            return []
        intent_results = await self.match(text, k=raw_k)

        # 按 owner 归组
        owner_groups: dict[str, list[FieldResult]] = defaultdict(list)
        for r in intent_results:
            owner_groups[r.owner].append(r)

        # 聚合：top-1 max（初版策略，可切换）
        owner_matches: list[OwnerMatch] = []
        for owner, intents in owner_groups.items():
            # intents 已按 score 降序（继承自 match 的排序）
            top = intents[:max_intents]
            owner_matches.append(
                OwnerMatch(
                    owner=owner,
                    score=top[0].score,  # max score
                    intents=tuple(top),
                )
            )

        # 按 owner score 降序排列，取 top-k
        owner_matches.sort(key=lambda m: m.score, reverse=True)
        return owner_matches[:k]

    async def remove(self, intent_id: str) -> None:
        """移除单个 Intent。不存在时静默。"""
        async with self._lock:
            self._remove_locked(intent_id)

    async def remove_owner(self, owner: str) -> int:
        """移除 owner 的所有 Intent。返回移除数量。锁内一次性完成。"""
        async with self._lock:
            intent_ids = list(self._owner_index.get(owner, set()))
            for iid in intent_ids:
                self._remove_locked(iid)
            return len(intent_ids)

    def _remove_locked(self, intent_id: str) -> None:
        """锁内移除单个 Intent。调用方必须持有 self._lock。"""
        if intent_id not in self._intents:
            return
        intent = self._intents.pop(intent_id)
        dedup_key = hashlib.sha256(
            f"{intent.owner}|{intent.text}".encode()
        ).hexdigest()
        self._dedup.discard(dedup_key)
        self._owner_index[intent.owner].discard(intent_id)
        if not self._owner_index[intent.owner]:
            del self._owner_index[intent.owner]

        # 从向量矩阵移除（swap with last, O(1)）
        idx = self._pos_index.pop(intent_id, None)
        if idx is None:
            return
        last = self._active_count - 1
        if idx != last:
            moved_id = self._id_index[last]
            self._vector_buf[idx] = self._vector_buf[last]
            self._id_index[idx] = moved_id
            self._pos_index[moved_id] = idx
        self._id_index.pop()
        self._active_count -= 1
        self._vectors = self._vector_buf[: self._active_count]

    async def count(self) -> int:
        return self._active_count

    async def count_owners(self) -> int:
        return len(self._owner_index)

    def _grow_buffer(self) -> None:
        """向量矩阵容量翻倍。"""
        new_capacity = self._capacity * 2
        new_buf = np.zeros((new_capacity, self._packed_dim), dtype=np.uint8)
        new_buf[: self._active_count] = self._vector_buf[: self._active_count]
        self._vector_buf = new_buf
        self._capacity = new_capacity
        logger.info("Field buffer grown to %d", new_capacity)
