"""
AToA 应用共享基础设施。

- JSONFileAdapter: 从 JSON 文件读取 Agent 画像的适配器
- MockLLMClient: 开发模式下的模拟 LLM 客户端
"""

from .json_adapter import JSONFileAdapter
from .mock_llm import MockLLMClient

__all__ = [
    "JSONFileAdapter",
    "MockLLMClient",
]
