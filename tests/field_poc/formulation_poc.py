"""
Formulation POC: 隐式意图能否拯救模糊的显式意图？

四路对比（Genome §6 验证）：

  A. Raw          — 直接编码查询（基线）
  B. LLM-only     — LLM 扩展查询，无 Profile
  C. LLM+Profile  — LLM 读 Profile+查询 → 提取概念关键词
  D. Raw Bundle   — 查询 + 全部 Profile 碎片 → 各自编码 → bundle（纯向量数学，无 LLM）

使用 mpnet-768d + SimHash 10,000-dim binary（comparison POC 最佳策略）。

运行方式：
  cd backend && source venv/bin/activate
  TOWOW_ANTHROPIC_API_KEY=sk-ant-... python ../tests/field_poc/formulation_poc.py
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

# 项目路径设置
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from towow.hdc.encoder import EmbeddingEncoder

try:
    from tests.field_poc.field_poc import load_all_profiles
    from tests.field_poc.test_profiles import FORMULATION_TESTS
    from tests.field_poc.hdc import (
        SimHash, bundle_binary, bundle_dense,
        batch_hamming_similarity, cosine_similarity,
    )
except ModuleNotFoundError:
    from field_poc import load_all_profiles
    from test_profiles import FORMULATION_TESTS
    from hdc import (
        SimHash, bundle_binary, bundle_dense,
        batch_hamming_similarity, cosine_similarity,
    )

# ================================================================
# LLM Formulation
# ================================================================

async def llm_formulate(query: str, profile: str | None, api_key: str, base_url: str | None = None) -> list[str]:
    """
    用 Claude 从查询（+ 可选 Profile）中提取匹配关键词。

    返回 5-10 个概念关键词/短语，用于独立编码后 bundle。
    """
    import anthropic

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    client = anthropic.Anthropic(**kwargs)

    if profile:
        prompt = f"""你是一个意图分析器。用户发出了一段模糊的需求，同时我们有这个用户的历史数据（Profile）。

用户的需求："{query}"

用户的历史数据（碎片化的生活记录）：
{profile}

请从用户的需求和历史数据中，推断用户真正需要什么样的人或能力。
输出 5-10 个搜索关键词或短语，每行一个。这些关键词将用于在人才库中匹配合适的人。

要求：
- 结合用户的显式需求和隐式上下文（历史数据中的兴趣、经历、关注点）
- 关键词要具体、可匹配（如"Shader编程"而不是"技术"）
- 包含用户可能没有明确表达但从历史数据可以推断的需求维度
- 只输出关键词，每行一个，不要编号，不要解释"""
    else:
        prompt = f"""你是一个意图分析器。用户发出了一段模糊的需求。

用户的需求："{query}"

请推断用户可能需要什么样的人或能力。
输出 5-10 个搜索关键词或短语，每行一个。这些关键词将用于在人才库中匹配合适的人。

要求：
- 从模糊需求中推断可能的具体方向
- 关键词要具体、可匹配
- 只输出关键词，每行一个，不要编号，不要解释"""

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    keywords = [line.strip() for line in text.split("\n") if line.strip()]
    return keywords


# ================================================================
# 编码策略
# ================================================================

async def strategy_a_raw(
    encoder: EmbeddingEncoder,
    simhash: SimHash,
    query: str,
) -> np.ndarray:
    """Strategy A: 直接编码查询 → SimHash binary"""
    vec = await encoder.encode(query)
    return simhash.project(vec)


async def strategy_b_llm_only(
    encoder: EmbeddingEncoder,
    simhash: SimHash,
    query: str,
    api_key: str,
    base_url: str | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Strategy B: LLM 扩展查询（无 Profile）→ 每个关键词编码 → bundle"""
    keywords = await llm_formulate(query, None, api_key, base_url)
    if not keywords:
        return await strategy_a_raw(encoder, simhash, query), []

    all_texts = [query] + keywords
    vecs = await encoder.batch_encode(all_texts)
    bins = simhash.batch_project(np.stack(vecs))
    return bundle_binary(bins), keywords


async def strategy_c_llm_profile(
    encoder: EmbeddingEncoder,
    simhash: SimHash,
    query: str,
    profile_fragments: list[str],
    api_key: str,
    base_url: str | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Strategy C: LLM 读 Profile+查询 → 提取概念 → 编码 → bundle"""
    profile_text = "\n".join(f"- {frag}" for frag in profile_fragments)
    keywords = await llm_formulate(query, profile_text, api_key, base_url)
    if not keywords:
        return await strategy_a_raw(encoder, simhash, query), []

    all_texts = [query] + keywords
    vecs = await encoder.batch_encode(all_texts)
    bins = simhash.batch_project(np.stack(vecs))
    return bundle_binary(bins), keywords


async def strategy_d_raw_bundle(
    encoder: EmbeddingEncoder,
    simhash: SimHash,
    query: str,
    profile_fragments: list[str],
) -> np.ndarray:
    """Strategy D: 查询 + 全部 Profile 碎片 → 各自编码 → SimHash → bundle（无 LLM）"""
    all_texts = [query] + profile_fragments
    vecs = await encoder.batch_encode(all_texts)
    bins = simhash.batch_project(np.stack(vecs))
    return bundle_binary(bins)


# ================================================================
# 匹配 + 评估
# ================================================================

def match_binary_topk(
    query_bin: np.ndarray,
    agent_bins: dict[str, np.ndarray],
    k: int = 10,
    D: int = 10_000,
) -> list[tuple[str, float]]:
    """Binary Hamming similarity Top-K"""
    agent_ids = list(agent_bins.keys())
    candidates = [agent_bins[aid] for aid in agent_ids]
    sims = batch_hamming_similarity(query_bin, candidates, D=D)
    indexed = [(agent_ids[i], float(sims[i])) for i in range(len(agent_ids))]
    indexed.sort(key=lambda x: x[1], reverse=True)
    return indexed[:k]


def evaluate_topk(top_k, test):
    """评估一条查询的 Top-K 结果"""
    top_base_ids = [
        aid.split("_", 1)[1] if "_" in aid else aid
        for aid, _ in top_k
    ]
    hits = [eid for eid in test["expected_hits"] if eid in top_base_ids]
    return {
        "hit_count": len(hits),
        "expected_count": len(test["expected_hits"]),
        "min_required": test["min_hits"],
        "passed": len(hits) >= test["min_hits"],
        "hits": hits,
    }


# ================================================================
# 主流程
# ================================================================

async def run_formulation_poc():
    # 检查 API key
    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("TOWOW_ANTHROPIC_BASE_URL", "") or None
    if not api_key:
        print("ERROR: TOWOW_ANTHROPIC_API_KEY not set")
        print("Usage: TOWOW_ANTHROPIC_API_KEY=sk-ant-... python formulation_poc.py")
        sys.exit(1)
    if base_url:
        print(f"  Using base URL: {base_url}")

    print("=" * 80)
    print("Formulation POC: 隐式意图能否拯救模糊的显式意图？")
    print("=" * 80)

    # 1. 加载 Agent 池
    print("\n[1] 加载 Agent 池 + 编码...")
    profiles = load_all_profiles()
    print(f"  {len(profiles)} 个 Agent Profile")

    MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
    DIM = 768
    D = 10_000

    encoder = EmbeddingEncoder(model_name=MODEL_NAME)
    simhash = SimHash(input_dim=DIM, D=D, seed=42)

    # 编码全部 Agent → binary
    agent_ids = list(profiles.keys())
    agent_texts = [profiles[aid] for aid in agent_ids]

    t0 = time.time()
    agent_vecs = await encoder.batch_encode(agent_texts)
    agent_bins_list = simhash.batch_project(np.stack(agent_vecs))
    agent_bins = {aid: bvec for aid, bvec in zip(agent_ids, agent_bins_list)}
    print(f"  Agent 编码完成: {time.time()-t0:.1f}s")

    # 2. 运行测试
    print(f"\n[2] 运行 {len(FORMULATION_TESTS)} 条 Formulation 测试...")

    strategies = ["A_raw", "B_llm_only", "C_llm_profile", "D_raw_bundle"]
    all_results: dict[str, list[dict]] = {s: [] for s in strategies}
    all_keywords: dict[str, dict] = {}  # 记录 LLM 输出的关键词

    for i, test in enumerate(FORMULATION_TESTS):
        query = test["query"]
        frags = test["profile_fragments"]
        print(f"\n  Q{i+1} [{test['level']}]: \"{query}\"")
        print(f"    Profile: {len(frags)} 碎片, ~{sum(len(f) for f in frags)} 字")

        test_keywords = {}

        # Strategy A: Raw
        t0 = time.time()
        q_bin_a = await strategy_a_raw(encoder, simhash, query)
        top_k_a = match_binary_topk(q_bin_a, agent_bins)
        ev_a = evaluate_topk(top_k_a, test)
        ev_a["time_ms"] = (time.time() - t0) * 1000
        ev_a["query"] = query
        ev_a["level"] = test["level"]
        ev_a["top5"] = [(aid, f"{s:.4f}") for aid, s in top_k_a[:5]]
        all_results["A_raw"].append(ev_a)

        status_a = "PASS" if ev_a["passed"] else "FAIL"
        print(f"    A_raw:        {status_a} {ev_a['hit_count']}/{ev_a['expected_count']}")

        # Strategy B: LLM-only
        t0 = time.time()
        q_bin_b, b_keywords = await strategy_b_llm_only(encoder, simhash, query, api_key, base_url)
        top_k_b = match_binary_topk(q_bin_b, agent_bins)
        ev_b = evaluate_topk(top_k_b, test)
        ev_b["time_ms"] = (time.time() - t0) * 1000
        ev_b["query"] = query
        ev_b["level"] = test["level"]
        ev_b["top5"] = [(aid, f"{s:.4f}") for aid, s in top_k_b[:5]]
        ev_b["keywords"] = b_keywords
        test_keywords["B_llm_only"] = b_keywords
        all_results["B_llm_only"].append(ev_b)

        status_b = "PASS" if ev_b["passed"] else "FAIL"
        print(f"    B_llm_only:   {status_b} {ev_b['hit_count']}/{ev_b['expected_count']}  keywords={b_keywords[:3]}...")

        # Strategy C: LLM+Profile
        t0 = time.time()
        q_bin_c, c_keywords = await strategy_c_llm_profile(encoder, simhash, query, frags, api_key, base_url)
        top_k_c = match_binary_topk(q_bin_c, agent_bins)
        ev_c = evaluate_topk(top_k_c, test)
        ev_c["time_ms"] = (time.time() - t0) * 1000
        ev_c["query"] = query
        ev_c["level"] = test["level"]
        ev_c["top5"] = [(aid, f"{s:.4f}") for aid, s in top_k_c[:5]]
        ev_c["keywords"] = c_keywords
        test_keywords["C_llm_profile"] = c_keywords
        all_results["C_llm_profile"].append(ev_c)

        status_c = "PASS" if ev_c["passed"] else "FAIL"
        print(f"    C_llm_profile:{status_c} {ev_c['hit_count']}/{ev_c['expected_count']}  keywords={c_keywords[:3]}...")

        # Strategy D: Raw Bundle
        t0 = time.time()
        q_bin_d = await strategy_d_raw_bundle(encoder, simhash, query, frags)
        top_k_d = match_binary_topk(q_bin_d, agent_bins)
        ev_d = evaluate_topk(top_k_d, test)
        ev_d["time_ms"] = (time.time() - t0) * 1000
        ev_d["query"] = query
        ev_d["level"] = test["level"]
        ev_d["top5"] = [(aid, f"{s:.4f}") for aid, s in top_k_d[:5]]
        all_results["D_raw_bundle"].append(ev_d)

        status_d = "PASS" if ev_d["passed"] else "FAIL"
        print(f"    D_raw_bundle: {status_d} {ev_d['hit_count']}/{ev_d['expected_count']}  ({len(frags)+1} chunks bundled)")

        all_keywords[f"Q{i+1}"] = test_keywords

    # ================================================================
    # 汇总报告
    # ================================================================
    print("\n\n" + "=" * 80)
    print("汇总报告")
    print("=" * 80)

    # 对比表
    levels = sorted(set(t["level"] for t in FORMULATION_TESTS))

    header = f"{'Strategy':<22}"
    for level in levels:
        header += f" | {level:>5}"
    header += f" | {'Total':>7} | {'Hits':>10}"
    print(f"\n{header}")
    print("-" * len(header))

    summary = {}
    for sname in strategies:
        by_level: dict[str, dict] = {}
        for r in all_results[sname]:
            level = r["level"]
            by_level.setdefault(level, {"passed": 0, "total": 0, "hits": 0, "expected": 0})
            by_level[level]["total"] += 1
            by_level[level]["hits"] += r["hit_count"]
            by_level[level]["expected"] += r["expected_count"]
            if r["passed"]:
                by_level[level]["passed"] += 1
        total_passed = sum(d["passed"] for d in by_level.values())
        total_queries = sum(d["total"] for d in by_level.values())
        total_hits = sum(d["hits"] for d in by_level.values())
        total_expected = sum(d["expected"] for d in by_level.values())
        summary[sname] = {
            "by_level": by_level,
            "total_passed": total_passed,
            "total_queries": total_queries,
            "total_hits": total_hits,
            "total_expected": total_expected,
        }

        row = f"{sname:<22}"
        for level in levels:
            ld = by_level.get(level, {"passed": 0, "total": 0})
            row += f" | {ld['passed']}/{ld['total']:>2}"
        row += f" | {total_passed:>3}/{total_queries:>2}"
        row += f" | {total_hits:>3}/{total_expected:>3}"
        print(row)

    # LLM 关键词对比
    print(f"\n\n{'=' * 80}")
    print("LLM 关键词对比（B vs C）")
    print("=" * 80)

    for qi, test in enumerate(FORMULATION_TESTS):
        qkey = f"Q{qi+1}"
        kw = all_keywords.get(qkey, {})
        print(f"\n  {qkey} [{test['level']}]: \"{test['query']}\"")
        print(f"    B (LLM only):   {kw.get('B_llm_only', [])}")
        print(f"    C (LLM+Profile):{kw.get('C_llm_profile', [])}")

    # Top-5 对比
    print(f"\n\n{'=' * 80}")
    print("Top-5 详细对比")
    print("=" * 80)

    for qi, test in enumerate(FORMULATION_TESTS):
        print(f"\n  Q{qi+1} [{test['level']}]: \"{test['query']}\"")
        print(f"    Expected: {test['expected_hits']}")
        for sname in strategies:
            r = all_results[sname][qi]
            status = "PASS" if r["passed"] else "FAIL"
            top5_display = []
            for aid, score in r["top5"]:
                base = aid.split("_", 1)[1] if "_" in aid else aid
                marker = " *" if base in test["expected_hits"] else ""
                top5_display.append(f"{aid}({score}){marker}")
            print(f"    {status} {sname:<20} [{r['hit_count']}/{r['expected_count']}] {', '.join(top5_display[:3])}")

    # 写入结果
    output_path = PROJECT_ROOT / "tests" / "field_poc" / "formulation_results.json"
    output = {
        "config": {
            "model": MODEL_NAME,
            "dim": DIM,
            "hdc_dim": D,
            "llm_model": "claude-sonnet-4-5-20250929",
            "base_url": base_url or "anthropic-default",
        },
        "summary": summary,
        "keywords": all_keywords,
        "details": {sname: results for sname, results in all_results.items()},
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n\n结果写入: {output_path}")


if __name__ == "__main__":
    asyncio.run(run_formulation_poc())
