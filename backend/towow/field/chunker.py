"""
文本切分 — text → list[str]。

短文本（≤ max_chars）整体作为一个 chunk。
长文本按句号/换行切分，相邻短句合并至 max_chars 以内。
零 LLM 调用。
"""

from __future__ import annotations

import re

# mpnet 有效窗口约 128 tokens ≈ 200-300 中文字符
_DEFAULT_MAX_CHARS = 256

# 中英文句子边界
_SENTENCE_SPLIT = re.compile(r"(?<=[。！？；\n.!?;])\s*")


def split_chunks(text: str, max_chars: int = _DEFAULT_MAX_CHARS) -> list[str]:
    """
    文本 → 语义块列表。

    - 短文本不切分
    - 长文本按句子边界切分，相邻短句合并
    - 返回至少一个 chunk（除非输入为空）
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentences = _SENTENCE_SPLIT.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks: list[str] = []
    current = sentences[0]

    for sent in sentences[1:]:
        # 尝试合并到当前 chunk
        merged = current + " " + sent
        if len(merged) <= max_chars:
            current = merged
        else:
            chunks.append(current)
            current = sent

    if current:
        chunks.append(current)

    return chunks if chunks else [text]
