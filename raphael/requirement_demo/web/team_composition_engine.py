"""
Team Composition Engine - 团队组合引擎

核心算法：
输入：N 个 MatchOffer
输出：K 个 TeamProposal（多个不同的团队方案）

逻辑：
1. 角色覆盖检测（必需角色是否满足）
2. 技能互补识别（技能组合是否互补）
3. 冲突检测（时间冲突、角色重叠等）
4. 意外发现标注（跨域组合）

设计原则：
- 简单优先：先实现最直接的算法，V1 不追求完美
- 复杂度控制：每个函数 < 50 行
- 代码保障：用代码保证逻辑正确性，LLM 提供创造性
"""

import logging
import uuid
from typing import List, Dict, Set, Any, Optional, Callable, Awaitable
from itertools import combinations

from .team_match_service import (
    TeamRequest,
    MatchOffer,
    TeamProposal,
    TeamMember,
)
from .team_prompts import (
    team_composition_system_prompt,
    team_composition_user_prompt,
    parse_llm_team_response,
)
from .oauth2_client import get_oauth2_client, ChatError

logger = logging.getLogger(__name__)


# ============ LLM 团队组合 ============

async def llm_compose_teams(
    request: TeamRequest,
    offers: List[MatchOffer],
    access_token: str,
    max_proposals: int = 3,
    progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
) -> List[TeamProposal]:
    """
    使用 SecondMe Chat API 生成团队方案（LLM 驱动，取代纯算法组合）

    Raises: ChatError（LLM 调用失败）, ValueError（解析失败/无有效方案）
    """
    logger.info(
        f"LLM compose teams: {len(offers)} offers, "
        f"max_proposals={max_proposals}"
    )

    # 1. 转换数据为 dict 格式
    request_data = _request_to_dict(request)
    offers_data = [_offer_to_dict(o) for o in offers]

    # 2. 构建 prompt
    system_prompt = team_composition_system_prompt()
    user_prompt = team_composition_user_prompt(request_data, offers_data)
    messages = [{"role": "user", "content": user_prompt}]

    # 3. 调用 LLM 流式接口
    full_response = await _stream_llm_response(
        access_token, messages, system_prompt, progress_callback
    )

    # 4. 解析 LLM 响应
    parsed = parse_llm_team_response(full_response)
    if parsed is None:
        raise ValueError("LLM 响应解析失败")

    # 5. 转换为 TeamProposal 列表
    proposals = _llm_result_to_proposals(parsed, offers, request)
    if not proposals:
        raise ValueError("LLM 未生成有效方案")

    logger.info(f"LLM composed {len(proposals)} team proposals")
    return proposals[:max_proposals]


async def _stream_llm_response(
    access_token: str,
    messages: list,
    system_prompt: str,
    progress_callback: Optional[Callable[[str], Awaitable[None]]] = None,
) -> str:
    """
    流式调用 SecondMe Chat API 并累积完整响应

    Args:
        access_token: SecondMe Access Token
        messages: 消息列表
        system_prompt: 系统提示词
        progress_callback: 可选的进度回调

    Returns:
        str: 完整的 LLM 响应文本

    Raises:
        ChatError: LLM 调用失败
    """
    client = await get_oauth2_client()
    full_response = ""
    first_token_logged = False

    async for event in client.chat_stream(
        access_token, messages, system_prompt
    ):
        if event.get("type") == "data":
            content = event.get("content", "")
            full_response += content

            if not first_token_logged and content:
                logger.info("LLM first token received")
                first_token_logged = True

            if progress_callback and content:
                await progress_callback(content)

    logger.info(
        f"LLM stream complete, response length: {len(full_response)}"
    )
    return full_response


def _request_to_dict(request: TeamRequest) -> dict:
    """将 TeamRequest 转换为 dict 格式供 prompt 使用"""
    return {
        "title": request.title,
        "description": request.description,
        "required_roles": request.required_roles,
        "team_size": request.team_size,
        "metadata": request.metadata,
    }


def _offer_to_dict(offer: MatchOffer) -> dict:
    """将 MatchOffer 转换为 dict 格式供 prompt 使用"""
    return {
        "offer_id": offer.offer_id,
        "agent_name": offer.agent_name,
        "role": offer.role,
        "skills": offer.skills,
        "specialties": offer.specialties,
        "motivation": offer.motivation,
        "availability": offer.availability,
        "metadata": offer.metadata,
    }


def _llm_result_to_proposals(
    parsed: Dict[str, Any],
    offers: List[MatchOffer],
    request: TeamRequest,
) -> List[TeamProposal]:
    """
    将 LLM 解析结果转换为 TeamProposal 列表

    Args:
        parsed: parse_llm_team_response() 返回的结构化数据
        offers: 原始 MatchOffer 列表（用于查找成员详情）
        request: 原始组队请求

    Returns:
        List[TeamProposal]: 转换后的团队方案列表
    """
    offer_map = {o.offer_id: o for o in offers}
    proposals = []

    for raw_proposal in parsed.get("proposals", []):
        proposal = _build_llm_proposal(raw_proposal, offer_map, request)
        if proposal is not None:
            proposals.append(proposal)

    return proposals


def _build_llm_proposal(
    raw: Dict[str, Any],
    offer_map: Dict[str, MatchOffer],
    request: TeamRequest,
) -> Optional[TeamProposal]:
    """从单个 LLM 方案数据构建 TeamProposal，成员全部查找失败时返回 None"""
    members = _build_llm_members(raw, offer_map)
    if not members:
        logger.warning(f"No valid members for proposal: {raw.get('proposal_label')}")
        return None

    unexpected = [raw["unexpected_insight"]] if raw.get("unexpected_insight") else []

    return TeamProposal(
        proposal_id=f"proposal_{uuid.uuid4().hex[:8]}",
        request_id=request.request_id,
        title=raw.get("proposal_label", "LLM 方案"),
        members=members,
        coverage_score=0.0,
        synergy_score=0.0,
        unexpected_combinations=unexpected,
        reasoning=raw.get("reasoning", ""),
        metadata={
            "proposal_type": raw.get("proposal_type", ""),
            "coverage_analysis": raw.get("coverage_analysis", {}),
            "source": "llm",
        },
    )


def _build_llm_members(
    raw: Dict[str, Any],
    offer_map: Dict[str, MatchOffer],
) -> List[TeamMember]:
    """从 LLM 方案数据中构建 TeamMember 列表，跳过无法匹配的 offer_id"""
    member_ids = raw.get("members", [])
    member_roles = raw.get("member_roles", {})
    member_reasons = raw.get("member_match_reasons", {})

    members = []
    for offer_id in member_ids:
        offer = offer_map.get(offer_id)
        if offer is None:
            logger.warning(f"Offer not found for id: {offer_id}, skipping")
            continue

        role = member_roles.get(offer_id, offer.role)
        contribution = member_reasons.get(offer_id, f"{role}方面的专业支持")
        members.append(TeamMember(
            agent_id=offer.agent_id,
            agent_name=offer.agent_name,
            role=role,
            skills=offer.skills,
            specialties=offer.specialties,
            contribution=contribution,
        ))

    return members


# ============ 算法组合（Fallback） ============

async def generate_team_combinations(
    request: TeamRequest,
    offers: List[MatchOffer],
    max_proposals: int = 3,
) -> List[TeamProposal]:
    """
    生成团队组合方案

    算法：
    1. 从 N 个 offer 中生成所有可能的团队组合（组合数学）
    2. 对每个组合计算评分（覆盖度、协同度）
    3. 选择 top K 个不同的方案
    4. 标注意外组合

    Args:
        request: 组队请求
        offers: 参与意向列表
        max_proposals: 最多返回几个方案

    Returns:
        List[TeamProposal]: 团队方案列表（按评分排序）
    """
    if not offers:
        logger.warning("No offers to generate proposals")
        return []

    team_size = request.team_size
    required_roles = set(request.required_roles)

    logger.info(
        f"Generating combinations: {len(offers)} offers, "
        f"team_size={team_size}, required_roles={required_roles}"
    )

    # 1. 生成所有可能的团队组合
    all_combinations = list(combinations(offers, team_size))
    logger.debug(f"Total combinations: {len(all_combinations)}")

    # 2. 评估每个组合
    scored_combinations = []
    for combo in all_combinations:
        score_result = _evaluate_team_combination(
            combo, required_roles, request
        )
        if score_result:
            scored_combinations.append(score_result)

    # 3. 按总分排序
    scored_combinations.sort(
        key=lambda x: x["total_score"], reverse=True
    )

    # 4. 选择 top K 个不同的方案
    selected = scored_combinations[:max_proposals]

    # 5. 生成 TeamProposal
    proposals = []
    for i, combo_data in enumerate(selected):
        proposal = _build_team_proposal(
            request=request,
            combo_data=combo_data,
            rank=i + 1,
        )
        proposals.append(proposal)

    logger.info(f"Generated {len(proposals)} team proposals")
    return proposals


def _evaluate_team_combination(
    combo: tuple,
    required_roles: Set[str],
    request: TeamRequest,
) -> Optional[Dict[str, Any]]:
    """
    评估团队组合

    评分维度：
    - 角色覆盖度（必需角色是否满足）
    - 技能互补度（技能是否互补）
    - 跨域发现（是否有意外组合）

    Args:
        combo: 组合（多个 MatchOffer）
        required_roles: 必需角色集合
        request: 组队请求

    Returns:
        Dict: 评分结果，包含 total_score, coverage_score, synergy_score 等
        None: 如果组合不合格
    """
    # 1. 检查角色覆盖
    offered_roles = {offer.role for offer in combo}
    coverage_score = _calculate_coverage_score(
        offered_roles, required_roles
    )

    # 如果角色覆盖度太低，直接排除
    if coverage_score < 0.5:
        return None

    # 2. 计算技能互补度
    all_skills = set()
    for offer in combo:
        all_skills.update(offer.skills)

    synergy_score = _calculate_synergy_score(combo, all_skills)

    # 3. 识别意外组合（跨域）
    unexpected = _identify_unexpected_combinations(combo)

    # 4. 计算总分（加权）
    total_score = (
        coverage_score * 0.5 +  # 角色覆盖 50%
        synergy_score * 0.3 +   # 技能互补 30%
        len(unexpected) * 0.05  # 意外发现加分
    )

    return {
        "combo": combo,
        "total_score": total_score,
        "coverage_score": coverage_score,
        "synergy_score": synergy_score,
        "unexpected_combinations": unexpected,
        "all_skills": list(all_skills),
    }


def _calculate_coverage_score(
    offered_roles: Set[str],
    required_roles: Set[str],
) -> float:
    """
    计算角色覆盖度

    覆盖度 = (满足的必需角色数) / (总必需角色数)

    Args:
        offered_roles: 提供的角色集合
        required_roles: 必需的角色集合

    Returns:
        float: 覆盖度 (0.0 ~ 1.0)
    """
    if not required_roles:
        return 1.0

    # 简单匹配：检查角色名称包含关系
    # 例如："前端开发" 匹配 "前端"
    matched_count = 0
    for required in required_roles:
        for offered in offered_roles:
            if required.lower() in offered.lower():
                matched_count += 1
                break

    coverage = matched_count / len(required_roles)
    return coverage


def _calculate_synergy_score(
    combo: tuple,
    all_skills: Set[str],
) -> float:
    """
    计算技能互补度

    互补度基于：
    - 技能多样性（技能总数 / 成员数）
    - 专长互补性（不同专长领域）

    Args:
        combo: 组合（多个 MatchOffer）
        all_skills: 所有技能集合

    Returns:
        float: 互补度 (0.0 ~ 1.0)
    """
    if not combo:
        return 0.0

    # 1. 技能多样性
    member_count = len(combo)
    skill_count = len(all_skills)
    diversity = min(skill_count / (member_count * 3), 1.0)  # 假设平均每人 3 个技能

    # 2. 专长互补性
    all_specialties = set()
    for offer in combo:
        all_specialties.update(offer.specialties)

    specialty_diversity = min(len(all_specialties) / member_count, 1.0)

    # 3. 加权平均
    synergy = diversity * 0.6 + specialty_diversity * 0.4
    return synergy


def _identify_unexpected_combinations(
    combo: tuple,
) -> List[str]:
    """
    识别意外组合（跨域互补）

    意外组合的定义：
    - 不同专长领域的组合（如 "设计" + "技术"）
    - 跨领域技能组合

    Args:
        combo: 组合（多个 MatchOffer）

    Returns:
        List[str]: 意外组合描述列表
    """
    unexpected = []

    # 1. 检查专长跨域
    specialties_by_member = [
        set(offer.specialties) for offer in combo
    ]

    # 识别跨领域组合（简单启发式）
    cross_domain_pairs = [
        ("设计", "技术"),
        ("前端", "后端"),
        ("产品", "技术"),
        ("运营", "技术"),
    ]

    for domain1, domain2 in cross_domain_pairs:
        has_domain1 = any(
            any(domain1 in s for s in specialties)
            for specialties in specialties_by_member
        )
        has_domain2 = any(
            any(domain2 in s for s in specialties)
            for specialties in specialties_by_member
        )

        if has_domain1 and has_domain2:
            unexpected.append(f"{domain1}+{domain2} 跨域组合")

    # 2. 检查技能互补（不同角色的互补技能）
    roles = [offer.role for offer in combo]
    if "设计" in " ".join(roles) and "开发" in " ".join(roles):
        unexpected.append("设计+开发 互补")

    return unexpected


def _build_team_proposal(
    request: TeamRequest,
    combo_data: Dict[str, Any],
    rank: int,
) -> TeamProposal:
    """
    构建 TeamProposal

    Args:
        request: 组队请求
        combo_data: 组合数据（来自 _evaluate_team_combination）
        rank: 方案排名

    Returns:
        TeamProposal: 团队方案
    """
    combo = combo_data["combo"]
    coverage_score = combo_data["coverage_score"]
    synergy_score = combo_data["synergy_score"]
    unexpected = combo_data["unexpected_combinations"]
    all_skills = combo_data["all_skills"]

    # 构建团队成员
    members = []
    for offer in combo:
        member = TeamMember(
            agent_id=offer.agent_id,
            agent_name=offer.agent_name,
            role=offer.role,
            skills=offer.skills,
            specialties=offer.specialties,
            contribution=f"{offer.role}方面的专业支持",
        )
        members.append(member)

    # 生成推理说明
    reasoning = _generate_reasoning(
        members=members,
        coverage_score=coverage_score,
        synergy_score=synergy_score,
        unexpected=unexpected,
        all_skills=all_skills,
    )

    # 生成方案标题
    title = f"方案 {rank}：" + " + ".join([m.role for m in members])

    proposal = TeamProposal(
        proposal_id=f"proposal_{uuid.uuid4().hex[:8]}",
        request_id=request.request_id,
        title=title,
        members=members,
        coverage_score=coverage_score,
        synergy_score=synergy_score,
        unexpected_combinations=unexpected,
        reasoning=reasoning,
        metadata={
            "rank": rank,
            "total_skills": len(all_skills),
        },
    )

    return proposal


def _generate_reasoning(
    members: List[TeamMember],
    coverage_score: float,
    synergy_score: float,
    unexpected: List[str],
    all_skills: List[str],
) -> str:
    """
    生成方案推理说明

    Args:
        members: 团队成员列表
        coverage_score: 覆盖度
        synergy_score: 协同度
        unexpected: 意外组合
        all_skills: 所有技能

    Returns:
        str: 推理说明
    """
    parts = []

    # 1. 团队组成
    member_names = [m.agent_name for m in members]
    parts.append(f"团队成员：{', '.join(member_names)}")

    # 2. 角色覆盖
    if coverage_score >= 0.8:
        parts.append(f"角色覆盖度高（{coverage_score:.0%}），满足需求")
    elif coverage_score >= 0.5:
        parts.append(f"角色覆盖度中等（{coverage_score:.0%}），基本满足")
    else:
        parts.append(f"角色覆盖度较低（{coverage_score:.0%}）")

    # 3. 技能互补
    if synergy_score >= 0.7:
        parts.append(f"技能互补性强（{synergy_score:.0%}），协作潜力大")
    else:
        parts.append(f"技能互补性一般（{synergy_score:.0%}）")

    # 4. 意外发现
    if unexpected:
        parts.append(f"意外发现：{', '.join(unexpected)}")

    # 5. 技能清单
    parts.append(f"覆盖技能：{', '.join(all_skills[:10])}")  # 最多显示 10 个

    return "；".join(parts)
