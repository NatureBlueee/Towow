"""
SecondMe服务接口
定义数字分身服务的标准接口

SecondMe 是用户的数字分身代理，负责：
1. 理解用户需求 (understand_demand)
2. 代表用户生成响应 (generate_response)
3. 评估/反馈协作方案 (evaluate_proposal / generate_feedback)
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SecondMeService(ABC):
    """
    SecondMe服务抽象基类

    定义数字分身服务需要实现的接口。
    别名: SecondMeClient (保持向后兼容)
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

    async def generate_feedback(
        self,
        user_id: str,
        proposal: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成方案反馈 (evaluate_proposal 的别名)

        为保持接口一致性，提供此别名方法。
        默认实现调用 evaluate_proposal。

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
        return await self.evaluate_proposal(user_id, proposal, profile)

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


# 别名，保持向后兼容
SecondMeClient = SecondMeService


class RealSecondMeClient(SecondMeService):
    """
    真实 SecondMe API 客户端（预留）

    用于对接真实的 SecondMe 服务。
    当前为占位实现，待 SecondMe API 就绪后实现。
    """

    def __init__(
        self,
        api_base_url: str = "https://api.secondme.io",
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        初始化真实客户端

        Args:
            api_base_url: SecondMe API 基础 URL
            api_key: API 密钥
            timeout: 请求超时时间（秒）
        """
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.timeout = timeout
        logger.info(f"RealSecondMeClient initialized (placeholder) - base_url: {api_base_url}")

    async def understand_demand(
        self,
        raw_input: str,
        user_id: str
    ) -> Dict[str, Any]:
        """理解用户需求 - 预留实现"""
        # TODO: 实现真实 API 调用
        # POST /api/v1/demand/understand
        # Body: {"raw_input": raw_input, "user_id": user_id}
        raise NotImplementedError(
            "RealSecondMeClient.understand_demand not implemented. "
            "Please use MockSecondMeClient for development."
        )

    async def generate_response(
        self,
        user_id: str,
        demand: Dict[str, Any],
        profile: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成用户响应 - 预留实现"""
        # TODO: 实现真实 API 调用
        # POST /api/v1/response/generate
        # Body: {"user_id": user_id, "demand": demand, "profile": profile, "context": context}
        raise NotImplementedError(
            "RealSecondMeClient.generate_response not implemented. "
            "Please use MockSecondMeClient for development."
        )

    async def evaluate_proposal(
        self,
        user_id: str,
        proposal: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估协作方案 - 预留实现"""
        # TODO: 实现真实 API 调用
        # POST /api/v1/proposal/evaluate
        # Body: {"user_id": user_id, "proposal": proposal, "profile": profile}
        raise NotImplementedError(
            "RealSecondMeClient.evaluate_proposal not implemented. "
            "Please use MockSecondMeClient for development."
        )

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户档案 - 预留实现"""
        # TODO: 实现真实 API 调用
        # GET /api/v1/users/{user_id}/profile
        raise NotImplementedError(
            "RealSecondMeClient.get_user_profile not implemented. "
            "Please use MockSecondMeClient for development."
        )
