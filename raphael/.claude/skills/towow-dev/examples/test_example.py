"""
测试编写示例

展示如何为通爻代码编写高质量测试

关键要点：
1. 正常情况测试（happy path）
2. 边界情况测试（边界值、空输入）
3. 异常情况测试（错误输入、外部依赖失败）
4. Mock 外部依赖（不依赖真实 API）
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import Optional


# ============================================================================
# 被测试的代码（来自 projection_example.py）
# ============================================================================

@dataclass
class ProfileData:
    """用户 Profile 数据"""
    user_id: str
    skills: list[str]
    experiences: list[str]


@dataclass
class HDCVector:
    """HDC 超向量"""
    data: list[int]  # 简化为 list，实际是 numpy.ndarray


class ProfileDataSource:
    """Profile 数据源接口（抽象）"""
    def get_profile(self, user_id: str) -> ProfileData:
        raise NotImplementedError


class UserNotFoundError(Exception):
    """用户不存在异常"""
    pass


def project(profile_data: ProfileData, lens: str) -> HDCVector:
    """投影函数（简化版本）"""
    # 简化：用技能数量作为向量维度
    dimension = len(profile_data.skills) * 100
    return HDCVector(data=[1] * dimension)


def get_edge_agent_vector(
    user_id: str,
    data_source: ProfileDataSource
) -> HDCVector:
    """
    获取 Edge Agent 的 HDC 向量

    这是我们要测试的函数
    """
    if not user_id:
        raise ValueError("user_id cannot be empty")

    profile_data = data_source.get_profile(user_id)
    return project(profile_data, lens="full_dimension")


# ============================================================================
# 测试：正常情况（Happy Path）
# ============================================================================

def test_get_edge_agent_vector_normal():
    """
    测试正常情况：成功获取 Edge Agent Vector

    测试要点：
    - 输入合法
    - 数据源返回正常
    - 返回值类型正确
    """
    # Arrange（准备）
    # 创建 Mock 数据源
    mock_source = Mock(spec=ProfileDataSource)
    mock_profile = ProfileData(
        user_id="user123",
        skills=["Python", "FastAPI", "React"],
        experiences=["Built e-commerce"]
    )
    mock_source.get_profile.return_value = mock_profile

    # Act（执行）
    vector = get_edge_agent_vector("user123", mock_source)

    # Assert（验证）
    assert isinstance(vector, HDCVector), "返回值应该是 HDCVector 类型"
    assert len(vector.data) > 0, "向量不应该为空"
    mock_source.get_profile.assert_called_once_with("user123"), \
        "应该正好调用一次 get_profile，参数为 user123"


def test_get_edge_agent_vector_with_many_skills():
    """
    测试正常情况：用户有很多技能

    边界值测试：技能数量较多的情况
    """
    # Arrange
    mock_source = Mock(spec=ProfileDataSource)
    many_skills = [f"skill_{i}" for i in range(50)]  # 50 个技能
    mock_profile = ProfileData(
        user_id="user456",
        skills=many_skills,
        experiences=[]
    )
    mock_source.get_profile.return_value = mock_profile

    # Act
    vector = get_edge_agent_vector("user456", mock_source)

    # Assert
    assert len(vector.data) == 5000, "50 个技能应该产生 5000 维向量"


# ============================================================================
# 测试：边界情况（Edge Cases）
# ============================================================================

def test_get_edge_agent_vector_empty_user_id():
    """
    测试边界情况：空的 user_id

    边界值：空字符串
    预期：抛出 ValueError
    """
    # Arrange
    mock_source = Mock(spec=ProfileDataSource)

    # Act & Assert
    with pytest.raises(ValueError, match="user_id cannot be empty"):
        get_edge_agent_vector("", mock_source)

    # 验证：不应该调用 get_profile（因为参数验证失败）
    mock_source.get_profile.assert_not_called()


def test_get_edge_agent_vector_user_with_no_skills():
    """
    测试边界情况：用户没有技能

    边界值：空的 skills 列表
    预期：返回空向量（或最小维度向量）
    """
    # Arrange
    mock_source = Mock(spec=ProfileDataSource)
    mock_profile = ProfileData(
        user_id="user789",
        skills=[],  # 空技能列表
        experiences=[]
    )
    mock_source.get_profile.return_value = mock_profile

    # Act
    vector = get_edge_agent_vector("user789", mock_source)

    # Assert
    assert len(vector.data) == 0, "没有技能应该产生空向量"


def test_get_edge_agent_vector_special_characters_in_user_id():
    """
    测试边界情况：user_id 包含特殊字符

    边界值：特殊字符（如空格、Unicode）
    预期：正常处理（不应该崩溃）
    """
    # Arrange
    special_user_ids = [
        "user with spaces",
        "user@email.com",
        "用户123",  # Unicode
        "user_with_emoji_😀"
    ]

    for user_id in special_user_ids:
        mock_source = Mock(spec=ProfileDataSource)
        mock_profile = ProfileData(
            user_id=user_id,
            skills=["Python"],
            experiences=[]
        )
        mock_source.get_profile.return_value = mock_profile

        # Act
        vector = get_edge_agent_vector(user_id, mock_source)

        # Assert
        assert isinstance(vector, HDCVector), f"特殊 user_id '{user_id}' 应该正常处理"


# ============================================================================
# 测试：异常情况（Error Cases）
# ============================================================================

def test_get_edge_agent_vector_user_not_found():
    """
    测试异常情况：用户不存在

    外部依赖失败：数据源抛出 UserNotFoundError
    预期：异常向上传播
    """
    # Arrange
    mock_source = Mock(spec=ProfileDataSource)
    mock_source.get_profile.side_effect = UserNotFoundError("user999 not found")

    # Act & Assert
    with pytest.raises(UserNotFoundError, match="user999 not found"):
        get_edge_agent_vector("user999", mock_source)


def test_get_edge_agent_vector_data_source_timeout():
    """
    测试异常情况：数据源超时

    外部依赖失败：网络超时
    预期：异常向上传播
    """
    # Arrange
    mock_source = Mock(spec=ProfileDataSource)
    mock_source.get_profile.side_effect = TimeoutError("Request timeout")

    # Act & Assert
    with pytest.raises(TimeoutError, match="Request timeout"):
        get_edge_agent_vector("user111", mock_source)


def test_get_edge_agent_vector_invalid_profile_data():
    """
    测试异常情况：Profile 数据格式错误

    外部依赖失败：返回的数据格式不正确
    预期：抛出 AttributeError 或 TypeError
    """
    # Arrange
    mock_source = Mock(spec=ProfileDataSource)
    # 返回错误的数据类型（不是 ProfileData）
    mock_source.get_profile.return_value = {"invalid": "data"}

    # Act & Assert
    with pytest.raises((AttributeError, TypeError)):
        get_edge_agent_vector("user222", mock_source)


# ============================================================================
# 测试：Mock 外部依赖的高级技巧
# ============================================================================

def test_get_edge_agent_vector_with_real_adapter():
    """
    测试：使用真实 Adapter（但 Mock API 调用）

    场景：测试 SecondMeAdapter，但不真正调用 SecondMe API
    """
    # Arrange
    # 假设我们有一个真实的 SecondMeAdapter 类
    class SecondMeAdapter:
        def __init__(self, api_key):
            self.api_key = api_key

        def get_profile(self, user_id: str) -> ProfileData:
            # 真实逻辑会调用 API
            import requests
            response = requests.get(f"https://api.secondme.com/profile/{user_id}")
            return ProfileData(**response.json())

    # 用 patch Mock HTTP 请求
    with patch("requests.get") as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "user_id": "user333",
            "skills": ["Python", "AI"],
            "experiences": ["Research"]
        }
        mock_get.return_value = mock_response

        # Act
        adapter = SecondMeAdapter(api_key="test_key")
        vector = get_edge_agent_vector("user333", adapter)

        # Assert
        assert isinstance(vector, HDCVector)
        mock_get.assert_called_once_with("https://api.secondme.com/profile/user333")


# ============================================================================
# 测试：集成测试（多个组件组合）
# ============================================================================

def test_get_edge_agent_vector_integration():
    """
    集成测试：测试多个组件的组合

    场景：
    1. Mock 数据源
    2. 调用 get_edge_agent_vector
    3. 验证 project 函数被正确调用
    """
    # Arrange
    mock_source = Mock(spec=ProfileDataSource)
    mock_profile = ProfileData(
        user_id="user444",
        skills=["Skill1", "Skill2"],
        experiences=["Exp1"]
    )
    mock_source.get_profile.return_value = mock_profile

    # Act
    with patch("__main__.project") as mock_project:
        mock_project.return_value = HDCVector(data=[1, 0, 1])

        vector = get_edge_agent_vector("user444", mock_source)

        # Assert
        # 验证 project 被调用，且参数正确
        mock_project.assert_called_once()
        call_args = mock_project.call_args
        assert call_args[0][0] == mock_profile, "第一个参数应该是 ProfileData"
        assert call_args[0][1] == "full_dimension", "第二个参数应该是 'full_dimension'"


# ============================================================================
# 测试：参数化测试（测试多个输入组合）
# ============================================================================

@pytest.mark.parametrize("user_id,skills,expected_dimension", [
    ("user1", ["A"], 100),
    ("user2", ["A", "B"], 200),
    ("user3", ["A", "B", "C"], 300),
    ("user4", [], 0),
])
def test_get_edge_agent_vector_parametrized(user_id, skills, expected_dimension):
    """
    参数化测试：测试多个输入组合

    好处：
    - 一个测试函数，测试多种场景
    - 清晰地展示输入-输出关系
    """
    # Arrange
    mock_source = Mock(spec=ProfileDataSource)
    mock_profile = ProfileData(
        user_id=user_id,
        skills=skills,
        experiences=[]
    )
    mock_source.get_profile.return_value = mock_profile

    # Act
    vector = get_edge_agent_vector(user_id, mock_source)

    # Assert
    assert len(vector.data) == expected_dimension, \
        f"{len(skills)} 个技能应该产生 {expected_dimension} 维向量"


# ============================================================================
# 测试：Fixture（测试夹具，复用测试数据）
# ============================================================================

@pytest.fixture
def mock_data_source():
    """
    Fixture：创建一个 Mock 数据源

    好处：
    - 复用测试数据
    - 统一的测试环境
    """
    mock_source = Mock(spec=ProfileDataSource)
    mock_profile = ProfileData(
        user_id="user_fixture",
        skills=["Python", "FastAPI"],
        experiences=["Built API"]
    )
    mock_source.get_profile.return_value = mock_profile
    return mock_source


def test_with_fixture_example_1(mock_data_source):
    """使用 Fixture 的测试 1"""
    vector = get_edge_agent_vector("user_fixture", mock_data_source)
    assert len(vector.data) == 200


def test_with_fixture_example_2(mock_data_source):
    """使用 Fixture 的测试 2"""
    vector = get_edge_agent_vector("user_fixture", mock_data_source)
    assert isinstance(vector, HDCVector)


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])

    # 运行特定测试
    # pytest.main([__file__, "-v", "-k", "test_get_edge_agent_vector_normal"])

    # 运行并查看覆盖率
    # pytest.main([__file__, "-v", "--cov=."])
