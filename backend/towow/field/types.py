"""
V2 Intent Field 数据类型。

Intent 是场中唯一的粒子（Genome §2）。
FieldResult 是 Intent 级匹配结果。
OwnerMatch 是 Owner 级聚合结果。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Intent:
    """场中的唯一粒子。demand/profile/feedback 编码后都是 Intent。"""

    id: str
    owner: str
    text: str
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class FieldResult:
    """Intent 级匹配结果。"""

    intent_id: str
    score: float
    owner: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class OwnerMatch:
    """Owner 级聚合结果。同一 owner 的多个 Intent 聚合为一条。"""

    owner: str
    score: float
    intents: tuple[FieldResult, ...] = ()
