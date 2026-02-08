# SecondMe 数据对接技术方案

## 文档元信息

- **文档类型**: 技术方案 (TECH)
- **版本**: v5
- **状态**: DRAFT
- **创建日期**: 2026-01-29
- **关联项目**: requirement_demo

---

## 1. 现状分析

### 1.1 SecondMe 当前暴露的数据

基于 `web/oauth2_client.py:354-407` [VERIFIED]，SecondMe 通过 `/gate/lab/api/secondme/user/info` API 返回以下数据：

```python
# SecondMe API 返回数据结构
{
    "code": 0,
    "data": {
        "openId": "xxx",           # 用户唯一标识（当前不返回，见注释 oauth2_client.py:396）
        "email": "xxx@xxx.com",   # 邮箱（用作备选唯一标识）
        "name": "用户名",          # 用户名 / nickname
        "avatar": "https://...",  # 头像 URL / avatarUrl
        "bio": "个人简介",         # 个人简介 / description
        # 以下字段 [ASSUMPTION - 需实际 API 调用验证]
        "selfIntroduction": "...", # 自我介绍（更详细）
        "voiceId": "...",         # 语音 ID
        "profileCompleteness": 80 # 资料完整度
    }
}
```

**已确认的 SecondMe API 端点** [VERIFIED - oauth2_client.py:238,304,368]：

| API 端点 | 方法 | 用途 |
|---------|------|------|
| `/gate/lab/api/oauth/token/code` | POST | 授权码换 Token |
| `/gate/lab/api/oauth/token/refresh` | POST | 刷新 Token |
| `/gate/lab/api/secondme/user/info` | GET | 获取用户信息 |

### 1.2 我们当前使用的数据

基于 `web/oauth2_client.py:395-401` [VERIFIED]，当前从 SecondMe 提取的字段：

| SecondMe 字段 | 提取到 UserInfo | 使用情况 |
|--------------|-----------------|----------|
| `openId` / `email` | `open_id` | 作为用户唯一标识 |
| `name` / `nickname` | `name` | 显示名称 |
| `avatar` / `avatarUrl` | `avatar` | 头像 URL |
| `bio` / `description` | `bio` | 个人简介 |
| 完整响应 | `raw_data` | 保存原始数据（未使用） |

### 1.3 用户还需要手动填写的数据

基于 `web/app.py:198-217` [VERIFIED] 的 `CompleteRegistrationRequest`：

| 字段 | 来源 | 说明 |
|------|------|------|
| `display_name` | **部分自动** | 可从 SecondMe `name` 预填，用户可修改 |
| `skills` | **必须手动填写** | 技能列表，SecondMe 不提供 |
| `specialties` | **必须手动填写** | 专长领域，SecondMe 不提供 |
| `bio` | **部分自动** | 可从 SecondMe `bio` 预填，用户可修改 |

### 1.4 数据流现状

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         当前注册数据流                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. OAuth2 授权                                                          │
│     SecondMe ──► access_token, refresh_token, open_id                   │
│                                                                          │
│  2. 获取用户信息 (oauth2_client.py:354-407)                              │
│     GET /gate/lab/api/secondme/user/info                                │
│     ──► name, email, avatar, bio                                        │
│     ──► raw_data (完整响应，未使用)                                       │
│                                                                          │
│  3. 前端补填 (app.py:198-217)                                            │
│     用户输入 ──► skills[], specialties[]                                 │
│     用户确认/修改 ──► display_name, bio                                  │
│                                                                          │
│  4. 完成注册 (app.py:655-710)                                            │
│     POST /api/auth/complete-registration                                │
│     ──► 创建 UserAgentConfig                                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据对标分析

### 2.1 完整字段映射表

| SecondMe 字段 | 我们的字段 | 映射方式 | 当前状态 | 优化建议 |
|--------------|-----------|----------|----------|----------|
| `openId` | `secondme_id` | 直接映射 | [VERIFIED] 使用中 | 保持 |
| `email` | `secondme_id` (备选) | 直接映射 | [VERIFIED] 使用中 | 保持 |
| `name` / `nickname` | `display_name` | 直接映射 | [VERIFIED] 使用中 | 预填到表单 |
| `avatar` / `avatarUrl` | `avatar_url` | 直接映射 | [VERIFIED] 使用中 | 自动填充 |
| `bio` / `description` | `bio` | 直接映射 | [VERIFIED] 使用中 | 预填到表单 |
| `selfIntroduction` | `self_intro` | 直接映射 | [ASSUMPTION] 未使用 | 需验证后使用 |
| - | `skills` | 用户补填 | 必须手动 | 无法自动化 |
| - | `specialties` | 用户补填 | 必须手动 | 无法自动化 |
| - | `agent_id` | 系统生成 | 自动 | 保持 |
| - | `created_at` | 系统生成 | 自动 | 保持 |
| - | `is_active` | 系统管理 | 自动 | 保持 |

### 2.2 可自动填充的数据

| 字段 | 来源 | 填充方式 | 用户可修改 |
|------|------|----------|-----------|
| `secondme_id` | SecondMe `openId` / `email` | 自动 | 否 |
| `display_name` | SecondMe `name` | 预填 | 是 |
| `avatar_url` | SecondMe `avatar` | 自动 | 否（暂不支持修改） |
| `bio` | SecondMe `bio` | 预填 | 是 |
| `self_intro` | SecondMe `selfIntroduction` | 预填 | 是 |

### 2.3 必须用户手动填写的数据

| 字段 | 原因 | 建议 |
|------|------|------|
| `skills` | SecondMe 不提供技能数据 | 提供常用技能选项列表 |
| `specialties` | SecondMe 不提供专长数据 | 提供常用专长选项列表 |

### 2.4 SecondMe 可能提供但未使用的数据 [ASSUMPTION]

以下字段可能存在于 SecondMe API 响应中，但需要实际调用验证：

| 字段 | 可能用途 | 验证方法 |
|------|----------|----------|
| `selfIntroduction` | 更详细的自我介绍 | 调用 API 查看 raw_data |
| `voiceId` | 语音 ID（AI 分身相关） | 调用 API 查看 raw_data |
| `profileCompleteness` | 资料完整度 | 调用 API 查看 raw_data |
| `tags` / `interests` | 用户标签/兴趣 | 调用 API 查看 raw_data |
| `skills` | 用户技能（如果有） | 调用 API 查看 raw_data |

---

## 3. 优化方案

### 3.1 方案总览

**目标**：减少用户手动填写，提升注册体验

**策略**：
1. **充分利用现有数据**：将 SecondMe 返回的数据预填到表单
2. **探索更多 API**：调研 SecondMe 是否有其他 API 可获取更多数据
3. **智能推荐**：基于用户 bio 推荐技能和专长

### 3.2 短期优化（无需额外 API）

#### 3.2.1 优化 OAuth 回调响应

**当前** (`app.py:623-632`)：
```python
return AuthCallbackResponse(
    success=True,
    message="授权成功",
    open_id=token_set.open_id,
    name=user_info.name,
    avatar=user_info.avatar,
    bio=user_info.bio,
    access_token=token_set.access_token,
    needs_registration=needs_registration,
)
```

**优化后**：
```python
return AuthCallbackResponse(
    success=True,
    message="授权成功",
    open_id=token_set.open_id,
    name=user_info.name,
    avatar=user_info.avatar,
    bio=user_info.bio,
    self_intro=user_info.raw_data.get("selfIntroduction"),  # 新增
    access_token=token_set.access_token,
    needs_registration=needs_registration,
    # 新增：返回原始数据供前端使用
    raw_user_data=user_info.raw_data,
)
```

#### 3.2.2 前端预填优化

前端注册表单应：
1. 自动填充 `display_name` 为 SecondMe 返回的 `name`
2. 自动填充 `bio` 为 SecondMe 返回的 `bio`
3. 显示用户头像（只读）
4. 如果有 `selfIntroduction`，预填到 `self_intro` 字段

### 3.3 中期优化（需要 API 调研）

#### 3.3.1 调研 SecondMe 更多 API

**待调研的 API** [ASSUMPTION]：

| API | 用途 | 优先级 |
|-----|------|--------|
| `/api/user/profile` | 获取完整用户资料 | P0 |
| `/api/user/skills` | 获取用户技能 | P0 |
| `/api/user/interests` | 获取用户兴趣/标签 | P1 |
| `/api/secondme/persona` | 获取 AI 分身信息 | P2 |

**调研方法**：
1. 使用 `test_secondme_api.py` 脚本测试 API
2. 查看 `raw_data` 中的完整字段
3. 联系 SecondMe 获取 API 文档

#### 3.3.2 基于 raw_data 的数据提取

修改 `UserInfo` 类，提取更多字段：

```python
@dataclass
class UserInfo:
    """用户信息（扩展版）"""
    open_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    self_intro: Optional[str] = None      # 新增
    tags: Optional[List[str]] = None      # 新增
    interests: Optional[List[str]] = None # 新增
    raw_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "UserInfo":
        """从 API 响应创建"""
        return cls(
            open_id=data.get("openId") or data.get("email", ""),
            name=data.get("name") or data.get("nickname"),
            avatar=data.get("avatar") or data.get("avatarUrl"),
            bio=data.get("bio") or data.get("description"),
            self_intro=data.get("selfIntroduction"),
            tags=data.get("tags", []),
            interests=data.get("interests", []),
            raw_data=data,
        )
```

### 3.4 长期优化（智能推荐）

#### 3.4.1 基于 Bio 的技能推荐

如果 SecondMe 不提供技能数据，可以基于用户 bio 进行智能推荐：

```python
async def suggest_skills_from_bio(bio: str) -> List[str]:
    """基于 bio 推荐技能（使用 LLM）"""
    # 使用 LLM 分析 bio，提取可能的技能
    prompt = f"""
    根据以下用户简介，推荐 3-5 个最相关的技能标签：

    简介：{bio}

    请返回 JSON 格式：["skill1", "skill2", ...]
    """
    # 调用 LLM API
    ...
```

#### 3.4.2 技能/专长选项库

提供预定义的技能和专长选项，方便用户快速选择：

```python
SKILL_OPTIONS = [
    # 技术类
    "Python", "JavaScript", "React", "Node.js", "Go", "Rust",
    "AI/ML", "数据分析", "后端开发", "前端开发", "全栈开发",
    # 设计类
    "UI设计", "UX设计", "产品设计", "平面设计",
    # 产品类
    "产品管理", "项目管理", "需求分析", "用户研究",
    # 其他
    "写作", "翻译", "营销", "运营",
]

SPECIALTY_OPTIONS = [
    "Web开发", "移动开发", "AI应用", "区块链",
    "电商", "金融科技", "教育科技", "医疗健康",
    "游戏", "社交", "企业服务", "工具软件",
]
```

---

## 4. 实现建议

### 4.1 代码修改清单

#### 4.1.1 修改 `AuthCallbackResponse` 模型

**文件**: `web/app.py:186-196`

```python
class AuthCallbackResponse(BaseModel):
    """OAuth 回调响应"""
    success: bool
    message: str
    open_id: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    self_intro: Optional[str] = None      # 新增
    access_token: str
    needs_registration: bool = True
    raw_user_data: Optional[Dict[str, Any]] = None  # 新增：原始数据
```

#### 4.1.2 修改 OAuth 回调处理

**文件**: `web/app.py:623-632`

```python
return AuthCallbackResponse(
    success=True,
    message="授权成功" if needs_registration else "用户已注册",
    open_id=token_set.open_id,
    name=user_info.name,
    avatar=user_info.avatar,
    bio=user_info.bio,
    self_intro=user_info.raw_data.get("selfIntroduction") if user_info.raw_data else None,
    access_token=token_set.access_token,
    needs_registration=needs_registration,
    raw_user_data=user_info.raw_data,  # 返回原始数据
)
```

#### 4.1.3 新增 API：获取技能/专长选项

**文件**: `web/app.py`（新增）

```python
@app.get(
    "/api/options/skills",
    tags=["选项"],
    summary="获取技能选项列表",
)
async def get_skill_options():
    """获取预定义的技能选项列表"""
    return {"skills": SKILL_OPTIONS}

@app.get(
    "/api/options/specialties",
    tags=["选项"],
    summary="获取专长选项列表",
)
async def get_specialty_options():
    """获取预定义的专长选项列表"""
    return {"specialties": SPECIALTY_OPTIONS}
```

### 4.2 数据流优化

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         优化后的注册数据流                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. OAuth2 授权                                                          │
│     SecondMe ──► access_token, refresh_token, open_id                   │
│                                                                          │
│  2. 获取用户信息                                                          │
│     GET /gate/lab/api/secondme/user/info                                │
│     ──► name, email, avatar, bio, selfIntroduction, raw_data            │
│                                                                          │
│  3. 返回给前端（优化）                                                     │
│     ──► 预填 display_name = name                                        │
│     ──► 预填 bio = bio                                                  │
│     ──► 预填 self_intro = selfIntroduction                              │
│     ──► 显示 avatar（只读）                                              │
│     ──► 返回 raw_user_data 供调试                                        │
│                                                                          │
│  4. 前端补填（简化）                                                       │
│     用户选择 ──► skills[]（从选项列表选择）                                │
│     用户选择 ──► specialties[]（从选项列表选择）                           │
│     用户确认/修改 ──► display_name, bio, self_intro                      │
│                                                                          │
│  5. 完成注册                                                              │
│     POST /api/auth/complete-registration                                │
│     ──► 创建 UserAgentConfig（包含所有字段）                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 前端优化建议

1. **表单预填**：
   - 从 OAuth 回调获取 `name`、`bio`、`self_intro`
   - 自动填充到对应表单字段
   - 用户可以修改

2. **技能选择**：
   - 调用 `/api/options/skills` 获取选项列表
   - 使用多选组件（如 Tag 选择器）
   - 支持自定义输入

3. **专长选择**：
   - 调用 `/api/options/specialties` 获取选项列表
   - 使用多选组件
   - 支持自定义输入

4. **头像显示**：
   - 显示 SecondMe 头像（只读）
   - 暂不支持修改

---

## 5. 待验证事项

### 5.1 SecondMe API 数据验证 [OPEN]

需要实际调用 SecondMe API 验证以下字段是否存在：

| 字段 | 验证方法 | 状态 |
|------|----------|------|
| `selfIntroduction` | 查看 raw_data | [TBD] |
| `tags` | 查看 raw_data | [TBD] |
| `interests` | 查看 raw_data | [TBD] |
| `skills` | 查看 raw_data | [TBD] |
| `profileCompleteness` | 查看 raw_data | [TBD] |

**验证步骤**：
1. 运行 `test_secondme_api.py` 脚本
2. 使用有效的 access_token 调用 API
3. 打印完整的 raw_data 响应
4. 记录所有可用字段

### 5.2 SecondMe 其他 API 调研 [OPEN]

需要调研 SecondMe 是否提供以下 API：

| API | 用途 | 调研方法 |
|-----|------|----------|
| 用户技能 API | 获取用户技能 | 联系 SecondMe / 查看文档 |
| 用户兴趣 API | 获取用户兴趣 | 联系 SecondMe / 查看文档 |
| AI 分身 API | 获取 AI 分身信息 | 联系 SecondMe / 查看文档 |

---

## 6. 风险与预案

| 风险 | 影响 | 概率 | 预案 |
|------|------|------|------|
| SecondMe API 不提供技能数据 | 用户必须手动填写 | 高 | 提供技能选项列表，简化选择 |
| SecondMe API 字段变更 | 数据提取失败 | 中 | 使用 raw_data 兜底，记录日志 |
| 用户 bio 为空 | 无法预填 | 中 | 显示空表单，用户自行填写 |
| LLM 技能推荐不准确 | 用户体验差 | 中 | 作为建议，用户可修改 |

---

## 7. 总结

### 7.1 当前状态

- SecondMe 提供：`openId/email`、`name`、`avatar`、`bio`
- 我们使用：全部使用
- 用户需填写：`skills`、`specialties`

### 7.2 优化后

- 自动填充：`display_name`、`avatar_url`、`bio`、`self_intro`
- 用户选择：`skills`（从选项列表）、`specialties`（从选项列表）
- 用户可修改：`display_name`、`bio`、`self_intro`

### 7.3 下一步行动

1. **P0**：验证 SecondMe API 返回的完整字段（运行 test_secondme_api.py）
2. **P0**：修改 OAuth 回调，返回更多预填数据
3. **P1**：新增技能/专长选项 API
4. **P2**：调研 SecondMe 其他 API
5. **P3**：实现基于 bio 的技能推荐

---

## 附录 A: 代码引用

| 文件 | 行号 | 内容 |
|------|------|------|
| `web/oauth2_client.py` | 354-407 | get_user_info 实现 |
| `web/oauth2_client.py` | 396-401 | UserInfo 字段提取 |
| `web/oauth2_client.py` | 98-114 | UserInfo 数据类定义 |
| `web/app.py` | 186-196 | AuthCallbackResponse 模型 |
| `web/app.py` | 198-217 | CompleteRegistrationRequest 模型 |
| `web/app.py` | 574-645 | auth_callback 处理函数 |
| `web/app.py` | 648-710 | complete_registration 处理函数 |
| `web/agent_manager.py` | 33-65 | UserAgentConfig 数据类 |
| `web/database.py` | 28-66 | User 数据库模型 |

## 附录 B: SecondMe API 端点汇总

| API 端点 | 方法 | 用途 | 状态 |
|---------|------|------|------|
| `https://app.me.bot/oauth` | GET | OAuth2 授权页面 | [VERIFIED] |
| `/gate/lab/api/oauth/token/code` | POST | 授权码换 Token | [VERIFIED] |
| `/gate/lab/api/oauth/token/refresh` | POST | 刷新 Token | [VERIFIED] |
| `/gate/lab/api/secondme/user/info` | GET | 获取用户信息 | [VERIFIED] |
| `/api/user/skills` | GET | 获取用户技能 | [ASSUMPTION] |
| `/api/user/profile` | GET | 获取完整资料 | [ASSUMPTION] |
