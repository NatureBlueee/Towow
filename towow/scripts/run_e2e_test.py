#!/usr/bin/env python3
"""
端到端测试运行脚本

可从命令行运行的 E2E 测试，支持：
- 运行全部场景或指定场景
- 详细日志输出
- 验证各阶段结果
- 生成测试报告

使用方法:
    python -m scripts.run_e2e_test                    # 运行全部场景
    python -m scripts.run_e2e_test --scenario A       # 只运行场景A
    python -m scripts.run_e2e_test --verbose          # 详细输出
    python -m scripts.run_e2e_test --report report.json  # 生成报告
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.secondme_mock import SecondMeMockService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("e2e_test")


# ============== 数据结构 ==============

@dataclass
class ScenarioConfig:
    """场景配置"""
    name: str
    key: str
    demand_input: str
    expected_capabilities: List[str]
    description: str


@dataclass
class StageResult:
    """阶段结果"""
    stage: str
    success: bool
    duration_ms: float
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ScenarioResult:
    """场景测试结果"""
    scenario: str
    success: bool
    stages: List[StageResult] = field(default_factory=list)
    total_duration_ms: float = 0
    candidates_count: int = 0
    participants_count: int = 0
    proposal_generated: bool = False
    feedback_summary: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TestReport:
    """测试报告"""
    timestamp: str
    total_scenarios: int
    passed: int
    failed: int
    total_duration_ms: float
    results: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""


# ============== 预定义场景 ==============

SCENARIOS = {
    "A": ScenarioConfig(
        name="场景A-活动组织",
        key="A",
        demand_input="我想在北京办一场50人的AI主题聚会",
        expected_capabilities=["场地", "活动", "AI", "策划"],
        description="测试活动组织类需求的处理流程"
    ),
    "B": ScenarioConfig(
        name="场景B-资源对接",
        key="B",
        demand_input="我需要找一个懂AI的设计师帮我做产品原型",
        expected_capabilities=["设计", "原型", "UI", "AI"],
        description="测试资源对接类需求的处理流程"
    ),
    "C": ScenarioConfig(
        name="场景C-模糊需求",
        key="C",
        demand_input="最近压力很大，想找人聊聊",
        expected_capabilities=[],
        description="测试模糊/情感类需求的处理流程"
    ),
}


# ============== 核心测试类 ==============

class E2ETestRunner:
    """端到端测试运行器"""

    def __init__(self, verbose: bool = False):
        """
        初始化测试运行器

        Args:
            verbose: 是否输出详细日志
        """
        self.verbose = verbose
        self.mock_agents: List[Dict[str, Any]] = []
        self.secondme: Optional[SecondMeMockService] = None

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    def load_mock_data(self) -> bool:
        """加载 Mock Agent 数据"""
        data_path = project_root / "data" / "mock_agents.json"

        if data_path.exists():
            with open(data_path, "r", encoding="utf-8") as f:
                self.mock_agents = json.load(f)
            logger.info(f"Loaded {len(self.mock_agents)} mock agents from {data_path}")
            return True

        # 尝试生成数据
        try:
            from scripts.generate_mock_agents import generate_mock_agents
            self.mock_agents = generate_mock_agents(count=100, seed=42)
            logger.info(f"Generated {len(self.mock_agents)} mock agents")
            return True
        except Exception as e:
            logger.error(f"Failed to load or generate mock agents: {e}")
            return False

    def init_services(self):
        """初始化服务"""
        self.secondme = SecondMeMockService()

        # 注册所有 Mock Agent profiles
        for agent in self.mock_agents:
            user_id = agent.get("user_id")
            if user_id:
                self.secondme.add_profile(user_id, agent)

        logger.info(f"Initialized SecondMe with {len(self.secondme.profiles)} profiles")

    async def run_scenario(self, config: ScenarioConfig) -> ScenarioResult:
        """
        运行单个测试场景

        Args:
            config: 场景配置

        Returns:
            场景测试结果
        """
        result = ScenarioResult(
            scenario=config.name,
            success=False
        )

        start_time = time.time()

        try:
            # Stage 1: 需求理解
            stage1 = await self._stage_understand_demand(config.demand_input)
            result.stages.append(stage1)
            if not stage1.success:
                result.error = f"需求理解失败: {stage1.error}"
                return result

            understanding = stage1.data

            # Stage 2: 智能筛选
            stage2 = await self._stage_smart_filter(understanding)
            result.stages.append(stage2)
            if not stage2.success:
                result.error = f"智能筛选失败: {stage2.error}"
                return result

            candidates = stage2.data.get("candidates", [])
            result.candidates_count = len(candidates)

            # 验证期望能力
            if config.expected_capabilities:
                self._log_capability_coverage(candidates, config.expected_capabilities)

            # Stage 3: 收集响应
            stage3 = await self._stage_collect_responses(understanding, candidates)
            result.stages.append(stage3)
            if not stage3.success:
                result.error = f"响应收集失败: {stage3.error}"
                return result

            participants = stage3.data.get("participants", [])
            result.participants_count = len(participants)

            if not participants:
                result.error = "没有人愿意参与"
                return result

            # Stage 4: 方案聚合
            stage4 = await self._stage_aggregate_proposal(understanding, participants)
            result.stages.append(stage4)
            if not stage4.success:
                result.error = f"方案聚合失败: {stage4.error}"
                return result

            proposal = stage4.data.get("proposal", {})
            result.proposal_generated = bool(proposal)

            # Stage 5: 收集反馈
            stage5 = await self._stage_collect_feedback(proposal, participants)
            result.stages.append(stage5)
            result.feedback_summary = stage5.data.get("feedback_summary", {})

            # 判断整体成功
            result.success = self._evaluate_success(result)

        except Exception as e:
            logger.error(f"Scenario {config.name} failed with exception: {e}")
            result.error = str(e)
            result.success = False

        result.total_duration_ms = (time.time() - start_time) * 1000
        return result

    async def _stage_understand_demand(self, demand_input: str) -> StageResult:
        """阶段1: 需求理解"""
        stage = "需求理解"
        start = time.time()

        try:
            understanding = await self.secondme.understand_demand(
                raw_input=demand_input,
                user_id="test_user"
            )

            if self.verbose:
                logger.debug(f"Understanding result: {json.dumps(understanding, ensure_ascii=False, indent=2)}")

            return StageResult(
                stage=stage,
                success=True,
                duration_ms=(time.time() - start) * 1000,
                data=understanding
            )
        except Exception as e:
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    async def _stage_smart_filter(self, understanding: Dict[str, Any]) -> StageResult:
        """阶段2: 智能筛选"""
        stage = "智能筛选"
        start = time.time()

        try:
            candidates = self._smart_filter(understanding)

            if self.verbose:
                logger.debug(f"Found {len(candidates)} candidates")
                for c in candidates[:5]:
                    logger.debug(f"  - {c.get('display_name')}: {c.get('reason', '')[:50]}")

            return StageResult(
                stage=stage,
                success=len(candidates) > 0,
                duration_ms=(time.time() - start) * 1000,
                data={"candidates": candidates}
            )
        except Exception as e:
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    def _smart_filter(self, understanding: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行智能筛选"""
        surface_demand = understanding.get("surface_demand", "")
        deep = understanding.get("deep_understanding", {})
        keywords = deep.get("keywords", [])
        location = deep.get("location")
        resource_requirements = deep.get("resource_requirements", [])
        demand_type = deep.get("type", "general")

        candidates = []

        # 检测是否为模糊/情感类需求
        is_vague_demand = (
            demand_type == "general" or
            len(keywords) == 0 or
            any(word in surface_demand for word in ["聊聊", "压力", "烦", "累", "无聊", "想"])
        )

        # 针对模糊需求的特殊关键词
        soft_skills_keywords = ["沟通", "社交", "助人", "倾听", "心理", "咨询", "运营", "社群"]

        for agent in self.mock_agents:
            score = 0
            reasons = []

            capabilities = agent.get("capabilities", [])
            interests = agent.get("interests", [])
            personality = agent.get("personality", "")
            decision_style = agent.get("decision_style", "")

            # 能力匹配
            for cap in capabilities:
                cap_lower = cap.lower()
                for kw in keywords:
                    if kw.lower() in cap_lower or cap_lower in kw.lower():
                        score += 20
                        reasons.append(f"能力'{cap}'匹配'{kw}'")
                        break

                for req in resource_requirements:
                    if cap in req or req in cap:
                        score += 15
                        reasons.append(f"能力'{cap}'满足'{req}'")
                        break

                if cap_lower in surface_demand.lower():
                    score += 10
                    reasons.append(f"能力'{cap}'匹配需求")

                # 模糊需求: 软技能加分
                if is_vague_demand:
                    for soft in soft_skills_keywords:
                        if soft in cap_lower:
                            score += 15
                            reasons.append(f"具备'{cap}'软技能")
                            break

            # 兴趣匹配
            for interest in interests:
                interest_lower = interest.lower()
                for kw in keywords:
                    if kw.lower() in interest_lower or interest_lower in kw.lower():
                        score += 10
                        reasons.append(f"兴趣'{interest}'匹配")
                        break

                # 模糊需求: 社交类兴趣加分
                if is_vague_demand:
                    if any(word in interest_lower for word in ["社交", "社群", "分享"]):
                        score += 10
                        reasons.append(f"有'{interest}'兴趣")

            # 性格匹配 (对模糊需求特别重要)
            if is_vague_demand:
                # 外向、善于沟通的人更适合聊天
                positive_traits = ["沟通", "外向", "乐于", "热情", "善于", "积极", "助人", "分享"]
                for trait in positive_traits:
                    if trait in personality or trait in decision_style:
                        score += 10
                        reasons.append(f"性格适合: {personality[:15]}...")
                        break

            # 地点匹配
            agent_location = agent.get("location", "")
            if location and agent_location:
                if location in agent_location or agent_location in location:
                    score += 15
                    reasons.append(f"地点匹配: {agent_location}")
                elif agent_location == "远程":
                    score += 5

            # 对于模糊需求，降低门槛
            threshold = 10 if is_vague_demand else 20

            if score >= threshold:
                candidates.append({
                    "agent_id": f"user_agent_{agent.get('user_id', '')}",
                    "user_id": agent.get("user_id"),
                    "display_name": agent.get("display_name"),
                    "name": agent.get("name"),
                    "capabilities": capabilities,
                    "location": agent_location,
                    "relevance_score": score,
                    "reason": "; ".join(reasons[:3]) if reasons else "综合匹配",
                    "profile": agent
                })

        candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        return candidates[:12]

    async def _stage_collect_responses(
        self,
        understanding: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> StageResult:
        """阶段3: 收集响应"""
        stage = "响应收集"
        start = time.time()

        try:
            responses = []
            for candidate in candidates:
                profile = candidate.get("profile", {})
                user_id = candidate.get("user_id", "")

                response = await self.secondme.generate_response(
                    user_id=user_id,
                    demand=understanding,
                    profile=profile,
                    context={"filter_reason": candidate.get("reason", "")}
                )
                response["agent_id"] = candidate.get("agent_id")
                response["user_id"] = user_id
                response["display_name"] = candidate.get("display_name")
                response["profile"] = profile
                responses.append(response)

            participants = [
                r for r in responses
                if r.get("decision") in ("participate", "conditional")
            ]

            if self.verbose:
                logger.debug(f"Responses: {len(responses)} total, {len(participants)} participants")
                for r in responses:
                    logger.debug(f"  - {r.get('display_name')}: {r.get('decision')}")

            return StageResult(
                stage=stage,
                success=True,
                duration_ms=(time.time() - start) * 1000,
                data={
                    "responses": responses,
                    "participants": participants
                }
            )
        except Exception as e:
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    async def _stage_aggregate_proposal(
        self,
        understanding: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> StageResult:
        """阶段4: 方案聚合"""
        stage = "方案聚合"
        start = time.time()

        try:
            surface_demand = understanding.get("surface_demand", "")

            assignments = []
            for i, p in enumerate(participants[:8]):
                role = p.get("suggested_role", f"参与者-{i+1}")
                assignments.append({
                    "agent_id": p.get("agent_id"),
                    "display_name": p.get("display_name"),
                    "role": role,
                    "responsibility": p.get("contribution", "待分配")
                })

            proposal = {
                "summary": f"关于'{surface_demand[:30]}...'的协作方案" if len(surface_demand) > 30 else f"关于'{surface_demand}'的协作方案",
                "assignments": assignments,
                "participants_count": len(assignments),
                "timeline": "待定",
                "success_criteria": ["需求满足", "达成共识"],
                "confidence": "medium"
            }

            if self.verbose:
                logger.debug(f"Proposal: {proposal.get('summary')}")
                logger.debug(f"Assignments: {len(assignments)}")

            return StageResult(
                stage=stage,
                success=True,
                duration_ms=(time.time() - start) * 1000,
                data={"proposal": proposal}
            )
        except Exception as e:
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    async def _stage_collect_feedback(
        self,
        proposal: Dict[str, Any],
        participants: List[Dict[str, Any]]
    ) -> StageResult:
        """阶段5: 收集反馈"""
        stage = "反馈收集"
        start = time.time()

        try:
            feedback_counts = {"accept": 0, "reject": 0, "negotiate": 0}

            for participant in participants:
                user_id = participant.get("user_id", "")
                profile = participant.get("profile", {})

                feedback = await self.secondme.evaluate_proposal(
                    user_id=user_id,
                    proposal=proposal,
                    profile=profile
                )

                feedback_type = feedback.get("feedback_type", "accept")
                if feedback_type in feedback_counts:
                    feedback_counts[feedback_type] += 1

            if self.verbose:
                logger.debug(f"Feedback summary: {feedback_counts}")

            return StageResult(
                stage=stage,
                success=True,
                duration_ms=(time.time() - start) * 1000,
                data={"feedback_summary": feedback_counts}
            )
        except Exception as e:
            return StageResult(
                stage=stage,
                success=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    def _evaluate_success(self, result: ScenarioResult) -> bool:
        """评估场景是否成功"""
        # 需要有候选人
        if result.candidates_count < 3:
            return False

        # 需要有参与者
        if result.participants_count == 0:
            return False

        # 需要生成方案
        if not result.proposal_generated:
            return False

        # 需要有反馈
        if not result.feedback_summary:
            return False

        return True

    def _log_capability_coverage(
        self,
        candidates: List[Dict[str, Any]],
        expected: List[str]
    ):
        """记录能力覆盖情况"""
        found = set()
        for c in candidates:
            for cap in c.get("capabilities", []):
                for exp in expected:
                    if exp.lower() in cap.lower() or cap.lower() in exp.lower():
                        found.add(exp)

        coverage = len(found) / len(expected) if expected else 1.0
        logger.info(f"Capability coverage: {len(found)}/{len(expected)} ({coverage:.0%})")
        logger.info(f"  Expected: {expected}")
        logger.info(f"  Found: {list(found)}")


def print_result(result: ScenarioResult):
    """打印场景结果"""
    status = "PASS" if result.success else "FAIL"
    color = "\033[92m" if result.success else "\033[91m"
    reset = "\033[0m"

    print("\n" + "=" * 70)
    print(f"{color}[{status}]{reset} {result.scenario}")
    print("=" * 70)
    print(f"总耗时: {result.total_duration_ms:.2f}ms")
    print(f"候选人数: {result.candidates_count}")
    print(f"参与者数: {result.participants_count}")
    print(f"方案生成: {'是' if result.proposal_generated else '否'}")
    print(f"反馈汇总: {result.feedback_summary}")

    if result.error:
        print(f"错误: {result.error}")

    print("\n阶段详情:")
    for stage in result.stages:
        s_status = "OK" if stage.success else "FAIL"
        s_color = "\033[92m" if stage.success else "\033[91m"
        print(f"  {s_color}[{s_status}]{reset} {stage.stage}: {stage.duration_ms:.2f}ms")
        if stage.error:
            print(f"       Error: {stage.error}")

    print("=" * 70)


def generate_report(results: List[ScenarioResult]) -> TestReport:
    """生成测试报告"""
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    total_duration = sum(r.total_duration_ms for r in results)

    report = TestReport(
        timestamp=datetime.utcnow().isoformat(),
        total_scenarios=len(results),
        passed=passed,
        failed=failed,
        total_duration_ms=total_duration,
        results=[],
        summary=f"通过 {passed}/{len(results)} 场景"
    )

    for r in results:
        report.results.append({
            "scenario": r.scenario,
            "success": r.success,
            "duration_ms": r.total_duration_ms,
            "candidates_count": r.candidates_count,
            "participants_count": r.participants_count,
            "proposal_generated": r.proposal_generated,
            "feedback_summary": r.feedback_summary,
            "error": r.error,
            "stages": [
                {
                    "stage": s.stage,
                    "success": s.success,
                    "duration_ms": s.duration_ms,
                    "error": s.error
                }
                for s in r.stages
            ]
        })

    return report


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="运行 ToWow 端到端测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m scripts.run_e2e_test                     # 运行全部场景
  python -m scripts.run_e2e_test --scenario A        # 只运行场景A
  python -m scripts.run_e2e_test --scenario A B      # 运行场景A和B
  python -m scripts.run_e2e_test --verbose           # 详细输出
  python -m scripts.run_e2e_test --report report.json  # 生成报告

场景说明:
  A - 活动组织: 我想在北京办一场50人的AI主题聚会
  B - 资源对接: 我需要找一个懂AI的设计师帮我做产品原型
  C - 模糊需求: 最近压力很大，想找人聊聊
        """
    )

    parser.add_argument(
        "--scenario", "-s",
        nargs="*",
        choices=["A", "B", "C"],
        help="指定要运行的场景 (默认全部)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    parser.add_argument(
        "--report", "-r",
        type=str,
        help="生成 JSON 报告文件"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="只输出结果汇总"
    )

    args = parser.parse_args()

    # 选择场景
    scenario_keys = args.scenario if args.scenario else ["A", "B", "C"]
    scenarios_to_run = [SCENARIOS[k] for k in scenario_keys if k in SCENARIOS]

    if not scenarios_to_run:
        print("没有有效的场景")
        return 1

    # 初始化
    print("\n" + "=" * 70)
    print("ToWow 端到端测试")
    print("=" * 70)
    print(f"场景: {', '.join(s.name for s in scenarios_to_run)}")

    runner = E2ETestRunner(verbose=args.verbose)

    print("\n加载 Mock Agent 数据...")
    if not runner.load_mock_data():
        print("无法加载 Mock Agent 数据")
        return 1

    print("初始化服务...")
    runner.init_services()

    # 运行测试
    results = []
    for config in scenarios_to_run:
        print(f"\n运行: {config.name}")
        print(f"描述: {config.description}")
        print(f"输入: {config.demand_input}")

        result = await runner.run_scenario(config)
        results.append(result)

        if not args.quiet:
            print_result(result)

    # 汇总
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed

    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    for r in results:
        status = "\033[92mPASS\033[0m" if r.success else "\033[91mFAIL\033[0m"
        print(f"[{status}] {r.scenario}: {r.total_duration_ms:.0f}ms")

    print("-" * 70)
    total_color = "\033[92m" if passed == len(results) else "\033[93m" if passed > 0 else "\033[91m"
    print(f"{total_color}总计: {passed}/{len(results)} 通过\033[0m")
    print("=" * 70)

    # 生成报告
    if args.report:
        report = generate_report(results)
        report_path = Path(args.report)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)
        print(f"\n报告已生成: {report_path}")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
