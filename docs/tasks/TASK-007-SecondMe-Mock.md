# TASK-007：SecondMe Mock服务

## 任务信息

| 属性 | 值 |
|------|-----|
| 任务ID | TASK-007 |
| 所属Phase | Phase 2：核心Agent |
| 依赖 | TASK-001 |
| 预估工作量 | 1天 |
| 状态 | 待开始 |

---

## 任务描述

实现SecondMe的Mock服务，用于开发和测试阶段，同时定义与真实SecondMe对接的接口。

---

## 具体工作

### 1. SecondMe客户端接口

`services/secondme.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import aiohttp

class SecondMeClient(ABC):
    """SecondMe客户端抽象接口"""

    @abstractmethod
    async def understand_demand(
        self,
        user_id: str,
        raw_input: str
    ) -> Dict[str, Any]:
        """
        需求理解（提示词1）

        Returns:
            {
                "surface_demand": "表面需求",
                "deep_understanding": {
                    "motivation": "动机",
                    "likely_preferences": ["偏好1", "偏好2"],
                    "emotional_context": "情感背景"
                },
                "uncertainties": ["不确定的点"],
                "confidence": "high/medium/low"
            }
        """
        pass

    @abstractmethod
    async def generate_response(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        回应生成（提示词3）

        Returns:
            {
                "decision": "participate/decline/need_more_info",
                "contribution": "可以提供什么",
                "conditions": ["条件1", "条件2"],
                "reasoning": "决策理由"
            }
        """
        pass

    @abstractmethod
    async def generate_feedback(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        方案反馈（提示词5）

        Returns:
            {
                "feedback_type": "accept/negotiate/withdraw",
                "adjustment_request": "调整请求（如果是negotiate）",
                "reasoning": "理由"
            }
        """
        pass


class RealSecondMeClient(SecondMeClient):
    """真实SecondMe API客户端"""

    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _request(self, endpoint: str, data: Dict) -> Dict:
        """发送请求"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers=headers
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def understand_demand(
        self,
        user_id: str,
        raw_input: str
    ) -> Dict[str, Any]:
        return await self._request(
            "/api/secondme/understand",
            {"user_id": user_id, "raw_input": raw_input}
        )

    async def generate_response(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self._request(
            "/api/secondme/respond",
            {"user_id": user_id, "context": context}
        )

    async def generate_feedback(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self._request(
            "/api/secondme/feedback",
            {"user_id": user_id, "context": context}
        )
```

### 2. Mock SecondMe实现

`services/secondme_mock.py`:

```python
from typing import Dict, Any
from services.secondme import SecondMeClient
from services.llm import LLMService
import random

class MockSecondMeClient(SecondMeClient):
    """
    Mock SecondMe客户端

    使用LLM模拟SecondMe的行为，用于开发和测试
    """

    def __init__(self, llm_service: LLMService, mock_profiles: Dict[str, Dict] = None):
        self.llm = llm_service
        self.mock_profiles = mock_profiles or {}

    def _get_user_profile(self, user_id: str) -> Dict:
        """获取用户Mock Profile"""
        return self.mock_profiles.get(user_id, {
            "name": f"用户{user_id[-4:]}",
            "personality": "随和，对新事物有好奇心",
            "interests": ["技术", "社交"],
            "availability": "工作日晚上有时间",
            "decision_style": "中等谨慎，需要一定信息才做决定"
        })

    async def understand_demand(
        self,
        user_id: str,
        raw_input: str
    ) -> Dict[str, Any]:
        """模拟需求理解"""
        profile = self._get_user_profile(user_id)

        prompt = f"""
你是{profile['name']}的数字分身（SecondMe）。

用户性格：{profile['personality']}
用户兴趣：{profile['interests']}
用户时间：{profile['availability']}

用户说："{raw_input}"

请理解这个需求，输出JSON格式：
```json
{{
    "surface_demand": "表面需求（一句话）",
    "deep_understanding": {{
        "motivation": "为什么会提出这个需求",
        "likely_preferences": ["偏好1", "偏好2"],
        "emotional_context": "情感状态"
    }},
    "uncertainties": ["不确定的点1", "不确定的点2"],
    "confidence": "medium"
}}
```
"""
        response = await self.llm.complete(
            prompt=prompt,
            system="你是一个数字分身，深度理解你的主人。"
        )

        return self._parse_json_response(response, {
            "surface_demand": raw_input,
            "deep_understanding": {"motivation": "未知"},
            "uncertainties": [],
            "confidence": "low"
        })

    async def generate_response(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """模拟回应生成"""
        profile = self._get_user_profile(user_id)
        demand = context.get("demand", {})

        prompt = f"""
你是{profile['name']}的数字分身（SecondMe）。

用户性格：{profile['personality']}
用户兴趣：{profile['interests']}
用户时间：{profile['availability']}
决策风格：{profile['decision_style']}

收到一个协作邀请：
需求：{demand.get('surface_demand', '')}
被选中的原因：{context.get('selection_reason', '')}

请代表用户决定是否参与，输出JSON格式：
```json
{{
    "decision": "participate 或 decline 或 need_more_info",
    "contribution": "如果参与，能提供什么",
    "conditions": ["条件1", "条件2"],
    "reasoning": "决策理由"
}}
```

注意：不要总是说"参与"，要根据用户的真实情况判断。
"""
        response = await self.llm.complete(
            prompt=prompt,
            system="你是一个数字分身，代表主人做决策，要准确模拟主人的决策风格。"
        )

        return self._parse_json_response(response, {
            "decision": "need_more_info",
            "contribution": "",
            "conditions": [],
            "reasoning": "无法解析响应"
        })

    async def generate_feedback(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """模拟方案反馈"""
        profile = self._get_user_profile(user_id)
        proposal = context.get("proposal", {})
        my_assignment = context.get("my_assignment", {})

        prompt = f"""
你是{profile['name']}的数字分身（SecondMe）。

用户性格：{profile['personality']}
决策风格：{profile['decision_style']}

收到了一个协作方案：
方案摘要：{proposal.get('summary', '')}
给你的分配：{my_assignment}

请代表用户决定是否接受，输出JSON格式：
```json
{{
    "feedback_type": "accept 或 negotiate 或 withdraw",
    "adjustment_request": "如果是negotiate，需要调整什么",
    "reasoning": "理由"
}}
```
"""
        response = await self.llm.complete(
            prompt=prompt,
            system="你是一个数字分身，代表主人对方案给出反馈。"
        )

        return self._parse_json_response(response, {
            "feedback_type": "accept",
            "adjustment_request": "",
            "reasoning": "默认接受"
        })

    def _parse_json_response(self, response: str, default: Dict) -> Dict:
        """解析JSON响应"""
        import json
        import re

        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return default


class SimpleRandomMockClient(SecondMeClient):
    """
    简单随机Mock客户端

    不调用LLM，直接返回随机结果，用于压力测试
    """

    async def understand_demand(
        self,
        user_id: str,
        raw_input: str
    ) -> Dict[str, Any]:
        return {
            "surface_demand": raw_input,
            "deep_understanding": {
                "motivation": "测试动机",
                "likely_preferences": ["快速", "简单"],
                "emotional_context": "平静"
            },
            "uncertainties": [],
            "confidence": "high"
        }

    async def generate_response(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        # 70%概率参与
        if random.random() < 0.7:
            return {
                "decision": "participate",
                "contribution": "可以提供帮助",
                "conditions": [],
                "reasoning": "感兴趣"
            }
        else:
            return {
                "decision": "decline",
                "contribution": "",
                "conditions": [],
                "reasoning": "时间不允许"
            }

    async def generate_feedback(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        # 80%概率接受
        if random.random() < 0.8:
            return {
                "feedback_type": "accept",
                "adjustment_request": "",
                "reasoning": "方案可以接受"
            }
        else:
            return {
                "feedback_type": "negotiate",
                "adjustment_request": "希望调整时间",
                "reasoning": "时间有冲突"
            }
```

### 3. Mock数据加载

`scripts/load_mock_profiles.py`:

```python
"""加载Mock用户Profile"""
import json

MOCK_PROFILES = {
    "user-001": {
        "name": "张三",
        "personality": "外向、热情、喜欢组织活动",
        "interests": ["AI", "创业", "社交"],
        "availability": "周末有时间",
        "decision_style": "果断，喜欢新鲜事物",
        "capabilities": ["场地资源", "活动策划"],
        "location": "北京朝阳"
    },
    "user-002": {
        "name": "李四",
        "personality": "内向、专注、技术导向",
        "interests": ["AI", "编程", "开源"],
        "availability": "工作日晚上",
        "decision_style": "谨慎，需要详细信息",
        "capabilities": ["技术分享", "代码贡献"],
        "location": "北京海淀"
    },
    # ... 更多Mock用户
}

def get_mock_profiles():
    return MOCK_PROFILES
```

---

## 验收标准

- [ ] SecondMeClient接口定义完整
- [ ] MockSecondMeClient能够正确模拟三个接口
- [ ] SimpleRandomMockClient可用于压力测试
- [ ] 能够加载和使用Mock用户Profile
- [ ] RealSecondMeClient预留给真实对接

---

## 产出物

- `services/secondme.py` - 客户端接口和实现
- `services/secondme_mock.py` - Mock实现
- `scripts/load_mock_profiles.py` - Mock数据
- 单元测试

---

## 与真实SecondMe对接

当SecondMe团队提供API后，只需：

1. 修改`RealSecondMeClient`的`base_url`
2. 根据实际API格式调整请求/响应处理
3. 在配置中切换客户端类型

```python
# config.py
SECONDME_MODE = "mock"  # "mock" | "real"
SECONDME_API_URL = "https://api.secondme.com"

# 使用
if SECONDME_MODE == "mock":
    client = MockSecondMeClient(llm_service)
else:
    client = RealSecondMeClient(SECONDME_API_URL)
```

---

**创建时间**: 2026-01-21
