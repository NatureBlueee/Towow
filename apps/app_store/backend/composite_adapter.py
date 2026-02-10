"""
CompositeAdapter — 多数据源合并的 ProfileDataSource 适配器。

将多个子 adapter（SecondMe 用户、JSON 样板间等）合并为一个统一的
ProfileDataSource，让引擎看到所有 Agent 在同一个网络里。

每个 Agent 带有来源标签(source)和场景标签(scene_ids)，支持 scope 过滤。
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

from towow import BaseAdapter

logger = logging.getLogger(__name__)


class AgentEntry:
    """网络中一个 Agent 的注册信息。"""

    __slots__ = ("agent_id", "adapter", "source", "scene_ids", "display_name")

    def __init__(
        self,
        agent_id: str,
        adapter: BaseAdapter,
        source: str = "",
        scene_ids: list[str] | None = None,
        display_name: str = "",
    ):
        self.agent_id = agent_id
        self.adapter = adapter
        self.source = source
        self.scene_ids = scene_ids or []
        self.display_name = display_name


class CompositeAdapter(BaseAdapter):
    """
    多数据源合并适配器。

    用法：
        composite = CompositeAdapter()
        composite.register_source("hackathon", json_adapter, scene_ids=["hackathon"])
        composite.register_agent("user_abc", secondme_adapter, source="secondme")

        # 查询
        all_ids = composite.all_agent_ids
        hackathon_ids = composite.get_agents_by_scope("scene:hackathon")
        network_ids = composite.get_agents_by_scope("all")

        # ProfileDataSource 接口 — 自动路由到正确的子 adapter
        profile = await composite.get_profile("user_abc")
        response = await composite.chat("user_abc", messages)
    """

    def __init__(self):
        self._agents: dict[str, AgentEntry] = {}

    # ── 注册方法 ──

    def register_source(
        self,
        source_name: str,
        adapter: BaseAdapter,
        agent_ids: list[str] | None = None,
        scene_ids: list[str] | None = None,
        display_names: dict[str, str] | None = None,
    ) -> list[str]:
        """
        批量注册一个数据源的所有 Agent。

        Args:
            source_name: 来源标识（如 "hackathon", "secondme"）
            adapter: 子 adapter 实例
            agent_ids: 要注册的 agent_id 列表。如果 adapter 有 agent_ids 属性则自动获取。
            scene_ids: 这些 Agent 关联的场景 ID 列表
            display_names: agent_id → 显示名 映射

        Returns:
            实际注册的 agent_id 列表
        """
        if agent_ids is None:
            agent_ids = getattr(adapter, "agent_ids", [])

        names = display_names or {}
        if not names and hasattr(adapter, "get_display_names"):
            names = adapter.get_display_names()

        registered = []
        for aid in agent_ids:
            entry = AgentEntry(
                agent_id=aid,
                adapter=adapter,
                source=source_name,
                scene_ids=list(scene_ids or []),
                display_name=names.get(aid, aid),
            )
            self._agents[aid] = entry
            registered.append(aid)

        logger.info(
            "注册数据源 %s: %d 个 Agent, 场景=%s",
            source_name, len(registered), scene_ids or [],
        )
        return registered

    def register_agent(
        self,
        agent_id: str,
        adapter: BaseAdapter,
        source: str = "",
        scene_ids: list[str] | None = None,
        display_name: str = "",
    ) -> None:
        """注册单个 Agent。"""
        self._agents[agent_id] = AgentEntry(
            agent_id=agent_id,
            adapter=adapter,
            source=source,
            scene_ids=list(scene_ids or []),
            display_name=display_name,
        )
        logger.info("注册 Agent %s (来源=%s, 场景=%s)", agent_id, source, scene_ids or [])

    def unregister_agent(self, agent_id: str) -> bool:
        """移除一个 Agent。返回是否成功。"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def add_scene_to_agent(self, agent_id: str, scene_id: str) -> None:
        """给已注册的 Agent 添加场景标签。"""
        entry = self._agents.get(agent_id)
        if entry and scene_id not in entry.scene_ids:
            entry.scene_ids.append(scene_id)

    # ── 查询方法 ──

    @property
    def all_agent_ids(self) -> list[str]:
        """所有已注册的 agent_id。"""
        return list(self._agents.keys())

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    def get_agents_by_scope(self, scope: str) -> list[str]:
        """
        根据 scope 过滤 Agent。

        scope 格式：
        - "all" 或 "network": 返回所有 Agent
        - "scene:{scene_id}": 只返回属于该场景的 Agent
        """
        if scope in ("all", "network", ""):
            return self.all_agent_ids

        if scope.startswith("scene:"):
            target_scene = scope[len("scene:"):]
            return [
                aid for aid, entry in self._agents.items()
                if target_scene in entry.scene_ids
            ]

        logger.warning("未知的 scope 格式: %s, 返回全部", scope)
        return self.all_agent_ids

    def get_display_names(self) -> dict[str, str]:
        """返回所有 Agent 的显示名（含来源标注）。"""
        result = {}
        for aid, entry in self._agents.items():
            name = entry.display_name or aid
            if entry.source:
                result[aid] = f"{name}（{entry.source}）"
            else:
                result[aid] = name
        return result

    def get_agent_info(self, agent_id: str) -> dict[str, Any] | None:
        """获取 Agent 的注册信息（来源、场景等）。"""
        entry = self._agents.get(agent_id)
        if not entry:
            return None
        return {
            "agent_id": entry.agent_id,
            "source": entry.source,
            "scene_ids": entry.scene_ids,
            "display_name": entry.display_name,
        }

    def get_all_agents_info(self) -> list[dict[str, Any]]:
        """列出所有 Agent 的注册信息。"""
        return [
            {
                "agent_id": e.agent_id,
                "source": e.source,
                "scene_ids": e.scene_ids,
                "display_name": e.display_name,
            }
            for e in self._agents.values()
        ]

    # ── ProfileDataSource 接口实现 ──

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """从正确的子 adapter 获取画像。"""
        entry = self._agents.get(agent_id)
        if not entry:
            logger.warning("Agent %s 未注册", agent_id)
            return {"agent_id": agent_id}

        profile = await entry.adapter.get_profile(agent_id)
        # 注入来源和场景信息
        profile.setdefault("source", entry.source)
        profile.setdefault("scene_ids", entry.scene_ids)
        return profile

    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """路由到正确的子 adapter 进行对话。"""
        entry = self._agents.get(agent_id)
        if not entry:
            return f"[{agent_id}] Agent 未注册到网络中"
        return await entry.adapter.chat(agent_id, messages, system_prompt)

    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """路由到正确的子 adapter 进行流式对话。"""
        entry = self._agents.get(agent_id)
        if not entry:
            yield f"[{agent_id}] Agent 未注册到网络中"
            return
        async for chunk in entry.adapter.chat_stream(agent_id, messages, system_prompt):
            yield chunk
