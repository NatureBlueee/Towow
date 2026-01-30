"""
SecondMe OAuth2 Client - 处理 SecondMe OAuth2 认证流程

主要功能：
1. 构建授权 URL（引导用户到 SecondMe 授权页面）
2. 用授权码交换 Access Token
3. 使用 Access Token 获取用户信息
4. 刷新 Token
"""

import os
import secrets
import logging
import threading
from typing import Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx

if TYPE_CHECKING:
    from .session_store import SessionStore

# ============ 常量定义 ============
STATE_EXPIRY_MINUTES = 10  # state 有效期（分钟）
TOKEN_EXPIRY_BUFFER_MINUTES = 5  # Token 过期判断提前量（分钟）

logger = logging.getLogger(__name__)


@dataclass
class OAuth2Config:
    """OAuth2 配置"""
    client_id: str
    client_secret: str
    redirect_uri: str
    api_base_url: str = "https://app.mindos.com"
    auth_url: str = "https://app.me.bot/oauth"

    @classmethod
    def from_env(cls) -> "OAuth2Config":
        """从环境变量加载配置"""
        client_id = os.getenv("SECONDME_CLIENT_ID")
        client_secret = os.getenv("SECONDME_CLIENT_SECRET")
        redirect_uri = os.getenv("SECONDME_REDIRECT_URI")

        if not client_id or not client_secret or not redirect_uri:
            raise ValueError(
                "Missing required environment variables: "
                "SECONDME_CLIENT_ID, SECONDME_CLIENT_SECRET, SECONDME_REDIRECT_URI"
            )

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            api_base_url=os.getenv("SECONDME_API_BASE_URL", "https://app.mindos.com"),
            auth_url=os.getenv("SECONDME_AUTH_URL", "https://app.me.bot/oauth"),
        )


@dataclass
class TokenSet:
    """Token 集合"""
    access_token: str
    refresh_token: str
    open_id: str
    expires_in: int  # 秒
    token_type: str = "Bearer"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    @property
    def expires_at(self) -> datetime:
        """Token 过期时间"""
        return self.created_at + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """检查 Token 是否过期（提前判断，留有缓冲）"""
        return datetime.now() >= self.expires_at - timedelta(minutes=TOKEN_EXPIRY_BUFFER_MINUTES)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "open_id": self.open_id,
            "expires_in": self.expires_in,
            "token_type": self.token_type,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


@dataclass
class UserInfo:
    """用户信息"""
    open_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "open_id": self.open_id,
            "name": self.name,
            "avatar": self.avatar,
            "bio": self.bio,
        }


class OAuth2Error(Exception):
    """OAuth2 错误"""
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.response_body = response_body


class SecondMeOAuth2Client:
    """
    SecondMe OAuth2 客户端

    使用示例:
        # 创建客户端（带 SessionStore）
        session_store = await get_session_store()
        client = SecondMeOAuth2Client(config, session_store)

        # 1. 构建授权 URL，重定向用户
        auth_url, state = await client.build_authorization_url()

        # 2. 用户授权后，用回调中的 code 交换 Token
        token_set = await client.exchange_token(code)

        # 3. 获取用户信息
        user_info = await client.get_user_info(token_set.access_token)
    """

    def __init__(
        self,
        config: OAuth2Config,
        session_store: Optional["SessionStore"] = None
    ):
        self.config = config
        self._http_client: Optional[httpx.AsyncClient] = None
        self._session_store = session_store

    @classmethod
    def from_env(cls, session_store: Optional["SessionStore"] = None) -> "SecondMeOAuth2Client":
        """从环境变量创建客户端"""
        config = OAuth2Config.from_env()
        return cls(config, session_store)

    @property
    def http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端（懒加载）"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._http_client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def generate_state(self) -> str:
        """生成随机 state 用于 CSRF 防护"""
        state = secrets.token_hex(16)
        if self._session_store:
            await self._session_store.set(
                f"oauth_state:{state}",
                "1",
                ttl_seconds=STATE_EXPIRY_MINUTES * 60
            )
        return state

    async def verify_state(self, state: str) -> bool:
        """
        验证 state 是否有效（原子操作，防止竞态条件）

        使用 delete 的返回值作为原子验证：
        - 如果 state 存在，删除并返回 True
        - 如果 state 不存在（已被使用或过期），返回 False
        """
        if self._session_store:
            key = f"oauth_state:{state}"
            # 原子操作：delete 返回 True 表示键存在并被删除
            return await self._session_store.delete(key)
        return False

    async def build_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        构建授权 URL

        Args:
            state: 可选的 state 参数，如果不提供则自动生成

        Returns:
            (authorization_url, state) 元组
        """
        if state is None:
            state = await self.generate_state()

        # 不对 redirect_uri 进行编码，SecondMe 可能会自行处理
        url = (
            f"{self.config.auth_url}"
            f"?client_id={self.config.client_id}"
            f"&redirect_uri={self.config.redirect_uri}"
            f"&response_type=code"
            f"&state={state}"
        )
        return url, state

    async def exchange_token(self, code: str) -> TokenSet:
        """
        用授权码交换 Token

        Args:
            code: 授权码

        Returns:
            TokenSet 对象

        Raises:
            OAuth2Error: 交换失败
        """
        url = f"{self.config.api_base_url}/gate/lab/api/oauth/token/code"

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        logger.info(f"Exchanging authorization code for tokens...")

        try:
            response = await self.http_client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            body = response.json()

            if response.status_code != 200 or body.get("code") != 0:
                error_msg = body.get("message", "Token exchange failed")
                # 脱敏日志：不记录完整的 response body
                logger.error(f"Token exchange failed: {error_msg}, code={body.get('code')}")
                raise OAuth2Error(
                    message=error_msg,
                    error_code=str(body.get("code")),
                    status_code=response.status_code,
                    response_body=body,
                )

            data = body.get("data", {})

            token_set = TokenSet(
                access_token=data.get("accessToken") or data.get("access_token"),
                refresh_token=data.get("refreshToken") or data.get("refresh_token"),
                open_id=data.get("openId") or data.get("open_id", ""),
                expires_in=data.get("expiresIn") or data.get("expires_in", 7200),
                token_type=data.get("tokenType") or data.get("token_type", "Bearer"),
            )

            # 脱敏日志：只显示 open_id 前 8 位
            logger.info(f"Token exchange successful, open_id: {token_set.open_id[:8]}...")
            return token_set

        except httpx.RequestError as e:
            logger.error(f"Network error during token exchange: {e}")
            raise OAuth2Error(
                message=f"Network error: {str(e)}",
                error_code="network_error",
            )

    async def refresh_token(self, refresh_token: str) -> TokenSet:
        """
        刷新 Access Token

        Args:
            refresh_token: Refresh Token

        Returns:
            新的 TokenSet 对象

        Raises:
            OAuth2Error: 刷新失败
        """
        url = f"{self.config.api_base_url}/gate/lab/api/oauth/token/refresh"

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        logger.info("Refreshing access token...")

        try:
            response = await self.http_client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            body = response.json()

            if response.status_code != 200 or body.get("code") != 0:
                error_msg = body.get("message", "Token refresh failed")
                logger.error(f"Token refresh failed: {error_msg}")
                raise OAuth2Error(
                    message=error_msg,
                    error_code=str(body.get("code")),
                    status_code=response.status_code,
                    response_body=body,
                )

            data = body.get("data", {})

            token_set = TokenSet(
                access_token=data.get("accessToken") or data.get("access_token"),
                refresh_token=data.get("refreshToken") or data.get("refresh_token"),
                open_id=data.get("openId") or data.get("open_id", ""),
                expires_in=data.get("expiresIn") or data.get("expires_in", 7200),
                token_type=data.get("tokenType") or data.get("token_type", "Bearer"),
            )

            logger.info("Token refresh successful")
            return token_set

        except httpx.RequestError as e:
            logger.error(f"Network error during token refresh: {e}")
            raise OAuth2Error(
                message=f"Network error: {str(e)}",
                error_code="network_error",
            )

    async def get_user_info(self, access_token: str, token_type: str = "Bearer") -> UserInfo:
        """
        获取用户信息

        Args:
            access_token: Access Token
            token_type: Token 类型，默认为 "Bearer"

        Returns:
            UserInfo 对象

        Raises:
            OAuth2Error: 获取失败
        """
        url = f"{self.config.api_base_url}/gate/lab/api/secondme/user/info"

        logger.info("Fetching user info...")

        try:
            response = await self.http_client.get(
                url,
                headers={
                    "Authorization": f"{token_type} {access_token}",
                    "Content-Type": "application/json",
                },
            )

            body = response.json()

            if response.status_code != 200 or (body.get("code") is not None and body.get("code") != 0):
                error_msg = body.get("message", "Failed to get user info")
                logger.error(f"Get user info failed: {error_msg}")
                raise OAuth2Error(
                    message=error_msg,
                    error_code=str(body.get("code")),
                    status_code=response.status_code,
                    response_body=body,
                )

            data = body.get("data", body)

            user_info = UserInfo(
                # SecondMe 不返回 openId，使用 email 作为唯一标识符
                open_id=data.get("openId") or data.get("open_id") or data.get("email", ""),
                name=data.get("name") or data.get("nickname"),
                avatar=data.get("avatar") or data.get("avatarUrl"),
                bio=data.get("bio") or data.get("description"),
                raw_data=data,
            )

            # 脱敏日志：只显示 open_id 前 8 位
            open_id_masked = user_info.open_id[:8] + "..." if user_info.open_id else "N/A"
            logger.info(f"User info fetched: name={user_info.name}, open_id: {open_id_masked}")
            return user_info

        except httpx.RequestError as e:
            logger.error(f"Network error during get user info: {e}")
            raise OAuth2Error(
                message=f"Network error: {str(e)}",
                error_code="network_error",
            )


# 全局 OAuth2 客户端实例（懒加载）
_oauth2_client: Optional[SecondMeOAuth2Client] = None
_oauth2_client_lock = threading.Lock()


async def get_oauth2_client(
    session_store: Optional["SessionStore"] = None
) -> SecondMeOAuth2Client:
    """
    获取 OAuth2 客户端单例（线程安全）

    Args:
        session_store: 可选的 SessionStore 实例，首次创建时使用

    Returns:
        SecondMeOAuth2Client 实例
    """
    global _oauth2_client
    if _oauth2_client is None:
        with _oauth2_client_lock:
            # 双重检查锁定，避免竞态条件
            if _oauth2_client is None:
                _oauth2_client = SecondMeOAuth2Client.from_env(session_store)
    return _oauth2_client


def reset_oauth2_client():
    """重置 OAuth2 客户端（用于测试）"""
    global _oauth2_client
    with _oauth2_client_lock:
        _oauth2_client = None
