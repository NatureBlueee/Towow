"""
SceneRegistry — 场景上下文注册与管理。

其他应用注册自己的"场景"到 App Store，提供：
- 场景描述（这个场景关注什么）
- 优先策略（什么能力更重要）
- 领域上下文（Center 协调时的背景知识）

场景不是边界，是透镜——影响共振权重和 Center 策略。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SceneContext:
    """一个场景的上下文定义。"""
    scene_id: str
    name: str
    description: str = ""
    priority_strategy: str = ""  # 该场景优先什么能力/特质
    domain_context: str = ""  # 领域背景知识，注入 Center
    created_by: str = ""  # 注册者标识（应用名/开发者）
    agent_count: int = 0  # 该场景下注册的 Agent 数量

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "description": self.description,
            "priority_strategy": self.priority_strategy,
            "domain_context": self.domain_context,
            "created_by": self.created_by,
            "agent_count": self.agent_count,
        }

    def to_center_context(self) -> str:
        """
        生成注入 Center system prompt 的场景上下文段落。
        Center 协调时会参考这段文字来理解场景特点。
        """
        parts = []
        if self.name:
            parts.append(f"当前场景：{self.name}")
        if self.description:
            parts.append(f"场景说明：{self.description}")
        if self.priority_strategy:
            parts.append(f"优先策略：{self.priority_strategy}")
        if self.domain_context:
            parts.append(f"领域背景：{self.domain_context}")
        return "\n".join(parts)


class SceneRegistry:
    """场景注册表 — 管理所有已注册的场景上下文。"""

    def __init__(self):
        self._scenes: dict[str, SceneContext] = {}

    def register(self, scene: SceneContext) -> None:
        """注册或更新一个场景。"""
        self._scenes[scene.scene_id] = scene
        logger.info("注册场景: %s (%s)", scene.scene_id, scene.name)

    def unregister(self, scene_id: str) -> bool:
        if scene_id in self._scenes:
            del self._scenes[scene_id]
            return True
        return False

    def get(self, scene_id: str) -> SceneContext | None:
        return self._scenes.get(scene_id)

    @property
    def all_scenes(self) -> list[SceneContext]:
        return list(self._scenes.values())

    def list_scenes(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._scenes.values()]

    def get_center_context(self, scene_id: str) -> str:
        """获取场景的 Center 上下文，用于注入协商 prompt。"""
        scene = self._scenes.get(scene_id)
        if scene:
            return scene.to_center_context()
        return ""

    def increment_agent_count(self, scene_id: str) -> None:
        scene = self._scenes.get(scene_id)
        if scene:
            scene.agent_count += 1
