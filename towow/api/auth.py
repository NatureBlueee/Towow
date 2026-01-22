"""
Admin API 认证中间件

提供 Admin API 的 API Key 认证保护
"""
import os

from fastapi import Header, HTTPException


async def verify_admin_token(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    """
    验证 Admin API Key

    Args:
        x_admin_key: 从请求头 X-Admin-Key 获取的 API Key

    Returns:
        True: 验证通过

    Raises:
        HTTPException(500): Admin API Key 未配置
        HTTPException(403): API Key 无效
    """
    admin_key = os.getenv("ADMIN_API_KEY")
    if not admin_key:
        raise HTTPException(status_code=500, detail="Admin API key not configured")
    if x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True
