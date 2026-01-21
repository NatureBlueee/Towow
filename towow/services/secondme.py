"""
SecondMe服务接口
定义数字分身服务的标准接口
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class SecondMeService(ABC):
    """
    SecondMe服务抽象基类

    定义数字分身服务需要实现的接口
    """

    @abstractmethod
    async def understand_demand(
        self,
        raw_input: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        理解用户需求

        Args:
            raw_input: 原始需求输入
            user_id: 用户ID

        Returns:
            {
                "surface_demand": "表面需求",
                "deep_understanding": {"motivation": "...", ...},
                "uncertainties": ["不确定点1", ...],
                "confidence": "high/medium/low"
            }
        """
        pass

    @abstractmethod
    async def generate_response(
        self,
        user_id: str,
        demand: Dict[str, Any],
        profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成用户对需求的响应

        Args:
            user_id: 用户ID
            demand: 需求信息
            profile: 用户档案
            context: 上下文信息

        Returns:
            {
                "decision": "participate/decline/conditional",
                "contribution": "贡献说明",
                "conditions": ["条件1", ...],
                "reasoning": "决策理由"
            }
        """
        pass

    @abstractmethod
    async def evaluate_proposal(
        self,
        user_id: str,
        proposal: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        评估协作方案

        Args:
            user_id: 用户ID
            proposal: 协作方案
            profile: 用户档案

        Returns:
            {
                "feedback_type": "accept/reject/negotiate",
                "adjustment_request": "调整请求",
                "reasoning": "评估理由"
            }
        """
        pass

    @abstractmethod
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户档案

        Args:
            user_id: 用户ID

        Returns:
            用户档案字典，或None
        """
        pass
