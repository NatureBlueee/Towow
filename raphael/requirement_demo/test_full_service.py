#!/usr/bin/env python3
"""
完整的后端服务测试脚本

测试内容：
1. 数据层测试 - SQLite CRUD
2. API 测试 - 所有端点
3. WebSocket 测试 - 实时推送
4. 集成测试 - 完整用户流程
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080"

# 测试结果统计
results = {"passed": 0, "failed": 0, "tests": []}


def log_test(name: str, passed: bool, detail: str = ""):
    """记录测试结果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")
    if detail and not passed:
        print(f"       └─ {detail}")
    results["tests"].append({"name": name, "passed": passed, "detail": detail})
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1


async def test_health():
    """测试健康检查端点"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/health") as resp:
            data = await resp.json()
            log_test(
                "GET /health",
                resp.status == 200 and data.get("status") == "healthy",
                f"status={resp.status}, data={data}"
            )


async def test_list_agents():
    """测试获取 Agent 列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/agents") as resp:
            data = await resp.json()
            log_test(
                "GET /api/agents",
                resp.status == 200 and "agents" in data,
                f"status={resp.status}, total={data.get('total', 0)}"
            )
            return data.get("agents", [])


async def test_get_agent(agent_id: str):
    """测试获取单个 Agent"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/agents/{agent_id}") as resp:
            passed = resp.status == 200
            log_test(
                f"GET /api/agents/{agent_id}",
                passed,
                f"status={resp.status}"
            )


async def test_create_requirement():
    """测试创建需求"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "title": "测试需求：构建一个简单的 API 服务",
            "description": "这是一个测试需求，用于验证 API 功能",
            "submitter_id": "test_user",
            "metadata": {"tags": ["test", "api"], "priority": "high"}
        }
        async with session.post(
            f"{BASE_URL}/api/requirements",
            json=payload
        ) as resp:
            data = await resp.json()
            passed = resp.status == 200 and "requirement_id" in data
            log_test(
                "POST /api/requirements",
                passed,
                f"status={resp.status}, requirement_id={data.get('requirement_id')}"
            )
            return data.get("requirement_id")


async def test_list_requirements():
    """测试获取需求列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/requirements") as resp:
            data = await resp.json()
            log_test(
                "GET /api/requirements",
                resp.status == 200 and "requirements" in data,
                f"status={resp.status}, total={data.get('total', 0)}"
            )
            return data.get("requirements", [])


async def test_get_requirement(requirement_id: str):
    """测试获取单个需求"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/requirements/{requirement_id}") as resp:
            passed = resp.status == 200
            log_test(
                f"GET /api/requirements/{requirement_id}",
                passed,
                f"status={resp.status}"
            )


async def test_update_requirement(requirement_id: str):
    """测试更新需求"""
    async with aiohttp.ClientSession() as session:
        # PATCH 使用 Query 参数
        async with session.patch(
            f"{BASE_URL}/api/requirements/{requirement_id}?status=in_progress"
        ) as resp:
            passed = resp.status == 200
            log_test(
                f"PATCH /api/requirements/{requirement_id}",
                passed,
                f"status={resp.status}"
            )


async def test_send_channel_message(channel_id: str):
    """测试发送 Channel 消息"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "sender_id": "test_user",
            "content": "这是一条测试消息",
            "message_type": "text"
        }
        async with session.post(
            f"{BASE_URL}/api/channels/{channel_id}/messages",
            json=payload
        ) as resp:
            data = await resp.json()
            passed = resp.status == 200 and "message_id" in data
            log_test(
                f"POST /api/channels/{channel_id}/messages",
                passed,
                f"status={resp.status}, message_id={data.get('message_id')}"
            )


async def test_get_channel_messages(channel_id: str):
    """测试获取 Channel 消息"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/channels/{channel_id}/messages") as resp:
            data = await resp.json()
            log_test(
                f"GET /api/channels/{channel_id}/messages",
                resp.status == 200 and "messages" in data,
                f"status={resp.status}, total={data.get('total', 0)}"
            )


async def test_websocket():
    """测试 WebSocket 连接"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"{WS_URL}/ws/test_ws_user") as ws:
                # 测试连接
                log_test("WebSocket 连接", True, "连接成功")

                # 测试 ping
                await ws.send_json({"action": "ping"})
                msg = await asyncio.wait_for(ws.receive_json(), timeout=5)
                log_test(
                    "WebSocket ping/pong",
                    msg.get("type") == "pong",
                    f"response={msg}"
                )

                # 测试订阅
                await ws.send_json({"action": "subscribe", "channel_id": "test_channel"})
                msg = await asyncio.wait_for(ws.receive_json(), timeout=5)
                log_test(
                    "WebSocket subscribe",
                    msg.get("type") == "subscribed",
                    f"response={msg}"
                )

                # 测试取消订阅
                await ws.send_json({"action": "unsubscribe", "channel_id": "test_channel"})
                msg = await asyncio.wait_for(ws.receive_json(), timeout=5)
                log_test(
                    "WebSocket unsubscribe",
                    msg.get("type") == "unsubscribed",
                    f"response={msg}"
                )

                await ws.close()

    except Exception as e:
        log_test("WebSocket 连接", False, str(e))


async def test_ws_stats():
    """测试 WebSocket 统计"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/ws/stats") as resp:
            data = await resp.json()
            log_test(
                "GET /api/ws/stats",
                resp.status == 200 and "total_connections" in data,
                f"status={resp.status}, connections={data.get('total_connections', 0)}"
            )


async def test_oauth_login():
    """测试 OAuth2 登录 URL 生成"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/auth/login") as resp:
            data = await resp.json()
            log_test(
                "GET /api/auth/login",
                resp.status == 200 and "authorization_url" in data,
                f"status={resp.status}, has_url={'authorization_url' in data}"
            )


async def test_stats():
    """测试统计端点"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/stats") as resp:
            data = await resp.json()
            log_test(
                "GET /api/stats",
                resp.status == 200 and "total_agents" in data,
                f"status={resp.status}, data={data}"
            )


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("后端服务完整测试")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"目标: {BASE_URL}")
    print("=" * 60)
    print()

    # 1. 基础 API 测试
    print("【1. 基础 API 测试】")
    print("-" * 40)
    await test_health()
    await test_stats()
    await test_oauth_login()
    print()

    # 2. Agent API 测试
    print("【2. Agent API 测试】")
    print("-" * 40)
    agents = await test_list_agents()
    if agents:
        await test_get_agent(agents[0]["agent_id"])
    print()

    # 3. 需求 API 测试
    print("【3. 需求 API 测试】")
    print("-" * 40)
    requirement_id = await test_create_requirement()
    await test_list_requirements()
    if requirement_id:
        await test_get_requirement(requirement_id)
        await test_update_requirement(requirement_id)
    print()

    # 4. Channel 消息 API 测试
    print("【4. Channel 消息 API 测试】")
    print("-" * 40)
    # requirement_id 已经包含 req_ 前缀，不需要再加
    channel_id = requirement_id if requirement_id else "test_channel"
    await test_send_channel_message(channel_id)
    await test_get_channel_messages(channel_id)
    print()

    # 5. WebSocket 测试
    print("【5. WebSocket 测试】")
    print("-" * 40)
    await test_websocket()
    await test_ws_stats()
    print()

    # 测试结果汇总
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"总计: {results['passed'] + results['failed']}")
    print()

    if results["failed"] > 0:
        print("失败的测试:")
        for test in results["tests"]:
            if not test["passed"]:
                print(f"  - {test['name']}: {test['detail']}")
        sys.exit(1)
    else:
        print("🎉 所有测试通过！")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
