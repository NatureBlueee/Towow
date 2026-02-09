"""
M1 AI 相亲匹配应用 — 基于通爻 SDK 的 AToA 应用。

场景：AI 相亲。发出你的择偶期望（"希望找到一个有趣的灵魂"），
用户 Agent 自主判断兴趣和价值观的匹配度，协商出最佳匹配方案。

启动：
    cd apps/M1_matchmaking
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn backend.app:app --reload --port 8103
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from apps.shared import create_app, AppConfig

config = AppConfig(
    app_name="AI 相亲",
    app_description="AI 驱动的智能相亲 — 说出你的理想伴侣特征，让合适的人来响应你",
    data_dir=str(Path(__file__).resolve().parent.parent / "data"),
    frontend_dir=str(Path(__file__).resolve().parent.parent / "frontend"),
    port=8103,
    scene_id="scene_matchmaking",
    scene_name="AI 相亲",
    scene_description="基于兴趣和价值观的深度匹配",
    expected_responders=4,
)

app = create_app(config)
