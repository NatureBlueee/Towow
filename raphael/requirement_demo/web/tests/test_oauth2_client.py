"""
SecondMe OAuth2 Client 单元测试
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# 导入被测试的模块
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.oauth2_client import (
    OAuth2Config,
    TokenSet,
    UserInfo,
    SecondMeOAuth2Client,
    OAuth2Error,
    get_oauth2_client,
    reset_oauth2_client,
)


class TestOAuth2Config:
    """OAuth2Config 测试"""

    def test_from_env_missing_vars(self):
        """测试缺少环境变量时抛出异常"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                OAuth2Config.from_env()
            assert "Missing required environment variables" in str(exc_info.value)

    def test_from_env_success(self):
        """测试从环境变量成功加载配置"""
        env_vars = {
            "SECONDME_CLIENT_ID": "test_client_id",
            "SECONDME_CLIENT_SECRET": "test_secret",
            "SECONDME_REDIRECT_URI": "http://localhost:8080/callback",
        }
        with patch.dict('os.environ', env_vars, clear=True):
            config = OAuth2Config.from_env()
            assert config.client_id == "test_client_id"
            assert config.client_secret == "test_secret"
            assert config.redirect_uri == "http://localhost:8080/callback"
            # 默认值
            assert config.api_base_url == "https://app.mindos.com"
            assert config.auth_url == "https://app.me.bot/oauth"

    def test_from_env_with_custom_urls(self):
        """测试自定义 URL"""
        env_vars = {
            "SECONDME_CLIENT_ID": "test_client_id",
            "SECONDME_CLIENT_SECRET": "test_secret",
            "SECONDME_REDIRECT_URI": "http://localhost:8080/callback",
            "SECONDME_API_BASE_URL": "https://custom.api.com",
            "SECONDME_AUTH_URL": "https://custom.auth.com/oauth",
        }
        with patch.dict('os.environ', env_vars, clear=True):
            config = OAuth2Config.from_env()
            assert config.api_base_url == "https://custom.api.com"
            assert config.auth_url == "https://custom.auth.com/oauth"


class TestTokenSet:
    """TokenSet 测试"""

    def test_token_set_creation(self):
        """测试 TokenSet 创建"""
        token = TokenSet(
            access_token="access_123",
            refresh_token="refresh_456",
            open_id="user_789",
            expires_in=7200,
        )
        assert token.access_token == "access_123"
        assert token.refresh_token == "refresh_456"
        assert token.open_id == "user_789"
        assert token.expires_in == 7200
        assert token.token_type == "Bearer"
        assert token.created_at is not None

    def test_token_set_expiry(self):
        """测试 Token 过期判断"""
        # 创建一个即将过期的 token（有效期 1 分钟）
        token = TokenSet(
            access_token="access_123",
            refresh_token="refresh_456",
            open_id="user_789",
            expires_in=60,  # 1 分钟
        )
        # 由于我们提前 5 分钟判断过期，所以 1 分钟有效期的 token 会被认为已过期
        assert token.is_expired is True

        # 创建一个未过期的 token（有效期 2 小时）
        token2 = TokenSet(
            access_token="access_123",
            refresh_token="refresh_456",
            open_id="user_789",
            expires_in=7200,  # 2 小时
        )
        assert token2.is_expired is False

    def test_token_set_to_dict(self):
        """测试 TokenSet 转字典"""
        token = TokenSet(
            access_token="access_123",
            refresh_token="refresh_456",
            open_id="user_789",
            expires_in=7200,
        )
        d = token.to_dict()
        assert d["access_token"] == "access_123"
        assert d["refresh_token"] == "refresh_456"
        assert d["open_id"] == "user_789"
        assert d["expires_in"] == 7200
        assert "created_at" in d
        assert "expires_at" in d


class TestUserInfo:
    """UserInfo 测试"""

    def test_user_info_creation(self):
        """测试 UserInfo 创建"""
        user = UserInfo(
            open_id="user_123",
            name="Test User",
            avatar="https://example.com/avatar.jpg",
            bio="Hello World",
        )
        assert user.open_id == "user_123"
        assert user.name == "Test User"
        assert user.avatar == "https://example.com/avatar.jpg"
        assert user.bio == "Hello World"

    def test_user_info_to_dict(self):
        """测试 UserInfo 转字典"""
        user = UserInfo(
            open_id="user_123",
            name="Test User",
        )
        d = user.to_dict()
        assert d["open_id"] == "user_123"
        assert d["name"] == "Test User"
        assert d["avatar"] is None
        assert d["bio"] is None


class TestSecondMeOAuth2Client:
    """SecondMeOAuth2Client 测试"""

    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost:8080/callback",
        )

    @pytest.fixture
    def client(self, config):
        """创建测试客户端"""
        return SecondMeOAuth2Client(config)

    def test_generate_state(self, client):
        """测试 state 生成"""
        state1 = client.generate_state()
        state2 = client.generate_state()

        # state 应该是 32 字符的十六进制字符串
        assert len(state1) == 32
        assert len(state2) == 32
        # 每次生成的 state 应该不同
        assert state1 != state2
        # state 应该被存储
        assert state1 in client._pending_states
        assert state2 in client._pending_states

    def test_verify_state(self, client):
        """测试 state 验证"""
        state = client.generate_state()

        # 验证有效 state
        assert client.verify_state(state) is True
        # 验证后 state 应该被删除
        assert state not in client._pending_states

        # 验证无效 state
        assert client.verify_state("invalid_state") is False

    def test_build_authorization_url(self, client):
        """测试构建授权 URL"""
        url, state = client.build_authorization_url()

        assert "https://app.me.bot/oauth" in url
        assert f"client_id={client.config.client_id}" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert f"state={state}" in url

    @pytest.mark.asyncio
    async def test_exchange_token_success(self, client):
        """测试成功交换 Token"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "message": "success",
            "data": {
                "accessToken": "access_123",
                "refreshToken": "refresh_456",
                "openId": "user_789",
                "expiresIn": 7200,
            }
        }

        with patch.object(client.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            token_set = await client.exchange_token("auth_code_123")

            assert token_set.access_token == "access_123"
            assert token_set.refresh_token == "refresh_456"
            assert token_set.open_id == "user_789"
            assert token_set.expires_in == 7200

    @pytest.mark.asyncio
    async def test_exchange_token_error(self, client):
        """测试交换 Token 失败"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "code": 10001,
            "message": "Invalid authorization code",
        }

        with patch.object(client.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            with pytest.raises(OAuth2Error) as exc_info:
                await client.exchange_token("invalid_code")

            assert "Invalid authorization code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, client):
        """测试成功获取用户信息"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "openId": "user_123",
                "name": "Test User",
                "avatar": "https://example.com/avatar.jpg",
                "bio": "Hello World",
            }
        }

        with patch.object(client.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            user_info = await client.get_user_info("access_token_123")

            assert user_info.open_id == "user_123"
            assert user_info.name == "Test User"
            assert user_info.avatar == "https://example.com/avatar.jpg"
            assert user_info.bio == "Hello World"

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client):
        """测试成功刷新 Token"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "accessToken": "new_access_123",
                "refreshToken": "new_refresh_456",
                "openId": "user_789",
                "expiresIn": 7200,
            }
        }

        with patch.object(client.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            token_set = await client.refresh_token("old_refresh_token")

            assert token_set.access_token == "new_access_123"
            assert token_set.refresh_token == "new_refresh_456"


class TestGlobalClient:
    """全局客户端测试"""

    def test_get_oauth2_client_missing_config(self):
        """测试缺少配置时获取客户端"""
        reset_oauth2_client()

        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError):
                get_oauth2_client()

    def test_get_oauth2_client_singleton(self):
        """测试客户端单例"""
        reset_oauth2_client()

        env_vars = {
            "SECONDME_CLIENT_ID": "test_client_id",
            "SECONDME_CLIENT_SECRET": "test_secret",
            "SECONDME_REDIRECT_URI": "http://localhost:8080/callback",
        }

        with patch.dict('os.environ', env_vars, clear=True):
            client1 = get_oauth2_client()
            client2 = get_oauth2_client()
            assert client1 is client2

        reset_oauth2_client()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
