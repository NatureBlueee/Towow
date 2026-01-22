"""
Demand API Router

Handles demand submission and status queries.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from events.recorder import event_recorder

logger = logging.getLogger(__name__)

# 存储活跃任务的集合
_active_tasks: Set[asyncio.Task] = set()


def _task_done_callback(task: asyncio.Task):
    """任务完成回调，处理异常和清理"""
    _active_tasks.discard(task)
    if task.cancelled():
        logger.info(f"任务 {task.get_name()} 已取消")
    elif task.exception():
        logger.error(f"任务 {task.get_name()} 执行失败: {task.exception()}")

router = APIRouter(prefix="/api/v1/demand", tags=["demand"])


class DemandSubmitRequest(BaseModel):
    """Request model for demand submission."""
    raw_input: str
    user_id: Optional[str] = "anonymous"


class DemandSubmitResponse(BaseModel):
    """Response model for demand submission."""
    demand_id: str
    channel_id: str
    status: str
    understanding: Dict[str, Any]


# In-memory demand storage
_demands: Dict[str, Dict] = {}


@router.post("/submit", response_model=DemandSubmitResponse)
async def submit_demand(request: DemandSubmitRequest):
    """
    Submit a new demand.

    POST /api/v1/demand/submit

    Args:
        request: Demand submission request with raw_input and optional user_id

    Returns:
        Demand ID, channel ID, status, and initial understanding
    """
    try:
        # Generate demand_id
        demand_id = f"d-{uuid4().hex[:8]}"
        channel_id = f"collab-{demand_id[2:]}"

        # Store demand
        _demands[demand_id] = {
            "demand_id": demand_id,
            "channel_id": channel_id,
            "raw_input": request.raw_input,
            "user_id": request.user_id,
            "status": "processing",
            "created_at": datetime.utcnow().isoformat()
        }

        # Simple demand understanding (MVP stage)
        understanding = {
            "surface_demand": request.raw_input,
            "confidence": "high"
        }

        # Record demand understood event
        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.demand.understood",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "demand_id": demand_id,
                "channel_id": channel_id,
                "surface_demand": understanding["surface_demand"],
                "confidence": understanding["confidence"]
            }
        })

        # Trigger mock negotiation flow asynchronously
        task = asyncio.create_task(
            trigger_mock_negotiation(demand_id, channel_id, request.raw_input),
            name=f"negotiation-{demand_id}"
        )
        task.add_done_callback(_task_done_callback)
        _active_tasks.add(task)

        return DemandSubmitResponse(
            demand_id=demand_id,
            channel_id=channel_id,
            status="processing",
            understanding=understanding
        )

    except Exception as e:
        logger.error(f"提交需求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def trigger_mock_negotiation(demand_id: str, channel_id: str, raw_input: str):
    """
    Trigger mock negotiation flow with rich event sequence.

    In MVP stage, simulates the full negotiation flow with complete events:
    - Filter candidates
    - Collect responses (accept/decline with reasons)
    - Agent withdrawal
    - Bargaining events
    - Proposal distribution
    - Finalization/Failure

    Args:
        demand_id: Demand ID
        channel_id: Channel ID
        raw_input: Original demand text
    """
    try:
        # 候选人列表（更丰富的信息）
        candidates = [
            {
                "agent_id": "user_agent_bob",
                "display_name": "Bob",
                "reason": "场地资源",
                "capabilities": ["场地资源", "活动组织"]
            },
            {
                "agent_id": "user_agent_alice",
                "display_name": "Alice",
                "reason": "技术分享",
                "capabilities": ["技术分享", "AI研究"]
            },
            {
                "agent_id": "user_agent_charlie",
                "display_name": "Charlie",
                "reason": "活动策划",
                "capabilities": ["活动策划", "流程设计"]
            },
            {
                "agent_id": "user_agent_david",
                "display_name": "David",
                "reason": "UI设计",
                "capabilities": ["UI设计", "产品原型"]
            },
            {
                "agent_id": "user_agent_emma",
                "display_name": "Emma",
                "reason": "产品管理",
                "capabilities": ["产品经理", "需求分析"]
            },
        ]

        # === 阶段1: 筛选完成 ===
        await asyncio.sleep(2)

        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.filter.completed",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "demand_id": demand_id,
                "channel_id": channel_id,
                "candidates": [
                    {"agent_id": c["agent_id"], "display_name": c["display_name"], "reason": c["reason"]}
                    for c in candidates
                ],
                "total_candidates": len(candidates)
            }
        })

        # === 阶段2: 收集响应 ===
        await asyncio.sleep(1)

        # 模拟不同的响应：部分接受、部分拒绝、部分有条件
        responses = [
            # Bob: 接受
            {
                "agent_id": "user_agent_bob",
                "display_name": "Bob",
                "decision": "participate",
                "contribution": "我可以提供30人的会议室，还有投影设备和茶歇",
                "reasoning": "这个活动正好是我擅长的领域，很乐意参与！",
                "decline_reason": ""
            },
            # Alice: 接受
            {
                "agent_id": "user_agent_alice",
                "display_name": "Alice",
                "decision": "participate",
                "contribution": "我可以做一个30分钟的AI技术分享",
                "reasoning": "AI分享是我的专长，很高兴有这个机会",
                "decline_reason": ""
            },
            # Charlie: 有条件接受
            {
                "agent_id": "user_agent_charlie",
                "display_name": "Charlie",
                "decision": "conditional",
                "contribution": "可以负责活动流程设计和现场协调",
                "reasoning": "整体感兴趣，但需要确认时间安排",
                "conditions": ["需要提前一周确定具体时间", "希望能了解其他参与者背景"],
                "decline_reason": ""
            },
            # David: 拒绝（带理由）
            {
                "agent_id": "user_agent_david",
                "display_name": "David",
                "decision": "decline",
                "contribution": "",
                "reasoning": "当前需求与我的能力方向不太匹配",
                "decline_reason": "感谢邀请，但这段时间实在抽不开身。下个月有个重要项目上线，每天都在加班。如果之后还有类似活动，请一定再叫上我！"
            },
            # Emma: 拒绝（带理由）
            {
                "agent_id": "user_agent_emma",
                "display_name": "Emma",
                "decision": "decline",
                "contribution": "",
                "reasoning": "需求与我的能力不太匹配",
                "decline_reason": "谢谢邀请，但我觉得自己可能不是最合适的人选。这个方向不太是我的强项，我更擅长产品管理方面的事情。"
            },
        ]

        for resp in responses:
            await asyncio.sleep(0.8)
            await event_recorder.record({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": "towow.offer.submitted",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "channel_id": channel_id,
                    "demand_id": demand_id,
                    "agent_id": resp["agent_id"],
                    "display_name": resp["display_name"],
                    "decision": resp["decision"],
                    "contribution": resp["contribution"],
                    "reasoning": resp["reasoning"],
                    "decline_reason": resp.get("decline_reason", ""),
                    "conditions": resp.get("conditions", []),
                    "round": 1
                }
            })

        # === 阶段3: 生成初步方案 ===
        await asyncio.sleep(1.5)

        summary_text = raw_input[:30] + "..." if len(raw_input) > 30 else raw_input
        proposal = {
            "summary": f"关于'{summary_text}'的协作方案",
            "objective": "组织一次高质量的技术交流活动",
            "assignments": [
                {
                    "agent_id": "user_agent_bob",
                    "display_name": "Bob",
                    "role": "场地提供者",
                    "responsibility": "提供30人会议室，负责茶歇和设备"
                },
                {
                    "agent_id": "user_agent_alice",
                    "display_name": "Alice",
                    "role": "技术讲师",
                    "responsibility": "30分钟AI技术分享"
                },
                {
                    "agent_id": "user_agent_charlie",
                    "display_name": "Charlie",
                    "role": "活动策划",
                    "responsibility": "活动流程设计和现场协调"
                },
            ],
            "timeline": {
                "start_date": "待定",
                "milestones": [
                    {"name": "方案确认", "date": "本周内"},
                    {"name": "活动执行", "date": "下周末"}
                ]
            },
            "confidence": "high"
        }

        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.proposal.distributed",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "channel_id": channel_id,
                "demand_id": demand_id,
                "proposal": proposal,
                "participants": ["user_agent_bob", "user_agent_alice", "user_agent_charlie"],
                "round": 1
            }
        })

        # === 阶段4: 讨价还价 ===
        await asyncio.sleep(1)

        # Charlie 提出角色调整请求
        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.negotiation.bargain",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "channel_id": channel_id,
                "agent_id": "user_agent_charlie",
                "display_name": "Charlie",
                "bargain_type": "role_change",
                "content": "我觉得我更适合担任主持人而不是只做流程设计，这样能更好地协调现场",
                "round": 1
            }
        })

        await asyncio.sleep(0.8)

        # Alice 提出时间调整请求
        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.negotiation.bargain",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "channel_id": channel_id,
                "agent_id": "user_agent_alice",
                "display_name": "Alice",
                "bargain_type": "condition",
                "content": "分享时长能否延长到45分钟？30分钟太紧凑了，很多内容讲不完",
                "round": 1
            }
        })

        # === 阶段5: 模拟一个 Agent 中途退出 ===
        await asyncio.sleep(1)

        # 随机决定是否有 agent 退出（50%概率）
        import random
        if random.random() < 0.3:  # 30% 概率有人退出
            await event_recorder.record({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": "towow.agent.withdrawn",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "channel_id": channel_id,
                    "agent_id": "user_agent_charlie",
                    "display_name": "Charlie",
                    "reason": "非常抱歉，公司那边突然有个紧急项目，需要我全力投入。真的很对不起大家。",
                    "round": 1,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

            # 更新方案，移除退出的参与者
            proposal["assignments"] = [
                a for a in proposal["assignments"]
                if a["agent_id"] != "user_agent_charlie"
            ]

            await asyncio.sleep(0.5)

        # === 阶段6: 方案反馈 ===
        await asyncio.sleep(1)

        # 收集反馈
        feedbacks = [
            {
                "agent_id": "user_agent_bob",
                "display_name": "Bob",
                "feedback_type": "accept",
                "reasoning": "方案合理，角色分配符合我的能力"
            },
            {
                "agent_id": "user_agent_alice",
                "display_name": "Alice",
                "feedback_type": "accept",
                "reasoning": "整体可以接受，时间问题后续协调"
            },
        ]

        for fb in feedbacks:
            await asyncio.sleep(0.6)
            await event_recorder.record({
                "event_id": f"evt-{uuid4().hex[:8]}",
                "event_type": "towow.proposal.feedback",
                "timestamp": datetime.utcnow().isoformat(),
                "payload": {
                    "channel_id": channel_id,
                    "agent_id": fb["agent_id"],
                    "display_name": fb["display_name"],
                    "feedback_type": fb["feedback_type"],
                    "reasoning": fb["reasoning"],
                    "round": 1
                }
            })

        # === 阶段7: 协商完成 ===
        await asyncio.sleep(1.5)

        # 统计参与者
        final_participants = [a["agent_id"] for a in proposal["assignments"]]
        declined_count = 2  # David 和 Emma
        withdrawn_count = 1 if "user_agent_charlie" not in final_participants else 0

        summary = f"经过1轮协商，{len(final_participants)}位参与者达成共识"
        if declined_count > 0:
            summary += f"，{declined_count}人婉拒"
        if withdrawn_count > 0:
            summary += f"，{withdrawn_count}人中途退出"

        await event_recorder.record({
            "event_id": f"evt-{uuid4().hex[:8]}",
            "event_type": "towow.proposal.finalized",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "channel_id": channel_id,
                "demand_id": demand_id,
                "status": "success",
                "final_proposal": proposal,
                "total_rounds": 1,
                "participants_count": len(final_participants),
                "declined_count": declined_count,
                "withdrawn_count": withdrawn_count,
                "participants": final_participants,
                "summary": summary,
                "finalized_at": datetime.utcnow().isoformat()
            }
        })

        # Update status
        if demand_id in _demands:
            _demands[demand_id]["status"] = "completed"

        logger.info(f"需求 {demand_id} 的模拟协商流程完成")

    except Exception as e:
        logger.error(f"模拟协商流程错误: {e}")


@router.get("/{demand_id}")
async def get_demand(demand_id: str):
    """
    Get demand details.

    GET /api/v1/demand/{demand_id}

    Args:
        demand_id: Demand ID to retrieve

    Returns:
        Demand details
    """
    if demand_id not in _demands:
        raise HTTPException(status_code=404, detail="需求不存在")

    return _demands[demand_id]


@router.get("/{demand_id}/status")
async def get_demand_status(demand_id: str):
    """
    Get demand status.

    GET /api/v1/demand/{demand_id}/status

    Args:
        demand_id: Demand ID to check status

    Returns:
        Status information
    """
    if demand_id not in _demands:
        raise HTTPException(status_code=404, detail="需求不存在")

    demand = _demands[demand_id]
    return {
        "demand_id": demand_id,
        "status": demand.get("status", "unknown"),
        "current_round": 1
    }


async def cleanup_tasks():
    """清理所有活跃任务（在 shutdown 时调用）"""
    if not _active_tasks:
        return

    logger.info(f"正在清理 {len(_active_tasks)} 个活跃任务")
    for task in _active_tasks:
        task.cancel()
    await asyncio.gather(*_active_tasks, return_exceptions=True)
    _active_tasks.clear()
    logger.info("所有任务已清理完成")
