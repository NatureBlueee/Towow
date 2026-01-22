"""OpenAgents configuration."""

from pydantic_settings import BaseSettings
from typing import Optional


class OpenAgentConfig(BaseSettings):
    """OpenAgent connection settings."""

    host: str = "localhost"
    http_port: int = 8700
    grpc_port: int = 8600
    use_grpc: bool = True

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self.http_port}"

    @property
    def grpc_url(self) -> str:
        return f"{self.host}:{self.grpc_port}"

    class Config:
        env_prefix = "OPENAGENT_"


class AppConfig(BaseSettings):
    """Application configuration."""

    env: str = "development"
    debug: bool = True
    anthropic_api_key: str = ""
    database_url: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"  # 忽略额外的环境变量


openagent_config = OpenAgentConfig()
app_config = AppConfig()
