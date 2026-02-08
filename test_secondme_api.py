#!/usr/bin/env python3
"""
测试 SecondMe API 返回的完整数据结构
"""

import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

from web.oauth2_client import get_oauth2_client

# 使用之前获取的 access_token
# 如果过期了需要重新授权
ACCESS_TOKEN = "lba_at_28f3985d-e3c9-4e2a-a3f9-e2e2e2e2e2e2"  # 替换为实际的 token


async def test_user_info():
    """测试获取用户信息 API"""
    client = get_oauth2_client()

    print("=" * 60)
    print("测试 SecondMe /api/secondme/user/info API")
    print("=" * 60)

    try:
        # 直接调用底层 HTTP 请求，获取原始响应
        import aiohttp

        url = f"{client.config.api_base_url}/gate/lab/api/secondme/user/info"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"\nStatus: {response.status}")
                print(f"Headers: {dict(response.headers)}")

                raw_text = await response.text()
                print(f"\n原始响应:\n{raw_text}")

                try:
                    data = json.loads(raw_text)
                    print(f"\n解析后的 JSON:")
                    print(json.dumps(data, indent=2, ensure_ascii=False))

                    if "data" in data:
                        print(f"\n=== data 字段的所有 key ===")
                        for key in data["data"].keys():
                            value = data["data"][key]
                            value_type = type(value).__name__
                            value_preview = str(value)[:100] if value else "null"
                            print(f"  {key}: ({value_type}) {value_preview}")
                except json.JSONDecodeError:
                    print("响应不是有效的 JSON")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("\n请先确保 ACCESS_TOKEN 是有效的")
    print("如果 token 过期，需要重新通过 OAuth2 流程获取\n")

    await test_user_info()


if __name__ == "__main__":
    asyncio.run(main())
