"""
SecondMe Mock实现
MVP阶段的模拟数字分身服务

提供两种 Mock 实现：
1. SecondMeMockService - 基于规则和 LLM 的智能 Mock
2. SimpleRandomMockClient - 纯随机结果，用于压力测试
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import random
import logging
import json

from .secondme import SecondMeService

logger = logging.getLogger(__name__)


# 预设的用户档案（10个丰富的 Mock 用户）
MOCK_PROFILES: Dict[str, Dict[str, Any]] = {
    "bob": {
        "user_id": "bob",
        "display_name": "Bob",
        "name": "Bob Chen",
        "capabilities": ["场地资源", "活动组织", "会议室"],
        "location": "北京朝阳",
        "availability": "工作日可用",
        "personality": "热情外向，喜欢组织活动",
        "interests": ["AI", "创业", "社交"],
        "decision_style": "快速决策，倾向于参与"
    },
    "alice": {
        "user_id": "alice",
        "display_name": "Alice",
        "name": "Alice Wang",
        "capabilities": ["技术分享", "AI研究", "演讲"],
        "location": "北京海淀",
        "availability": "周末优先",
        "personality": "专业认真，乐于分享",
        "interests": ["机器学习", "NLP", "技术布道"],
        "decision_style": "谨慎评估，看重技术深度"
    },
    "charlie": {
        "user_id": "charlie",
        "display_name": "Charlie",
        "name": "Charlie Zhang",
        "capabilities": ["活动策划", "流程设计", "现场协调"],
        "location": "北京",
        "availability": "灵活",
        "personality": "细心周到，执行力强",
        "interests": ["项目管理", "活动运营", "社区建设"],
        "decision_style": "注重细节，需要明确分工"
    },
    "david": {
        "user_id": "david",
        "display_name": "David",
        "name": "David Liu",
        "capabilities": ["UI设计", "产品原型", "用户体验"],
        "location": "远程",
        "availability": "按项目排期",
        "personality": "创意丰富，注重细节",
        "interests": ["设计系统", "AI产品", "交互设计"],
        "decision_style": "看重项目创意和设计空间"
    },
    "emma": {
        "user_id": "emma",
        "display_name": "Emma",
        "name": "Emma Li",
        "capabilities": ["产品经理", "需求分析", "用户研究"],
        "location": "上海",
        "availability": "工作日",
        "personality": "逻辑清晰，善于沟通",
        "interests": ["AI产品", "用户增长", "商业模式"],
        "decision_style": "数据驱动，关注用户价值"
    },
    "frank": {
        "user_id": "frank",
        "display_name": "Frank",
        "name": "Frank Wu",
        "capabilities": ["后端开发", "系统架构", "数据库优化"],
        "location": "杭州",
        "availability": "晚上和周末",
        "personality": "稳重务实，技术导向",
        "interests": ["分布式系统", "云原生", "性能优化"],
        "decision_style": "技术可行性优先，不喜欢不靠谱的项目"
    },
    "grace": {
        "user_id": "grace",
        "display_name": "Grace",
        "name": "Grace Huang",
        "capabilities": ["前端开发", "React", "小程序"],
        "location": "深圳",
        "availability": "灵活，需提前沟通",
        "personality": "乐观积极，学习能力强",
        "interests": ["Web3", "新技术", "开源项目"],
        "decision_style": "喜欢尝试新事物，但需要看到学习价值"
    },
    "henry": {
        "user_id": "henry",
        "display_name": "Henry",
        "name": "Henry Zhao",
        "capabilities": ["数据分析", "机器学习", "Python"],
        "location": "北京",
        "availability": "周末",
        "personality": "内敛安静，深度思考",
        "interests": ["数据科学", "量化投资", "算法"],
        "decision_style": "需要看到数据和逻辑支撑"
    },
    "ivy": {
        "user_id": "ivy",
        "display_name": "Ivy",
        "name": "Ivy Sun",
        "capabilities": ["运营推广", "社群管理", "内容创作"],
        "location": "广州",
        "availability": "全职可用",
        "personality": "活泼开朗，善于社交",
        "interests": ["社群运营", "内容营销", "品牌建设"],
        "decision_style": "看重项目影响力和社交价值"
    },
    "jack": {
        "user_id": "jack",
        "display_name": "Jack",
        "name": "Jack Zhou",
        "capabilities": ["投资咨询", "商业规划", "资源对接"],
        "location": "上海",
        "availability": "需要预约",
        "personality": "商业敏锐，资源丰富",
        "interests": ["创业投资", "商业模式", "行业趋势"],
        "decision_style": "看重商业价值和回报潜力"
    }
}


class SecondMeMockService(SecondMeService):
    """
    SecondMe Mock服务

    基于预设档案和简单规则模拟数字分身行为
    """

    def __init__(self, custom_profiles: Dict[str, Dict] = None):
        self.profiles = {**MOCK_PROFILES}
        if custom_profiles:
            self.profiles.update(custom_profiles)

    async def understand_demand(
        self,
        raw_input: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        理解用户需求（Mock实现）

        基于提示词1：需求理解
        将用户的自然语言输入转化为结构化的需求理解结果

        Args:
            raw_input: 用户原始输入
            user_id: 用户ID

        Returns:
            结构化的需求理解结果，包含：
            - surface_demand: 表面需求（用户原话）
            - deep_understanding: 深层理解
                - motivation: 用户动机
                - type: 需求类型
                - keywords: 关键词
                - location: 地点
                - scale: 规模
                - timeline: 时间线
            - uncertainties: 不确定点列表
            - clarifying_questions: 澄清问题列表
            - confidence: 置信度
        """
        logger.info(f"Mock understanding demand: {raw_input[:50]}...")

        # 简单的关键词提取
        keywords = self._extract_keywords(raw_input)

        # 推断需求类型
        demand_type = self._infer_demand_type(raw_input)

        # 提取地点
        location = self._extract_location(raw_input)

        # 提取规模
        scale = self._extract_scale(raw_input)

        # 提取时间线
        timeline = self._extract_timeline(raw_input)

        # 生成不确定点
        uncertainties = self._generate_uncertainties(raw_input)

        # 生成澄清问题
        clarifying_questions = self._generate_clarifying_questions(
            raw_input, demand_type, location, scale, timeline
        )

        return {
            "surface_demand": raw_input,
            "deep_understanding": {
                "motivation": self._generate_motivation(demand_type),
                "type": demand_type,
                "keywords": keywords,
                "location": location,
                "scale": scale,
                "timeline": timeline,
                "resource_requirements": self._infer_resource_requirements(demand_type, scale)
            },
            "uncertainties": uncertainties,
            "clarifying_questions": clarifying_questions,
            "confidence": self._calculate_understanding_confidence(
                location, scale, timeline, len(uncertainties)
            )
        }

    def _extract_scale(self, text: str) -> Optional[Dict[str, Any]]:
        """提取规模信息"""
        import re
        # 提取人数
        people_pattern = r'(\d+)\s*[人个位名]'
        people_match = re.search(people_pattern, text)
        people_count = int(people_match.group(1)) if people_match else None

        # 规模级别
        if people_count:
            if people_count <= 10:
                level = "small"
            elif people_count <= 50:
                level = "medium"
            else:
                level = "large"
        else:
            level = None

        return {
            "people_count": people_count,
            "level": level
        } if people_count else None

    def _extract_timeline(self, text: str) -> Optional[Dict[str, Any]]:
        """提取时间线信息"""
        timeline = {}

        # 时间关键词
        if any(w in text for w in ["紧急", "尽快", "立即", "马上"]):
            timeline["urgency"] = "high"
        elif any(w in text for w in ["下周", "这周", "近期"]):
            timeline["urgency"] = "medium"
        else:
            timeline["urgency"] = "low"

        # 具体日期识别（简化）
        if "周末" in text:
            timeline["preferred_time"] = "weekend"
        elif "工作日" in text:
            timeline["preferred_time"] = "weekday"
        elif "晚上" in text:
            timeline["preferred_time"] = "evening"

        return timeline if timeline else None

    def _infer_resource_requirements(
        self, demand_type: str, scale: Optional[Dict]
    ) -> List[str]:
        """推断资源需求"""
        requirements = []

        type_requirements = {
            "event": ["场地", "时间协调", "活动策划"],
            "design": ["设计能力", "原型工具", "设计评审"],
            "development": ["技术能力", "开发环境", "代码评审"],
            "sharing": ["分享者", "场地/平台", "受众组织"],
            "general": ["资源协调", "沟通协作"]
        }

        requirements.extend(type_requirements.get(demand_type, []))

        if scale and scale.get("level") == "large":
            requirements.append("大规模组织能力")

        return requirements

    def _generate_clarifying_questions(
        self,
        text: str,
        demand_type: str,
        location: Optional[str],
        scale: Optional[Dict],
        timeline: Optional[Dict]
    ) -> List[str]:
        """生成澄清问题"""
        questions = []

        if not location:
            questions.append("活动/项目的地点是线上还是线下？如果线下，在哪个城市？")

        if not scale:
            questions.append("预计参与人数大概是多少？")

        if not timeline or timeline.get("urgency") == "low":
            questions.append("希望在什么时间范围内完成？有截止日期吗？")

        if "预算" not in text and "费用" not in text:
            questions.append("是否有预算限制？")

        if demand_type == "event":
            if "形式" not in text and "方式" not in text:
                questions.append("活动形式有什么偏好吗？（如：工作坊、分享会、圆桌等）")
        elif demand_type == "development":
            if "技术" not in text and "语言" not in text:
                questions.append("有技术栈偏好吗？")

        return questions[:3]  # 最多返回3个问题

    def _calculate_understanding_confidence(
        self,
        location: Optional[str],
        scale: Optional[Dict],
        timeline: Optional[Dict],
        uncertainty_count: int
    ) -> str:
        """计算理解置信度"""
        score = 100

        if not location:
            score -= 20
        if not scale:
            score -= 20
        if not timeline:
            score -= 15
        score -= uncertainty_count * 10

        if score >= 70:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：查找预定义关键词
        keywords = []
        keyword_list = [
            "聚会", "活动", "会议", "分享", "设计", "开发",
            "AI", "技术", "产品", "创业", "社交", "学习"
        ]
        for kw in keyword_list:
            if kw in text:
                keywords.append(kw)
        return keywords

    def _infer_demand_type(self, text: str) -> str:
        """推断需求类型"""
        if any(w in text for w in ["聚会", "活动", "party", "meetup"]):
            return "event"
        elif any(w in text for w in ["设计", "原型", "UI"]):
            return "design"
        elif any(w in text for w in ["开发", "代码", "技术"]):
            return "development"
        elif any(w in text for w in ["分享", "演讲", "培训"]):
            return "sharing"
        else:
            return "general"

    def _extract_location(self, text: str) -> Optional[str]:
        """提取地点"""
        locations = ["北京", "上海", "深圳", "杭州", "广州", "远程", "线上"]
        for loc in locations:
            if loc in text:
                return loc
        return None

    def _generate_motivation(self, demand_type: str) -> str:
        """生成动机分析"""
        motivations = {
            "event": "希望通过活动建立人脉、交流想法",
            "design": "需要专业设计支持来实现产品愿景",
            "development": "需要技术能力来实现功能",
            "sharing": "希望学习新知识或分享经验",
            "general": "寻求资源或能力互补的合作"
        }
        return motivations.get(demand_type, "寻求协作机会")

    def _generate_uncertainties(self, text: str) -> List[str]:
        """生成不确定点"""
        uncertainties = []
        if "时间" not in text and "什么时候" not in text:
            uncertainties.append("具体时间待确定")
        if not self._extract_location(text):
            uncertainties.append("地点待确定")
        if "预算" not in text and "费用" not in text:
            uncertainties.append("预算范围不明确")
        return uncertainties

    async def generate_response(
        self,
        user_id: str,
        demand: Dict[str, Any],
        profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成响应（Mock实现）

        基于提示词3：回应生成
        根据用户档案和需求信息，模拟数字分身的决策和响应

        Args:
            user_id: 用户ID
            demand: 需求信息（包含surface_demand和deep_understanding）
            profile: 用户档案
            context: 可选上下文（如历史交互）

        Returns:
            响应结果，包含：
            - decision: 决定（participate/decline/conditional）
            - contribution: 贡献描述
            - conditions: 条件列表
            - reasoning: 决策理由
            - enthusiasm_level: 热情程度（high/medium/low）
            - suggested_role: 建议角色
            - availability_note: 可用性说明
        """
        logger.info(f"Mock generating response for {user_id}")

        # 获取档案
        full_profile = profile or self.profiles.get(user_id, {})
        capabilities = full_profile.get("capabilities", [])
        personality = full_profile.get("personality", "")
        decision_style = full_profile.get("decision_style", "")
        availability = full_profile.get("availability", "")
        interests = full_profile.get("interests", [])

        # 判断能力匹配
        demand_text = str(demand.get("surface_demand", ""))
        deep = demand.get("deep_understanding", {})
        keywords = deep.get("keywords", [])
        demand_type = deep.get("type", "general")
        resource_requirements = deep.get("resource_requirements", [])

        # 计算匹配度（综合多维度）
        capability_match = self._calculate_match_score(capabilities, demand_text, keywords)
        interest_match = self._calculate_interest_match(interests, keywords, demand_type)
        overall_match = (capability_match * 0.6) + (interest_match * 0.4)

        # 基于档案特征调整决策倾向
        decision_bias = self._get_decision_bias(decision_style)

        # 综合匹配度和决策倾向决定结果
        if overall_match >= 0.7 or (overall_match >= 0.5 and decision_bias > 0):
            decision = "participate"
            enthusiasm_level = "high" if overall_match >= 0.8 else "medium"
            contribution = self._generate_detailed_contribution(
                capabilities, demand_text, resource_requirements
            )
        elif overall_match >= 0.4:
            # 有时参与，有时有条件参与
            if random.random() > 0.3 + decision_bias * 0.1:
                decision = "conditional"
                enthusiasm_level = "medium"
            else:
                decision = "participate"
                enthusiasm_level = "medium"
            contribution = self._generate_detailed_contribution(
                capabilities, demand_text, resource_requirements
            )
        else:
            # 低匹配度
            if random.random() > 0.8 - decision_bias * 0.1:
                decision = "decline"
                enthusiasm_level = "low"
                contribution = ""
            else:
                decision = "conditional"
                enthusiasm_level = "low"
                contribution = "可以提供有限支持"

        # 生成条件
        conditions = []
        if decision == "conditional":
            conditions = self._generate_detailed_conditions(full_profile, deep)

        # 生成建议角色
        suggested_role = self._suggest_role(capabilities, demand_type, resource_requirements)

        # 生成可用性说明
        availability_note = self._generate_availability_note(availability, deep.get("timeline"))

        return {
            "decision": decision,
            "contribution": contribution,
            "conditions": conditions,
            "reasoning": self._generate_detailed_reasoning(
                decision, overall_match, full_profile, demand_type
            ),
            "enthusiasm_level": enthusiasm_level,
            "suggested_role": suggested_role,
            "availability_note": availability_note,
            "match_analysis": {
                "capability_match": round(capability_match, 2),
                "interest_match": round(interest_match, 2),
                "overall_match": round(overall_match, 2)
            }
        }

    def _calculate_interest_match(
        self,
        interests: List[str],
        keywords: List[str],
        demand_type: str
    ) -> float:
        """计算兴趣匹配度"""
        if not interests:
            return 0.3

        score = 0.3
        for interest in interests:
            interest_lower = interest.lower()
            for kw in keywords:
                if kw.lower() in interest_lower or interest_lower in kw.lower():
                    score += 0.15
            # 需求类型匹配
            if demand_type in interest_lower:
                score += 0.1

        return min(score, 1.0)

    def _get_decision_bias(self, decision_style: str) -> float:
        """根据决策风格获取偏好值"""
        if not decision_style:
            return 0

        positive_keywords = ["快速", "积极", "喜欢", "乐于", "热情"]
        negative_keywords = ["谨慎", "严格", "挑剔", "看重"]

        bias = 0
        for kw in positive_keywords:
            if kw in decision_style:
                bias += 0.1
        for kw in negative_keywords:
            if kw in decision_style:
                bias -= 0.1

        return max(-0.3, min(0.3, bias))

    def _generate_detailed_contribution(
        self,
        capabilities: List[str],
        demand_text: str,
        resource_requirements: List[str]
    ) -> str:
        """生成详细的贡献描述"""
        if not capabilities:
            return "愿意提供支持"

        # 找到与需求相关的能力
        relevant_caps = []
        demand_lower = demand_text.lower()
        for cap in capabilities:
            if cap.lower() in demand_lower:
                relevant_caps.append(cap)

        # 找到与资源需求匹配的能力
        for cap in capabilities:
            for req in resource_requirements:
                if cap in req or req in cap:
                    if cap not in relevant_caps:
                        relevant_caps.append(cap)

        if relevant_caps:
            contribution_parts = []
            for cap in relevant_caps[:3]:
                contribution_parts.append(f"提供{cap}支持")
            return "、".join(contribution_parts)
        else:
            return f"可以贡献 {capabilities[0]} 能力，协助完成相关工作"

    def _generate_detailed_conditions(
        self,
        profile: Dict,
        deep_understanding: Dict
    ) -> List[str]:
        """生成详细的条件列表"""
        conditions = []
        availability = profile.get("availability", "")
        decision_style = profile.get("decision_style", "")
        timeline = deep_understanding.get("timeline", {})

        # 基于可用性的条件
        if "工作日" in availability:
            conditions.append("需要安排在工作日进行")
        elif "周末" in availability:
            conditions.append("优先在周末进行")
        elif "需要预约" in availability or "需预约" in availability:
            conditions.append("需要提前至少一周预约时间")

        # 基于决策风格的条件
        if "技术" in decision_style:
            conditions.append("需要明确技术方案和实现路径")
        if "价值" in decision_style or "用户" in decision_style:
            conditions.append("需要了解项目的用户价值和影响范围")
        if "细节" in decision_style:
            conditions.append("需要详细的需求说明和分工文档")

        # 基于时间线的条件
        if timeline and timeline.get("urgency") == "high":
            conditions.append("紧急需求需要确认能投入足够时间")

        # 随机添加一些通用条件
        if random.random() > 0.5:
            conditions.append("需要提前确认具体时间安排")
        if random.random() > 0.7:
            conditions.append("希望能了解其他参与者的背景")

        return conditions[:3]  # 最多返回3个条件

    def _suggest_role(
        self,
        capabilities: List[str],
        demand_type: str,
        resource_requirements: List[str]
    ) -> str:
        """建议角色"""
        if not capabilities:
            return "参与者"

        # 角色映射
        role_mapping = {
            "场地资源": "场地提供者",
            "活动组织": "活动协调员",
            "技术分享": "技术讲师",
            "AI研究": "技术顾问",
            "活动策划": "活动策划",
            "产品经理": "产品负责人",
            "UI设计": "设计师",
            "后端开发": "技术开发",
            "前端开发": "前端开发",
            "运营推广": "运营负责人",
            "社群管理": "社区运营",
            "投资咨询": "商业顾问"
        }

        for cap in capabilities:
            if cap in role_mapping:
                return role_mapping[cap]

        # 基于需求类型建议
        type_roles = {
            "event": "活动参与者",
            "design": "设计支持",
            "development": "技术支持",
            "sharing": "分享参与者",
            "general": "协作伙伴"
        }

        return type_roles.get(demand_type, "参与者")

    def _generate_availability_note(
        self,
        availability: str,
        timeline: Optional[Dict]
    ) -> str:
        """生成可用性说明"""
        notes = []

        if availability:
            notes.append(f"通常{availability}")

        if timeline:
            urgency = timeline.get("urgency", "low")
            if urgency == "high":
                notes.append("紧急需求需要协调时间")
            preferred_time = timeline.get("preferred_time")
            if preferred_time:
                time_map = {
                    "weekend": "周末时间较为灵活",
                    "weekday": "工作日可以安排",
                    "evening": "晚间时间可以参与"
                }
                notes.append(time_map.get(preferred_time, ""))

        return "；".join([n for n in notes if n]) if notes else "时间待协商"

    def _generate_detailed_reasoning(
        self,
        decision: str,
        match_score: float,
        profile: Dict,
        demand_type: str
    ) -> str:
        """生成详细的决策理由"""
        personality = profile.get("personality", "")
        interests = profile.get("interests", [])

        if decision == "participate":
            reasons = []
            if match_score >= 0.7:
                reasons.append("需求与我的能力高度匹配")
            if any(interest for interest in interests if demand_type in interest.lower()):
                reasons.append("这个方向正好是我感兴趣的")
            if personality:
                trait = personality.split("，")[0] if "，" in personality else personality
                reasons.append(f"作为{trait}的人，很愿意参与")
            return "，".join(reasons) if reasons else "愿意参与此次协作"

        elif decision == "conditional":
            return "整体感兴趣，但需要确认一些细节后才能完全投入"

        else:
            return "当前需求与我的能力方向不太匹配，可能无法提供有效帮助"

    def _calculate_match_score(
        self,
        capabilities: List[str],
        demand_text: str,
        keywords: List[str]
    ) -> float:
        """计算能力匹配度"""
        if not capabilities:
            return 0.3  # 基础分

        score = 0.3
        demand_lower = demand_text.lower()

        for cap in capabilities:
            if cap.lower() in demand_lower:
                score += 0.2

        for kw in keywords:
            if any(kw.lower() in cap.lower() for cap in capabilities):
                score += 0.1

        return min(score, 1.0)

    def _generate_contribution(self, capabilities: List[str], demand_text: str) -> str:
        """生成贡献描述"""
        if not capabilities:
            return "愿意提供支持"

        relevant = []
        for cap in capabilities:
            if cap.lower() in demand_text.lower():
                relevant.append(cap)

        if relevant:
            return f"可以提供 {', '.join(relevant)} 方面的支持"
        else:
            return f"可以贡献 {capabilities[0]} 能力"

    def _generate_conditions(self, profile: Dict) -> List[str]:
        """生成条件"""
        conditions = []
        availability = profile.get("availability", "")

        if "工作日" in availability:
            conditions.append("需要安排在工作日")
        elif "周末" in availability:
            conditions.append("优先周末进行")

        if random.random() > 0.5:
            conditions.append("需要提前至少3天通知")

        return conditions

    def _generate_reasoning(
        self,
        decision: str,
        match_score: float,
        profile: Dict
    ) -> str:
        """生成决策理由"""
        personality = profile.get("personality", "")

        if decision == "participate":
            return f"需求与我的能力匹配度较高，{personality.split('，')[0] if personality else '愿意参与'}"
        elif decision == "conditional":
            return "整体感兴趣，但需要确认一些细节"
        else:
            return "目前的需求与我的能力方向不太匹配"

    async def evaluate_proposal(
        self,
        user_id: str,
        proposal: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估方案（Mock实现）"""
        logger.info(f"Mock evaluating proposal for {user_id}")

        full_profile = profile or self.profiles.get(user_id, {})

        # 找到自己在方案中的角色
        my_assignment = None
        agent_id = f"user_agent_{user_id}"
        for assignment in proposal.get("assignments", []):
            if assignment.get("agent_id") == agent_id:
                my_assignment = assignment
                break

        # 基于角色和性格评估
        if my_assignment:
            # 检查角色是否合理
            responsibility = my_assignment.get("responsibility", "")
            capabilities = full_profile.get("capabilities", [])

            if any(cap.lower() in responsibility.lower() for cap in capabilities):
                # 角色匹配
                if random.random() > 0.15:
                    return {
                        "feedback_type": "accept",
                        "adjustment_request": "",
                        "reasoning": "方案合理，角色分配符合我的能力"
                    }
                else:
                    return {
                        "feedback_type": "negotiate",
                        "adjustment_request": "希望能调整一下时间安排",
                        "reasoning": "整体可以，时间上需要协调"
                    }
            else:
                # 角色可能不太匹配
                return {
                    "feedback_type": "negotiate",
                    "adjustment_request": f"希望能调整我的职责，更偏向 {capabilities[0] if capabilities else '我擅长的方向'}",
                    "reasoning": "当前分配的职责与我的专长不太匹配"
                }
        else:
            # 没有分配角色
            return {
                "feedback_type": "accept",
                "adjustment_request": "",
                "reasoning": "方案整体合理"
            }

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        return self.profiles.get(user_id)

    def add_profile(self, user_id: str, profile: Dict[str, Any]):
        """添加用户档案"""
        self.profiles[user_id] = profile

    def list_profiles(self) -> Dict[str, Dict]:
        """列出所有档案"""
        return dict(self.profiles)


# 全局Mock服务实例
secondme_mock_service: Optional[SecondMeMockService] = None


def init_secondme_mock() -> SecondMeMockService:
    """初始化SecondMe Mock服务"""
    global secondme_mock_service
    secondme_mock_service = SecondMeMockService()
    logger.info("SecondMe Mock service initialized with %d profiles", len(secondme_mock_service.profiles))
    return secondme_mock_service


def get_secondme_service() -> Optional[SecondMeMockService]:
    """获取SecondMe服务"""
    return secondme_mock_service


class SimpleRandomMockClient(SecondMeService):
    """
    简单随机 Mock 客户端

    用于压力测试，返回纯随机结果，不依赖 LLM。
    所有响应都是预定义的随机选择，保证快速响应。
    """

    # 预定义的响应模板
    DECISIONS = ["participate", "decline", "conditional"]
    FEEDBACK_TYPES = ["accept", "reject", "negotiate"]
    CONFIDENCE_LEVELS = ["high", "medium", "low"]

    CONTRIBUTION_TEMPLATES = [
        "可以提供技术支持",
        "可以帮忙协调资源",
        "愿意参与讨论",
        "可以分享经验",
        "能够提供部分时间"
    ]

    CONDITION_TEMPLATES = [
        "需要提前确认时间",
        "需要远程参与",
        "希望有明确的分工",
        "需要了解更多细节",
        "时间上需要协调"
    ]

    REASONING_TEMPLATES = [
        "符合我的兴趣方向",
        "时间安排合适",
        "能够发挥我的专长",
        "整体方案合理",
        "期待合作机会"
    ]

    ADJUSTMENT_TEMPLATES = [
        "希望调整时间安排",
        "建议优化分工",
        "需要更多信息",
        "希望明确目标",
        ""
    ]

    def __init__(
        self,
        seed: Optional[int] = None,
        participate_probability: float = 0.6,
        accept_probability: float = 0.7
    ):
        """
        初始化随机 Mock 客户端

        Args:
            seed: 随机种子（用于可重复测试）
            participate_probability: 参与概率 (0-1)
            accept_probability: 接受方案概率 (0-1)
        """
        self._random = random.Random(seed)
        self.participate_probability = participate_probability
        self.accept_probability = accept_probability
        self._profiles = dict(MOCK_PROFILES)
        logger.info(
            f"SimpleRandomMockClient initialized - "
            f"participate_prob={participate_probability}, accept_prob={accept_probability}"
        )

    async def understand_demand(
        self,
        raw_input: str,
        user_id: str
    ) -> Dict[str, Any]:
        """理解用户需求（随机生成）"""
        return {
            "surface_demand": raw_input,
            "deep_understanding": {
                "motivation": self._random.choice([
                    "寻求协作机会",
                    "解决实际问题",
                    "拓展人脉资源",
                    "学习新技能"
                ]),
                "type": self._random.choice(["event", "project", "sharing", "general"]),
                "keywords": self._extract_random_keywords(raw_input),
                "location": self._random.choice(["北京", "上海", "远程", None])
            },
            "uncertainties": self._random.sample([
                "时间待定",
                "地点待定",
                "预算不明",
                "人数不确定",
                "形式待商议"
            ], k=self._random.randint(0, 3)),
            "confidence": self._random.choice(self.CONFIDENCE_LEVELS)
        }

    def _extract_random_keywords(self, text: str) -> List[str]:
        """随机提取关键词"""
        all_keywords = ["AI", "技术", "活动", "分享", "协作", "学习", "创业"]
        found = [kw for kw in all_keywords if kw in text]
        if not found:
            found = self._random.sample(all_keywords, k=self._random.randint(1, 3))
        return found

    async def generate_response(
        self,
        user_id: str,
        demand: Dict[str, Any],
        profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成用户响应（随机生成）"""
        # 基于概率决定是否参与
        rand_val = self._random.random()
        if rand_val < self.participate_probability:
            decision = "participate"
        elif rand_val < self.participate_probability + 0.2:
            decision = "conditional"
        else:
            decision = "decline"

        conditions = []
        if decision == "conditional":
            conditions = self._random.sample(
                self.CONDITION_TEMPLATES,
                k=self._random.randint(1, 2)
            )

        return {
            "decision": decision,
            "contribution": self._random.choice(self.CONTRIBUTION_TEMPLATES) if decision != "decline" else "",
            "conditions": conditions,
            "reasoning": self._random.choice(self.REASONING_TEMPLATES)
        }

    async def evaluate_proposal(
        self,
        user_id: str,
        proposal: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估方案（随机生成）"""
        rand_val = self._random.random()
        if rand_val < self.accept_probability:
            feedback_type = "accept"
            adjustment = ""
        elif rand_val < self.accept_probability + 0.2:
            feedback_type = "negotiate"
            adjustment = self._random.choice(self.ADJUSTMENT_TEMPLATES)
        else:
            feedback_type = "reject"
            adjustment = self._random.choice([
                "方案不太适合我",
                "时间冲突",
                "目标不够明确"
            ])

        return {
            "feedback_type": feedback_type,
            "adjustment_request": adjustment,
            "reasoning": self._random.choice(self.REASONING_TEMPLATES)
        }

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案"""
        return self._profiles.get(user_id)

    def add_profile(self, user_id: str, profile: Dict[str, Any]):
        """添加用户档案"""
        self._profiles[user_id] = profile

    def list_profiles(self) -> Dict[str, Dict]:
        """列出所有档案"""
        return dict(self._profiles)

    def generate_random_profiles(self, count: int = 100) -> Dict[str, Dict[str, Any]]:
        """
        批量生成随机用户档案（用于压力测试）

        Args:
            count: 生成数量

        Returns:
            生成的用户档案字典
        """
        names = ["User"]
        capabilities_pool = [
            "技术开发", "产品设计", "项目管理", "运营推广",
            "数据分析", "内容创作", "资源对接", "活动策划"
        ]
        locations = ["北京", "上海", "深圳", "杭州", "广州", "远程"]
        personalities = [
            "积极主动", "稳重务实", "创意丰富", "逻辑清晰",
            "善于沟通", "技术导向", "注重细节", "快速行动"
        ]

        generated = {}
        for i in range(count):
            user_id = f"stress_user_{i}"
            generated[user_id] = {
                "user_id": user_id,
                "display_name": f"User_{i}",
                "name": f"Stress Test User {i}",
                "capabilities": self._random.sample(
                    capabilities_pool,
                    k=self._random.randint(1, 3)
                ),
                "location": self._random.choice(locations),
                "availability": self._random.choice(["灵活", "工作日", "周末", "需预约"]),
                "personality": self._random.choice(personalities),
                "interests": self._random.sample(
                    ["AI", "技术", "创业", "社交", "学习", "投资"],
                    k=self._random.randint(1, 3)
                ),
                "decision_style": self._random.choice([
                    "快速决策",
                    "谨慎评估",
                    "看重价值",
                    "注重细节"
                ])
            }
            self._profiles[user_id] = generated[user_id]

        logger.info(f"Generated {count} random profiles for stress testing")
        return generated


# 别名，保持命名一致性
MockSecondMeClient = SecondMeMockService
