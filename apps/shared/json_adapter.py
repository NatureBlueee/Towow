"""
JSONFileAdapter — 从 JSON 文件读取 Agent 画像的适配器。

实现 ProfileDataSource Protocol，所有 AToA 应用共用。
每个应用提供自己的 agents.json，本适配器负责读取和服务。

使用方式：
    adapter = JSONFileAdapter(
        json_path="data/agents.json",
        llm_client=my_llm_client,  # 用于 chat/chat_stream
    )
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from towow import BaseAdapter

logger = logging.getLogger(__name__)


class JSONFileAdapter(BaseAdapter):
    """
    从 JSON 文件加载 Agent 画像数据的适配器。

    JSON 格式：
    {
        "agent_id": {
            "name": "显示名",
            "role": "角色",
            "skills": ["技能1", "技能2"],
            "bio": "简介",
            ...任意字段...
        }
    }

    chat 功能通过传入的 PlatformLLMClient 实现——
    将 Agent 画像注入 system prompt，让 LLM 扮演该 Agent。
    """

    def __init__(
        self,
        json_path: str | Path,
        llm_client: Any = None,
        model: str = "claude-sonnet-4-5-20250929",
    ):
        self._profiles: dict[str, dict[str, Any]] = {}
        self._llm_client = llm_client
        self._model = model
        self._load(json_path)

    def _load(self, json_path: str | Path) -> None:
        path = Path(json_path)
        if not path.exists():
            logger.warning("Agent 数据文件不存在: %s", path)
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            self._profiles = data
        elif isinstance(data, list):
            # 支持列表格式：[{agent_id: "xxx", ...}, ...]
            for item in data:
                aid = item.get("agent_id", item.get("id", ""))
                if aid:
                    self._profiles[aid] = item
        logger.info("加载了 %d 个 Agent 画像: %s", len(self._profiles), list(self._profiles.keys()))

    @property
    def agent_ids(self) -> list[str]:
        return list(self._profiles.keys())

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        return self._profiles

    def get_display_names(self) -> dict[str, str]:
        return {
            aid: p.get("name", aid) for aid, p in self._profiles.items()
        }

    async def get_profile(self, agent_id: str) -> dict[str, Any]:
        profile = self._profiles.get(agent_id)
        if profile is None:
            return {"agent_id": agent_id}
        return profile

    def _build_system_prompt(self, agent_id: str) -> str:
        """根据 Agent 画像构建 system prompt，让 LLM 扮演该 Agent。"""
        profile = self._profiles.get(agent_id, {})
        name = profile.get("name", agent_id)
        role = profile.get("role", "")
        skills = profile.get("skills", [])
        bio = profile.get("bio", "")
        extra = {k: v for k, v in profile.items()
                 if k not in ("name", "role", "skills", "bio", "agent_id", "id")}

        parts = [f"你是{name}。"]
        if role:
            parts.append(f"你的角色是：{role}。")
        if skills:
            parts.append(f"你的核心技能：{', '.join(skills)}。")
        if bio:
            parts.append(f"你的简介：{bio}")
        if extra:
            for k, v in extra.items():
                if isinstance(v, str):
                    parts.append(f"{k}：{v}")
                elif isinstance(v, list):
                    parts.append(f"{k}：{', '.join(str(i) for i in v)}")
        parts.append("请用中文回复，保持你的角色特征。回复要具体、有洞察力。")
        return "\n".join(parts)

    async def chat(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        if self._llm_client is None:
            # 无 LLM 客户端时，返回基于画像的模拟回复
            profile = self._profiles.get(agent_id, {})
            name = profile.get("name", agent_id)
            skills = profile.get("skills", [])
            bio = profile.get("bio", "")
            return f"[{name}] 我的技能是{', '.join(skills)}。{bio}"

        sp = system_prompt or self._build_system_prompt(agent_id)
        # 使用 PlatformLLMClient 的 chat 接口
        if hasattr(self._llm_client, "chat"):
            result = await self._llm_client.chat(
                messages=messages,
                system_prompt=sp,
            )
            # PlatformLLMClient 返回 dict
            if isinstance(result, dict):
                return result.get("content", "") or ""
            return str(result)
        return f"[{agent_id}] LLM 客户端不支持 chat"

    async def chat_stream(
        self,
        agent_id: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        # V1: 不实现真正的流式，直接 yield 完整回复
        full = await self.chat(agent_id, messages, system_prompt)
        yield full
