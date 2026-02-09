"""
AToA 应用共享基础设施。

所有 AToA 应用共享：
- JSONFileAdapter: 从 JSON 文件读取 Agent 画像的适配器
- create_app: 创建标准 FastAPI 应用的工厂函数
- MockLLMClient: 开发模式下的模拟 LLM 客户端
"""

from .json_adapter import JSONFileAdapter
from .app_factory import create_app, AppConfig
from .mock_llm import MockLLMClient

__all__ = [
    "JSONFileAdapter",
    "create_app",
    "AppConfig",
    "MockLLMClient",
]
