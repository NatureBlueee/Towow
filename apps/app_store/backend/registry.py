"""
应用注册表 — App Store 的核心组件。

管理所有已注册的 AToA 应用：
- 注册/注销应用
- 查询应用列表
- 获取跨应用 Agent 列表
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RegisteredApp:
    """已注册的 AToA 应用。"""
    app_id: str
    app_name: str
    base_url: str  # e.g. "http://localhost:8100"
    scene_id: str = ""
    scene_name: str = ""
    description: str = ""
    agent_count: int = 0
    agent_ids: list[str] = field(default_factory=list)


class AppRegistry:
    """
    AToA 应用注册表。

    每个应用启动时向 App Store 注册自己的信息。
    App Store 通过注册表知道所有可用的应用和 Agent。
    """

    def __init__(self):
        self._apps: dict[str, RegisteredApp] = {}

    def register(self, app: RegisteredApp) -> None:
        self._apps[app.app_id] = app
        logger.info("应用注册: %s (%s) — %d 个 Agent", app.app_name, app.app_id, app.agent_count)

    def unregister(self, app_id: str) -> None:
        if app_id in self._apps:
            name = self._apps[app_id].app_name
            del self._apps[app_id]
            logger.info("应用注销: %s (%s)", name, app_id)

    @property
    def apps(self) -> dict[str, RegisteredApp]:
        return self._apps

    def get_all_agents(self) -> list[dict[str, Any]]:
        """获取所有应用的 Agent 列表（含来源应用信息）。"""
        agents = []
        for app in self._apps.values():
            for aid in app.agent_ids:
                agents.append({
                    "agent_id": f"{app.app_id}:{aid}",
                    "original_agent_id": aid,
                    "app_id": app.app_id,
                    "app_name": app.app_name,
                    "app_url": app.base_url,
                })
        return agents

    async def discover_app(self, base_url: str) -> RegisteredApp | None:
        """
        自动发现应用——调用应用的 /api/info 接口获取信息。

        这实现了"每个应用可以独立运行，连接 App Store 后自动扩展"的设计。
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/api/info")
                resp.raise_for_status()
                data = resp.json()

                app = RegisteredApp(
                    app_id=data.get("scene_id", base_url),
                    app_name=data.get("app_name", "未知应用"),
                    base_url=base_url,
                    scene_id=data.get("scene_id", ""),
                    scene_name=data.get("scene_name", ""),
                    description=data.get("description", ""),
                    agent_count=data.get("agent_count", 0),
                    agent_ids=data.get("agent_ids", []),
                )
                return app
        except Exception as e:
            logger.warning("发现应用失败 %s: %s", base_url, e)
            return None
