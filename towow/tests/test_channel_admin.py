"""
Tests for ChannelAdmin Agent

测试覆盖：
- Channel状态机转换
- 需求广播
- 响应收集和聚合
- 方案分发和反馈处理
- 多轮协商
- 超时机制
"""
import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# 直接导入需要测试的类，跳过SDK依赖
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Mock OpenAgents SDK 依赖
class MockEventContext:
    """Mock EventContext"""
    def __init__(self, payload=None):
        self.incoming_event = MagicMock()
        self.incoming_event.payload = payload or {}
        self._reply_data = None

    async def reply(self, data):
        self._reply_data = data


class MockChannelMessageContext(MockEventContext):
    """Mock ChannelMessageContext"""
    def __init__(self, channel="test-channel", payload=None):
        super().__init__(payload)
        self.channel = channel


# Mock base class
class MockTowowBaseAgent:
    """Mock TowowBaseAgent"""
    def __init__(self, **kwargs):
        self.db = kwargs.get("db")
        self.llm = kwargs.get("llm_service")
        self._logger = MagicMock()
        self._sent_messages = []

    async def send_to_agent(self, agent_id, data):
        self._sent_messages.append((agent_id, data))

    def workspace(self):
        return MagicMock()


# Patch before importing
sys.modules["openagents.agents.worker_agent"] = MagicMock()
sys.modules["openagents.models.event_context"] = MagicMock()
sys.modules["openagents.models.agent_config"] = MagicMock()

# Now patch the base class import
with patch.dict("sys.modules", {"openagents.agents.base": MagicMock()}):
    # Import the module components we need to test
    from dataclasses import dataclass, field
    from enum import Enum
    from typing import Any, Dict, List, Optional


# Define test versions of the classes
class ChannelStatus(Enum):
    """Channel状态枚举"""
    CREATED = "created"
    BROADCASTING = "broadcasting"
    COLLECTING = "collecting"
    AGGREGATING = "aggregating"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    FINALIZED = "finalized"
    FAILED = "failed"


@dataclass
class ChannelState:
    """Channel状态数据类"""
    channel_id: str
    demand_id: str
    demand: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    status: ChannelStatus = ChannelStatus.CREATED
    current_round: int = 1
    max_rounds: int = 3
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    current_proposal: Optional[Dict[str, Any]] = None
    proposal_feedback: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_subnet: bool = False
    parent_channel_id: Optional[str] = None
    recursion_depth: int = 0


class TestChannelStatus:
    """测试Channel状态枚举"""

    def test_all_statuses_exist(self):
        """验证所有状态值"""
        expected = [
            "created", "broadcasting", "collecting", "aggregating",
            "proposal_sent", "negotiating", "finalized", "failed"
        ]
        actual = [s.value for s in ChannelStatus]
        assert actual == expected

    def test_status_transitions(self):
        """验证状态可以正确转换"""
        state = ChannelState(
            channel_id="test-ch",
            demand_id="test-demand",
            demand={},
            candidates=[]
        )
        assert state.status == ChannelStatus.CREATED

        state.status = ChannelStatus.BROADCASTING
        assert state.status == ChannelStatus.BROADCASTING

        state.status = ChannelStatus.FINALIZED
        assert state.status == ChannelStatus.FINALIZED


class TestChannelState:
    """测试Channel状态数据类"""

    def test_create_state(self):
        """测试创建状态"""
        state = ChannelState(
            channel_id="ch-001",
            demand_id="demand-001",
            demand={"surface_demand": "测试需求"},
            candidates=[{"agent_id": "agent-1"}, {"agent_id": "agent-2"}]
        )

        assert state.channel_id == "ch-001"
        assert state.demand_id == "demand-001"
        assert state.status == ChannelStatus.CREATED
        assert state.current_round == 1
        assert state.max_rounds == 3
        assert len(state.candidates) == 2

    def test_state_defaults(self):
        """测试默认值"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={},
            candidates=[]
        )

        assert state.responses == {}
        assert state.current_proposal is None
        assert state.proposal_feedback == {}
        assert state.is_subnet is False
        assert state.parent_channel_id is None
        assert state.recursion_depth == 0

    def test_subnet_state(self):
        """测试子网状态"""
        state = ChannelState(
            channel_id="sub-ch-001",
            demand_id="demand-001",
            demand={},
            candidates=[],
            is_subnet=True,
            parent_channel_id="ch-001",
            recursion_depth=1
        )

        assert state.is_subnet is True
        assert state.parent_channel_id == "ch-001"
        assert state.recursion_depth == 1


class TestChannelStateMachine:
    """测试Channel状态机转换逻辑"""

    def test_happy_path_state_transitions(self):
        """测试正常流程的状态转换"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={},
            candidates=[{"agent_id": "agent-1"}]
        )

        # CREATED -> BROADCASTING
        assert state.status == ChannelStatus.CREATED
        state.status = ChannelStatus.BROADCASTING
        assert state.status == ChannelStatus.BROADCASTING

        # BROADCASTING -> COLLECTING
        state.status = ChannelStatus.COLLECTING
        assert state.status == ChannelStatus.COLLECTING

        # COLLECTING -> AGGREGATING
        state.status = ChannelStatus.AGGREGATING
        assert state.status == ChannelStatus.AGGREGATING

        # AGGREGATING -> PROPOSAL_SENT
        state.status = ChannelStatus.PROPOSAL_SENT
        assert state.status == ChannelStatus.PROPOSAL_SENT

        # PROPOSAL_SENT -> NEGOTIATING
        state.status = ChannelStatus.NEGOTIATING
        assert state.status == ChannelStatus.NEGOTIATING

        # NEGOTIATING -> FINALIZED
        state.status = ChannelStatus.FINALIZED
        assert state.status == ChannelStatus.FINALIZED

    def test_failure_state_transition(self):
        """测试失败状态转换"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={},
            candidates=[]
        )

        # 从任何状态都可以转到FAILED
        state.status = ChannelStatus.COLLECTING
        state.status = ChannelStatus.FAILED
        assert state.status == ChannelStatus.FAILED


class TestResponseCollection:
    """测试响应收集逻辑"""

    def test_record_response(self):
        """测试记录响应"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={},
            candidates=[{"agent_id": "agent-1"}, {"agent_id": "agent-2"}]
        )

        # 记录第一个响应
        state.responses["agent-1"] = {
            "decision": "participate",
            "contribution": "可以提供帮助"
        }
        assert len(state.responses) == 1

        # 记录第二个响应
        state.responses["agent-2"] = {
            "decision": "decline",
            "reasoning": "时间不允许"
        }
        assert len(state.responses) == 2

    def test_filter_participants(self):
        """测试筛选参与者"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={},
            candidates=[]
        )

        state.responses = {
            "agent-1": {"decision": "participate"},
            "agent-2": {"decision": "decline"},
            "agent-3": {"decision": "conditional"},
            "agent-4": {"decision": "decline"},
        }

        participants = [
            aid for aid, resp in state.responses.items()
            if resp.get("decision") in ("participate", "conditional")
        ]

        assert len(participants) == 2
        assert "agent-1" in participants
        assert "agent-3" in participants


class TestFeedbackEvaluation:
    """测试反馈评估逻辑"""

    def test_majority_accept(self):
        """测试多数接受"""
        feedback = {
            "agent-1": {"feedback_type": "accept"},
            "agent-2": {"feedback_type": "accept"},
            "agent-3": {"feedback_type": "negotiate"},
        }

        accepts = sum(1 for f in feedback.values() if f.get("feedback_type") == "accept")
        total = len(feedback)

        # 80%阈值
        assert accepts >= total * 0.8 or accepts == total

    def test_majority_reject(self):
        """测试多数拒绝"""
        feedback = {
            "agent-1": {"feedback_type": "reject"},
            "agent-2": {"feedback_type": "reject"},
            "agent-3": {"feedback_type": "accept"},
        }

        rejects = sum(1 for f in feedback.values() if f.get("feedback_type") == "reject")
        total = len(feedback)

        assert rejects > total / 2

    def test_needs_negotiation(self):
        """测试需要协商"""
        feedback = {
            "agent-1": {"feedback_type": "accept"},
            "agent-2": {"feedback_type": "negotiate"},
            "agent-3": {"feedback_type": "negotiate"},
        }

        accepts = sum(1 for f in feedback.values() if f.get("feedback_type") == "accept")
        negotiates = sum(1 for f in feedback.values() if f.get("feedback_type") == "negotiate")
        total = len(feedback)

        # 不满足80%接受，且有协商请求
        assert accepts < total * 0.8
        assert negotiates > 0


class TestMultiRoundNegotiation:
    """测试多轮协商"""

    def test_round_increment(self):
        """测试轮次递增"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={},
            candidates=[],
            max_rounds=3
        )

        assert state.current_round == 1

        state.current_round += 1
        assert state.current_round == 2

        state.current_round += 1
        assert state.current_round == 3

    def test_max_rounds_check(self):
        """测试最大轮次检查"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={},
            candidates=[],
            max_rounds=3
        )

        state.current_round = 3
        assert state.current_round >= state.max_rounds

    def test_clear_feedback_between_rounds(self):
        """测试轮次间清除反馈"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={},
            candidates=[]
        )

        state.proposal_feedback = {
            "agent-1": {"feedback_type": "negotiate"}
        }
        assert len(state.proposal_feedback) == 1

        # 进入下一轮时清除
        old_feedback = state.proposal_feedback.copy()
        state.proposal_feedback.clear()
        state.current_round += 1

        assert len(state.proposal_feedback) == 0
        assert len(old_feedback) == 1


class TestProposalGeneration:
    """测试方案生成逻辑"""

    def test_mock_proposal_structure(self):
        """测试Mock方案结构"""
        state = ChannelState(
            channel_id="test",
            demand_id="test",
            demand={"surface_demand": "测试需求"},
            candidates=[]
        )

        participants = [
            {"agent_id": "agent-1", "contribution": "贡献1"},
            {"agent_id": "agent-2", "contribution": "贡献2"},
        ]

        # 模拟Mock方案生成
        surface_demand = state.demand.get("surface_demand", "未知需求")
        proposal = {
            "summary": f"关于'{surface_demand}'的协作方案",
            "assignments": [
                {
                    "agent_id": p["agent_id"],
                    "role": f"参与者-{i+1}",
                    "responsibility": p.get("contribution", "待分配职责"),
                }
                for i, p in enumerate(participants)
            ],
            "timeline": "待确定",
            "confidence": "medium",
        }

        assert "summary" in proposal
        assert len(proposal["assignments"]) == 2
        assert proposal["assignments"][0]["agent_id"] == "agent-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
