"""
MockLLMClient — 开发模式下的模拟 LLM 客户端。

实现 PlatformLLMClient Protocol，用于无 API Key 时的本地开发。
Center 会收到预设的 tool call 响应，直接输出方案。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MockLLMClient:
    """
    模拟的 PlatformLLMClient，用于开发和测试。

    行为：
    - 第一次调用：返回 output_plan tool call
    - 支持 tools 参数（忽略但不报错）
    """

    def __init__(self, plan_template: str = ""):
        self._plan_template = plan_template
        self._call_count = 0

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        self._call_count += 1

        # 从 messages 中提取需求和 offer 信息
        context_parts = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 20:
                context_parts.append(content[:200])

        if tools:
            # Center 调用（有 tools）— 返回 output_plan
            plan_text = self._plan_template or self._generate_plan(context_parts)
            return {
                "content": None,
                "tool_calls": [{
                    "name": "output_plan",
                    "arguments": {"plan_text": plan_text},
                    "id": f"mock_tool_{self._call_count}",
                }],
                "stop_reason": "tool_use",
            }
        else:
            # 普通 chat 调用
            return {
                "content": "这是一个基于团队分析的综合方案。",
                "tool_calls": None,
                "stop_reason": "end_turn",
            }

    def _generate_plan(self, context_parts: list[str]) -> str:
        return (
            "## 协商方案\n\n"
            "基于所有参与者的响应分析，以下是推荐方案：\n\n"
            "### 核心发现\n"
            "各参与者展现了互补的能力特征，可以形成有效的协作组合。\n\n"
            "### 推荐组合\n"
            "根据需求分析和能力匹配，建议以上参与者组成协作团队。\n\n"
            "### 注意事项\n"
            "- 团队成员的技能互补性较好\n"
            "- 建议先进行一次线上沟通确认合作意向\n"
            "- 具体分工可根据项目进展动态调整\n"
        )
