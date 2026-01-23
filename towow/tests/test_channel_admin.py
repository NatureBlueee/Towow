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

# 导入真实的ChannelStatus用于后面的测试
from openagents.agents.channel_admin import ChannelStatus as RealChannelStatus


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
        # 4/5 = 80% 接受率，满足阈值
        feedback = {
            "agent-1": {"feedback_type": "accept"},
            "agent-2": {"feedback_type": "accept"},
            "agent-3": {"feedback_type": "accept"},
            "agent-4": {"feedback_type": "accept"},
            "agent-5": {"feedback_type": "negotiate"},
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


class TestProposalGenerationT04:
    """测试 T04: ChannelAdmin 方案聚合"""

    @pytest.fixture
    def agent(self):
        """创建测试用Agent实例"""
        from openagents.agents.channel_admin import ChannelAdminAgent
        return ChannelAdminAgent()

    def test_mock_proposal_complete_structure(self, agent):
        """AC-1/AC-2: 测试Mock方案包含完整结构"""
        from openagents.agents.channel_admin import ChannelState

        state = ChannelState(
            channel_id="test-ch",
            demand_id="d-test",
            demand={"surface_demand": "办一场AI聚会"},
            candidates=[]
        )

        participants = [
            {"agent_id": "bob", "display_name": "Bob", "contribution": "提供场地"},
            {"agent_id": "alice", "display_name": "Alice", "contribution": "技术分享"},
        ]

        proposal = agent._mock_proposal(state, participants)

        # AC-1: 方案包含完整结构
        assert "summary" in proposal
        assert "objective" in proposal
        assert "assignments" in proposal
        assert "timeline" in proposal
        assert "collaboration_model" in proposal
        assert "success_criteria" in proposal
        assert "risks" in proposal
        assert "gaps" in proposal
        assert "confidence" in proposal

        # AC-2: 每个参与者都有 role 和 responsibility
        assert len(proposal["assignments"]) >= 2
        for assignment in proposal["assignments"]:
            assert "agent_id" in assignment
            assert "display_name" in assignment
            assert "role" in assignment
            assert "responsibility" in assignment

    def test_mock_proposal_timeline_has_milestones(self, agent):
        """AC-3: timeline 包含至少一个 milestone"""
        from openagents.agents.channel_admin import ChannelState

        state = ChannelState(
            channel_id="test-ch",
            demand_id="d-test",
            demand={"surface_demand": "办一场AI聚会"},
            candidates=[]
        )

        participants = [
            {"agent_id": "bob", "contribution": "提供场地"},
        ]

        proposal = agent._mock_proposal(state, participants)

        # timeline 应该是对象，包含 milestones
        assert isinstance(proposal["timeline"], dict)
        assert "milestones" in proposal["timeline"]
        assert len(proposal["timeline"]["milestones"]) >= 1

        # 每个 milestone 应该有必要字段
        for milestone in proposal["timeline"]["milestones"]:
            assert "name" in milestone
            assert "date" in milestone
            assert "deliverable" in milestone

    def test_mock_proposal_success_criteria(self, agent):
        """AC-4: success_criteria 至少包含 2 个可衡量的标准"""
        from openagents.agents.channel_admin import ChannelState

        state = ChannelState(
            channel_id="test-ch",
            demand_id="d-test",
            demand={"surface_demand": "办一场AI聚会"},
            candidates=[]
        )

        participants = [
            {"agent_id": "bob", "contribution": "提供场地"},
        ]

        proposal = agent._mock_proposal(state, participants)

        assert "success_criteria" in proposal
        assert isinstance(proposal["success_criteria"], list)
        assert len(proposal["success_criteria"]) >= 2

    def test_validate_and_enhance_proposal_fills_gaps(self, agent):
        """测试 _validate_and_enhance_proposal 补充缺失字段"""
        # 一个不完整的方案
        incomplete_proposal = {
            "summary": "测试方案",
            "assignments": [
                {"agent_id": "bob", "role": "场地提供者"}
            ]
        }

        participants = [
            {"agent_id": "bob", "display_name": "Bob", "contribution": "场地"},
            {"agent_id": "alice", "display_name": "Alice", "contribution": "演讲"}
        ]

        enhanced = agent._validate_and_enhance_proposal(incomplete_proposal, participants)

        # 验证必要字段被补充
        assert "timeline" in enhanced
        assert "milestones" in enhanced["timeline"]
        assert "success_criteria" in enhanced
        assert len(enhanced["success_criteria"]) >= 2
        assert "collaboration_model" in enhanced
        assert "risks" in enhanced
        assert "gaps" in enhanced
        assert "confidence" in enhanced

        # 验证所有参与者都被分配
        assigned_ids = {a["agent_id"] for a in enhanced["assignments"]}
        assert "bob" in assigned_ids
        assert "alice" in assigned_ids

        # 验证 display_name 被补充
        for assignment in enhanced["assignments"]:
            assert "display_name" in assignment

    def test_validate_and_enhance_proposal_preserves_existing(self, agent):
        """测试 _validate_and_enhance_proposal 保留已有字段"""
        complete_proposal = {
            "summary": "完整方案",
            "objective": "具体目标",
            "assignments": [
                {"agent_id": "bob", "display_name": "Bob", "role": "Leader", "responsibility": "领导"}
            ],
            "timeline": {
                "start_date": "2026-02-01",
                "milestones": [{"name": "开始", "date": "2026-02-01", "deliverable": "启动"}]
            },
            "success_criteria": ["标准1", "标准2", "标准3"],
            "confidence": "high"
        }

        participants = [
            {"agent_id": "bob", "display_name": "Bob", "contribution": "场地"}
        ]

        enhanced = agent._validate_and_enhance_proposal(complete_proposal, participants)

        # 验证已有字段被保留
        assert enhanced["summary"] == "完整方案"
        assert enhanced["objective"] == "具体目标"
        assert enhanced["confidence"] == "high"
        assert len(enhanced["success_criteria"]) == 3
        assert enhanced["timeline"]["start_date"] == "2026-02-01"

    def test_build_proposal_prompt_format(self, agent):
        """测试 _build_proposal_prompt 返回格式正确的提示词"""
        from openagents.agents.channel_admin import ChannelState

        state = ChannelState(
            channel_id="test-ch",
            demand_id="d-test",
            demand={
                "surface_demand": "办一场AI聚会",
                "deep_understanding": {
                    "type": "event",
                    "motivation": "交流学习"
                }
            },
            candidates=[],
            current_round=1,
            max_rounds=3
        )

        participants = [
            {"agent_id": "bob", "display_name": "Bob", "decision": "participate", "contribution": "提供场地"},
        ]

        prompt = agent._build_proposal_prompt(state, participants)

        # 验证提示词包含关键内容
        assert "办一场AI聚会" in prompt
        assert "Bob" in prompt
        assert "提供场地" in prompt
        assert "第 1 轮" in prompt
        assert "最多 3 轮" in prompt
        assert "JSON" in prompt

    def test_get_proposal_system_prompt(self, agent):
        """测试 _get_proposal_system_prompt 返回正确的系统提示词"""
        system_prompt = agent._get_proposal_system_prompt()

        # 验证系统提示词包含关键原则
        assert "ToWow" in system_prompt
        assert "方案" in system_prompt
        assert "JSON" in system_prompt


class TestChannelAdminAgent:
    """测试ChannelAdminAgent类"""

    @pytest.fixture
    def agent(self):
        """创建测试用Agent实例"""
        # 直接导入真实的ChannelAdminAgent
        from openagents.agents.channel_admin import ChannelAdminAgent
        return ChannelAdminAgent()

    def test_agent_creation(self, agent):
        """测试Agent创建"""
        assert agent.AGENT_TYPE == "channel_admin"
        assert agent.MAX_NEGOTIATION_ROUNDS == 5  # v4 改为 5 轮
        assert agent.RESPONSE_TIMEOUT == 300
        assert agent.FEEDBACK_TIMEOUT == 120

    def test_agent_has_channels_dict(self, agent):
        """测试Agent有channels字典"""
        assert hasattr(agent, "channels")
        assert isinstance(agent.channels, dict)
        assert len(agent.channels) == 0

    def test_get_channel_status_not_found(self, agent):
        """测试获取不存在的Channel状态"""
        status = agent.get_channel_status("non-existent")
        assert status is None

    def test_get_all_channels_empty(self, agent):
        """测试获取所有Channel（空）"""
        all_channels = agent.get_all_channels()
        assert all_channels == {}

    def test_get_active_channels_empty(self, agent):
        """测试获取活跃Channel（空）"""
        active = agent.get_active_channels()
        assert active == []


class TestChannelAdminPublicAPI:
    """测试ChannelAdminAgent公共API"""

    @pytest.fixture
    def agent(self):
        """创建测试用Agent实例"""
        from openagents.agents.channel_admin import ChannelAdminAgent
        return ChannelAdminAgent()

    @pytest.mark.asyncio
    async def test_start_managing(self, agent):
        """测试start_managing方法"""
        channel_id = await agent.start_managing(
            channel_name="test-channel",
            demand_id="demand-001",
            demand={"surface_demand": "测试需求"},
            invited_agents=[
                {"agent_id": "agent-1"},
                {"agent_id": "agent-2"}
            ]
        )

        assert channel_id == "test-channel"
        assert "test-channel" in agent.channels
        state = agent.channels["test-channel"]
        assert state.demand_id == "demand-001"
        assert len(state.candidates) == 2
        assert state.max_rounds == 5  # v4 默认 5 轮

    @pytest.mark.asyncio
    async def test_start_managing_auto_id(self, agent):
        """测试start_managing自动生成ID"""
        channel_id = await agent.start_managing(
            channel_name="",  # 空名称，自动生成
            demand_id="demand-002",
            demand={},
            invited_agents=[]
        )

        assert channel_id.startswith("ch-")
        assert channel_id in agent.channels

    @pytest.mark.asyncio
    async def test_start_managing_custom_max_rounds(self, agent):
        """测试start_managing自定义最大轮次"""
        channel_id = await agent.start_managing(
            channel_name="custom-rounds",
            demand_id="demand-003",
            demand={},
            invited_agents=[],
            max_rounds=3
        )

        state = agent.channels[channel_id]
        assert state.max_rounds == 3

    @pytest.mark.asyncio
    async def test_handle_response(self, agent):
        """测试handle_response方法"""
        # 先创建channel
        await agent.start_managing(
            channel_name="response-test",
            demand_id="demand-004",
            demand={},
            invited_agents=[{"agent_id": "agent-1"}]
        )

        # 处理响应
        result = await agent.handle_response(
            channel_id="response-test",
            agent_id="agent-1",
            decision="participate",
            contribution="我可以帮忙",
            conditions=["需要资源支持"]
        )

        assert result is True
        state = agent.channels["response-test"]
        assert "agent-1" in state.responses
        assert state.responses["agent-1"]["decision"] == "participate"

    @pytest.mark.asyncio
    async def test_handle_feedback(self, agent):
        """测试handle_feedback方法"""
        # 创建channel并模拟进入NEGOTIATING状态
        await agent.start_managing(
            channel_name="feedback-test",
            demand_id="demand-005",
            demand={},
            invited_agents=[{"agent_id": "agent-1"}]
        )

        # 模拟响应和进入协商状态
        state = agent.channels["feedback-test"]
        state.responses["agent-1"] = {"decision": "participate"}
        state.status = RealChannelStatus.NEGOTIATING
        state.current_proposal = {"summary": "测试方案"}

        # 处理反馈
        result = await agent.handle_feedback(
            channel_id="feedback-test",
            agent_id="agent-1",
            feedback_type="accept"
        )

        assert result is True
        assert "agent-1" in state.proposal_feedback


class TestMultiRoundNegotiationT05:
    """测试 T05: 多轮协商逻辑"""

    @pytest.fixture
    def agent(self):
        """创建测试用Agent实例"""
        from openagents.agents.channel_admin import ChannelAdminAgent
        return ChannelAdminAgent()

    @pytest.fixture
    def create_test_state(self, agent):
        """创建测试状态的工厂函数"""
        from openagents.agents.channel_admin import ChannelState

        def _create(round_num=1, max_rounds=3):
            state = ChannelState(
                channel_id="test-ch",
                demand_id="d-test",
                demand={"surface_demand": "测试需求"},
                candidates=[
                    {"agent_id": "bob", "display_name": "Bob"},
                    {"agent_id": "alice", "display_name": "Alice"},
                    {"agent_id": "charlie", "display_name": "Charlie"},
                ],
                current_round=round_num,
                max_rounds=max_rounds
            )
            state.responses = {
                "bob": {"decision": "participate", "contribution": "场地"},
                "alice": {"decision": "participate", "contribution": "演讲"},
                "charlie": {"decision": "participate", "contribution": "组织"},
            }
            state.status = RealChannelStatus.NEGOTIATING
            state.current_proposal = {"summary": "测试方案"}
            agent.channels["test-ch"] = state
            return state

        return _create

    @pytest.mark.asyncio
    async def test_80_percent_accept_triggers_finalize(self, agent, create_test_state):
        """AC-2: 80%+ 接受时正确触发完成"""
        state = create_test_state(round_num=1)

        # 4/5 = 80% 接受
        state.proposal_feedback = {
            "bob": {"feedback_type": "accept"},
            "alice": {"feedback_type": "accept"},
            "charlie": {"feedback_type": "accept"},
            "dave": {"feedback_type": "accept"},
            "eve": {"feedback_type": "negotiate"},
        }
        state.responses["dave"] = {"decision": "participate"}
        state.responses["eve"] = {"decision": "participate"}

        await agent._evaluate_feedback(state)

        assert state.status == RealChannelStatus.FINALIZED

    @pytest.mark.asyncio
    async def test_majority_reject_triggers_fail(self, agent, create_test_state):
        """AC-3: 50%+ 拒绝时正确触发失败"""
        state = create_test_state(round_num=1)

        # 2/3 = 67% 拒绝/退出
        state.proposal_feedback = {
            "bob": {"feedback_type": "reject"},
            "alice": {"feedback_type": "withdraw"},
            "charlie": {"feedback_type": "accept"},
        }

        await agent._evaluate_feedback(state)

        assert state.status == RealChannelStatus.FAILED

    @pytest.mark.asyncio
    async def test_negotiate_triggers_next_round(self, agent, create_test_state):
        """AC-4: negotiate 反馈触发方案调整"""
        state = create_test_state(round_num=1, max_rounds=3)

        # 50% 接受，50% 协商
        state.proposal_feedback = {
            "bob": {"feedback_type": "accept"},
            "alice": {"feedback_type": "negotiate", "adjustment_request": "调整时间"},
        }

        initial_round = state.current_round
        await agent._evaluate_feedback(state)

        # 应该进入下一轮
        assert state.current_round == initial_round + 1
        # 状态会变成 NEGOTIATING（因为 _distribute_proposal 会更新状态）
        assert state.status == RealChannelStatus.NEGOTIATING

    @pytest.mark.asyncio
    async def test_withdraw_counted_as_reject(self, agent, create_test_state):
        """AC-5: withdraw 反馈正确处理（计入拒绝）"""
        state = create_test_state(round_num=1)

        # 2 withdraw + 1 reject = 100% 拒绝/退出
        state.proposal_feedback = {
            "bob": {"feedback_type": "withdraw"},
            "alice": {"feedback_type": "withdraw"},
            "charlie": {"feedback_type": "reject"},
        }

        await agent._evaluate_feedback(state)

        assert state.status == RealChannelStatus.FAILED

    @pytest.mark.asyncio
    async def test_max_rounds_reached_generates_compromise(self, agent, create_test_state):
        """[v4更新] AC-5: 达到最大轮次后触发强制终结（FORCE_FINALIZED）"""
        state = create_test_state(round_num=5, max_rounds=5)  # v4: 5轮

        # 2 接受，1 协商 → 不满足80%接受，触发强制终结
        state.proposal_feedback = {
            "bob": {"feedback_type": "accept"},
            "alice": {"feedback_type": "accept"},
            "charlie": {"feedback_type": "negotiate"},
        }

        await agent._evaluate_feedback(state)

        # v4: 应该是 FORCE_FINALIZED
        assert state.status == RealChannelStatus.FORCE_FINALIZED

    @pytest.mark.asyncio
    async def test_max_rounds_reached_with_more_rejects_fails(self, agent, create_test_state):
        """[v4更新] 测试达到最大轮次且拒绝>=50%时失败"""
        state = create_test_state(round_num=5, max_rounds=5)  # v4: 5轮

        # 1 接受，2 拒绝 → 拒绝率 66.67% >= 50%，应该失败
        state.proposal_feedback = {
            "bob": {"feedback_type": "accept"},
            "alice": {"feedback_type": "reject"},
            "charlie": {"feedback_type": "reject"},
        }

        await agent._evaluate_feedback(state)

        # 拒绝率超过50%，应该失败
        assert state.status == RealChannelStatus.FAILED

    @pytest.mark.asyncio
    async def test_round_started_event_published(self, agent, create_test_state):
        """AC-6: 每轮发布 towow.negotiation.round_started 事件"""
        state = create_test_state(round_num=1, max_rounds=3)

        # 需要协商
        state.proposal_feedback = {
            "bob": {"feedback_type": "accept"},
            "alice": {"feedback_type": "negotiate", "adjustment_request": "调整时间"},
        }

        # Mock _publish_event
        published_events = []
        original_publish = agent._publish_event

        async def mock_publish(event_type, payload):
            published_events.append((event_type, payload))
            await original_publish(event_type, payload)

        agent._publish_event = mock_publish

        await agent._evaluate_feedback(state)

        # 检查是否发布了 round_started 事件
        round_started_events = [
            e for e in published_events
            if e[0] == "towow.negotiation.round_started"
        ]
        assert len(round_started_events) >= 1
        assert round_started_events[0][1]["round"] == 2
        assert round_started_events[0][1]["max_rounds"] == 3

    @pytest.mark.asyncio
    async def test_feedback_evaluated_event_includes_accept_rate(self, agent, create_test_state):
        """测试反馈评估事件包含 accept_rate"""
        state = create_test_state(round_num=1, max_rounds=3)

        state.proposal_feedback = {
            "bob": {"feedback_type": "accept"},
            "alice": {"feedback_type": "accept"},
            "charlie": {"feedback_type": "negotiate"},
        }

        published_events = []
        original_publish = agent._publish_event

        async def mock_publish(event_type, payload):
            published_events.append((event_type, payload))
            await original_publish(event_type, payload)

        agent._publish_event = mock_publish

        await agent._evaluate_feedback(state)

        # 检查 feedback.evaluated 事件
        evaluated_events = [
            e for e in published_events
            if e[0] == "towow.feedback.evaluated"
        ]
        assert len(evaluated_events) >= 1
        payload = evaluated_events[0][1]
        assert "accept_rate" in payload
        assert payload["accept_rate"] == 2 / 3  # 约 66.67%
        assert payload["accepts"] == 2
        assert payload["negotiates"] == 1

    @pytest.mark.asyncio
    async def test_all_accept_without_80_percent_triggers_finalize(self, agent, create_test_state):
        """测试全员接受（不足 80%）但无反对时触发完成"""
        state = create_test_state(round_num=1)

        # 只有一个人接受（100% 接受但只有 1 人）
        state.proposal_feedback = {
            "bob": {"feedback_type": "accept"},
        }
        state.responses = {"bob": {"decision": "participate"}}

        await agent._evaluate_feedback(state)

        # 全员接受，应该完成
        assert state.status == RealChannelStatus.FINALIZED

    @pytest.mark.asyncio
    async def test_adjust_proposal_without_llm(self, agent, create_test_state):
        """测试无 LLM 时的方案调整"""
        state = create_test_state(round_num=2)
        state.current_proposal = {"summary": "原方案", "round": 1}

        feedback = {
            "bob": {"feedback_type": "negotiate", "adjustment_request": "调整时间"},
        }

        adjusted = await agent._adjust_proposal(state, feedback)

        # 应该返回原方案并标记轮次
        assert adjusted["round"] == 2
        assert adjusted.get("adjusted") is True


class TestChannelAdminAggregateT04V4:
    """测试 T04: ChannelAdmin 方案聚合 v4 功能"""

    @pytest.fixture
    def agent(self):
        """创建测试用Agent实例"""
        from openagents.agents.channel_admin import ChannelAdminAgent
        return ChannelAdminAgent()

    @pytest.fixture
    def create_test_channel(self, agent):
        """创建测试Channel的工厂函数"""
        from openagents.agents.channel_admin import ChannelState

        def _create(candidates=None):
            if candidates is None:
                candidates = [
                    {"agent_id": "agent1", "display_name": "Agent 1"},
                    {"agent_id": "agent2", "display_name": "Agent 2"},
                    {"agent_id": "agent3", "display_name": "Agent 3"},
                ]
            state = ChannelState(
                channel_id="test-channel",
                demand_id="d-test",
                demand={"surface_demand": "办聚会"},
                candidates=candidates,
            )
            state.status = RealChannelStatus.COLLECTING
            agent.channels["test-channel"] = state
            return state

        return _create

    @pytest.mark.asyncio
    async def test_idempotent_handling_by_message_id(self, agent, create_test_channel):
        """AC-3: 测试基于 message_id 的幂等处理"""
        state = create_test_channel()

        # 第一次处理
        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent1",
            "response_type": "offer",
            "decision": "participate",
            "contribution": "提供场地",
            "message_id": "msg-001"
        })

        assert len(state.responses) == 1
        assert "agent1" in state.responses
        assert "msg-001" in state.processed_message_ids

        # 第二次处理相同的消息（应该被忽略）
        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent1",
            "response_type": "offer",
            "decision": "participate",
            "contribution": "修改后的贡献",  # 不同内容
            "message_id": "msg-001"  # 相同的消息ID
        })

        # 应该还是只有1个响应，且内容不变
        assert len(state.responses) == 1
        assert state.responses["agent1"]["contribution"] == "提供场地"

    @pytest.mark.asyncio
    async def test_offer_response_type_processing(self, agent, create_test_channel):
        """AC-2: 测试 offer 响应类型正确处理"""
        state = create_test_channel()

        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent1",
            "response_type": "offer",
            "decision": "participate",
            "contribution": "提供场地",
            "message_id": "msg-offer-001"
        })

        assert state.responses["agent1"]["response_type"] == "offer"
        assert state.responses["agent1"]["decision"] == "participate"
        assert state.responses["agent1"]["contribution"] == "提供场地"
        assert state.responses["agent1"]["negotiation_points"] == []

    @pytest.mark.asyncio
    async def test_negotiate_response_type_processing(self, agent, create_test_channel):
        """AC-2: 测试 negotiate 响应类型正确处理"""
        state = create_test_channel()

        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent1",
            "response_type": "negotiate",
            "decision": "conditional",
            "contribution": "演讲嘉宾",
            "negotiation_points": [
                {
                    "aspect": "时间",
                    "current_value": "周五",
                    "desired_value": "周末",
                    "reason": "工作日不方便"
                }
            ],
            "message_id": "msg-negotiate-001"
        })

        assert state.responses["agent1"]["response_type"] == "negotiate"
        assert state.responses["agent1"]["decision"] == "conditional"
        assert len(state.responses["agent1"]["negotiation_points"]) == 1
        assert state.responses["agent1"]["negotiation_points"][0]["aspect"] == "时间"
        assert state.responses["agent1"]["negotiation_points"][0]["desired_value"] == "周末"

    @pytest.mark.asyncio
    async def test_aggregate_after_all_responses_collected(self, agent, create_test_channel):
        """AC-1: 测试收集完所有响应后自动触发聚合"""
        state = create_test_channel(candidates=[
            {"agent_id": "agent1", "display_name": "Agent 1"},
        ])

        # 发送响应
        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent1",
            "response_type": "offer",
            "decision": "participate",
            "contribution": "提供场地",
            "message_id": "msg-001"
        })

        # 应该自动触发聚合，状态变为 NEGOTIATING
        assert state.status == RealChannelStatus.NEGOTIATING
        assert state.current_proposal is not None

    def test_fallback_proposal_v4_structure(self, agent):
        """AC-5: 测试降级方案结构正确"""
        from openagents.agents.channel_admin import ChannelState

        state = ChannelState(
            channel_id="test-ch",
            demand_id="d-test",
            demand={"surface_demand": "办AI聚会"},
            candidates=[]
        )

        offers = [
            {
                "agent_id": "bob",
                "display_name": "Bob",
                "contribution": "提供场地",
                "confidence": 80
            }
        ]

        negotiations = [
            {
                "agent_id": "alice",
                "display_name": "Alice",
                "contribution": "演讲嘉宾",
                "negotiation_points": [
                    {"aspect": "时间", "desired_value": "周末"}
                ]
            }
        ]

        proposal = agent._get_fallback_proposal_v4(state, offers, negotiations)

        # 验证降级方案结构
        assert proposal["is_fallback"] is True
        assert proposal["confidence"] == "low"
        assert "办AI聚会" in proposal["summary"]
        assert len(proposal["assignments"]) == 2

        # 验证 offer 类型的分配
        bob_assignment = next(a for a in proposal["assignments"] if a["agent_id"] == "bob")
        assert bob_assignment["is_confirmed"] is True
        assert bob_assignment["responsibility"] == "提供场地"

        # 验证 negotiate 类型的分配
        alice_assignment = next(a for a in proposal["assignments"] if a["agent_id"] == "alice")
        assert alice_assignment["is_confirmed"] is False
        assert "协商" in alice_assignment["notes"]

    def test_build_aggregation_prompt_v4(self, agent):
        """测试 v4 聚合提示词正确构建"""
        demand = {
            "surface_demand": "办AI聚会",
            "deep_understanding": {"type": "event"},
            "capability_tags": ["场地", "演讲"]
        }

        offers = [
            {
                "agent_id": "bob",
                "display_name": "Bob",
                "decision": "participate",
                "contribution": "提供场地",
                "confidence": 80
            }
        ]

        negotiations = [
            {
                "agent_id": "alice",
                "display_name": "Alice",
                "decision": "conditional",
                "contribution": "演讲嘉宾",
                "negotiation_points": [
                    {"aspect": "时间", "current_value": "周五", "desired_value": "周末", "reason": "工作日不方便"}
                ]
            }
        ]

        declines = []

        prompt = agent._build_aggregation_prompt_v4(
            demand=demand,
            offers=offers,
            negotiations=negotiations,
            declines=declines,
            current_round=1,
            max_rounds=5
        )

        # 验证提示词包含关键内容
        assert "办AI聚会" in prompt
        assert "offer" in prompt.lower()
        assert "negotiate" in prompt.lower()
        assert "Bob" in prompt
        assert "Alice" in prompt
        assert "时间" in prompt
        assert "周末" in prompt
        assert "第 1 轮" in prompt
        assert "5" in prompt  # max_rounds

    def test_validate_and_enhance_proposal_v4_adds_missing_participants(self, agent):
        """测试 v4 方案验证增强 - 补充缺失的参与者"""
        proposal = {
            "summary": "测试方案",
            "assignments": [
                {"agent_id": "bob", "role": "场地提供者"}
            ]
        }

        offers = [
            {"agent_id": "bob", "display_name": "Bob", "contribution": "场地"}
        ]
        negotiations = [
            {"agent_id": "alice", "display_name": "Alice", "contribution": "演讲"}
        ]

        enhanced = agent._validate_and_enhance_proposal_v4(proposal, offers, negotiations)

        # 验证 alice 被补充
        assigned_ids = {a["agent_id"] for a in enhanced["assignments"]}
        assert "alice" in assigned_ids

        # 验证 negotiate 类型的参与者标记为未确认
        alice_assignment = next(a for a in enhanced["assignments"] if a["agent_id"] == "alice")
        assert alice_assignment["is_confirmed"] is False
        assert "协商中" in alice_assignment["notes"]

    def test_validate_and_enhance_proposal_v4_adds_negotiation_handling(self, agent):
        """测试 v4 方案验证增强 - 添加 negotiation_handling"""
        proposal = {
            "summary": "测试方案",
            "assignments": []
        }

        enhanced = agent._validate_and_enhance_proposal_v4(proposal, [], [])

        # 验证 negotiation_handling 被添加
        assert "negotiation_handling" in enhanced
        assert "addressed" in enhanced["negotiation_handling"]
        assert "declined" in enhanced["negotiation_handling"]

    @pytest.mark.asyncio
    async def test_proposal_distributed_event_v4_format(self, agent, create_test_channel):
        """AC-6: 测试 towow.proposal.distributed 事件格式"""
        state = create_test_channel(candidates=[
            {"agent_id": "agent1", "display_name": "Agent 1"},
        ])

        # Mock _publish_event
        published_events = []
        original_publish = agent._publish_event

        async def mock_publish(event_type, payload):
            published_events.append((event_type, payload))
            await original_publish(event_type, payload)

        agent._publish_event = mock_publish

        # 触发聚合
        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent1",
            "response_type": "offer",
            "decision": "participate",
            "contribution": "提供场地",
            "message_id": "msg-001"
        })

        # 检查 proposal.distributed 事件
        distributed_events = [
            e for e in published_events
            if e[0] == "towow.proposal.distributed"
        ]

        assert len(distributed_events) >= 1
        payload = distributed_events[0][1]

        # 验证 v4 事件格式
        assert "channel_id" in payload
        assert "demand_id" in payload
        assert "proposal_id" in payload
        assert "summary" in payload
        assert "participants_count" in payload
        assert "has_gaps" in payload
        assert "version" in payload

    @pytest.mark.asyncio
    async def test_proposal_distributed_to_all_participants(self, agent, create_test_channel):
        """AC-7: 测试方案分发给所有参与者"""
        state = create_test_channel(candidates=[
            {"agent_id": "agent1", "display_name": "Agent 1"},
            {"agent_id": "agent2", "display_name": "Agent 2"},
        ])

        # 记录发送的消息
        sent_messages = []
        original_send = agent.send_to_agent

        async def mock_send(agent_id, data):
            sent_messages.append((agent_id, data))
            return await original_send(agent_id, data)

        agent.send_to_agent = mock_send

        # 发送两个响应
        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent1",
            "response_type": "offer",
            "decision": "participate",
            "message_id": "msg-001"
        })
        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent2",
            "response_type": "negotiate",
            "decision": "conditional",
            "message_id": "msg-002"
        })

        # 检查方案是否发送给所有参与者
        proposal_review_messages = [
            m for m in sent_messages
            if m[1].get("type") == "proposal_review"
        ]

        agent_ids_received = {m[0] for m in proposal_review_messages}
        assert "agent1" in agent_ids_received
        assert "agent2" in agent_ids_received

    @pytest.mark.asyncio
    async def test_your_assignment_included_in_proposal_review(self, agent, create_test_channel):
        """测试方案分发包含参与者的具体分配"""
        state = create_test_channel(candidates=[
            {"agent_id": "agent1", "display_name": "Agent 1"},
        ])

        # 记录发送的消息
        sent_messages = []
        original_send = agent.send_to_agent

        async def mock_send(agent_id, data):
            sent_messages.append((agent_id, data))
            return await original_send(agent_id, data)

        agent.send_to_agent = mock_send

        # 发送响应
        await agent._handle_offer_response({
            "channel_id": "test-channel",
            "agent_id": "agent1",
            "response_type": "offer",
            "decision": "participate",
            "contribution": "提供场地",
            "message_id": "msg-001"
        })

        # 检查 your_assignment 字段
        proposal_review_messages = [
            m for m in sent_messages
            if m[1].get("type") == "proposal_review"
        ]

        assert len(proposal_review_messages) >= 1
        message = proposal_review_messages[0][1]

        # your_assignment 可能存在（如果 agent 被分配了角色）
        if "your_assignment" in message:
            assert "role" in message["your_assignment"]
            assert "responsibility" in message["your_assignment"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
