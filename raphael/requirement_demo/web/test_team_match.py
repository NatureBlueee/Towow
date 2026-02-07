"""
Team Matcher 单元测试

测试策略：
- 正常情况：happy path
- 边界情况：极端输入
- 异常情况：错误输入

使用 pytest 运行：
    pytest web/test_team_match.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from .team_match_service import (
    TeamMatchService,
    TeamRequest,
    MatchOffer,
    TeamProposal,
    TeamRequestStatus,
)
from .team_composition_engine import (
    generate_team_combinations,
    _evaluate_team_combination,
    _calculate_coverage_score,
    _calculate_synergy_score,
    _identify_unexpected_combinations,
)


# ============ TeamMatchService 测试 ============

class TestTeamMatchService:
    """TeamMatchService 单元测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return TeamMatchService()

    @pytest.mark.asyncio
    async def test_create_team_request_normal(self, service):
        """正常情况：创建组队请求成功"""
        # Act
        request = await service.create_team_request(
            title="寻找黑客松队友",
            description="参加 AI 黑客松",
            submitter_id="user_alice",
            required_roles=["前端", "后端", "设计师"],
            team_size=3,
        )

        # Assert
        assert request.request_id.startswith("team_req_")
        assert request.title == "寻找黑客松队友"
        assert len(request.required_roles) == 3
        assert request.team_size == 3
        assert request.status == TeamRequestStatus.PENDING
        assert request.channel_id.startswith("team_ch_")

    @pytest.mark.asyncio
    async def test_create_team_request_invalid_title(self, service):
        """边界情况：空标题"""
        # Act & Assert
        with pytest.raises(ValueError, match="title cannot be empty"):
            await service.create_team_request(
                title="",
                description="测试",
                submitter_id="user_alice",
                required_roles=["前端"],
                team_size=2,
            )

    @pytest.mark.asyncio
    async def test_create_team_request_invalid_team_size(self, service):
        """边界情况：团队规模太小"""
        # Act & Assert
        with pytest.raises(ValueError, match="team_size must be at least 2"):
            await service.create_team_request(
                title="测试",
                description="测试",
                submitter_id="user_alice",
                required_roles=["前端"],
                team_size=1,  # 太小
            )

    @pytest.mark.asyncio
    async def test_submit_match_offer_normal(self, service):
        """正常情况：提交参与意向成功"""
        # Arrange
        request = await service.create_team_request(
            title="测试",
            description="测试",
            submitter_id="user_alice",
            required_roles=["前端"],
            team_size=2,
        )

        # Act
        offer = await service.submit_match_offer(
            request_id=request.request_id,
            agent_id="user_bob",
            agent_name="Bob",
            role="前端开发",
            skills=["React", "TypeScript"],
            specialties=["web-development"],
            motivation="想学习",
            availability="周末",
        )

        # Assert
        assert offer.offer_id.startswith("offer_")
        assert offer.agent_name == "Bob"
        assert offer.role == "前端开发"
        assert len(offer.skills) == 2

        # 验证请求状态变化
        updated_request = service.get_team_request(request.request_id)
        assert updated_request.status == TeamRequestStatus.COLLECTING

    @pytest.mark.asyncio
    async def test_submit_match_offer_request_not_found(self, service):
        """异常情况：请求不存在"""
        # Act & Assert
        with pytest.raises(ValueError, match="Team request not found"):
            await service.submit_match_offer(
                request_id="nonexistent_request",
                agent_id="user_bob",
                agent_name="Bob",
                role="前端开发",
                skills=["React"],
                specialties=[],
                motivation="测试",
                availability="随时",
            )

    @pytest.mark.asyncio
    async def test_generate_team_proposals_normal(self, service):
        """正常情况：生成团队方案成功"""
        # Arrange
        request = await service.create_team_request(
            title="测试",
            description="测试",
            submitter_id="user_alice",
            required_roles=["前端", "后端"],
            team_size=2,
        )

        # 添加 offer
        await service.submit_match_offer(
            request_id=request.request_id,
            agent_id="user_bob",
            agent_name="Bob",
            role="前端开发",
            skills=["React", "TypeScript"],
            specialties=["web-development", "frontend"],
            motivation="想学习",
            availability="周末",
        )

        await service.submit_match_offer(
            request_id=request.request_id,
            agent_id="user_carol",
            agent_name="Carol",
            role="后端开发",
            skills=["Python", "FastAPI"],
            specialties=["web-development", "backend"],
            motivation="有经验",
            availability="工作日晚上",
        )

        # Act
        proposals = await service.generate_team_proposals(
            request_id=request.request_id,
            max_proposals=3,
        )

        # Assert
        assert len(proposals) > 0
        assert proposals[0].request_id == request.request_id
        assert len(proposals[0].members) == 2
        assert 0.0 <= proposals[0].coverage_score <= 1.0
        assert 0.0 <= proposals[0].synergy_score <= 1.0

        # 验证请求状态变化
        updated_request = service.get_team_request(request.request_id)
        assert updated_request.status == TeamRequestStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_generate_team_proposals_not_enough_offers(self, service):
        """异常情况：offer 数量不足"""
        # Arrange
        request = await service.create_team_request(
            title="测试",
            description="测试",
            submitter_id="user_alice",
            required_roles=["前端"],
            team_size=3,  # 需要 3 人
        )

        # 只添加 1 个 offer（不足）
        await service.submit_match_offer(
            request_id=request.request_id,
            agent_id="user_bob",
            agent_name="Bob",
            role="前端开发",
            skills=["React"],
            specialties=[],
            motivation="测试",
            availability="随时",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Not enough offers"):
            await service.generate_team_proposals(
                request_id=request.request_id,
                max_proposals=3,
            )


# ============ TeamCompositionEngine 测试 ============

class TestTeamCompositionEngine:
    """团队组合引擎单元测试"""

    @pytest.fixture
    def sample_request(self):
        """创建示例请求"""
        return TeamRequest(
            request_id="test_req_123",
            title="测试",
            description="测试",
            submitter_id="user_alice",
            required_roles=["前端", "后端"],
            team_size=2,
        )

    @pytest.fixture
    def sample_offers(self):
        """创建示例 offer 列表"""
        return [
            MatchOffer(
                offer_id="offer_1",
                request_id="test_req_123",
                agent_id="user_bob",
                agent_name="Bob",
                role="前端开发",
                skills=["React", "TypeScript", "CSS"],
                specialties=["web-development", "frontend"],
                motivation="想学习",
                availability="周末",
            ),
            MatchOffer(
                offer_id="offer_2",
                request_id="test_req_123",
                agent_id="user_carol",
                agent_name="Carol",
                role="后端开发",
                skills=["Python", "FastAPI", "PostgreSQL"],
                specialties=["web-development", "backend"],
                motivation="有经验",
                availability="工作日晚上",
            ),
            MatchOffer(
                offer_id="offer_3",
                request_id="test_req_123",
                agent_id="user_dave",
                agent_name="Dave",
                role="全栈开发",
                skills=["React", "Python", "Docker"],
                specialties=["web-development"],
                motivation="兴趣",
                availability="随时",
            ),
        ]

    @pytest.mark.asyncio
    async def test_generate_team_combinations_normal(
        self, sample_request, sample_offers
    ):
        """正常情况：生成团队组合"""
        # Act
        proposals = await generate_team_combinations(
            request=sample_request,
            offers=sample_offers,
            max_proposals=3,
        )

        # Assert
        assert len(proposals) > 0
        assert len(proposals) <= 3
        for proposal in proposals:
            assert len(proposal.members) == sample_request.team_size
            assert proposal.request_id == sample_request.request_id

    @pytest.mark.asyncio
    async def test_generate_team_combinations_empty_offers(
        self, sample_request
    ):
        """边界情况：空 offer 列表"""
        # Act
        proposals = await generate_team_combinations(
            request=sample_request,
            offers=[],
            max_proposals=3,
        )

        # Assert
        assert len(proposals) == 0

    def test_calculate_coverage_score_full_coverage(self):
        """正常情况：完全覆盖"""
        # Arrange
        offered_roles = {"前端开发", "后端开发", "设计师"}
        required_roles = {"前端", "后端", "设计"}

        # Act
        score = _calculate_coverage_score(offered_roles, required_roles)

        # Assert
        assert score == 1.0

    def test_calculate_coverage_score_partial_coverage(self):
        """正常情况：部分覆盖"""
        # Arrange
        offered_roles = {"前端开发"}
        required_roles = {"前端", "后端"}

        # Act
        score = _calculate_coverage_score(offered_roles, required_roles)

        # Assert
        assert 0.0 < score < 1.0

    def test_calculate_coverage_score_no_required(self):
        """边界情况：无必需角色"""
        # Arrange
        offered_roles = {"前端开发"}
        required_roles = set()

        # Act
        score = _calculate_coverage_score(offered_roles, required_roles)

        # Assert
        assert score == 1.0

    def test_calculate_synergy_score_normal(self, sample_offers):
        """正常情况：计算协同度"""
        # Arrange
        combo = (sample_offers[0], sample_offers[1])  # 前端 + 后端
        all_skills = set()
        for offer in combo:
            all_skills.update(offer.skills)

        # Act
        score = _calculate_synergy_score(combo, all_skills)

        # Assert
        assert 0.0 <= score <= 1.0

    def test_identify_unexpected_combinations_cross_domain(
        self, sample_offers
    ):
        """正常情况：识别跨域组合"""
        # Arrange
        # 修改 sample_offers 使其包含明确的跨域标识
        frontend_offer = MatchOffer(
            offer_id="offer_1",
            request_id="test",
            agent_id="user_1",
            agent_name="Frontend Dev",
            role="前端开发",
            skills=["React"],
            specialties=["前端开发", "web-development"],  # 包含 "前端"
            motivation="测试",
            availability="随时",
        )
        backend_offer = MatchOffer(
            offer_id="offer_2",
            request_id="test",
            agent_id="user_2",
            agent_name="Backend Dev",
            role="后端开发",
            skills=["Python"],
            specialties=["后端开发", "api-design"],  # 包含 "后端"
            motivation="测试",
            availability="随时",
        )
        combo = (frontend_offer, backend_offer)

        # Act
        unexpected = _identify_unexpected_combinations(combo)

        # Assert
        # 应该识别到前端+后端跨域组合
        assert len(unexpected) > 0

    def test_identify_unexpected_combinations_same_domain(
        self
    ):
        """正常情况：同领域无意外组合"""
        # Arrange
        # 两个前端开发（同领域）
        combo = (
            MatchOffer(
                offer_id="offer_1",
                request_id="test",
                agent_id="user_1",
                agent_name="User 1",
                role="前端开发",
                skills=["React"],
                specialties=["frontend"],
                motivation="测试",
                availability="随时",
            ),
            MatchOffer(
                offer_id="offer_2",
                request_id="test",
                agent_id="user_2",
                agent_name="User 2",
                role="前端工程师",
                skills=["Vue"],
                specialties=["frontend"],
                motivation="测试",
                availability="随时",
            ),
        )

        # Act
        unexpected = _identify_unexpected_combinations(combo)

        # Assert
        # 同领域，不应该有跨域组合
        assert len(unexpected) == 0


# ============ 集成测试 ============

class TestTeamMatcherIntegration:
    """端到端集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """集成测试：完整工作流"""
        service = TeamMatchService()

        # 1. 创建组队请求
        request = await service.create_team_request(
            title="黑客松组队",
            description="参加 AI 黑客松，寻找队友",
            submitter_id="user_alice",
            required_roles=["前端", "后端", "设计"],
            team_size=3,
        )

        # 2. 提交多个参与意向
        offers_data = [
            {
                "agent_id": "user_bob",
                "agent_name": "Bob",
                "role": "前端开发",
                "skills": ["React", "TypeScript"],
                "specialties": ["frontend"],
            },
            {
                "agent_id": "user_carol",
                "agent_name": "Carol",
                "role": "后端开发",
                "skills": ["Python", "FastAPI"],
                "specialties": ["backend"],
            },
            {
                "agent_id": "user_dave",
                "agent_name": "Dave",
                "role": "UI设计师",
                "skills": ["Figma", "Sketch"],
                "specialties": ["design"],
            },
            {
                "agent_id": "user_eve",
                "agent_name": "Eve",
                "role": "全栈开发",
                "skills": ["React", "Python"],
                "specialties": ["fullstack"],
            },
        ]

        for offer_data in offers_data:
            await service.submit_match_offer(
                request_id=request.request_id,
                **offer_data,
                motivation="想参加",
                availability="周末",
            )

        # 3. 生成团队方案
        proposals = await service.generate_team_proposals(
            request_id=request.request_id,
            max_proposals=3,
        )

        # 4. 验证结果
        assert len(proposals) > 0
        assert len(proposals) <= 3

        # 验证第一个方案
        best_proposal = proposals[0]
        assert len(best_proposal.members) == 3
        assert best_proposal.coverage_score > 0.5
        assert best_proposal.synergy_score >= 0.0

        # 验证至少有一个方案包含意外组合
        has_unexpected = any(
            len(p.unexpected_combinations) > 0 for p in proposals
        )
        assert has_unexpected, "应该至少有一个方案包含意外组合"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
