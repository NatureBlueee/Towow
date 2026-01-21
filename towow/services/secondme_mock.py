"""
SecondMe Mock实现
MVP阶段的模拟数字分身服务
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import random
import logging

from .secondme import SecondMeService

logger = logging.getLogger(__name__)


# 预设的用户档案
MOCK_PROFILES: Dict[str, Dict[str, Any]] = {
    "bob": {
        "user_id": "bob",
        "display_name": "Bob",
        "capabilities": ["场地资源", "活动组织", "会议室"],
        "location": "北京朝阳",
        "availability": "工作日可用",
        "personality": "热情外向，喜欢组织活动",
        "interests": ["AI", "创业", "社交"]
    },
    "alice": {
        "user_id": "alice",
        "display_name": "Alice",
        "capabilities": ["技术分享", "AI研究", "演讲"],
        "location": "北京海淀",
        "availability": "周末优先",
        "personality": "专业认真，乐于分享",
        "interests": ["机器学习", "NLP", "技术布道"]
    },
    "charlie": {
        "user_id": "charlie",
        "display_name": "Charlie",
        "capabilities": ["活动策划", "流程设计", "现场协调"],
        "location": "北京",
        "availability": "灵活",
        "personality": "细心周到，执行力强",
        "interests": ["项目管理", "活动运营", "社区建设"]
    },
    "david": {
        "user_id": "david",
        "display_name": "David",
        "capabilities": ["UI设计", "产品原型", "用户体验"],
        "location": "远程",
        "availability": "按项目排期",
        "personality": "创意丰富，注重细节",
        "interests": ["设计系统", "AI产品", "交互设计"]
    },
    "emma": {
        "user_id": "emma",
        "display_name": "Emma",
        "capabilities": ["产品经理", "需求分析", "用户研究"],
        "location": "上海",
        "availability": "工作日",
        "personality": "逻辑清晰，善于沟通",
        "interests": ["AI产品", "用户增长", "商业模式"]
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
        """理解用户需求（Mock实现）"""
        logger.info(f"Mock understanding demand: {raw_input[:50]}...")

        # 简单的关键词提取
        keywords = self._extract_keywords(raw_input)

        # 推断需求类型
        demand_type = self._infer_demand_type(raw_input)

        # 提取地点
        location = self._extract_location(raw_input)

        return {
            "surface_demand": raw_input,
            "deep_understanding": {
                "motivation": self._generate_motivation(demand_type),
                "type": demand_type,
                "keywords": keywords,
                "location": location
            },
            "uncertainties": self._generate_uncertainties(raw_input),
            "confidence": "medium"
        }

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
        """生成响应（Mock实现）"""
        logger.info(f"Mock generating response for {user_id}")

        # 获取档案
        full_profile = profile or self.profiles.get(user_id, {})
        capabilities = full_profile.get("capabilities", [])

        # 判断能力匹配
        demand_text = str(demand.get("surface_demand", ""))
        deep = demand.get("deep_understanding", {})
        keywords = deep.get("keywords", [])

        # 计算匹配度
        match_score = self._calculate_match_score(capabilities, demand_text, keywords)

        # 基于匹配度和随机因素决策
        if match_score >= 0.7:
            decision = "participate"
            contribution = self._generate_contribution(capabilities, demand_text)
        elif match_score >= 0.4:
            # 有时参与，有时有条件参与
            if random.random() > 0.3:
                decision = "conditional"
                contribution = self._generate_contribution(capabilities, demand_text)
            else:
                decision = "participate"
                contribution = self._generate_contribution(capabilities, demand_text)
        else:
            # 低匹配度，大概率拒绝
            if random.random() > 0.8:
                decision = "decline"
                contribution = ""
            else:
                decision = "conditional"
                contribution = "可以提供有限支持"

        conditions = []
        if decision == "conditional":
            conditions = self._generate_conditions(full_profile)

        return {
            "decision": decision,
            "contribution": contribution,
            "conditions": conditions,
            "reasoning": self._generate_reasoning(decision, match_score, full_profile)
        }

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
