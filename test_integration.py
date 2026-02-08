#!/usr/bin/env python3
"""
集成测试：完整的多 Agent 协作流程

测试流程：
1. 启动 Nature 的 Agent (user_d212ce7f)
2. 提交一个需求
3. 验证 Admin 邀请、Coordinator 分发、Worker 响应
4. 通过 WebSocket 接收实时消息
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080"

# 存储接收到的 WebSocket 消息
ws_messages = []


async def start_agent(agent_id: str):
    """启动 Agent"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/agents/{agent_id}/action",
            json={"action": "start"}
        ) as resp:
            data = await resp.json()
            print(f"启动 Agent {agent_id}: {data.get('message')}")
            return data.get("success")


async def stop_agent(agent_id: str):
    """停止 Agent"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/api/agents/{agent_id}/action",
            json={"action": "stop"}
        ) as resp:
            data = await resp.json()
            print(f"停止 Agent {agent_id}: {data.get('message')}")
            return data.get("success")


async def submit_requirement(title: str, description: str, submitter_id: str):
    """提交需求"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "title": title,
            "description": description,
            "submitter_id": submitter_id,
            "metadata": {"priority": "high"}
        }
        async with session.post(
            f"{BASE_URL}/api/requirements",
            json=payload
        ) as resp:
            data = await resp.json()
            print(f"提交需求: {data}")
            return data.get("requirement_id")


async def ws_listener(agent_id: str, duration: int = 30):
    """WebSocket 监听器"""
    print(f"\n开始 WebSocket 监听 (agent_id={agent_id}, 持续 {duration} 秒)...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"{WS_URL}/ws/{agent_id}") as ws:
                print("WebSocket 连接成功")

                # 设置超时
                end_time = asyncio.get_event_loop().time() + duration

                while asyncio.get_event_loop().time() < end_time:
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=1)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            ws_messages.append(data)
                            print(f"  📥 收到消息: {data.get('type', 'unknown')}")
                            if data.get('type') not in ['pong', 'subscribed', 'unsubscribed']:
                                print(f"      内容: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print("WebSocket 连接关闭")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"WebSocket 错误: {ws.exception()}")
                            break
                    except asyncio.TimeoutError:
                        continue

                print("WebSocket 监听结束")

    except Exception as e:
        print(f"WebSocket 错误: {e}")


async def main():
    """运行集成测试"""
    print("=" * 60)
    print("集成测试：完整的多 Agent 协作流程")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)
    print()

    # 1. 检查 Agent 状态
    print("【1. 检查 Agent 状态】")
    print("-" * 40)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/agents") as resp:
            data = await resp.json()
            print(f"已注册的 Agent: {data.get('total', 0)} 个")
            for agent in data.get("agents", []):
                print(f"  - {agent['agent_id']}: {agent['display_name']} (运行中: {agent['is_running']})")
    print()

    # 2. 启动 Nature 的 Agent
    print("【2. 启动 Nature 的 Agent】")
    print("-" * 40)
    agent_id = "user_d212ce7f"
    await start_agent(agent_id)
    await asyncio.sleep(3)  # 等待 Agent 启动
    print()

    # 3. 启动 WebSocket 监听（后台任务）
    print("【3. 启动 WebSocket 监听】")
    print("-" * 40)
    ws_task = asyncio.create_task(ws_listener(agent_id, duration=25))
    await asyncio.sleep(1)  # 等待 WebSocket 连接
    print()

    # 4. 提交需求
    print("【4. 提交需求】")
    print("-" * 40)
    requirement_id = await submit_requirement(
        title="Web3 钱包集成测试",
        description="需要一个 Web3 钱包集成方案，支持 MetaMask 和 WalletConnect，用于 AI 产品",
        submitter_id="integration_test"
    )
    print()

    # 5. 等待 Agent 协作完成
    print("【5. 等待 Agent 协作】")
    print("-" * 40)
    print("等待 Admin 邀请、Coordinator 分发、Worker 响应...")
    await ws_task  # 等待 WebSocket 监听完成
    print()

    # 6. 检查需求状态
    print("【6. 检查需求状态】")
    print("-" * 40)
    if requirement_id:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/api/requirements/{requirement_id}") as resp:
                data = await resp.json()
                print(f"需求状态: {json.dumps(data, ensure_ascii=False, indent=2)}")
    print()

    # 7. 停止 Agent
    print("【7. 停止 Agent】")
    print("-" * 40)
    await stop_agent(agent_id)
    print()

    # 8. 测试结果汇总
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"收到的 WebSocket 消息: {len(ws_messages)} 条")

    # 统计消息类型
    msg_types = {}
    for msg in ws_messages:
        t = msg.get("type", "unknown")
        msg_types[t] = msg_types.get(t, 0) + 1

    print("消息类型统计:")
    for t, count in msg_types.items():
        print(f"  - {t}: {count}")

    print()
    if len(ws_messages) > 0:
        print("🎉 集成测试完成！")
    else:
        print("⚠️ 未收到 WebSocket 消息，可能需要检查 OpenAgents 网络是否运行")


if __name__ == "__main__":
    asyncio.run(main())
