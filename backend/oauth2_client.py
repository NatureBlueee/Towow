"""
SecondMe OAuth2 Client - 处理 SecondMe OAuth2 认证流程

主要功能：
1. 构建授权 URL（引导用户到 SecondMe 授权页面）
2. 用授权码交换 Access Token
3. 使用 Access Token 获取用户信息
4. 刷新 Token
"""

import os
import json
import secrets
import logging
import threading
from typing import Optional, Dict, Any, AsyncGenerator, TYPE_CHECKING
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
    self_introduction: Optional[str] = None
    voice_id: Optional[str] = None
    profile_completeness: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "open_id": self.open_id,
            "name": self.name,
            "avatar": self.avatar,
            "bio": self.bio,
            "self_introduction": self.self_introduction,
            "voice_id": self.voice_id,
            "profile_completeness": self.profile_completeness,
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


class ChatError(OAuth2Error):
    """Chat API 错误"""
    pass


@dataclass
class Shade:
    """SecondMe 兴趣标签"""
    id: str
    name: str = ""
    description: str = ""
    content: str = ""
    confidence: str = "MEDIUM"
    source_topics: list[str] = None
    is_public: bool = False

    def __post_init__(self):
        if self.source_topics is None:
            self.source_topics = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "confidence": self.confidence,
            "source_topics": self.source_topics,
        }


@dataclass
class SoftMemory:
    """SecondMe 事实性记忆"""
    id: int
    category: str = ""
    content: str = ""
    create_time: int = 0
    update_time: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "content": self.content,
        }


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

    async def build_authorization_url(
        self,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ) -> tuple[str, str]:
        """
        构建授权 URL

        Args:
            state: 可选的 state 参数，如果不提供则自动生成
            redirect_uri: 可选的回调地址，如果不提供则使用配置中的默认值

        Returns:
            (authorization_url, state) 元组
        """
        if state is None:
            state = await self.generate_state()

        uri = redirect_uri or self.config.redirect_uri

        # 不对 redirect_uri 进行编码 — SecondMe 要求原始 URL，
        # 编码后会返回 "Application not found"
        url = (
            f"{self.config.auth_url}"
            f"?client_id={self.config.client_id}"
            f"&redirect_uri={uri}"
            f"&response_type=code"
            f"&state={state}"
            f"&scope=user.info+user.info.shades+user.info.softmemory+chat"
        )
        return url, state

    async def exchange_token(self, code: str, redirect_uri: Optional[str] = None) -> TokenSet:
        """
        用授权码交换 Token

        Args:
            code: 授权码
            redirect_uri: 可选的回调地址，如果不提供则使用配置中的默认值

        Returns:
            TokenSet 对象

        Raises:
            OAuth2Error: 交换失败
        """
        url = f"{self.config.api_base_url}/gate/lab/api/oauth/token/code"

        uri = redirect_uri or self.config.redirect_uri

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": uri,
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
                self_introduction=data.get("selfIntroduction"),
                voice_id=data.get("voiceId"),
                profile_completeness=data.get("profileCompleteness"),
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

    async def get_shades(self, access_token: str) -> list[Shade]:
        """
        获取用户兴趣标签（Shades）

        优先使用公开版第三人称描述，适合作为 Agent 画像的外部展示。

        Returns:
            Shade 对象列表
        """
        url = f"{self.config.api_base_url}/gate/lab/api/secondme/user/shades"

        logger.info("Fetching user shades...")

        try:
            response = await self.http_client.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            body = response.json()

            if response.status_code != 200 or (body.get("code") is not None and body.get("code") != 0):
                error_msg = body.get("message", "Failed to get shades")
                logger.error(f"Get shades failed: {error_msg}")
                raise OAuth2Error(
                    message=error_msg,
                    error_code=str(body.get("code")),
                    status_code=response.status_code,
                    response_body=body,
                )

            data = body.get("data", {})
            raw_shades = data.get("shades", [])

            shades = []
            for s in raw_shades:
                # 优先公开版第三人称，回退到私有版
                shade = Shade(
                    id=str(s.get("id", "")),
                    name=s.get("shadeNamePublic") or s.get("shadeName", ""),
                    description=(
                        s.get("shadeDescriptionThirdViewPublic")
                        or s.get("shadeDescriptionPublic")
                        or s.get("shadeDescriptionThirdView")
                        or s.get("shadeDescription", "")
                    ),
                    content=(
                        s.get("shadeContentThirdViewPublic")
                        or s.get("shadeContentPublic")
                        or s.get("shadeContentThirdView")
                        or s.get("shadeContent", "")
                    ),
                    confidence=s.get("confidenceLevelPublic") or s.get("confidenceLevel", "MEDIUM"),
                    source_topics=s.get("sourceTopicsPublic") or s.get("sourceTopics", []),
                    is_public=bool(s.get("hasPublicContent")),
                )
                shades.append(shade)

            logger.info(f"Fetched {len(shades)} shades")
            return shades

        except OAuth2Error:
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error during get shades: {e}")
            raise OAuth2Error(message=f"Network error: {str(e)}", error_code="network_error")

    async def get_softmemory(
        self,
        access_token: str,
        keyword: Optional[str] = None,
        page_no: int = 1,
        page_size: int = 100,
    ) -> list[SoftMemory]:
        """
        获取用户事实性记忆（Soft Memory）

        Returns:
            SoftMemory 对象列表
        """
        url = f"{self.config.api_base_url}/gate/lab/api/secondme/user/softmemory"

        params: Dict[str, Any] = {"pageNo": page_no, "pageSize": page_size}
        if keyword:
            params["keyword"] = keyword

        logger.info(f"Fetching soft memory (keyword={keyword}, page={page_no})...")

        try:
            response = await self.http_client.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            body = response.json()

            if response.status_code != 200 or (body.get("code") is not None and body.get("code") != 0):
                error_msg = body.get("message", "Failed to get soft memory")
                logger.error(f"Get soft memory failed: {error_msg}")
                raise OAuth2Error(
                    message=error_msg,
                    error_code=str(body.get("code")),
                    status_code=response.status_code,
                    response_body=body,
                )

            data = body.get("data", {})
            raw_list = data.get("list", [])

            memories = []
            for m in raw_list:
                mem = SoftMemory(
                    id=m.get("id", 0),
                    category=m.get("factObject", ""),
                    content=m.get("factContent", ""),
                    create_time=m.get("createTime", 0),
                    update_time=m.get("updateTime", 0),
                )
                memories.append(mem)

            total = data.get("total", len(memories))
            logger.info(f"Fetched {len(memories)}/{total} soft memories")
            return memories

        except OAuth2Error:
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error during get soft memory: {e}")
            raise OAuth2Error(message=f"Network error: {str(e)}", error_code="network_error")

    async def chat_stream(
        self,
        access_token: str,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        session_id: Optional[str] = None,
        enable_web_search: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        调用 SecondMe Chat API（流式）

        通过 SSE 流式接收 LLM 回复，支持 session 管理、工具调用等事件。

        Args:
            access_token: Access Token
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            system_prompt: 可选的系统提示词
            session_id: 可选的会话 ID（用于上下文关联）
            enable_web_search: 是否启用网络搜索，默认 False

        Yields:
            dict: 解析后的 SSE 事件，包含 "type" 字段：
                - {"type": "session", "sessionId": "..."}
                - {"type": "data", "content": "text chunk"}
                - {"type": "tool_call", "name": "...", "parameters": "..."}
                - {"type": "tool_result", "name": "...", "result": "..."}
                - {"type": "done"}

        Raises:
            ChatError: Chat API 调用失败
        """
        url = f"{self.config.api_base_url}/gate/lab/api/secondme/chat/stream"

        # SecondMe Chat API 使用 "message"(单条字符串)，不是 "messages"(数组)
        # 取最后一条 user 消息作为 message；用 sessionId 维护上下文
        last_content = ""
        for m in reversed(messages):
            if m.get("role") == "user" and m.get("content"):
                last_content = m["content"]
                break
        if not last_content and messages:
            last_content = messages[-1].get("content", "")

        payload: Dict[str, Any] = {
            "message": last_content,
            "enableWebSearch": enable_web_search,
        }
        if system_prompt is not None:
            payload["systemPrompt"] = system_prompt
        if session_id is not None:
            payload["sessionId"] = session_id

        # 脱敏日志
        logger.info(
            f"Starting chat stream: message={last_content[:50]!r}..."
        )

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0),
                follow_redirects=True,
            ) as stream_client:
                async with stream_client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                ) as response:
                    if response.status_code != 200:
                        # 读取错误响应体
                        error_body = b""
                        async for chunk in response.aiter_bytes():
                            error_body += chunk
                        try:
                            body = json.loads(error_body.decode("utf-8"))
                            error_msg = body.get("message", "Chat stream request failed")
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            error_msg = f"Chat stream request failed with status {response.status_code}"
                            body = None

                        logger.error(
                            f"Chat stream failed: status={response.status_code}, "
                            f"error={error_msg}"
                        )
                        raise ChatError(
                            message=error_msg,
                            error_code="chat_stream_error",
                            status_code=response.status_code,
                            response_body=body,
                        )

                    # 解析 SSE 流
                    current_event_type = None
                    line_count = 0
                    data_event_count = 0
                    async for line in response.aiter_lines():
                        line = line.strip()
                        line_count += 1

                        # 前 20 行全量打日志（调试用）
                        if line_count <= 20:
                            logger.info(f"SSE L{line_count}: {line!r}")

                        # 空行表示事件结束
                        if not line:
                            current_event_type = None
                            continue

                        # 解析 event: 行
                        if line.startswith("event:"):
                            current_event_type = line[len("event:"):].strip()
                            logger.debug(f"SSE event type: {current_event_type}")
                            continue

                        # 解析 data: 行
                        if line.startswith("data:"):
                            data_str = line[len("data:"):].strip()

                            # 检查流结束标记
                            if data_str == "[DONE]":
                                logger.info(
                                    "Chat stream completed: %d lines, %d data events",
                                    line_count, data_event_count,
                                )
                                yield {"type": "done"}
                                return

                            # 尝试解析 JSON 数据
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                logger.warning(f"Non-JSON data line: {data_str[:200]}")
                                # 非 JSON 数据作为纯文本 data 事件
                                if current_event_type:
                                    yield {"type": current_event_type, "raw": data_str}
                                continue

                            # 根据事件类型构造输出
                            event_type = current_event_type or "data"

                            if event_type == "session":
                                yield {
                                    "type": "session",
                                    "sessionId": data.get("sessionId", ""),
                                }
                            elif event_type == "data":
                                data_event_count += 1
                                # 兼容两种格式：
                                # 1. {"content": "text"}  (直接 content)
                                # 2. {"choices": [{"delta": {"content": "text"}}]}  (OpenAI 格式)
                                content = data.get("content", "")
                                if not content and "choices" in data:
                                    try:
                                        content = data["choices"][0]["delta"]["content"]
                                    except (IndexError, KeyError, TypeError):
                                        content = ""
                                # 前 5 个 data event 打日志
                                if data_event_count <= 5:
                                    logger.info(
                                        "SSE data #%d: content=%r, has_choices=%s, keys=%s",
                                        data_event_count,
                                        content[:50] if content else "(empty)",
                                        "choices" in data,
                                        list(data.keys()),
                                    )
                                yield {
                                    "type": "data",
                                    "content": content,
                                }
                            elif event_type == "tool_call":
                                yield {
                                    "type": "tool_call",
                                    "name": data.get("name", ""),
                                    "parameters": data.get("parameters", ""),
                                }
                            elif event_type == "tool_result":
                                yield {
                                    "type": "tool_result",
                                    "name": data.get("name", ""),
                                    "result": data.get("result", ""),
                                }
                            else:
                                # 未知事件类型，透传
                                logger.info(f"SSE unknown event: {event_type}, data_keys={list(data.keys())}")
                                yield {"type": event_type, **data}

                    # 流结束但没收到 [DONE]
                    logger.warning(
                        "SSE stream ended without [DONE]: %d lines, %d data events",
                        line_count, data_event_count,
                    )

        except ChatError:
            # 已处理的 ChatError，直接向上抛出
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error during chat stream: {e}")
            raise ChatError(
                message=f"Network error: {str(e)}",
                error_code="network_error",
            )
        except Exception as e:
            logger.error(f"Unexpected error during chat stream: {e}")
            raise ChatError(
                message=f"Chat stream error: {str(e)}",
                error_code="chat_error",
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


def build_agent_profile(
    user_info: UserInfo,
    shades: list[Shade] | None = None,
    memories: list[SoftMemory] | None = None,
) -> Dict[str, Any]:
    """
    从 SecondMe 数据构建完整的 Agent 画像。

    用于：
    - 存储为 adapter 的 profile 数据
    - 文本化后进行向量编码
    - 注入 Center 的协商上下文

    Args:
        user_info: 用户基本信息
        shades: 兴趣标签列表
        memories: 事实性记忆列表

    Returns:
        结构化的 profile 字典
    """
    profile: Dict[str, Any] = {
        "agent_id": user_info.open_id,
        "name": user_info.name or "Unknown",
        "bio": user_info.bio or "",
        "self_introduction": user_info.self_introduction or "",
        "avatar": user_info.avatar or "",
        "profile_completeness": user_info.profile_completeness or 0,
        "source": "secondme",
    }

    if shades:
        profile["shades"] = [s.to_dict() for s in shades]

    if memories:
        profile["memories"] = [m.to_dict() for m in memories]

    return profile


def profile_to_text(profile: Dict[str, Any]) -> str:
    """
    将 Agent 画像转为文本，用于向量编码。

    编码策略：先放最重要的身份信息，再放兴趣标签和记忆。
    兴趣标签按置信度排序（HIGH > MEDIUM > LOW）。
    """
    parts = []

    name = profile.get("name", "")
    if name:
        parts.append(name)

    intro = profile.get("self_introduction", "")
    if intro:
        parts.append(intro)

    bio = profile.get("bio", "")
    if bio and bio != intro:
        parts.append(bio)

    # 兴趣标签 — 按置信度排序
    confidence_order = {"VERY_HIGH": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "VERY_LOW": 4}
    shades = profile.get("shades", [])
    if shades:
        sorted_shades = sorted(shades, key=lambda s: confidence_order.get(s.get("confidence", "MEDIUM"), 2))
        shade_texts = []
        for s in sorted_shades:
            text = s.get("description", "") or s.get("name", "")
            if text:
                shade_texts.append(text)
        if shade_texts:
            parts.append("兴趣与专长：" + "；".join(shade_texts))

    # 事实性记忆
    memories = profile.get("memories", [])
    if memories:
        mem_texts = []
        for m in memories:
            cat = m.get("category", "")
            content = m.get("content", "")
            if content:
                mem_texts.append(f"{cat}：{content}" if cat else content)
        if mem_texts:
            # 取前 20 条，避免文本过长
            parts.append("个人经历：" + "；".join(mem_texts[:20]))

    return "\n".join(parts)
