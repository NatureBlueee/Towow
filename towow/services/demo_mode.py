"""
演示模式服务 - TASK-020

为 2000 人现场演示提供稳定可靠的演示体验：
- 预设成功案例
- 加速协商过程
- 模拟 Agent 交互
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DemoScenario(Enum):
    """演示场景"""
    QUICK_CONSENSUS = "quick_consensus"        # 快速达成共识
    MILD_NEGOTIATION = "mild_negotiation"      # 温和协商
    TOUGH_NEGOTIATION = "tough_negotiation"    # 激烈协商（最终成功）
    CUSTOM = "custom"                          # 自定义场景


@dataclass
class DemoConfig:
    """演示模式配置"""
    enabled: bool = False                       # 是否启用演示模式
    scenario: DemoScenario = DemoScenario.QUICK_CONSENSUS
    speed_multiplier: float = 3.0               # 速度倍数（3x 表示 3 倍速）
    auto_success: bool = True                   # 自动成功
    max_rounds: int = 3                         # 最大协商轮数
    simulated_delay_ms: int = 500               # 模拟延迟（毫秒）


# ============================================================================
# 预设演示案例
# ============================================================================

DEMO_DEMANDS: Dict[str, Dict[str, Any]] = {
    "demo_travel": {
        "id": "demo-travel-001",
        "title": "团队团建旅游规划",
        "description": "需要为 20 人团队规划一次 3 天 2 夜的团建旅游",
        "requirements": [
            "预算人均 2000 元以内",
            "目的地距离不超过 3 小时车程",
            "需要包含团队活动",
            "餐饮住宿要求中等偏上"
        ],
        "expected_outcome": "确定目的地、行程安排、预算分配"
    },
    "demo_project": {
        "id": "demo-project-001",
        "title": "新产品功能优先级讨论",
        "description": "讨论 Q2 新产品功能的开发优先级",
        "requirements": [
            "需要平衡用户需求和技术可行性",
            "考虑资源限制",
            "明确 MVP 范围"
        ],
        "expected_outcome": "确定 Q2 功能优先级列表和里程碑"
    },
    "demo_budget": {
        "id": "demo-budget-001",
        "title": "部门年度预算分配",
        "description": "讨论部门年度预算在各项目间的分配",
        "requirements": [
            "总预算 500 万",
            "需要覆盖人力、设备、外包等",
            "预留 10% 应急资金"
        ],
        "expected_outcome": "确定各项目预算配额"
    }
}

DEMO_PARTICIPANTS: Dict[str, Dict[str, Any]] = {
    "alice": {
        "id": "demo-agent-alice",
        "name": "Alice (产品经理)",
        "role": "product_manager",
        "personality": "结果导向，注重用户价值",
        "priorities": ["用户体验", "功能完整性", "市场竞争力"]
    },
    "bob": {
        "id": "demo-agent-bob",
        "name": "Bob (技术负责人)",
        "role": "tech_lead",
        "personality": "务实稳健，关注技术债务",
        "priorities": ["技术可行性", "代码质量", "系统稳定性"]
    },
    "charlie": {
        "id": "demo-agent-charlie",
        "name": "Charlie (财务)",
        "role": "finance",
        "personality": "谨慎保守，成本意识强",
        "priorities": ["成本控制", "ROI", "预算合规"]
    },
    "diana": {
        "id": "demo-agent-diana",
        "name": "Diana (运营)",
        "role": "operations",
        "personality": "灵活务实，注重执行",
        "priorities": ["可执行性", "资源协调", "时间节点"]
    }
}

# 预设的协商对话
DEMO_DIALOGUES: Dict[str, List[Dict[str, Any]]] = {
    "quick_consensus": [
        {
            "speaker": "coordinator",
            "message": "欢迎各位参与本次协商。我们的目标是就该需求达成共识。让我们开始吧。",
            "action": "open_discussion"
        },
        {
            "speaker": "alice",
            "message": "从产品角度来看，这个需求是合理的。我建议我们先明确核心目标。",
            "action": "propose",
            "proposal": {"priority": "high", "approach": "user_centric"}
        },
        {
            "speaker": "bob",
            "message": "技术上可行，但我建议分阶段实施以降低风险。",
            "action": "counter_propose",
            "proposal": {"priority": "high", "approach": "phased_rollout"}
        },
        {
            "speaker": "charlie",
            "message": "预算在可控范围内，我支持分阶段方案。",
            "action": "support",
            "supports": "bob"
        },
        {
            "speaker": "diana",
            "message": "分阶段方案执行性更好，资源调配也更灵活。我同意。",
            "action": "support",
            "supports": "bob"
        },
        {
            "speaker": "alice",
            "message": "综合考虑各方意见，我接受分阶段方案。",
            "action": "accept"
        },
        {
            "speaker": "coordinator",
            "message": "很好！我们已达成共识：采用分阶段实施方案。",
            "action": "conclude",
            "result": "consensus_reached"
        }
    ],
    "mild_negotiation": [
        {
            "speaker": "coordinator",
            "message": "本次协商开始。请各位代表发表意见。",
            "action": "open_discussion"
        },
        {
            "speaker": "alice",
            "message": "我认为应该优先考虑用户需求，建议全力推进。",
            "action": "propose",
            "proposal": {"priority": "critical", "approach": "full_speed"}
        },
        {
            "speaker": "charlie",
            "message": "预算压力较大，建议缩小范围或延期部分功能。",
            "action": "counter_propose",
            "proposal": {"priority": "medium", "approach": "reduced_scope"}
        },
        {
            "speaker": "bob",
            "message": "我提议一个折中方案：核心功能优先，扩展功能视资源情况推进。",
            "action": "mediate",
            "proposal": {"priority": "high", "approach": "core_first"}
        },
        {
            "speaker": "alice",
            "message": "这个折中方案可以接受，前提是核心功能不打折扣。",
            "action": "conditional_accept",
            "condition": "core_features_complete"
        },
        {
            "speaker": "charlie",
            "message": "如果只做核心功能，预算可以支持。同意。",
            "action": "accept"
        },
        {
            "speaker": "diana",
            "message": "执行计划已有，我这边没有问题。",
            "action": "accept"
        },
        {
            "speaker": "coordinator",
            "message": "协商完成！最终方案：核心功能优先，扩展功能视资源推进。",
            "action": "conclude",
            "result": "consensus_reached"
        }
    ],
    "tough_negotiation": [
        {
            "speaker": "coordinator",
            "message": "本次协商涉及多方利益，请各位充分表达。",
            "action": "open_discussion"
        },
        {
            "speaker": "alice",
            "message": "用户反馈强烈，这个功能必须在本季度上线！",
            "action": "propose",
            "proposal": {"priority": "critical", "deadline": "this_quarter"}
        },
        {
            "speaker": "bob",
            "message": "技术团队资源紧张，本季度根本做不完。",
            "action": "reject",
            "reason": "resource_constraint"
        },
        {
            "speaker": "charlie",
            "message": "如果要加速，需要额外预算招外包，但这会超支。",
            "action": "flag_issue",
            "issue": "budget_overrun"
        },
        {
            "speaker": "coordinator",
            "message": "看来存在分歧，让我们探索可能的解决方案。",
            "action": "facilitate"
        },
        {
            "speaker": "diana",
            "message": "能否从其他项目借调人手，先完成核心部分？",
            "action": "suggest_alternative"
        },
        {
            "speaker": "bob",
            "message": "如果能借调 2 人，核心功能可以本季度完成。",
            "action": "conditional_accept",
            "condition": "additional_resources"
        },
        {
            "speaker": "alice",
            "message": "核心功能本季度上，其余下季度，可以接受。",
            "action": "revise_proposal"
        },
        {
            "speaker": "charlie",
            "message": "临时借调不需要额外预算，财务可以支持。",
            "action": "accept"
        },
        {
            "speaker": "coordinator",
            "message": "经过充分讨论，我们达成共识：借调资源完成核心功能本季度上线。",
            "action": "conclude",
            "result": "consensus_reached"
        }
    ]
}


class DemoModeService:
    """
    演示模式服务

    特性：
    - 预设成功案例
    - 加速协商过程
    - 模拟 Agent 交互
    - 可配置的演示场景
    """

    def __init__(self, config: Optional[DemoConfig] = None):
        """
        初始化演示模式服务

        Args:
            config: 演示模式配置
        """
        self.config = config or DemoConfig()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._event_callbacks: List[Callable] = []

        # 统计信息
        self.stats = {
            "total_demos": 0,
            "successful_demos": 0,
            "active_sessions": 0
        }

    @property
    def enabled(self) -> bool:
        """是否启用演示模式"""
        return self.config.enabled

    def enable(self, scenario: Optional[DemoScenario] = None):
        """
        启用演示模式

        Args:
            scenario: 演示场景
        """
        self.config.enabled = True
        if scenario:
            self.config.scenario = scenario
        logger.info(f"Demo mode ENABLED (scenario={self.config.scenario.value})")

    def disable(self):
        """禁用演示模式"""
        self.config.enabled = False
        logger.info("Demo mode DISABLED")

    def toggle(self) -> bool:
        """
        切换演示模式

        Returns:
            切换后的状态
        """
        if self.config.enabled:
            self.disable()
        else:
            self.enable()
        return self.config.enabled

    def register_event_callback(self, callback: Callable):
        """注册事件回调"""
        self._event_callbacks.append(callback)

    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """发送事件"""
        for callback in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    async def start_demo_session(
        self,
        demand_key: str = "demo_travel",
        scenario: Optional[DemoScenario] = None
    ) -> Dict[str, Any]:
        """
        启动演示会话

        Args:
            demand_key: 预设需求 key
            scenario: 演示场景

        Returns:
            会话信息
        """
        session_id = str(uuid.uuid4())[:8]
        scenario = scenario or self.config.scenario

        # 获取预设需求
        demand = DEMO_DEMANDS.get(demand_key, DEMO_DEMANDS["demo_travel"])

        # 创建会话
        session = {
            "id": session_id,
            "demand": demand,
            "scenario": scenario.value,
            "participants": list(DEMO_PARTICIPANTS.values()),
            "status": "active",
            "current_round": 0,
            "max_rounds": self.config.max_rounds,
            "dialogues": [],
            "start_time": time.time(),
            "speed_multiplier": self.config.speed_multiplier
        }

        self._active_sessions[session_id] = session
        self.stats["total_demos"] += 1
        self.stats["active_sessions"] = len(self._active_sessions)

        logger.info(f"Demo session started: {session_id} (scenario={scenario.value})")

        await self._emit_event("demo_session_started", {
            "session_id": session_id,
            "demand": demand,
            "scenario": scenario.value
        })

        return session

    async def run_demo_negotiation(
        self,
        session_id: str,
        on_dialogue: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        运行演示协商

        Args:
            session_id: 会话 ID
            on_dialogue: 每条对话的回调

        Returns:
            协商结果
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        scenario_key = session["scenario"]
        dialogues = DEMO_DIALOGUES.get(scenario_key, DEMO_DIALOGUES["quick_consensus"])

        # 计算延迟
        base_delay = self.config.simulated_delay_ms / 1000.0
        delay = base_delay / self.config.speed_multiplier

        result_dialogue = None

        for i, dialogue in enumerate(dialogues):
            # 添加到会话记录
            dialogue_record = {
                "round": i + 1,
                "timestamp": time.time(),
                **dialogue
            }
            session["dialogues"].append(dialogue_record)

            # 发送事件
            await self._emit_event("demo_dialogue", {
                "session_id": session_id,
                "dialogue": dialogue_record
            })

            # 回调
            if on_dialogue:
                if asyncio.iscoroutinefunction(on_dialogue):
                    await on_dialogue(dialogue_record)
                else:
                    on_dialogue(dialogue_record)

            # 模拟延迟
            await asyncio.sleep(delay)

            # 检查是否是结论
            if dialogue.get("action") == "conclude":
                result_dialogue = dialogue
                break

        # 更新会话状态
        session["status"] = "completed"
        session["end_time"] = time.time()
        session["result"] = result_dialogue.get("result") if result_dialogue else "unknown"

        self.stats["successful_demos"] += 1
        self.stats["active_sessions"] = len([
            s for s in self._active_sessions.values()
            if s["status"] == "active"
        ])

        await self._emit_event("demo_session_completed", {
            "session_id": session_id,
            "result": session["result"],
            "duration": session["end_time"] - session["start_time"]
        })

        logger.info(f"Demo session completed: {session_id} (result={session['result']})")

        return {
            "session_id": session_id,
            "result": session["result"],
            "dialogue_count": len(session["dialogues"]),
            "duration": session["end_time"] - session["start_time"]
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        return self._active_sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        return list(self._active_sessions.values())

    def get_available_demands(self) -> Dict[str, Dict[str, Any]]:
        """获取可用的预设需求"""
        return DEMO_DEMANDS.copy()

    def get_available_scenarios(self) -> List[str]:
        """获取可用的演示场景"""
        return [s.value for s in DemoScenario]

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "enabled": self.config.enabled,
            "scenario": self.config.scenario.value,
            "speed_multiplier": self.config.speed_multiplier,
            "auto_success": self.config.auto_success,
            "stats": self.stats.copy(),
            "available_demands": list(DEMO_DEMANDS.keys()),
            "available_scenarios": self.get_available_scenarios()
        }


# 全局演示模式服务实例
_demo_service: Optional[DemoModeService] = None


def init_demo_service(config: Optional[DemoConfig] = None) -> DemoModeService:
    """
    初始化演示模式服务

    Args:
        config: 演示模式配置

    Returns:
        初始化后的 DemoModeService 实例
    """
    global _demo_service
    _demo_service = DemoModeService(config)
    logger.info("Demo mode service initialized")
    return _demo_service


def get_demo_service() -> Optional[DemoModeService]:
    """获取全局演示模式服务实例"""
    return _demo_service


def enable_demo_mode(scenario: Optional[str] = None):
    """
    快捷方式：启用演示模式

    Args:
        scenario: 场景名称
    """
    global _demo_service
    if not _demo_service:
        _demo_service = DemoModeService()

    if scenario:
        try:
            scene = DemoScenario(scenario)
            _demo_service.enable(scene)
        except ValueError:
            _demo_service.enable()
    else:
        _demo_service.enable()


def disable_demo_mode():
    """快捷方式：禁用演示模式"""
    if _demo_service:
        _demo_service.disable()


def is_demo_mode() -> bool:
    """检查是否处于演示模式"""
    return _demo_service.enabled if _demo_service else False
