"""
R1 AI 招聘应用 — 基于通爻 SDK 的 AToA 应用。

场景：AI 智能招聘。发出招聘需求（"需要一个高级后端开发者"），
候选人 Agent 自主判断匹配度，协商出最佳人才推荐方案。

启动：
    cd apps/R1_recruitment
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... uvicorn backend.app:app --reload --port 8102
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from apps.shared import create_app, AppConfig

config = AppConfig(
    app_name="AI 招聘",
    app_description="AI 驱动的智能招聘 — 发出岗位需求，让合适的候选人来响应你",
    data_dir=str(Path(__file__).resolve().parent.parent / "data"),
    frontend_dir=str(Path(__file__).resolve().parent.parent / "frontend"),
    port=8102,
    scene_id="scene_recruitment",
    scene_name="AI 招聘",
    scene_description="连接企业和候选人，协商最佳招聘方案",
    expected_responders=5,
)

app = create_app(config)
