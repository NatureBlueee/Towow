#!/usr/bin/env python3
"""
SecondMe Chat API 本地调试脚本（非交互式）。

用法:
  # 步骤 1: 用 code 换 token（从浏览器 OAuth 回调 URL 中拿 code）
  python debug_chat.py exchange <authorization_code>

  # 步骤 2: 直接测试 chat API
  python debug_chat.py chat <access_token>

  # 或者一步到位（先 exchange 再 chat）
  python debug_chat.py test <authorization_code>

  # 只打印授权 URL（手动在浏览器中打开）
  python debug_chat.py url
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 加载 .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

import httpx

# ============ Config ============

CLIENT_ID = os.getenv("SECONDME_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SECONDME_CLIENT_SECRET", "")
API_BASE = os.getenv("SECONDME_API_BASE_URL", "https://app.mindos.com")
AUTH_URL = os.getenv("SECONDME_AUTH_URL", "https://app.me.bot/oauth")
REDIRECT_URI = "http://localhost:8080/api/auth/secondme/callback"


def print_auth_url():
    url = (
        f"{AUTH_URL}"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&state=debug123"
        f"&scope=user.info+user.info.shades+user.info.softmemory+chat"
    )
    print(f"\n授权 URL:\n{url}\n")
    print("1. 在浏览器打开上面 URL")
    print("2. 授权后浏览器会跳到 localhost:8080/api/auth/secondme/callback?code=xxx&state=xxx")
    print("3. 复制 URL 中的 code 参数")
    print(f"4. 运行: python debug_chat.py exchange <code>\n")


async def exchange_code(code: str) -> str | None:
    """用 authorization code 换 access token。"""
    print(f"\n=== 交换 Token ===")
    token_url = f"{API_BASE}/gate/lab/api/oauth/token/code"

    print(f"URL: {token_url}")
    print(f"Code: {code[:20]}...")
    print(f"Redirect URI: {REDIRECT_URI}")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    print(f"Status: {resp.status_code}")
    body = resp.json()
    print(f"Response:\n{json.dumps(body, indent=2, ensure_ascii=False)}")

    if body.get("code") == 0:
        data = body.get("data", {})
        token = data.get("accessToken") or data.get("access_token")
        print(f"\n{'='*60}")
        print(f"ACCESS TOKEN:\n{token}")
        print(f"{'='*60}\n")
        return token
    else:
        print(f"\n[ERROR] Token 交换失败!")
        return None


async def test_chat(access_token: str):
    """直接调用 SecondMe Chat API 并打印原始 SSE 数据。"""
    print(f"\n=== SecondMe Chat Stream 原始调试 ===")
    print(f"Token: {access_token[:20]}...")

    chat_url = f"{API_BASE}/gate/lab/api/secondme/chat/stream"

    payload = {
        "messages": [
            {"role": "user", "content": "请帮我在黑客松场景中发现一个有价值的协作需求。"}
        ],
        "systemPrompt": (
            "你是用户的 AI 分身。基于你对用户的理解，创造一个有价值的协作需求。"
            "直接输出需求文本，不加解释。限制 200 字以内。"
        ),
    }

    print(f"\nEndpoint: {chat_url}")
    print(f"Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}")
    print(f"\n{'='*60}")
    print(f"原始 SSE 输出:")
    print(f"{'='*60}\n")

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=30.0),
            follow_redirects=True,
        ) as client:
            async with client.stream(
                "POST",
                chat_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
            ) as response:
                print(f"HTTP Status: {response.status_code}")
                print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
                print()

                if response.status_code != 200:
                    body = b""
                    async for chunk in response.aiter_bytes():
                        body += chunk
                    print(f"Error body:\n{body.decode('utf-8', errors='replace')}")
                    return

                # 打印每一行原始 SSE + 解析尝试
                line_num = 0
                collected = []
                current_event_type = None

                async for line in response.aiter_lines():
                    line_num += 1
                    # 打印原始行
                    print(f"  L{line_num:03d} | {line!r}")

                    stripped = line.strip()
                    if not stripped:
                        current_event_type = None
                        continue

                    if stripped.startswith("event:"):
                        current_event_type = stripped[6:].strip()
                        print(f"        ↳ event_type = {current_event_type!r}")
                        continue

                    if stripped.startswith("data:"):
                        data_str = stripped[5:].strip()

                        if data_str == "[DONE]":
                            print(f"        ↳ >>> STREAM DONE <<<")
                            continue

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            print(f"        ↳ (not JSON)")
                            continue

                        etype = current_event_type or "(none)"
                        print(f"        ↳ parsed JSON (event={etype}):")

                        # 检查各种 content 位置
                        content = ""

                        # 直接 content 字段
                        if "content" in data and isinstance(data["content"], str):
                            content = data["content"]
                            print(f"           data.content = {content!r}")

                        # choices[0].delta.content
                        if "choices" in data:
                            print(f"           data.choices = {json.dumps(data['choices'], ensure_ascii=False)}")
                            try:
                                c = data["choices"][0]["delta"]["content"]
                                if c:
                                    content = c
                                    print(f"           choices[0].delta.content = {c!r}")
                            except (IndexError, KeyError, TypeError) as e:
                                print(f"           choices 解析失败: {e}")

                        # sessionId
                        if "sessionId" in data:
                            print(f"           sessionId = {data['sessionId']}")

                        if content:
                            collected.append(content)

                print(f"\n{'='*60}")
                print(f"共 {line_num} 行 SSE")
                full = "".join(collected)
                print(f"拼接结果 ({len(full)} 字符):\n{full if full else '(空)'}")
                print(f"{'='*60}")

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def do_test(code: str):
    """exchange + chat 一步到位。"""
    token = await exchange_code(code)
    if token:
        await test_chat(token)


# ============ Main ============

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "url":
        print_auth_url()
    elif cmd == "exchange":
        if len(sys.argv) < 3:
            print("用法: python debug_chat.py exchange <authorization_code>")
            sys.exit(1)
        asyncio.run(exchange_code(sys.argv[2]))
    elif cmd == "chat":
        if len(sys.argv) < 3:
            print("用法: python debug_chat.py chat <access_token>")
            sys.exit(1)
        asyncio.run(test_chat(sys.argv[2]))
    elif cmd == "test":
        if len(sys.argv) < 3:
            print("用法: python debug_chat.py test <authorization_code>")
            sys.exit(1)
        asyncio.run(do_test(sys.argv[2]))
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)
