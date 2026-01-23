"""
LLM服务 - 封装大模型调用

提供统一的LLM调用接口，支持：
- 多模型切换
- 异步调用
- 基础错误处理
- 熔断器机制
- 降级响应
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# 降级预案 - TASK-020
# ============================================================================

class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态，允许请求
    OPEN = "open"          # 熔断状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，允许少量请求测试


@dataclass
class CircuitBreaker:
    """
    熔断器实现

    当连续失败次数达到阈值时，熔断器打开，
    在恢复时间后进入半开状态，允许少量请求测试。
    """
    failure_threshold: int = 3        # 失败阈值
    recovery_timeout: float = 30.0    # 恢复超时（秒）
    half_open_max_calls: int = 1      # 半开状态最大调用数

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    last_failure_time: float = field(default=0.0)
    half_open_calls: int = field(default=0)

    def can_execute(self) -> bool:
        """检查是否可以执行请求"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # 检查是否应该进入半开状态
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker entering HALF_OPEN state")
                return True
            return False

        # HALF_OPEN 状态
        if self.half_open_calls < self.half_open_max_calls:
            return True
        return False

    def record_success(self):
        """记录成功调用"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker CLOSED after successful test")
        self.failure_count = 0

    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN after half-open failure")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )

    def get_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout
        }


# 预设降级响应 - 用于演示场景
FALLBACK_RESPONSES: Dict[str, str] = {
    # 协调器相关
    "coordinator_analyze": '''{
        "analysis": "需求分析完成",
        "key_requirements": ["功能实现", "用户体验", "性能优化"],
        "estimated_participants": 3,
        "complexity": "medium"
    }''',

    "coordinator_plan": '''{
        "plan": "协商计划已生成",
        "phases": ["需求澄清", "方案讨论", "共识达成"],
        "estimated_rounds": 3
    }''',

    # 用户代理相关
    # 响应生成（提示词3）- TASK-T03
    "response_generation": '''{
        "decision": "decline",
        "contribution": "",
        "conditions": [],
        "reasoning": "服务暂时不可用，使用中性响应",
        "decline_reason": "由于系统原因，暂时无法做出决策",
        "confidence": 30,
        "enthusiasm_level": "low",
        "suggested_role": ""
    }''',

    "user_agent_evaluate": '''{
        "evaluation": "方案可接受",
        "score": 0.75,
        "concerns": [],
        "suggestions": ["可以进一步优化细节"]
    }''',

    "user_agent_propose": '''{
        "proposal": "基于当前讨论，建议采用渐进式方案",
        "key_points": ["分阶段实施", "风险可控", "成本适中"],
        "confidence": 0.8
    }''',

    "user_agent_respond": '''{
        "response": "同意该方案",
        "agreement_level": "agree",
        "conditions": []
    }''',

    # 频道管理员相关
    "channel_admin_moderate": '''{
        "action": "continue",
        "summary": "讨论进展顺利",
        "next_speaker": null
    }''',

    # 方案聚合相关
    "proposal_aggregation": '''{
        "summary": "协作方案（降级响应）",
        "objective": "完成协作需求",
        "assignments": [],
        "timeline": {
            "start_date": "待定",
            "end_date": "待定",
            "milestones": [
                {"name": "启动", "date": "待定", "deliverable": "项目启动"}
            ]
        },
        "collaboration_model": {
            "communication_channel": "微信群",
            "meeting_frequency": "每周一次",
            "decision_mechanism": "协商一致"
        },
        "success_criteria": ["需求被满足", "参与者达成共识"],
        "risks": [{"risk": "方案可能需要调整", "probability": "medium", "mitigation": "多轮协商"}],
        "gaps": [],
        "confidence": "low",
        "notes": "此为降级响应，LLM服务暂时不可用"
    }''',

    # 方案调整相关
    "proposal_adjustment": '''{
        "summary": "调整后的协作方案（降级响应）",
        "assignments": [],
        "timeline": {"start_date": "待定", "milestones": []},
        "success_criteria": ["需求被满足"],
        "confidence": "low",
        "adjustment_summary": {
            "round": 2,
            "changes_made": [],
            "requests_addressed": [],
            "requests_declined": [{"request": "所有调整请求", "reason": "LLM服务不可用"}]
        }
    }''',

    # 缺口识别相关（旧格式，保留兼容性）
    "gap_identify": '''{
        "gaps": [],
        "severity": "low",
        "recommendations": ["当前参与者组合可满足需求"]
    }''',

    # 缺口识别降级响应 - 供 GapIdentificationService 使用
    # 返回空数组表示没有发现缺口（这是安全的降级策略）
    "gap_identification": '''[]''',

    # 智能筛选降级响应 - TASK-T02
    "smart_filter": '''{
        "analysis": "基于关键词匹配的降级筛选",
        "candidates": [
            {
                "agent_id": "user_agent_bob",
                "display_name": "Bob",
                "reason": "场地资源丰富",
                "relevance_score": 90,
                "expected_role": "场地提供者"
            },
            {
                "agent_id": "user_agent_alice",
                "display_name": "Alice",
                "reason": "技术分享能力强",
                "relevance_score": 85,
                "expected_role": "技术顾问"
            },
            {
                "agent_id": "user_agent_charlie",
                "display_name": "Charlie",
                "reason": "活动策划经验丰富",
                "relevance_score": 80,
                "expected_role": "活动策划"
            }
        ],
        "coverage": {
            "covered": ["场地", "技术分享", "活动策划"],
            "uncovered": []
        }
    }''',

    # 通用降级
    "default": '''{
        "status": "fallback",
        "message": "服务暂时不可用，使用降级响应"
    }'''
}


class LLMService:
    """
    LLM服务

    封装大模型API调用，支持多种模型。
    当前支持 Anthropic Claude 系列模型。
    """

    def __init__(
        self,
        client=None,
        model: str = "claude-3-sonnet-20240229"
    ):
        """
        初始化LLM服务

        Args:
            client: Anthropic AsyncAnthropic客户端实例
            model: 模型名称
        """
        self.client = client
        self.model = model

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        fallback_key: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> str:
        """
        调用LLM完成

        Args:
            prompt: 用户提示
            system: 系统提示
            fallback_key: 降级响应key（预留给TASK-020）
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数传递给API

        Returns:
            LLM响应文本

        Raises:
            Exception: 当调用失败且没有降级响应时
        """
        if not self.client:
            logger.warning("No LLM client configured")
            return "{}"

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise

    async def complete_with_tools(
        self,
        prompt: str,
        tools: list,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用工具调用LLM

        Args:
            prompt: 用户提示
            tools: 工具定义列表
            system: 系统提示
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            包含响应和工具调用的字典
        """
        if not self.client:
            logger.warning("No LLM client configured")
            return {"content": "", "tool_calls": []}

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                **kwargs
            )

            result = {
                "content": "",
                "tool_calls": []
            }

            for block in response.content:
                if block.type == "text":
                    result["content"] = block.text
                elif block.type == "tool_use":
                    result["tool_calls"].append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })

            return result
        except Exception as e:
            logger.error(f"LLM tool call error: {e}")
            raise

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ):
        """
        流式调用LLM

        Args:
            prompt: 用户提示
            system: 系统提示
            max_tokens: 最大token数
            **kwargs: 其他参数

        Yields:
            响应文本片段
        """
        if not self.client:
            logger.warning("No LLM client configured")
            return

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """
        获取服务状态

        Returns:
            状态字典
        """
        return {
            "configured": self.client is not None,
            "model": self.model
        }


# 全局LLM服务实例
llm_service: Optional[LLMService] = None


def init_llm_service(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None
) -> LLMService:
    """
    初始化LLM服务

    Args:
        api_key: Anthropic API密钥
        model: 模型名称
        base_url: 自定义API基础URL（用于代理服务）

    Returns:
        初始化后的LLMService实例
    """
    global llm_service

    if api_key:
        try:
            import anthropic
            # 支持自定义 base_url（如 omnimaas 代理）
            if base_url:
                client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url)
                logger.info(f"LLM service initialized with custom base_url: {base_url}")
            else:
                client = anthropic.AsyncAnthropic(api_key=api_key)
                logger.info("LLM service initialized with API key")

            llm_service = LLMService(
                client=client,
                model=model or "claude-sonnet-4-5-20250929"
            )
        except ImportError:
            logger.warning("anthropic package not installed")
            llm_service = LLMService()
    else:
        llm_service = LLMService()
        logger.warning("LLM service initialized without API key")

    return llm_service


def get_llm_service() -> Optional[LLMService]:
    """
    获取全局LLM服务实例

    Returns:
        LLMService实例或None
    """
    return llm_service


# ============================================================================
# 带降级能力的 LLM 服务 - TASK-020
# ============================================================================

class LLMServiceWithFallback:
    """
    带降级能力的 LLM 服务

    特性:
    - 熔断器机制: 连续失败后自动熔断
    - 超时控制: 防止长时间等待
    - 降级响应: 熔断或超时时返回预设响应
    - 统计信息: 追踪成功/失败/降级次数
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        timeout: float = 10.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
        fallback_responses: Optional[Dict[str, str]] = None
    ):
        """
        初始化带降级能力的 LLM 服务

        Args:
            llm_service: 底层 LLM 服务实例
            timeout: 请求超时时间（秒）
            circuit_breaker: 熔断器实例
            fallback_responses: 自定义降级响应字典
        """
        self.llm_service = llm_service
        self.timeout = timeout
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.fallback_responses = fallback_responses or FALLBACK_RESPONSES

        # 统计信息
        self.stats = {
            "total_calls": 0,
            "success_count": 0,
            "failure_count": 0,
            "fallback_count": 0,
            "timeout_count": 0,
            "circuit_open_count": 0
        }

    def _get_fallback(self, fallback_key: Optional[str]) -> str:
        """获取降级响应"""
        if fallback_key and fallback_key in self.fallback_responses:
            return self.fallback_responses[fallback_key]
        return self.fallback_responses.get("default", "{}")

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        fallback_key: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any
    ) -> str:
        """
        带降级能力的 LLM 调用

        Args:
            prompt: 用户提示
            system: 系统提示
            fallback_key: 降级响应 key
            max_tokens: 最大 token 数
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            LLM 响应或降级响应
        """
        self.stats["total_calls"] += 1

        # 检查熔断器状态
        if not self.circuit_breaker.can_execute():
            self.stats["circuit_open_count"] += 1
            self.stats["fallback_count"] += 1
            logger.warning(
                f"Circuit breaker OPEN, returning fallback for: {fallback_key}"
            )
            return self._get_fallback(fallback_key)

        # 检查 LLM 服务是否可用
        if not self.llm_service or not self.llm_service.client:
            self.stats["fallback_count"] += 1
            logger.warning("LLM service not configured, returning fallback")
            return self._get_fallback(fallback_key)

        try:
            # 带超时的调用
            result = await asyncio.wait_for(
                self.llm_service.complete(
                    prompt=prompt,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                ),
                timeout=self.timeout
            )
            self.circuit_breaker.record_success()
            self.stats["success_count"] += 1
            return result

        except asyncio.TimeoutError:
            self.stats["timeout_count"] += 1
            self.stats["fallback_count"] += 1
            self.circuit_breaker.record_failure()
            logger.warning(
                f"LLM call timeout ({self.timeout}s), returning fallback"
            )
            return self._get_fallback(fallback_key)

        except Exception as e:
            self.stats["failure_count"] += 1
            self.stats["fallback_count"] += 1
            self.circuit_breaker.record_failure()
            logger.error(f"LLM call failed: {e}, returning fallback")
            return self._get_fallback(fallback_key)

    async def complete_with_tools(
        self,
        prompt: str,
        tools: list,
        system: Optional[str] = None,
        fallback_key: Optional[str] = None,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        带降级能力的工具调用

        Args:
            prompt: 用户提示
            tools: 工具定义列表
            system: 系统提示
            fallback_key: 降级响应 key
            max_tokens: 最大 token 数
            **kwargs: 其他参数

        Returns:
            工具调用结果或降级响应
        """
        self.stats["total_calls"] += 1

        # 检查熔断器状态
        if not self.circuit_breaker.can_execute():
            self.stats["circuit_open_count"] += 1
            self.stats["fallback_count"] += 1
            logger.warning("Circuit breaker OPEN, returning fallback")
            return {"content": self._get_fallback(fallback_key), "tool_calls": []}

        # 检查 LLM 服务是否可用
        if not self.llm_service or not self.llm_service.client:
            self.stats["fallback_count"] += 1
            return {"content": self._get_fallback(fallback_key), "tool_calls": []}

        try:
            result = await asyncio.wait_for(
                self.llm_service.complete_with_tools(
                    prompt=prompt,
                    tools=tools,
                    system=system,
                    max_tokens=max_tokens,
                    **kwargs
                ),
                timeout=self.timeout
            )
            self.circuit_breaker.record_success()
            self.stats["success_count"] += 1
            return result

        except asyncio.TimeoutError:
            self.stats["timeout_count"] += 1
            self.stats["fallback_count"] += 1
            self.circuit_breaker.record_failure()
            logger.warning("LLM tool call timeout, returning fallback")
            return {"content": self._get_fallback(fallback_key), "tool_calls": []}

        except Exception as e:
            self.stats["failure_count"] += 1
            self.stats["fallback_count"] += 1
            self.circuit_breaker.record_failure()
            logger.error(f"LLM tool call failed: {e}, returning fallback")
            return {"content": self._get_fallback(fallback_key), "tool_calls": []}

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "llm_configured": (
                self.llm_service is not None and
                self.llm_service.client is not None
            ),
            "model": (
                self.llm_service.model if self.llm_service else None
            ),
            "timeout": self.timeout,
            "circuit_breaker": self.circuit_breaker.get_status(),
            "stats": self.stats.copy()
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_calls": 0,
            "success_count": 0,
            "failure_count": 0,
            "fallback_count": 0,
            "timeout_count": 0,
            "circuit_open_count": 0
        }

    def reset_circuit_breaker(self):
        """重置熔断器状态"""
        self.circuit_breaker.state = CircuitState.CLOSED
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.half_open_calls = 0
        logger.info("Circuit breaker reset to CLOSED state")


# 全局带降级能力的 LLM 服务实例
llm_service_with_fallback: Optional[LLMServiceWithFallback] = None


def init_llm_service_with_fallback(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 10.0,
    failure_threshold: int = 3,
    recovery_timeout: float = 30.0
) -> LLMServiceWithFallback:
    """
    初始化带降级能力的 LLM 服务

    Args:
        api_key: Anthropic API 密钥
        model: 模型名称
        base_url: 自定义API基础URL
        timeout: 请求超时时间（秒）
        failure_threshold: 熔断器失败阈值
        recovery_timeout: 熔断器恢复超时（秒）

    Returns:
        初始化后的LLMServiceWithFallback实例
    """
    global llm_service_with_fallback

    # 初始化基础 LLM 服务
    base_llm_service = init_llm_service(
        api_key=api_key,
        model=model,
        base_url=base_url
    )

    # 创建熔断器
    circuit_breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )

    # 创建带降级能力的服务
    llm_service_with_fallback = LLMServiceWithFallback(
        llm_service=base_llm_service,
        timeout=timeout,
        circuit_breaker=circuit_breaker
    )

    logger.info(
        f"LLM service with fallback initialized "
        f"(timeout={timeout}s, failure_threshold={failure_threshold})"
    )
    return llm_service_with_fallback


def get_llm_service_with_fallback() -> Optional[LLMServiceWithFallback]:
    """
    获取全局带降级能力的 LLM 服务实例

    Returns:
        LLMServiceWithFallback 实例或 None
    """
    return llm_service_with_fallback
