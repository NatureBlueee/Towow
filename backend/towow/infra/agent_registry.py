"""
AgentRegistry — 统一的 Agent 注册表和 Adapter 路由。

基础设施层组件。所有 Agent（SecondMe 用户、Demo agent、JSON 样板间等）在此注册，
全网络共享一个 Registry 实例。Engine 和 App Store 都通过它访问 agent 信息。

实现 BaseAdapter（ProfileDataSource 协议），Engine 直接当 adapter 使用。
按 agent_id 路由到正确的子 adapter。

设计决策:
  - ADR-001: 从应用层下沉到基础设施层
  - ED-1: adapter 提供 LLM 通道，Registry 提供 profile 路由
  - ED-3: JSONFileAdapter agent 的 profile 由 adapter 自己提供
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

from towow.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class AgentEntry:
    """网络中一个 Agent 的注册信息。"""

    __slots__ = ("agent_id", "adapter", "source", "scene_ids", "display_name", "profile_data")

    def __init__(
        self,
        agent_id: str,
        adapter: BaseAdapter | None = None,
        source: str = "",
        scene_ids: list[str] | None = None,
        display_name: str = "",
        profile_data: dict | None = None,
    ):
        self.agent_id = agent_id
        self.adapter = adapter
        self.source = source
        self.scene_ids = scene_ids or []
        self.display_name = display_name
        self.profile_data = profile_data or {}


class AgentRegistry(BaseAdapter):
    """
    统一的 Agent 注册表，实现 ProfileDataSource 协议。

    用法：
        registry = AgentRegistry()
        registry.set_default_adapter(claude_adapter)
        registry.register_agent("user_abc", secondme_adapter, source="SecondMe")
        registry.register_source("hackathon", json_adapter, scene_ids=["hackathon"])

        # ProfileDataSource 接口 — 按 agent_id 路由到正确的子 adapter
        profile = await registry.get_profile("user_abc")
        response = await registry.chat("user_abc", messages)

        # 查询
        all_ids = registry.all_agent_ids
        hackathon_ids = registry.get_agents_by_scope("scene:hackathon")
    """

    def __init__(self):
        self._agents: dict[str, AgentEntry] = {}
        self._default_adapter: BaseAdapter | None = None

    # ── 默认 adapter ──

    def set_default_adapter(self, adapter: BaseAdapter) -> None:
        """设置默认 adapter（给 demo/匿名用户）。"""
        self._default_adapter = adapter

    @property
    def default_adapter(self) -> BaseAdapter | None:
        return self._default_adapter

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

        # 从 adapter 获取 profile 数据（如果有同步接口）
        profiles = getattr(adapter, "profiles", {})

        registered = []
        for aid in agent_ids:
            entry = AgentEntry(
                agent_id=aid,
                adapter=adapter,
                source=source_name,
                scene_ids=list(scene_ids or []),
                display_name=names.get(aid, aid),
                profile_data=profiles.get(aid, {}),
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
        adapter: BaseAdapter | None = None,
        source: str = "",
        scene_ids: list[str] | None = None,
        display_name: str = "",
        profile_data: dict | None = None,
    ) -> None:
        """注册单个 Agent。"""
        self._agents[agent_id] = AgentEntry(
            agent_id=agent_id,
            adapter=adapter,
            source=source,
            scene_ids=list(scene_ids or []),
            display_name=display_name,
            profile_data=profile_data,
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
        """获取 Agent 的注册信息（来源、场景、画像摘要）。"""
        entry = self._agents.get(agent_id)
        if not entry:
            return None
        info: dict[str, Any] = {
            "agent_id": entry.agent_id,
            "source": entry.source,
            "scene_ids": entry.scene_ids,
            "display_name": entry.display_name,
        }
        # 从 profile_data 提取摘要字段（供 agent listings / summaries 使用）
        pd = entry.profile_data
        if pd:
            for key in ("skills", "bio", "role", "self_introduction", "interests",
                         "experience", "shades", "memories", "raw_text"):
                if pd.get(key):
                    info[key] = pd[key]
        return info

    def get_identity(self, agent_id: str) -> dict[str, Any] | None:
        """
        获取 Agent 的身份信息（替代旧的 state.agents 查询）。

        Returns:
            {agent_id, display_name, source, scene_ids} 或 None
        """
        entry = self._agents.get(agent_id)
        if not entry:
            return None
        return {
            "agent_id": entry.agent_id,
            "display_name": entry.display_name,
            "source": entry.source,
            "scene_ids": entry.scene_ids,
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
        """
        从正确的子 adapter 获取画像。

        路由逻辑:
        1. agent 已注册 → 问 adapter.get_profile()
           - adapter 返回丰富数据（SecondMe）→ 直接用
           - adapter 返回最小数据（ClaudeAdapter）→ fallback 到 entry.profile_data
        2. agent 未注册 → 返回最小标识
        """
        entry = self._agents.get(agent_id)
        if not entry:
            logger.warning("Agent %s 未注册", agent_id)
            return {"agent_id": agent_id}

        # adapter=None（如：从文件恢复的 SecondMe 用户）→ 直接用 profile_data
        if entry.adapter is None:
            profile = {**(entry.profile_data or {}), "agent_id": agent_id}
            profile.setdefault("source", entry.source)
            profile.setdefault("scene_ids", entry.scene_ids)
            return profile

        profile = await entry.adapter.get_profile(agent_id)

        # ClaudeAdapter 只返回 {"agent_id": id}，用 profile_data 补充
        if len(profile) <= 1 and entry.profile_data:
            profile = {**entry.profile_data, **profile}

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
            from towow.core.errors import AdapterError
            raise AdapterError(f"Agent {agent_id} 未注册到网络中")
        if entry.adapter is None:
            from towow.core.errors import AdapterError
            raise AdapterError(f"Agent {agent_id} 的会话已过期，需要重新登录")
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
            from towow.core.errors import AdapterError
            raise AdapterError(f"Agent {agent_id} 未注册到网络中")
        if entry.adapter is None:
            from towow.core.errors import AdapterError
            raise AdapterError(f"Agent {agent_id} 的会话已过期，需要重新登录")

        async for chunk in entry.adapter.chat_stream(agent_id, messages, system_prompt):
            yield chunk
