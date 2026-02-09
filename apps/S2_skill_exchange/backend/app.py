"""
S2 技能交换平台 — 基于通爻 SDK 的 AToA 应用。

场景：技能交换。用户发出学习需求（"我想学吉他"），
技能提供者 Agent 自主判断是否能满足，协商出最佳学习方案。

启动：
    cd apps/S2_skill_exchange
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn backend.app:app --reload --port 8101
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from apps.shared import create_app, AppConfig

config = AppConfig(
    app_name="技能交换",
    app_description="AI 驱动的技能交换平台 — 发出你想学的技能，让合适的老师来响应你",
    data_dir=str(Path(__file__).resolve().parent.parent / "data"),
    frontend_dir=str(Path(__file__).resolve().parent.parent / "frontend"),
    port=8101,
    scene_id="scene_skill_exchange",
    scene_name="技能交换",
    scene_description="连接技能需求者和提供者，协商最佳学习方案",
    expected_responders=4,
)

app = create_app(config)
