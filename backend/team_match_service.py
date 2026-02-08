"""
Team Match Service - 团队匹配服务

核心业务逻辑：
1. 接收组队请求
2. 收集参与意向（Match Offer）
3. 生成团队组合方案（Team Proposal）
4. 标识意外组合（跨域互补）

设计原则：
- 本质与实现分离：接口稳定，实现可演化
- 代码保障 > Prompt 保障：状态机控制流程，LLM 提供智能
- 投影即函数：无状态设计
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============ 数据模型 ============

class TeamRequestStatus(Enum):
    """组队请求状态"""
    PENDING = "pending"  # 等待响应
    COLLECTING = "collecting"  # 收集中
    GENERATING = "generating"  # 生成方案中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


@dataclass
class TeamRequest:
    """组队请求"""
    request_id: str
    title: str
    description: str
    submitter_id: str
    required_roles: List[str]  # 需要的角色（如 ["前端", "后端", "设计师"]）
    team_size: int  # 期望团队规模
    status: TeamRequestStatus = TeamRequestStatus.PENDING
    channel_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MatchOffer:
    """参与意向"""
    offer_id: str
    request_id: str
    agent_id: str
    agent_name: str
    role: str  # 角色定位（如 "前端开发"）
    skills: List[str]  # 技能列表
    specialties: List[str]  # 专长领域
    motivation: str  # 参与动机
    availability: str  # 可用时间
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TeamMember:
    """团队成员"""
    agent_id: str
    agent_name: str
    role: str
    skills: List[str]
    specialties: List[str]
    contribution: str  # 预期贡献


@dataclass
class TeamProposal:
    """团队方案"""
    proposal_id: str
    request_id: str
    title: str
    members: List[TeamMember]
    coverage_score: float  # 角色覆盖度（0-1）
    synergy_score: float  # 协同度（0-1）
    unexpected_combinations: List[str]  # 意外组合（跨域发现）
    reasoning: str  # 方案推理
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "title": self.title,
            "members": [
                {
                    "agent_id": m.agent_id,
                    "agent_name": m.agent_name,
                    "role": m.role,
                    "skills": m.skills,
                    "specialties": m.specialties,
                    "contribution": m.contribution,
                }
                for m in self.members
            ],
            "coverage_score": self.coverage_score,
            "synergy_score": self.synergy_score,
            "unexpected_combinations": self.unexpected_combinations,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


# ============ Service 接口 ============

class TeamMatchService:
    """
    团队匹配服务

    职责：
    - 管理组队请求生命周期
    - 收集参与意向（Match Offer）
    - 调用 TeamCompositionEngine 生成方案
    - 发送 WebSocket 通知
    """

    def __init__(self):
        """初始化服务"""
        # request_id -> TeamRequest
        self._requests: Dict[str, TeamRequest] = {}
        # request_id -> List[MatchOffer]
        self._offers: Dict[str, List[MatchOffer]] = {}
        # request_id -> List[TeamProposal]
        self._proposals: Dict[str, List[TeamProposal]] = {}

        logger.info("TeamMatchService initialized")

    async def create_team_request(
        self,
        title: str,
        description: str,
        submitter_id: str,
        required_roles: List[str],
        team_size: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TeamRequest:
        """
        创建组队请求

        Args:
            title: 请求标题
            description: 请求描述
            submitter_id: 提交者 Agent ID
            required_roles: 需要的角色列表
            team_size: 期望团队规模
            metadata: 额外元数据

        Returns:
            TeamRequest: 创建的组队请求

        Raises:
            ValueError: 参数验证失败
        """
        # 参数验证
        if not title:
            raise ValueError("title cannot be empty")
        if not required_roles:
            raise ValueError("required_roles cannot be empty")
        if team_size < 2:
            raise ValueError("team_size must be at least 2")

        # 生成 ID
        request_id = f"team_req_{uuid.uuid4().hex[:12]}"
        channel_id = f"team_ch_{uuid.uuid4().hex[:12]}"

        # 创建请求
        request = TeamRequest(
            request_id=request_id,
            title=title,
            description=description,
            submitter_id=submitter_id,
            required_roles=required_roles,
            team_size=team_size,
            channel_id=channel_id,
            metadata=metadata or {},
        )

        # 存储
        self._requests[request_id] = request
        self._offers[request_id] = []

        logger.info(
            f"Team request created: {request_id}, "
            f"roles={required_roles}, size={team_size}"
        )

        return request

    async def submit_match_offer(
        self,
        request_id: str,
        agent_id: str,
        agent_name: str,
        role: str,
        skills: List[str],
        specialties: List[str],
        motivation: str,
        availability: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MatchOffer:
        """
        提交参与意向

        Args:
            request_id: 请求 ID
            agent_id: Agent ID
            agent_name: Agent 名称
            role: 角色定位
            skills: 技能列表
            specialties: 专长领域
            motivation: 参与动机
            availability: 可用时间
            metadata: 额外元数据

        Returns:
            MatchOffer: 提交的参与意向

        Raises:
            ValueError: 请求不存在或参数验证失败
        """
        # 验证请求存在
        if request_id not in self._requests:
            raise ValueError(f"Team request not found: {request_id}")

        # 参数验证
        if not role:
            raise ValueError("role cannot be empty")
        if not skills:
            raise ValueError("skills cannot be empty")

        # 生成 offer ID
        offer_id = f"offer_{uuid.uuid4().hex[:8]}"

        # 创建 offer
        offer = MatchOffer(
            offer_id=offer_id,
            request_id=request_id,
            agent_id=agent_id,
            agent_name=agent_name,
            role=role,
            skills=skills,
            specialties=specialties,
            motivation=motivation,
            availability=availability,
            metadata=metadata or {},
        )

        # 存储
        self._offers[request_id].append(offer)

        # 更新请求状态
        request = self._requests[request_id]
        if request.status == TeamRequestStatus.PENDING:
            request.status = TeamRequestStatus.COLLECTING

        logger.info(
            f"Match offer submitted: {offer_id} for request {request_id}, "
            f"agent={agent_name}, role={role}"
        )

        return offer

    async def generate_team_proposals(
        self,
        request_id: str,
        max_proposals: int = 3,
    ) -> List[TeamProposal]:
        """
        生成团队方案

        Args:
            request_id: 请求 ID
            max_proposals: 最多生成几个方案

        Returns:
            List[TeamProposal]: 生成的团队方案列表

        Raises:
            ValueError: 请求不存在或 offer 不足
        """
        # 验证请求存在
        if request_id not in self._requests:
            raise ValueError(f"Team request not found: {request_id}")

        request = self._requests[request_id]
        offers = self._offers.get(request_id, [])

        # 验证 offer 数量
        if len(offers) < request.team_size:
            raise ValueError(
                f"Not enough offers: need {request.team_size}, got {len(offers)}"
            )

        # 更新状态
        request.status = TeamRequestStatus.GENERATING

        logger.info(
            f"Generating team proposals for {request_id}: "
            f"{len(offers)} offers, need {max_proposals} proposals"
        )

        # 调用 TeamCompositionEngine（待实现）
        from .team_composition_engine import generate_team_combinations

        proposals = await generate_team_combinations(
            request=request,
            offers=offers,
            max_proposals=max_proposals,
        )

        # 存储方案
        self._proposals[request_id] = proposals

        # 更新状态
        request.status = TeamRequestStatus.COMPLETED

        logger.info(
            f"Team proposals generated: {len(proposals)} proposals for {request_id}"
        )

        return proposals

    def get_team_request(self, request_id: str) -> Optional[TeamRequest]:
        """获取组队请求"""
        return self._requests.get(request_id)

    def get_match_offers(self, request_id: str) -> List[MatchOffer]:
        """获取参与意向列表"""
        return self._offers.get(request_id, [])

    def get_team_proposals(self, request_id: str) -> List[TeamProposal]:
        """获取团队方案列表"""
        return self._proposals.get(request_id, [])

    def list_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有组队请求列表

        Args:
            status: 可选状态筛选（如 "pending", "collecting", "completed"）

        Returns:
            List[Dict]: 请求列表，每个包含 offer_count
        """
        results = []
        for req in self._requests.values():
            if status and req.status.value != status:
                continue
            offer_count = len(self._offers.get(req.request_id, []))
            results.append({
                "request": req,
                "offer_count": offer_count,
            })
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_requests": len(self._requests),
            "total_offers": sum(len(offers) for offers in self._offers.values()),
            "total_proposals": sum(
                len(proposals) for proposals in self._proposals.values()
            ),
            "requests_by_status": {
                status.value: sum(
                    1 for r in self._requests.values() if r.status == status
                )
                for status in TeamRequestStatus
            },
        }


# ============ 全局单例 ============

_team_match_service: Optional[TeamMatchService] = None


def get_team_match_service() -> TeamMatchService:
    """获取 TeamMatchService 单例"""
    global _team_match_service
    if _team_match_service is None:
        _team_match_service = TeamMatchService()
    return _team_match_service
