"""
Subnet Manager - ToWow 递归子网管理器

负责管理递归子网的创建、执行、超时控制和结果整合。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable
from uuid import uuid4

from .gap_types import Gap, GapAnalysisResult
from .gap_identification import GapIdentificationService

logger = logging.getLogger(__name__)


class SubnetStatus(Enum):
    """子网状态枚举"""
    PENDING = "pending"          # 等待创建
    CREATED = "created"          # 已创建
    RUNNING = "running"          # 运行中
    COMPLETED = "completed"      # 已完成
    TIMEOUT = "timeout"          # 超时
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


@dataclass
class SubnetInfo:
    """
    子网信息数据类

    Attributes:
        subnet_id: 子网唯一标识
        parent_channel_id: 父 Channel ID
        parent_demand_id: 父需求 ID
        gap_id: 触发该子网的缺口 ID
        sub_demand: 子需求内容
        recursion_depth: 当前递归深度
        status: 子网状态
        channel_id: 子网对应的 Channel ID（创建后填充）
        result: 子网执行结果
        created_at: 创建时间
        started_at: 开始执行时间
        completed_at: 完成时间
        timeout_seconds: 超时时间（秒）
        metadata: 额外元数据
    """
    subnet_id: str
    parent_channel_id: str
    parent_demand_id: str
    gap_id: str
    sub_demand: Dict[str, Any]
    recursion_depth: int
    status: SubnetStatus = SubnetStatus.PENDING
    channel_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    timeout_seconds: int = 180  # 默认 180 秒超时
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "subnet_id": self.subnet_id,
            "parent_channel_id": self.parent_channel_id,
            "parent_demand_id": self.parent_demand_id,
            "gap_id": self.gap_id,
            "sub_demand": self.sub_demand,
            "recursion_depth": self.recursion_depth,
            "status": self.status.value,
            "channel_id": self.channel_id,
            "result": self.result,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata
        }

    def is_active(self) -> bool:
        """检查子网是否活跃"""
        return self.status in (SubnetStatus.PENDING, SubnetStatus.CREATED, SubnetStatus.RUNNING)

    def is_finished(self) -> bool:
        """检查子网是否已结束"""
        return self.status in (
            SubnetStatus.COMPLETED, SubnetStatus.TIMEOUT,
            SubnetStatus.FAILED, SubnetStatus.CANCELLED
        )


@dataclass
class SubnetResult:
    """
    子网执行结果

    Attributes:
        subnet_id: 子网 ID
        success: 是否成功
        proposal: 生成的方案（成功时）
        participants: 参与者列表
        error: 错误信息（失败时）
        duration_seconds: 执行时长
    """
    subnet_id: str
    success: bool
    proposal: Optional[Dict[str, Any]] = None
    participants: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "subnet_id": self.subnet_id,
            "success": self.success,
            "proposal": self.proposal,
            "participants": self.participants,
            "error": self.error,
            "duration_seconds": self.duration_seconds
        }


# 子网创建回调类型
SubnetCreator = Callable[[Dict[str, Any], str, int], Awaitable[str]]


class SubnetManager:
    """
    子网管理器

    负责：
    1. 管理子网生命周期
    2. 控制递归深度
    3. 处理超时
    4. 整合子网结果
    """

    # 配置常量
    MAX_RECURSION_DEPTH = 2       # 最大递归深度
    MAX_SUBNETS_PER_LAYER = 3     # 单层最大子网数
    DEFAULT_TIMEOUT = 180         # 默认超时时间（秒）

    def __init__(
        self,
        gap_service: Optional[GapIdentificationService] = None,
        subnet_creator: Optional[SubnetCreator] = None,
        max_depth: int = MAX_RECURSION_DEPTH,
        max_subnets: int = MAX_SUBNETS_PER_LAYER,
        default_timeout: int = DEFAULT_TIMEOUT
    ):
        """
        初始化子网管理器

        Args:
            gap_service: 缺口识别服务
            subnet_creator: 子网创建回调函数
            max_depth: 最大递归深度
            max_subnets: 单层最大子网数
            default_timeout: 默认超时时间
        """
        self.gap_service = gap_service or GapIdentificationService()
        self.subnet_creator = subnet_creator
        self.max_depth = max_depth
        self.max_subnets = max_subnets
        self.default_timeout = default_timeout

        # 子网存储
        self._subnets: Dict[str, SubnetInfo] = {}
        # 父子关系映射
        self._parent_children: Dict[str, List[str]] = {}
        # 超时任务
        self._timeout_tasks: Dict[str, asyncio.Task] = {}
        # 事件发布回调
        self._event_publisher: Optional[Callable[[str, Dict], Awaitable[None]]] = None

        self._logger = logger

    def set_event_publisher(
        self,
        publisher: Callable[[str, Dict], Awaitable[None]]
    ) -> None:
        """设置事件发布回调"""
        self._event_publisher = publisher

    def set_subnet_creator(self, creator: SubnetCreator) -> None:
        """设置子网创建回调"""
        self.subnet_creator = creator

    async def process_gaps(
        self,
        analysis_result: GapAnalysisResult,
        recursion_depth: int = 0
    ) -> List[SubnetInfo]:
        """
        处理缺口，创建必要的子网

        Args:
            analysis_result: 缺口分析结果
            recursion_depth: 当前递归深度

        Returns:
            创建的子网信息列表
        """
        self._logger.info(
            f"Processing gaps for channel {analysis_result.channel_id}, "
            f"depth={recursion_depth}"
        )

        # 检查是否应该触发子网
        if not self.gap_service.should_trigger_subnet(
            analysis_result, recursion_depth, self.max_depth
        ):
            self._logger.info("No subnet triggered")
            return []

        # 获取子网需求
        sub_demands = self.gap_service.get_subnet_demands(
            analysis_result, self.max_subnets
        )

        if not sub_demands:
            self._logger.info("No sub-demands to process")
            return []

        # 创建子网
        created_subnets: List[SubnetInfo] = []

        for sub_demand in sub_demands:
            subnet = await self._create_subnet(
                parent_channel_id=analysis_result.channel_id,
                parent_demand_id=analysis_result.demand_id,
                gap_id=sub_demand["gap_id"],
                sub_demand=sub_demand,
                recursion_depth=recursion_depth + 1
            )
            if subnet:
                created_subnets.append(subnet)

        self._logger.info(f"Created {len(created_subnets)} subnets")

        # 发布事件
        if self._event_publisher and created_subnets:
            await self._event_publisher("towow.subnet.batch_created", {
                "parent_channel_id": analysis_result.channel_id,
                "parent_demand_id": analysis_result.demand_id,
                "subnet_count": len(created_subnets),
                "subnet_ids": [s.subnet_id for s in created_subnets],
                "recursion_depth": recursion_depth + 1
            })

        return created_subnets

    async def _create_subnet(
        self,
        parent_channel_id: str,
        parent_demand_id: str,
        gap_id: str,
        sub_demand: Dict[str, Any],
        recursion_depth: int
    ) -> Optional[SubnetInfo]:
        """
        创建单个子网

        Args:
            parent_channel_id: 父 Channel ID
            parent_demand_id: 父需求 ID
            gap_id: 缺口 ID
            sub_demand: 子需求内容
            recursion_depth: 递归深度

        Returns:
            创建的子网信息，失败返回 None
        """
        subnet_id = f"subnet-{uuid4().hex[:8]}"

        subnet = SubnetInfo(
            subnet_id=subnet_id,
            parent_channel_id=parent_channel_id,
            parent_demand_id=parent_demand_id,
            gap_id=gap_id,
            sub_demand=sub_demand,
            recursion_depth=recursion_depth,
            timeout_seconds=self.default_timeout
        )

        # 存储子网
        self._subnets[subnet_id] = subnet

        # 记录父子关系
        if parent_channel_id not in self._parent_children:
            self._parent_children[parent_channel_id] = []
        self._parent_children[parent_channel_id].append(subnet_id)

        self._logger.info(
            f"Created subnet {subnet_id} for gap {gap_id}, depth={recursion_depth}"
        )

        # 发布创建事件
        if self._event_publisher:
            await self._event_publisher("towow.subnet.created", {
                "subnet_id": subnet_id,
                "parent_channel_id": parent_channel_id,
                "gap_id": gap_id,
                "recursion_depth": recursion_depth
            })

        # 如果有创建器，立即启动子网
        if self.subnet_creator:
            await self._start_subnet(subnet)

        return subnet

    async def _start_subnet(self, subnet: SubnetInfo) -> None:
        """
        启动子网执行

        Args:
            subnet: 子网信息
        """
        try:
            subnet.status = SubnetStatus.CREATED
            subnet.started_at = datetime.utcnow().isoformat()

            # 调用创建器创建实际的 Channel
            channel_id = await self.subnet_creator(
                subnet.sub_demand,
                subnet.parent_channel_id,
                subnet.recursion_depth
            )

            subnet.channel_id = channel_id
            subnet.status = SubnetStatus.RUNNING

            self._logger.info(
                f"Subnet {subnet.subnet_id} started with channel {channel_id}"
            )

            # 启动超时监控
            self._start_timeout_monitor(subnet)

            # 发布启动事件
            if self._event_publisher:
                await self._event_publisher("towow.subnet.started", {
                    "subnet_id": subnet.subnet_id,
                    "channel_id": channel_id,
                    "timeout_seconds": subnet.timeout_seconds
                })

        except Exception as e:
            self._logger.error(f"Failed to start subnet {subnet.subnet_id}: {e}")
            subnet.status = SubnetStatus.FAILED
            subnet.result = {"error": str(e)}
            subnet.completed_at = datetime.utcnow().isoformat()

    def _start_timeout_monitor(self, subnet: SubnetInfo) -> None:
        """启动超时监控"""
        async def timeout_handler():
            await asyncio.sleep(subnet.timeout_seconds)
            if subnet.is_active():
                await self._handle_timeout(subnet)

        task = asyncio.create_task(timeout_handler())
        self._timeout_tasks[subnet.subnet_id] = task

    async def _handle_timeout(self, subnet: SubnetInfo) -> None:
        """处理子网超时"""
        if not subnet.is_active():
            return

        self._logger.warning(
            f"Subnet {subnet.subnet_id} timed out after {subnet.timeout_seconds}s"
        )

        subnet.status = SubnetStatus.TIMEOUT
        subnet.completed_at = datetime.utcnow().isoformat()
        subnet.result = {
            "error": "timeout",
            "message": f"Subnet timed out after {subnet.timeout_seconds} seconds"
        }

        # 发布超时事件
        if self._event_publisher:
            await self._event_publisher("towow.subnet.timeout", {
                "subnet_id": subnet.subnet_id,
                "channel_id": subnet.channel_id,
                "timeout_seconds": subnet.timeout_seconds
            })

        # 检查父 Channel 是否所有子网都已完成
        await self._check_parent_completion(subnet.parent_channel_id)

    async def handle_subnet_completed(
        self,
        channel_id: str,
        success: bool,
        proposal: Optional[Dict[str, Any]] = None,
        participants: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> Optional[SubnetResult]:
        """
        处理子网完成

        Args:
            channel_id: 子网 Channel ID
            success: 是否成功
            proposal: 生成的方案
            participants: 参与者列表
            error: 错误信息

        Returns:
            子网执行结果
        """
        # 查找对应的子网
        subnet = self._find_subnet_by_channel(channel_id)
        if not subnet:
            self._logger.warning(f"No subnet found for channel {channel_id}")
            return None

        if subnet.is_finished():
            self._logger.warning(f"Subnet {subnet.subnet_id} already finished")
            return None

        # 取消超时任务
        if subnet.subnet_id in self._timeout_tasks:
            self._timeout_tasks[subnet.subnet_id].cancel()
            del self._timeout_tasks[subnet.subnet_id]

        # 更新子网状态
        subnet.status = SubnetStatus.COMPLETED if success else SubnetStatus.FAILED
        subnet.completed_at = datetime.utcnow().isoformat()
        subnet.result = {
            "success": success,
            "proposal": proposal,
            "participants": participants or [],
            "error": error
        }

        # 计算执行时长
        duration = 0.0
        if subnet.started_at:
            start = datetime.fromisoformat(subnet.started_at)
            end = datetime.fromisoformat(subnet.completed_at)
            duration = (end - start).total_seconds()

        result = SubnetResult(
            subnet_id=subnet.subnet_id,
            success=success,
            proposal=proposal,
            participants=participants or [],
            error=error,
            duration_seconds=duration
        )

        self._logger.info(
            f"Subnet {subnet.subnet_id} completed: success={success}, duration={duration:.1f}s"
        )

        # 发布完成事件
        if self._event_publisher:
            await self._event_publisher("towow.subnet.completed", {
                "subnet_id": subnet.subnet_id,
                "channel_id": channel_id,
                "success": success,
                "duration_seconds": duration
            })

        # 检查父 Channel 是否所有子网都已完成
        await self._check_parent_completion(subnet.parent_channel_id)

        return result

    def _find_subnet_by_channel(self, channel_id: str) -> Optional[SubnetInfo]:
        """根据 Channel ID 查找子网"""
        for subnet in self._subnets.values():
            if subnet.channel_id == channel_id:
                return subnet
        return None

    async def _check_parent_completion(self, parent_channel_id: str) -> None:
        """检查父 Channel 的所有子网是否都已完成"""
        children = self._parent_children.get(parent_channel_id, [])
        if not children:
            return

        all_finished = all(
            self._subnets[sid].is_finished()
            for sid in children
            if sid in self._subnets
        )

        if all_finished:
            self._logger.info(
                f"All subnets for parent {parent_channel_id} completed"
            )

            # 发布所有子网完成事件
            if self._event_publisher:
                results = [
                    self._subnets[sid].result
                    for sid in children
                    if sid in self._subnets
                ]
                await self._event_publisher("towow.subnet.all_completed", {
                    "parent_channel_id": parent_channel_id,
                    "subnet_count": len(children),
                    "results": results
                })

    def integrate_subnet_results(
        self,
        parent_channel_id: str,
        parent_proposal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        整合子网结果到父方案

        Args:
            parent_channel_id: 父 Channel ID
            parent_proposal: 父方案

        Returns:
            整合后的方案
        """
        children = self._parent_children.get(parent_channel_id, [])
        if not children:
            return parent_proposal

        # 收集成功的子网结果
        successful_results = []
        failed_count = 0

        for subnet_id in children:
            subnet = self._subnets.get(subnet_id)
            if not subnet:
                continue

            if subnet.status == SubnetStatus.COMPLETED and subnet.result:
                result = subnet.result
                if result.get("success") and result.get("proposal"):
                    successful_results.append({
                        "subnet_id": subnet_id,
                        "gap_id": subnet.gap_id,
                        "proposal": result["proposal"],
                        "participants": result.get("participants", [])
                    })
            else:
                failed_count += 1

        # 整合到父方案
        integrated = dict(parent_proposal)

        # 添加子网整合信息
        integrated["subnet_integration"] = {
            "total_subnets": len(children),
            "successful": len(successful_results),
            "failed": failed_count,
            "integrated_at": datetime.utcnow().isoformat()
        }

        # 整合子方案的分配
        if successful_results:
            parent_assignments = integrated.get("assignments", [])

            for sub_result in successful_results:
                sub_proposal = sub_result["proposal"]
                sub_assignments = sub_proposal.get("assignments", [])

                # 标记为子网来源
                for assignment in sub_assignments:
                    assignment["source"] = "subnet"
                    assignment["subnet_id"] = sub_result["subnet_id"]
                    assignment["gap_id"] = sub_result["gap_id"]

                parent_assignments.extend(sub_assignments)

            integrated["assignments"] = parent_assignments

            # 合并参与者
            all_participants = set()
            for sub_result in successful_results:
                all_participants.update(sub_result.get("participants", []))

            if "subnet_participants" not in integrated:
                integrated["subnet_participants"] = []
            integrated["subnet_participants"].extend(list(all_participants))

        self._logger.info(
            f"Integrated {len(successful_results)} subnet results into parent proposal"
        )

        return integrated

    def get_subnet(self, subnet_id: str) -> Optional[SubnetInfo]:
        """获取子网信息"""
        return self._subnets.get(subnet_id)

    def get_subnets_by_parent(self, parent_channel_id: str) -> List[SubnetInfo]:
        """获取父 Channel 下的所有子网"""
        children = self._parent_children.get(parent_channel_id, [])
        return [
            self._subnets[sid]
            for sid in children
            if sid in self._subnets
        ]

    def get_active_subnets(self) -> List[SubnetInfo]:
        """获取所有活跃的子网"""
        return [s for s in self._subnets.values() if s.is_active()]

    def get_all_subnets(self) -> List[SubnetInfo]:
        """获取所有子网"""
        return list(self._subnets.values())

    async def cancel_subnet(self, subnet_id: str, reason: str = "manual") -> bool:
        """
        取消子网

        Args:
            subnet_id: 子网 ID
            reason: 取消原因

        Returns:
            是否成功取消
        """
        subnet = self._subnets.get(subnet_id)
        if not subnet:
            return False

        if subnet.is_finished():
            return False

        # 取消超时任务
        if subnet_id in self._timeout_tasks:
            self._timeout_tasks[subnet_id].cancel()
            del self._timeout_tasks[subnet_id]

        subnet.status = SubnetStatus.CANCELLED
        subnet.completed_at = datetime.utcnow().isoformat()
        subnet.result = {"cancelled": True, "reason": reason}

        self._logger.info(f"Subnet {subnet_id} cancelled: {reason}")

        # 发布取消事件
        if self._event_publisher:
            await self._event_publisher("towow.subnet.cancelled", {
                "subnet_id": subnet_id,
                "reason": reason
            })

        return True

    async def cleanup(self) -> None:
        """清理资源"""
        # 取消所有超时任务
        for task in self._timeout_tasks.values():
            if not task.done():
                task.cancel()
        self._timeout_tasks.clear()

        self._logger.info("SubnetManager cleaned up")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self._subnets)
        by_status = {}
        by_depth = {}

        for subnet in self._subnets.values():
            status = subnet.status.value
            by_status[status] = by_status.get(status, 0) + 1

            depth = subnet.recursion_depth
            by_depth[depth] = by_depth.get(depth, 0) + 1

        return {
            "total_subnets": total,
            "active_subnets": len(self.get_active_subnets()),
            "by_status": by_status,
            "by_depth": by_depth,
            "max_depth_configured": self.max_depth,
            "max_subnets_per_layer": self.max_subnets
        }
