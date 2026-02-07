"""
Team Prompts - 团队组合 LLM 提示词模块

提供团队组合分析所需的 Prompt 模板和响应解析。

核心功能：
1. 系统提示词（定义 LLM 的角色和输出格式）
2. 用户提示词（格式化请求和候选人数据）
3. 响应解析（将 LLM 输出解析为结构化数据）

设计原则：
- 自包含：仅依赖标准库
- 函数式：每个函数职责单一
- 防御性：优雅处理格式异常
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# ============ 系统提示词 ============

def team_composition_system_prompt() -> str:
    """
    生成团队组合分析的系统提示词

    Returns:
        str: 系统提示词，指导 LLM 作为团队组合顾问进行分析
    """
    return """你是一位团队组合顾问，专注于发现意想不到的协作潜力。

你的分析方法：
1. 基于候选人的 Profile 分析其能力（技能、经验、思维方式）
2. 识别互补性——不仅是技能匹配，还包括思维风格、背景差异
3. 发现意外价值：看似无关的组合可能创造跨域创新
4. 每个方案都要说明"为什么这个组合有独特价值"

你需要生成 3 个不同理念的团队方案：
- fast_validation（快速验证型）：效率优先，技能直接匹配，快速交付
- tech_depth（技术深度型）：深度技术能力，攻克技术难题
- cross_innovation（跨域创新型）：跨领域创造力，意外组合产生新价值

输出格式（严格 JSON）：
{
  "proposals": [
    {
      "proposal_type": "fast_validation|tech_depth|cross_innovation",
      "proposal_label": "方案中文标签（如：快速验证型）",
      "proposal_description": "一句话说明为什么这个组合有价值",
      "members": ["offer_id_1", "offer_id_2"],
      "member_roles": {"offer_id_1": "角色名称", "offer_id_2": "角色名称"},
      "member_match_reasons": {"offer_id_1": "匹配理由...", "offer_id_2": "匹配理由..."},
      "reasoning": "详细的团队组合推理",
      "unexpected_insight": "意外发现的跨域价值（如果有）",
      "coverage_analysis": {"需求维度1": "由谁覆盖", "需求维度2": "由谁覆盖"}
    }
  ]
}

注意：
- members 数组中使用 offer_id 引用候选人
- 每个方案的成员数量不必相同，根据实际需要选择
- unexpected_insight 是这个产品的核心价值，请认真思考
- 请只输出 JSON，不要输出其他内容"""


# ============ 用户提示词 ============

def team_composition_user_prompt(
    request_data: dict,
    offers_data: list[dict],
) -> str:
    """
    生成团队组合分析的用户提示词

    将请求信息和候选人 offer 数据格式化为 LLM 可理解的文本。

    Args:
        request_data: 组队请求数据，包含 title, description, required_roles 等
        offers_data: 候选人 offer 数据列表

    Returns:
        str: 格式化的用户提示词
    """
    request_section = format_request(request_data)
    offers_section = format_offers(offers_data)

    return f"""请为以下组队需求生成 3 个团队方案。

{request_section}

{offers_section}

请根据以上信息，生成 3 个不同理念（fast_validation、tech_depth、cross_innovation）的团队方案。"""


def format_request(request_data: dict) -> str:
    """
    格式化组队请求数据为提示词文本

    Args:
        request_data: 组队请求数据字典，期望包含以下字段：
            - title: 请求标题
            - description: 详细描述
            - required_roles: 需要的角色列表
            - team_size: 期望团队规模
            - metadata: 额外信息（可选）

    Returns:
        str: 格式化的请求信息文本
    """
    parts = ["== 组队需求 =="]

    title = request_data.get("title", "未指定")
    parts.append(f"标题：{title}")

    description = request_data.get("description", "未提供描述")
    parts.append(f"描述：{description}")

    required_roles = request_data.get("required_roles", [])
    if required_roles:
        parts.append(f"需要角色：{', '.join(required_roles)}")

    team_size = request_data.get("team_size")
    if team_size:
        parts.append(f"期望团队规模：{team_size} 人")

    # 额外元数据（如有）
    metadata = request_data.get("metadata", {})
    if metadata.get("project_stage"):
        parts.append(f"项目阶段：{metadata['project_stage']}")
    if metadata.get("timeline"):
        parts.append(f"时间要求：{metadata['timeline']}")

    return "\n".join(parts)


def format_offers(offers_data: list[dict]) -> str:
    """
    格式化候选人 offer 数据为提示词文本

    Args:
        offers_data: 候选人 offer 列表，每个 offer 期望包含：
            - offer_id: Offer ID（用于引用）
            - agent_name: 候选人名称
            - role: 角色定位
            - skills: 技能列表
            - specialties: 专长领域
            - motivation: 参与动机
            - availability: 可用时间
            - metadata: 额外信息（可选）

    Returns:
        str: 格式化的候选人信息文本
    """
    if not offers_data:
        return "== 候选人 ==\n（无候选人）"

    parts = [f"== 候选人（共 {len(offers_data)} 人）=="]

    for i, offer in enumerate(offers_data, 1):
        offer_id = offer.get("offer_id", f"unknown_{i}")
        name = offer.get("agent_name", "未知")
        role = offer.get("role", "未指定")

        parts.append(f"\n--- 候选人 {i}: {name} (ID: {offer_id}) ---")
        parts.append(f"  角色定位：{role}")

        skills = offer.get("skills", [])
        if skills:
            parts.append(f"  技能：{', '.join(skills)}")

        specialties = offer.get("specialties", [])
        if specialties:
            parts.append(f"  专长：{', '.join(specialties)}")

        motivation = offer.get("motivation", "")
        if motivation:
            parts.append(f"  参与动机：{motivation}")

        availability = offer.get("availability", "")
        if availability:
            parts.append(f"  可用时间：{availability}")

        # SecondMe Profile 数据（如有）
        metadata = offer.get("metadata", {})
        bio = metadata.get("bio") or metadata.get("self_introduction")
        if bio:
            parts.append(f"  个人简介：{bio}")

    return "\n".join(parts)


# ============ 响应解析 ============

def parse_llm_team_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    解析 LLM 返回的团队方案 JSON

    支持以下格式容错：
    - 纯 JSON 文本
    - Markdown 代码块包裹的 JSON (```json ... ```)
    - JSON 前后有多余文本
    - 字段缺失时提供默认值

    Args:
        response_text: LLM 返回的原始文本

    Returns:
        Dict: 解析后的结构化数据，格式为 {"proposals": [...]}
        None: 解析完全失败时返回 None
    """
    if not response_text or not response_text.strip():
        logger.warning("Empty response text, cannot parse")
        return None

    # 1. 尝试提取 JSON 内容
    json_str = extract_json_string(response_text)

    if json_str is None:
        logger.error("Failed to extract JSON from LLM response")
        logger.debug(f"Response text (first 500 chars): {response_text[:500]}")
        return None

    # 2. 解析 JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.debug(f"JSON string (first 500 chars): {json_str[:500]}")
        return None

    # 3. 验证和规范化结构
    return _normalize_proposals(data)


def extract_json_string(text: str) -> Optional[str]:
    """
    从文本中提取 JSON 字符串

    尝试多种策略：
    1. Markdown 代码块中的 JSON
    2. 第一个 { 到最后一个 } 之间的内容
    3. 整个文本作为 JSON

    Args:
        text: 原始文本

    Returns:
        str: 提取的 JSON 字符串
        None: 提取失败
    """
    text = text.strip()

    # 策略 1：从 Markdown 代码块中提取
    code_block_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```",
        text,
        re.DOTALL,
    )
    if code_block_match:
        return code_block_match.group(1).strip()

    # 策略 2：从第一个 { 到最后一个 } 之间提取
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1]

    # 策略 3：整个文本作为 JSON
    if text.startswith("{") or text.startswith("["):
        return text

    return None


def _normalize_proposals(data: Any) -> Optional[Dict[str, Any]]:
    """
    验证和规范化方案数据结构

    确保 proposals 列表存在且每个方案包含必需字段。
    缺失字段使用默认值填充。

    Args:
        data: 解析后的 JSON 数据

    Returns:
        Dict: 规范化后的数据 {"proposals": [...]}
        None: 数据结构无法修复
    """
    if not isinstance(data, dict):
        logger.error(f"Expected dict, got {type(data).__name__}")
        return None

    proposals = data.get("proposals")
    if not isinstance(proposals, list):
        logger.error("Missing or invalid 'proposals' field")
        return None

    if not proposals:
        logger.warning("Empty proposals list")
        return {"proposals": []}

    normalized = []
    for i, proposal in enumerate(proposals):
        if not isinstance(proposal, dict):
            logger.warning(f"Skipping non-dict proposal at index {i}")
            continue

        # 规范化每个方案，填充默认值
        normalized_proposal = {
            "proposal_type": proposal.get("proposal_type", "fast_validation"),
            "proposal_label": proposal.get("proposal_label", f"方案 {i + 1}"),
            "proposal_description": proposal.get("proposal_description", ""),
            "members": proposal.get("members", []),
            "member_roles": proposal.get("member_roles", {}),
            "member_match_reasons": proposal.get("member_match_reasons", {}),
            "reasoning": proposal.get("reasoning", ""),
            "unexpected_insight": proposal.get("unexpected_insight", ""),
            "coverage_analysis": proposal.get("coverage_analysis", {}),
        }
        normalized.append(normalized_proposal)

    logger.info(f"Parsed {len(normalized)} team proposals from LLM response")
    return {"proposals": normalized}


# ============ 表单建议提示词 ============

# 合法的 availability 值
VALID_AVAILABILITY = {"weekend_2d", "part_time", "full_time", "flexible", "one_month"}


def form_suggest_system_prompt() -> str:
    """
    生成表单自动填写建议的系统提示词

    用于 SecondMe Chat API 调用。SecondMe 已知用户的 Profile，
    此 prompt 让它基于对用户的了解，推测黑客松组队表单的建议值。
    """
    return """你是用户的 SecondMe（第二自我），你非常了解用户的技能、兴趣和经历。

现在用户正在参加一个黑客松组队活动，需要填写一份组队表单。
请基于你对用户的了解，帮他/她建议表单内容。

你必须用严格的 JSON 格式回答，包含以下字段：
{
  "message": "一段自然的对话文字，像朋友一样告诉用户你帮他/她想到了什么（2-3句话，用'我'指代自己，用'你'指代用户）",
  "suggestions": {
    "project_idea": "建议的项目想法（50-200字，结合用户背景和黑客松主题）",
    "skills": ["技能1", "技能2", "技能3"],
    "availability": "weekend_2d|part_time|full_time|flexible|one_month",
    "roles_needed": ["角色1", "角色2"]
  }
}

关于 skills，请从以下选项中选择最匹配的（也可以用自定义技能）：
Prompt Engineering, AI Agent 开发, LLM 应用, RAG, Fine-tuning, Multi-Agent 系统, AI Workflow, MCP, LangChain, CrewAI, React, Vue, Next.js, TypeScript, Node.js, Python, Go, Rust, Java, Swift, DevOps, Docker, Kubernetes, AWS, Machine Learning, Data Science, Computer Vision, NLP, Blockchain, Smart Contract, Solidity, Move, Sui, UI/UX, Figma, Product Design, 交互设计, 用户研究, Content Writing, 视频制作, 短视频运营, Copywriting, Marketing, Growth Hacking, 商业模式设计, 融资 & Pitch, Project Management, Business Strategy, 社区运营, 医疗健康, 教育, 金融, 游戏, 音乐, 电商

关于 availability，请从以下值中选一个：
- weekend_2d（本周末 2 天）
- part_time（每周 10-20 小时）
- full_time（全职投入）
- flexible（灵活安排）
- one_month（一个月项目）

关于 roles_needed，请从以下选项中选择：
AI Engineer, Full Stack Developer, Frontend Developer, Backend Developer, UI/UX Designer, Product Manager, Data Scientist, Blockchain Developer, Creative / Content, Marketing / Growth, Business Strategist, Domain Expert

注意：
- 请只输出 JSON，不要输出其他内容
- message 字段要口语化、亲切，让用户感到 SecondMe 真的理解自己
- project_idea 要具体且有创意，结合用户擅长的技术和黑客松主题
- skills 最多选 5 个，优先选用户最强的技能
- roles_needed 选 1-3 个，是用户希望找到的队友角色（不是用户自己的角色）"""


def form_suggest_user_prompt(hackathon_context: str) -> str:
    """
    生成表单建议的用户消息

    Args:
        hackathon_context: 黑客松场景描述
    """
    return f"我正在参加 {hackathon_context}，需要填写组队表单。请根据你对我的了解，帮我建议一下表单内容。"


def parse_suggest_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    解析 SecondMe 返回的表单建议 JSON

    Args:
        response_text: LLM 返回的原始文本

    Returns:
        Dict: {"message": "...", "suggestions": {...}} 或 None
    """
    if not response_text or not response_text.strip():
        logger.warning("Empty suggest response text")
        return None

    json_str = extract_json_string(response_text)
    if json_str is None:
        logger.error("Failed to extract JSON from suggest response")
        logger.debug(f"Response (first 500 chars): {response_text[:500]}")
        return None

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Suggest response JSON parse error: {e}")
        return None

    if not isinstance(data, dict):
        logger.error(f"Expected dict, got {type(data).__name__}")
        return None

    # 验证必需字段
    if "message" not in data or "suggestions" not in data:
        logger.error("Missing 'message' or 'suggestions' in suggest response")
        return None

    suggestions = data["suggestions"]
    if not isinstance(suggestions, dict):
        logger.error("'suggestions' is not a dict")
        return None

    # 规范化 availability
    availability = suggestions.get("availability", "")
    if availability not in VALID_AVAILABILITY:
        logger.info(f"Invalid availability '{availability}', defaulting to 'flexible'")
        suggestions["availability"] = "flexible"

    # 确保 skills 和 roles_needed 是列表
    if not isinstance(suggestions.get("skills"), list):
        suggestions["skills"] = []
    if not isinstance(suggestions.get("roles_needed"), list):
        suggestions["roles_needed"] = []

    logger.info("Successfully parsed form suggest response")
    return data
