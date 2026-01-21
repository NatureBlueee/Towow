"""
LLM服务 - 封装大模型调用

提供统一的LLM调用接口，支持：
- 多模型切换
- 异步调用
- 基础错误处理
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM服务

    封装大模型API调用，支持多种模型。
    当前支持 Anthropic Claude 系列模型。
    """

    def __init__(
        self,
        client=None,
        model: str = "claude-3-sonnet-20240229"
    ):
        """
        初始化LLM服务

        Args:
            client: Anthropic AsyncAnthropic客户端实例
            model: 模型名称
        """
        self.client = client
        self.model = model

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        fallback_key: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> str:
        """
        调用LLM完成

        Args:
            prompt: 用户提示
            system: 系统提示
            fallback_key: 降级响应key（预留给TASK-020）
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数传递给API

        Returns:
            LLM响应文本

        Raises:
            Exception: 当调用失败且没有降级响应时
        """
        if not self.client:
            logger.warning("No LLM client configured")
            return "{}"

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise

    async def complete_with_tools(
        self,
        prompt: str,
        tools: list,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用工具调用LLM

        Args:
            prompt: 用户提示
            tools: 工具定义列表
            system: 系统提示
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            包含响应和工具调用的字典
        """
        if not self.client:
            logger.warning("No LLM client configured")
            return {"content": "", "tool_calls": []}

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                **kwargs
            )

            result = {
                "content": "",
                "tool_calls": []
            }

            for block in response.content:
                if block.type == "text":
                    result["content"] = block.text
                elif block.type == "tool_use":
                    result["tool_calls"].append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })

            return result
        except Exception as e:
            logger.error(f"LLM tool call error: {e}")
            raise

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ):
        """
        流式调用LLM

        Args:
            prompt: 用户提示
            system: 系统提示
            max_tokens: 最大token数
            **kwargs: 其他参数

        Yields:
            响应文本片段
        """
        if not self.client:
            logger.warning("No LLM client configured")
            return

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """
        获取服务状态

        Returns:
            状态字典
        """
        return {
            "configured": self.client is not None,
            "model": self.model
        }


# 全局LLM服务实例
llm_service: Optional[LLMService] = None


def init_llm_service(
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> LLMService:
    """
    初始化LLM服务

    Args:
        api_key: Anthropic API密钥
        model: 模型名称

    Returns:
        初始化后的LLMService实例
    """
    global llm_service

    if api_key:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)
            llm_service = LLMService(
                client=client,
                model=model or "claude-3-sonnet-20240229"
            )
            logger.info("LLM service initialized with API key")
        except ImportError:
            logger.warning("anthropic package not installed")
            llm_service = LLMService()
    else:
        llm_service = LLMService()
        logger.warning("LLM service initialized without API key")

    return llm_service


def get_llm_service() -> Optional[LLMService]:
    """
    获取全局LLM服务实例

    Returns:
        LLMService实例或None
    """
    return llm_service
