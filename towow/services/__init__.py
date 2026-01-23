"""
ToWow 服务模块

SecondMe 服务层：
- SecondMeService / SecondMeClient: 抽象基类，定义数字分身接口
- RealSecondMeClient: 真实 API 客户端（预留）
- SecondMeMockService / MockSecondMeClient: 基于规则的智能 Mock
- SimpleRandomMockClient: 随机结果 Mock，用于压力测试

LLM 服务层：
- LLMService: 封装大模型调用
- LLMServiceWithFallback: 带降级能力的 LLM 服务
- CircuitBreaker: 熔断器实现

演示模式服务层 (TASK-020)：
- DemoModeService: 演示模式服务
- DemoConfig: 演示模式配置
- DemoScenario: 演示场景枚举

递归子网服务层：
- Gap Types: 缺口类型定义（GapType, Gap, GapAnalysisResult）
- GapIdentificationService: 缺口识别服务
- SubnetManager: 递归子网管理器
"""
from .llm import (
    LLMService,
    init_llm_service,
    get_llm_service,
    llm_service,
    # TASK-020: 降级能力
    CircuitBreaker,
    CircuitState,
    LLMServiceWithFallback,
    FALLBACK_RESPONSES,
    init_llm_service_with_fallback,
    get_llm_service_with_fallback,
    llm_service_with_fallback
)
from .secondme import SecondMeService, SecondMeClient, RealSecondMeClient
from .secondme_mock import (
    SecondMeMockService,
    MockSecondMeClient,
    SimpleRandomMockClient,
    MOCK_PROFILES,
    init_secondme_mock,
    get_secondme_service
)
from .gap_types import (
    GapType,
    GapSeverity,
    Gap,
    GapAnalysisResult
)
from .gap_identification import GapIdentificationService
from .subnet_manager import (
    SubnetStatus,
    SubnetInfo,
    SubnetResult,
    SubnetManager
)
# TASK-020: 演示模式服务
from .demo_mode import (
    DemoModeService,
    DemoConfig,
    DemoScenario,
    DEMO_DEMANDS,
    DEMO_PARTICIPANTS,
    init_demo_service,
    get_demo_service,
    enable_demo_mode,
    disable_demo_mode,
    is_demo_mode
)

# T07: 状态检查与恢复服务
from .state_checker import (
    StateChecker,
    CheckResult,
    StateCheckResult,
    RecoveryAttempt,
    ChannelRecoveryState,
    init_state_checker,
    get_state_checker,
    start_state_checker,
    stop_state_checker
)

__all__ = [
    # LLM 服务
    "LLMService",
    "init_llm_service",
    "get_llm_service",
    "llm_service",
    # LLM 降级能力 (TASK-020)
    "CircuitBreaker",
    "CircuitState",
    "LLMServiceWithFallback",
    "FALLBACK_RESPONSES",
    "init_llm_service_with_fallback",
    "get_llm_service_with_fallback",
    "llm_service_with_fallback",
    # SecondMe 接口
    "SecondMeService",
    "SecondMeClient",
    "RealSecondMeClient",
    # SecondMe Mock 实现
    "SecondMeMockService",
    "MockSecondMeClient",
    "SimpleRandomMockClient",
    "MOCK_PROFILES",
    "init_secondme_mock",
    "get_secondme_service",
    # 缺口类型
    "GapType",
    "GapSeverity",
    "Gap",
    "GapAnalysisResult",
    # 缺口识别服务
    "GapIdentificationService",
    # 子网管理
    "SubnetStatus",
    "SubnetInfo",
    "SubnetResult",
    "SubnetManager",
    # 演示模式服务 (TASK-020)
    "DemoModeService",
    "DemoConfig",
    "DemoScenario",
    "DEMO_DEMANDS",
    "DEMO_PARTICIPANTS",
    "init_demo_service",
    "get_demo_service",
    "enable_demo_mode",
    "disable_demo_mode",
    "is_demo_mode",
    # 状态检查服务 (T07)
    "StateChecker",
    "CheckResult",
    "StateCheckResult",
    "RecoveryAttempt",
    "ChannelRecoveryState",
    "init_state_checker",
    "get_state_checker",
    "start_state_checker",
    "stop_state_checker"
]
