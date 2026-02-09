"""
S1 黑客松组队应用 — 基于通爻 SDK 的 AToA 应用。

场景：黑客松参赛者组队。用户发出需求（"我想做一个AI产品"），
系统中的 Agent（参赛者）自主判断是否响应，最终协商出最佳团队组合。

启动：
    cd apps/S1_hackathon
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn backend.app:app --reload --port 8100

开发模式（无需 API Key）：
    uvicorn backend.app:app --reload --port 8100
"""

import sys
from pathlib import Path

# 确保能 import apps.shared
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from apps.shared import create_app, AppConfig

config = AppConfig(
    app_name="黑客松组队",
    app_description="AI 驱动的黑客松团队匹配 — 发出你的项目想法，让合适的队友来响应你",
    data_dir=str(Path(__file__).resolve().parent.parent / "data"),
    frontend_dir=str(Path(__file__).resolve().parent.parent / "frontend"),
    port=8100,
    scene_id="scene_hackathon",
    scene_name="黑客松组队",
    scene_description="为黑客松参赛者找到最佳队友组合",
    expected_responders=5,
)

app = create_app(config)
