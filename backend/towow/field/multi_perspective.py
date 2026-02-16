"""
多视角查询生成 — 将用户需求扩展为 3 个搜索视角。

ADR-012 核心决策：三种关系（共振/互补/干涉）不在编码层解决，
在查询层用 LLM 一次调用解决。

三个视角：
- 共振 (resonance): 直接技能/专业匹配，改写为精准关键词
- 互补 (complement): "我缺什么→谁有什么"，需求→能力方向的反转
- 干涉 (interference): 跨域深层关联，意外但有价值的连接

用法：
    generator = MultiPerspectiveGenerator(llm_client)
    result = await generator.generate("帮我部署一个能扛大流量的后端")
    # result.resonance = "后端架构 高并发 分布式系统 ..."
    # result.complement = "Kubernetes 容器编排 性能调优 ..."
    # result.interference = "安全审计 用户行为分析 ..."
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Prompt 模板：一次调用生成 3 个视角
_SYSTEM_PROMPT = """\
你是通爻网络的查询扩展专家。通爻是一个人才协作网络，用户发出需求，系统通过向量匹配找到能响应的人。

你的任务：将用户的一句话需求，扩展为 3 个不同视角的搜索查询。每个查询会被独立编码为向量，在人才库中搜索匹配的人。

三个视角：

1. **共振 (resonance)**：直接匹配。把需求改写为精准的技能和专业领域关键词。
   - 目标：找到技能描述与需求直接对应的人
   - 方法：提取核心技术栈、专业领域、具体工具名

2. **互补 (complement)**：能力反转。思考"满足这个需求需要什么能力"，然后搜索拥有这些能力的人。
   - 目标：找到能填补需求缺口的人
   - 方法：从需求推导所需能力，用能力描述去搜索

3. **干涉 (interference)**：跨域关联。思考哪些看似无关的领域可能为这个需求带来意外价值。
   - 目标：发现用户自己想不到的有价值的人
   - 方法：跨学科联想、类比思维、边缘交叉领域

每个查询应该是一段 30-80 字的中文描述（不是关键词列表），像在描述一个人的能力画像。

输出严格 JSON 格式：
{"resonance": "...", "complement": "...", "interference": "..."}

只输出 JSON，不要其他文字。"""


@dataclass
class MultiPerspectiveResult:
    """多视角查询生成结果。"""
    original: str
    resonance: str
    complement: str
    interference: str

    def all_queries(self) -> list[str]:
        """返回所有查询（含原始），用于批量搜索。"""
        return [self.original, self.resonance, self.complement, self.interference]

    def expanded_queries(self) -> list[str]:
        """返回 3 个扩展查询（不含原始）。"""
        return [self.resonance, self.complement, self.interference]


class MultiPerspectiveGenerator:
    """将用户需求扩展为多视角搜索查询。需要 ClaudePlatformClient。"""

    def __init__(self, llm_client) -> None:
        self._llm = llm_client

    async def generate(self, demand_text: str) -> MultiPerspectiveResult:
        """一次 LLM 调用生成 3 个搜索视角。"""
        response = await self._llm.chat(
            messages=[{"role": "user", "content": demand_text}],
            system_prompt=_SYSTEM_PROMPT,
        )

        content = response.get("content", "")
        if not content:
            logger.warning("LLM returned empty content for multi-perspective generation")
            return self._fallback(demand_text)

        try:
            # LLM 常返回 ```json...``` 包裹的 JSON，需要剥离
            text = content.strip()
            if text.startswith("```"):
                # 去掉 ```json\n 和末尾 ```
                lines = text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines)
            parsed = json.loads(text)
            return MultiPerspectiveResult(
                original=demand_text,
                resonance=parsed["resonance"],
                complement=parsed["complement"],
                interference=parsed["interference"],
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse multi-perspective JSON: %s | content: %s", e, content[:200])
            return self._fallback(demand_text)

    def _fallback(self, demand_text: str) -> MultiPerspectiveResult:
        """解析失败时的降级：3 个视角都用原始文本。"""
        return MultiPerspectiveResult(
            original=demand_text,
            resonance=demand_text,
            complement=demand_text,
            interference=demand_text,
        )
