"""
ToWow Shared Configuration

Centralized configuration for the ToWow platform.
All configurable parameters should be defined here.

Environment variables take precedence over default values.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List


def _get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable with default fallback."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_float(key: str, default: float) -> float:
    """Get float from environment variable with default fallback."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


# ============ Negotiation Configuration ============

# Maximum number of negotiation rounds before forcing a decision
# Can be overridden by TOWOW_MAX_NEGOTIATION_ROUNDS environment variable
MAX_NEGOTIATION_ROUNDS: int = _get_env_int("TOWOW_MAX_NEGOTIATION_ROUNDS", 3)

# Response timeout in seconds (how long to wait for agent responses)
RESPONSE_TIMEOUT: int = _get_env_int("TOWOW_RESPONSE_TIMEOUT", 300)

# Feedback timeout in seconds (how long to wait for proposal feedback)
FEEDBACK_TIMEOUT: int = _get_env_int("TOWOW_FEEDBACK_TIMEOUT", 120)

# ============ Negotiation Stage Delays (for realistic UX) ============

# Enable stage delays for more realistic negotiation experience
# Set to False for faster testing, True for production/demo
ENABLE_STAGE_DELAYS: bool = os.getenv("TOWOW_ENABLE_STAGE_DELAYS", "true").lower() == "true"

# Delay before filter completion event (seconds)
FILTER_STAGE_DELAY: float = _get_env_float("TOWOW_FILTER_STAGE_DELAY", 1.5)

# Delay before each agent response (seconds) - simulates "thinking time"
AGENT_RESPONSE_DELAY: float = _get_env_float("TOWOW_AGENT_RESPONSE_DELAY", 0.8)

# Delay before aggregation starts (seconds)
AGGREGATION_STAGE_DELAY: float = _get_env_float("TOWOW_AGGREGATION_STAGE_DELAY", 1.0)

# Delay before proposal distribution (seconds)
PROPOSAL_STAGE_DELAY: float = _get_env_float("TOWOW_PROPOSAL_STAGE_DELAY", 1.2)

# Delay for LLM mock responses (seconds) - simulates LLM processing time
LLM_MOCK_DELAY: float = _get_env_float("TOWOW_LLM_MOCK_DELAY", 0.5)


# ============ Gap Identification Configuration ============

# Minimum number of participants required for a successful negotiation
# Can be overridden by TOWOW_MIN_PARTICIPANTS_THRESHOLD environment variable
MIN_PARTICIPANTS_THRESHOLD: int = _get_env_int("TOWOW_MIN_PARTICIPANTS_THRESHOLD", 2)

# Coverage threshold (0.0 to 1.0) - below this value is considered a gap
# Can be overridden by TOWOW_COVERAGE_THRESHOLD environment variable
COVERAGE_THRESHOLD: float = _get_env_float("TOWOW_COVERAGE_THRESHOLD", 0.7)


# ============ Mock Candidates Configuration ============

# Shared mock candidate data used by both demand.py and coordinator.py
# This ensures consistency across fallback/mock scenarios
# FIX: Increased to 12 candidates to support meaningful filtering
MOCK_CANDIDATES: List[Dict[str, Any]] = [
    {
        "agent_id": "user_agent_bob",
        "display_name": "Bob",
        "reason": "场地资源丰富",
        "relevance_score": 95,
        "expected_role": "场地提供者",
        "capabilities": ["场地资源", "活动组织"],
        "keywords": ["场地", "会议室", "空间", "活动"]
    },
    {
        "agent_id": "user_agent_alice",
        "display_name": "Alice",
        "reason": "技术分享能力强",
        "relevance_score": 92,
        "expected_role": "技术顾问",
        "capabilities": ["技术分享", "AI研究"],
        "keywords": ["技术", "AI", "分享", "演讲", "人工智能"]
    },
    {
        "agent_id": "user_agent_charlie",
        "display_name": "Charlie",
        "reason": "活动策划经验丰富",
        "relevance_score": 88,
        "expected_role": "活动策划",
        "capabilities": ["活动策划", "流程设计"],
        "keywords": ["活动", "策划", "组织", "流程"]
    },
    {
        "agent_id": "user_agent_david",
        "display_name": "David",
        "reason": "UI设计能力出色",
        "relevance_score": 85,
        "expected_role": "设计师",
        "capabilities": ["UI设计", "产品原型"],
        "keywords": ["设计", "UI", "原型", "视觉"]
    },
    {
        "agent_id": "user_agent_emma",
        "display_name": "Emma",
        "reason": "产品管理经验丰富",
        "relevance_score": 82,
        "expected_role": "产品经理",
        "capabilities": ["产品经理", "需求分析"],
        "keywords": ["产品", "管理", "需求", "用户"]
    },
    {
        "agent_id": "user_agent_frank",
        "display_name": "Frank",
        "reason": "后端开发专家",
        "relevance_score": 80,
        "expected_role": "后端开发",
        "capabilities": ["后端开发", "系统架构"],
        "keywords": ["后端", "开发", "架构", "API", "技术"]
    },
    {
        "agent_id": "user_agent_grace",
        "display_name": "Grace",
        "reason": "市场营销专业",
        "relevance_score": 78,
        "expected_role": "市场营销",
        "capabilities": ["市场营销", "品牌推广"],
        "keywords": ["市场", "营销", "推广", "品牌", "活动"]
    },
    {
        "agent_id": "user_agent_henry",
        "display_name": "Henry",
        "reason": "摄影摄像能力强",
        "relevance_score": 75,
        "expected_role": "摄影师",
        "capabilities": ["摄影", "视频制作"],
        "keywords": ["摄影", "视频", "拍摄", "记录", "活动"]
    },
    {
        "agent_id": "user_agent_ivy",
        "display_name": "Ivy",
        "reason": "运营管理经验",
        "relevance_score": 72,
        "expected_role": "运营专员",
        "capabilities": ["运营管理", "数据分析"],
        "keywords": ["运营", "管理", "数据", "分析"]
    },
    {
        "agent_id": "user_agent_jack",
        "display_name": "Jack",
        "reason": "前端开发熟练",
        "relevance_score": 70,
        "expected_role": "前端开发",
        "capabilities": ["前端开发", "React"],
        "keywords": ["前端", "开发", "React", "技术", "界面"]
    },
    {
        "agent_id": "user_agent_kate",
        "display_name": "Kate",
        "reason": "内容创作专家",
        "relevance_score": 68,
        "expected_role": "内容创作",
        "capabilities": ["内容创作", "文案撰写"],
        "keywords": ["内容", "创作", "文案", "写作"]
    },
    {
        "agent_id": "user_agent_leo",
        "display_name": "Leo",
        "reason": "社区运营能手",
        "relevance_score": 65,
        "expected_role": "社区运营",
        "capabilities": ["社区运营", "用户增长"],
        "keywords": ["社区", "运营", "用户", "活动", "组织"]
    },
]


def get_mock_candidates(
    include_keywords: bool = False,
    limit: int | None = None
) -> List[Dict[str, Any]]:
    """
    Get mock candidates list.

    Args:
        include_keywords: Whether to include the keywords field
        limit: Maximum number of candidates to return (None for all)

    Returns:
        List of mock candidate dictionaries
    """
    candidates = MOCK_CANDIDATES[:limit] if limit else MOCK_CANDIDATES

    if include_keywords:
        return [dict(c) for c in candidates]

    # Remove keywords field for external use
    return [
        {k: v for k, v in c.items() if k != "keywords"}
        for c in candidates
    ]


def filter_mock_candidates_by_tags(
    capability_tags: List[str],
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Filter mock candidates by capability tags using keyword matching.

    Args:
        capability_tags: List of capability tags to match against
        max_results: Maximum number of results to return

    Returns:
        List of matching mock candidates (without keywords field)
    """
    # FIX: Return more candidates even without tags (for better demo)
    if not capability_tags:
        return get_mock_candidates(limit=10)

    matched = []
    for candidate in MOCK_CANDIDATES:
        agent_keywords = candidate.get("keywords", [])
        for tag in capability_tags:
            if any(kw in tag or tag in kw for kw in agent_keywords):
                # Remove keywords field for external use
                result = {k: v for k, v in candidate.items() if k != "keywords"}
                matched.append(result)
                break

    if matched:
        return matched[:max_results]

    # Fallback: return default candidates if no matches
    # FIX: Return more candidates for better demo
    return get_mock_candidates(limit=10)
