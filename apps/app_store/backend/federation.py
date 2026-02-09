"""
联邦 ProfileDataSource — 跨应用共振的关键。

这是 App Store 架构的核心创新：
通过一个联邦适配器，将所有注册应用的 Agent 聚合到同一个数据源中。
当任何应用发起需求时，所有应用的 Agent 都有机会响应。

架构决策（见 MASTER_PLAN_ATOA_APPS.md）：
- 联邦层不是新的引擎——它在 ProfileDataSource 层做文章
- 每个应用可以独立运行（不连接 App Store 也能用）
- 连接 App Store 后，ProfileDataSource 自动扩展到跨应用 Agent
- 协议层不变——只是 Agent 来源扩大了
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Optional

import httpx

from towow import BaseAdapter
from .registry import AppRegistry

logger = logging.getLogger(__name__)


class FederatedAdapter(BaseAdapter):
    """
    联邦适配器 — 聚合所有注册应用的 Agent。

    get_profile: 从对应应用的 API 获取 Agent 画像
    chat: 将请求路由到对应应用的 API

    Agent ID 格式: "{app_id}:{original_agent_id}"
    这样可以区分来自不同应用的同名 Agent。
    """

    def __init__(self, registry: AppRegistry):
        self._registry = registry
        self._profile_cache: dict[str, dict[str, Any]] = {}

    def _parse_agent_id(self, agent_id: str) -> tuple[str, str]:
        """解析联邦 Agent ID 为 (app_id, original_agent_id)。"""
        if ":" in agent_id:
            app_id, original_id = agent_id.split(":", 1)
            return app_id, original_id
        # 如果没有前缀，尝试在所有应用中查找
        for app in self._registry.apps.values():
            if agent_id in app.agent_ids:
                return app.app_id, agent_id
        return "", agent_id

    def _get_app_url(self, app_id: str) -> str | None:
        app = self._registry.apps.get(app_id)
        return app.base_url if app else None

    @property
    def all_agent_ids(self) -> list[str]:
        """所有联邦 Agent ID。"""
        return [a["agent_id"] for a in self._registry.get_all_agents()]

    def get_display_names(self) -> dict[str, str]:
        """所有 Agent 的显示名（含应用来源）。"""
        names = {}
        for app in self._registry.apps.values():
            for aid in app.agent_ids:
                fed_id = f"{app.app_id}:{aid}"
                names[fed_id] = f"{aid}（{app.app_name}）"
        return names

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        """从对应应用获取 Agent 画像。"""
        if agent_id in self._profile_cache:
            return self._profile_cache[agent_id]

        app_id, original_id = self._parse_agent_id(agent_id)
        base_url = self._get_app_url(app_id)
        if not base_url:
            return {"agent_id": agent_id, "error": "应用未注册"}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/api/agents")
                resp.raise_for_status()
                data = resp.json()
                for agent in data.get("agents", []):
                    if agent.get("agent_id") == original_id:
                        agent["source_app"] = app_id
                        self._profile_cache[agent_id] = agent
                        return agent
        except Exception as e:
            logger.warning("获取画像失败 %s: %s", agent_id, e)

        return {"agent_id": agent_id}

    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        路由 chat 请求到对应应用。

        跨应用 chat 通过 App Store 的 LLM 客户端完成——
        用该 Agent 的画像作为 system prompt，让平台 LLM 扮演。
        """
        profile = await self.get_profile(agent_id)
        name = profile.get("name", agent_id)
        role = profile.get("role", "")
        skills = profile.get("skills", [])
        bio = profile.get("bio", "")
        source = profile.get("source_app", "")

        sp = (
            f"你是{name}，来自「{source}」应用。\n"
            f"角色：{role}\n"
            f"技能：{', '.join(skills) if skills else '未知'}\n"
            f"简介：{bio}\n"
            f"请用中文回复，保持角色特征。"
        )
        if system_prompt:
            sp = system_prompt + "\n\n" + sp

        # 使用内置的 LLM 客户端（如果可用）
        if hasattr(self, '_llm_client') and self._llm_client:
            result = await self._llm_client.chat(messages=messages, system_prompt=sp)
            if isinstance(result, dict):
                return result.get("content", "") or ""
            return str(result)

        return f"[{name}] 来自{source}：{bio}"

    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        full = await self.chat(agent_id, messages, system_prompt)
        yield full

    def set_llm_client(self, client: Any) -> None:
        """设置用于跨应用 chat 的 LLM 客户端。"""
        self._llm_client = client
