"""
EXP-008: LLM-as-Judge 评估实验

假说: H1: 多视角查询在 LLM 裁判评分下的"总发现价值"≥ 单查询
设计: 配对实验 — 同一组匹配结果, 同一裁判
变量: 单查询 top-10 vs 多视角 top-10 的 LLM 裁判总价值评分
控制: BGE-M3-1024d + SimHash(D=10000), 447 agents, 20 queries

三阶段执行：
  Phase 1 — 跑匹配, 捕获 owner 列表（无需 API key）:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python ../tests/field_poc/exp008_llm_judge.py --match

  Phase 2 — LLM 裁判评分（需要 API key）:
    cd backend && source venv/bin/activate
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=. python ../tests/field_poc/exp008_llm_judge.py --judge

  Phase 3 — 分析结果（用缓存，无需 API）:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python ../tests/field_poc/exp008_llm_judge.py

关联: ADR-013 决策 3 — LLM-as-Judge 为主评估，结构性指标为辅
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from towow.field import (
    BgeM3Encoder,
    EncodingPipeline,
    MemoryField,
    SimHashProjector,
    load_all_profiles,
)

try:
    from tests.field_poc.test_queries import TEST_QUERIES
except ModuleNotFoundError:
    from test_queries import TEST_QUERIES

# ================================================================
# 配置
# ================================================================

BGE_M3_LOCAL = str(BACKEND_DIR / "models" / "bge-m3")
SIMHASH_D = 10_000
SIMHASH_SEED = 42
TOP_K = 10

RESULTS_DIR = Path(__file__).parent / "results"
MATCH_CACHE = RESULTS_DIR / "EXP-008_match_cache.json"
JUDGE_CACHE = RESULTS_DIR / "EXP-008_judge_cache.json"
RESULT_FILE = RESULTS_DIR / "EXP-008_llm_judge.json"
PERSPECTIVES_CACHE = RESULTS_DIR / "EXP-007_perspectives_cache.json"

_SCENE_PREFIXES = ("h_", "s_", "r_", "m_")

# LLM Judge 使用 Sonnet — 评估质量比速度重要
JUDGE_MODEL = "claude-sonnet-4-5-20250929"
JUDGE_MAX_TOKENS = 4096


def _strip_prefix(owner: str) -> str:
    for prefix in _SCENE_PREFIXES:
        if owner.startswith(prefix):
            return owner[len(prefix):]
    return owner


# ================================================================
# Judge System Prompt
# ================================================================

JUDGE_SYSTEM_PROMPT = """你是一位人才匹配评估专家。

你的任务：给定一个用户需求和一组候选人画像，独立评估每位候选人对这个需求的价值。

## 评分维度（每项 1-5 分）

### 直接相关性 (direct_relevance)
这个人的技能和经验能直接帮到这件事吗？
- 5: 技能完全对口，可以立即上手
- 4: 技能高度相关，稍作适配即可
- 3: 有一定相关性，但需要较多适配
- 2: 相关性较弱，只有部分技能沾边
- 1: 完全不相关

### 互补价值 (complementary_value)
这个人能带来用户没有明确要求、但实际有用的技能或视角吗？
- 5: 填补了需求中没说出来但明显存在的缺口（比如：做网站的人需要设计师但没说）
- 4: 带来有价值的补充技能或视角
- 3: 有一些额外贡献
- 2: 额外价值有限
- 1: 没有互补作用

### 意外发现价值 (serendipity)
这个匹配是否让人眼前一亮？用户自己不会去找这种人，但发现后会觉得"原来还能这样"。
- 5: 跨领域的惊喜关联，一看就有启发（如：做游戏的人匹配到建筑空间设计师）
- 4: 意想不到但确实有价值
- 3: 有点新意
- 2: 基本在预期范围内
- 1: 完全可预期，或完全无关联

## 重要原则
- 三个维度独立评分。一个人可以直接相关性低但意外发现价值高
- "直接相关性低"不代表没价值——意外发现是独立的价值维度
- 不要因为某人"不是用户会搜索的类型"就给低分——恰恰相反，这可能是高 serendipity 信号
- 根据候选人画像中的实际信息评分，不要臆造候选人没有的能力

## 输出格式
输出一个 JSON 数组，每个元素：
[
  {
    "agent_id": "候选人ID",
    "direct_relevance": 1-5,
    "complementary_value": 1-5,
    "serendipity": 1-5,
    "rationale": "一句话理由"
  }
]

只输出 JSON 数组，不要 markdown fence，不要其他内容。"""


# ================================================================
# Phase 1: 匹配 — 捕获 owner 列表
# ================================================================

async def phase_match():
    """Re-run single + multi matching, save per-query owner lists."""
    print("=" * 70)
    print("EXP-008 Phase 1: Matching — capture owner lists")
    print("=" * 70)

    # 加载视角缓存
    if not PERSPECTIVES_CACHE.exists():
        print(f"ERROR: Perspectives cache not found: {PERSPECTIVES_CACHE}")
        print("Run EXP-007 --generate first")
        sys.exit(1)
    with open(PERSPECTIVES_CACHE, encoding="utf-8") as f:
        perspectives = json.load(f)

    # 构建 Field
    print("\n  Loading encoder...")
    encoder = BgeM3Encoder(model_path=BGE_M3_LOCAL)
    projector = SimHashProjector(
        input_dim=encoder.dim, D=SIMHASH_D, seed=SIMHASH_SEED
    )
    pipeline = EncodingPipeline(encoder=encoder, projector=projector)

    print("  Loading profiles...")
    profiles = load_all_profiles()
    print(f"  {len(profiles)} profiles loaded")

    print("  Building field...")
    field = MemoryField(pipeline=pipeline)
    for owner, text in profiles.items():
        await field.deposit(text=text, owner=owner)
    n_intents = await field.count()
    n_owners = await field.count_owners()
    print(f"  Field: {n_intents} intents, {n_owners} owners")

    # 逐查询匹配
    cache = []
    for i, (q, persp) in enumerate(zip(TEST_QUERIES, perspectives)):
        query_text = q["query"]
        level = q["level"]
        print(f"\n  Q{i+1:02d} [{level}]: \"{query_text}\"")

        # Single query
        single_results = await field.match_owners(query_text, k=TOP_K)
        single_owners = [r.owner for r in single_results]

        # Multi perspective queries
        all_multi = []
        for perspective_key in ("resonance", "complement", "interference"):
            p_text = persp[perspective_key]
            results = await field.match_owners(p_text, k=TOP_K)
            all_multi.append(results)

        # Also include original query in multi
        orig_results = await field.match_owners(query_text, k=TOP_K)
        all_multi.append(orig_results)

        # Merge: max-score dedup, top-K
        owner_best_score: dict[str, float] = {}
        for results in all_multi:
            for r in results:
                if r.owner not in owner_best_score or r.score > owner_best_score[r.owner]:
                    owner_best_score[r.owner] = r.score
        sorted_multi = sorted(owner_best_score.items(), key=lambda x: x[1], reverse=True)
        multi_owners = [owner for owner, _ in sorted_multi[:TOP_K]]

        # Stats
        single_stripped = [_strip_prefix(o) for o in single_owners]
        multi_stripped = [_strip_prefix(o) for o in multi_owners]
        expected = set(q["expected_hits"])
        s_hits = len(expected & set(single_stripped)) if expected else 0
        m_hits = len(expected & set(multi_stripped)) if expected else 0
        overlap = set(single_owners) & set(multi_owners)

        print(f"    Single hits: {s_hits}/{len(expected)}, Multi hits: {m_hits}/{len(expected)}")
        print(f"    Overlap: {len(overlap)}/{TOP_K} owners in common")

        entry = {
            "query": query_text,
            "level": level,
            "expected_hits": q["expected_hits"],
            "min_hits": q["min_hits"],
            "single_owners": single_owners,
            "multi_owners": multi_owners,
            "single_expected_hits": s_hits,
            "multi_expected_hits": m_hits,
        }
        cache.append(entry)

    # Save
    RESULTS_DIR.mkdir(exist_ok=True)
    with open(MATCH_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"\n  Match cache saved: {MATCH_CACHE}")

    # Also save profile text for judge phase
    profile_cache_path = RESULTS_DIR / "EXP-008_profiles.json"
    # Collect only profiles that appear in results
    needed_owners = set()
    for entry in cache:
        needed_owners.update(entry["single_owners"])
        needed_owners.update(entry["multi_owners"])
    needed_profiles = {k: v for k, v in profiles.items() if k in needed_owners}
    with open(profile_cache_path, "w", encoding="utf-8") as f:
        json.dump(needed_profiles, f, ensure_ascii=False, indent=2)
    print(f"  Profiles cache saved: {profile_cache_path} ({len(needed_profiles)} agents)")


# ================================================================
# Phase 2: LLM 裁判评分
# ================================================================

def _parse_judge_response(text: str) -> list[dict]:
    """Parse JSON array from LLM response, tolerating markdown fences."""
    text = text.strip()
    # Strip markdown code fence if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        return [result]
    except json.JSONDecodeError as e:
        print(f"    WARNING: JSON parse failed: {e}")
        print(f"    Raw text (first 200): {text[:200]}")
        return []


async def phase_judge():
    """Call LLM judge on each (query, agent_set) pair."""
    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: TOWOW_ANTHROPIC_API_KEY not set")
        sys.exit(1)

    if not MATCH_CACHE.exists():
        print(f"ERROR: Match cache not found: {MATCH_CACHE}")
        print("Run with --match first")
        sys.exit(1)

    with open(MATCH_CACHE, encoding="utf-8") as f:
        match_data = json.load(f)

    profile_cache_path = RESULTS_DIR / "EXP-008_profiles.json"
    with open(profile_cache_path, encoding="utf-8") as f:
        profiles = json.load(f)

    from towow.infra.llm_client import ClaudePlatformClient
    llm = ClaudePlatformClient(
        api_key=api_key, model=JUDGE_MODEL, max_tokens=JUDGE_MAX_TOKENS
    )

    print("=" * 70)
    print("EXP-008 Phase 2: LLM Judge scoring")
    print(f"  Model: {JUDGE_MODEL}")
    print(f"  Queries: {len(match_data)}")
    print("=" * 70)

    judge_results = []
    total_calls = 0
    total_agents_judged = 0

    for i, entry in enumerate(match_data):
        query = entry["query"]
        level = entry["level"]
        print(f"\n  Q{i+1:02d} [{level}]: \"{query}\"")

        # Union of single and multi owners — judge each only once
        all_owners = list(dict.fromkeys(
            entry["single_owners"] + entry["multi_owners"]
        ))
        print(f"    Judging {len(all_owners)} unique agents (single ∪ multi)")

        # Build agent profile text for the prompt
        agent_lines = []
        for idx, owner in enumerate(all_owners):
            profile_text = profiles.get(owner, "(画像不可用)")
            # Truncate very long profiles
            if len(profile_text) > 500:
                profile_text = profile_text[:500] + "..."
            agent_lines.append(f"### 候选人 {idx+1}: {owner}\n{profile_text}")

        agents_text = "\n\n".join(agent_lines)
        user_msg = f"## 用户需求\n{query}\n\n## 候选人列表\n{agents_text}\n\n请评估每个候选人。"

        # Call LLM judge
        t0 = time.monotonic()
        try:
            response = await llm.chat(
                messages=[{"role": "user", "content": user_msg}],
                system_prompt=JUDGE_SYSTEM_PROMPT,
            )
            elapsed = time.monotonic() - t0
            total_calls += 1

            scores = _parse_judge_response(response.get("content", ""))
            print(f"    Got {len(scores)} scores in {elapsed:.1f}s")

            # Build owner → scores map
            scores_by_id = {}
            for s in scores:
                aid = s.get("agent_id", "")
                scores_by_id[aid] = {
                    "direct_relevance": s.get("direct_relevance", 0),
                    "complementary_value": s.get("complementary_value", 0),
                    "serendipity": s.get("serendipity", 0),
                    "rationale": s.get("rationale", ""),
                }

            # Match scores back to owners (handle LLM returning slightly different IDs)
            owner_scores = {}
            for owner in all_owners:
                if owner in scores_by_id:
                    owner_scores[owner] = scores_by_id[owner]
                elif _strip_prefix(owner) in scores_by_id:
                    owner_scores[owner] = scores_by_id[_strip_prefix(owner)]
                else:
                    # Try matching by index order
                    idx_in_list = all_owners.index(owner)
                    if idx_in_list < len(scores):
                        s = scores[idx_in_list]
                        owner_scores[owner] = {
                            "direct_relevance": s.get("direct_relevance", 0),
                            "complementary_value": s.get("complementary_value", 0),
                            "serendipity": s.get("serendipity", 0),
                            "rationale": s.get("rationale", ""),
                        }
                    else:
                        owner_scores[owner] = {
                            "direct_relevance": 0,
                            "complementary_value": 0,
                            "serendipity": 0,
                            "rationale": "MISS: judge did not score this agent",
                        }
                        print(f"    WARNING: No score for {owner}")

            total_agents_judged += len(owner_scores)

            judge_results.append({
                "query": query,
                "level": level,
                "single_owners": entry["single_owners"],
                "multi_owners": entry["multi_owners"],
                "expected_hits": entry["expected_hits"],
                "scores": owner_scores,
            })

        except Exception as e:
            elapsed = time.monotonic() - t0
            print(f"    ERROR after {elapsed:.1f}s: {e}")
            judge_results.append({
                "query": query,
                "level": level,
                "single_owners": entry["single_owners"],
                "multi_owners": entry["multi_owners"],
                "expected_hits": entry["expected_hits"],
                "scores": {},
                "error": str(e),
            })

    # Save
    with open(JUDGE_CACHE, "w", encoding="utf-8") as f:
        json.dump(judge_results, f, ensure_ascii=False, indent=2)
    print(f"\n  Judge cache saved: {JUDGE_CACHE}")
    print(f"  Total LLM calls: {total_calls}")
    print(f"  Total agents judged: {total_agents_judged}")


# ================================================================
# Phase 3: 分析结果
# ================================================================

def _total_value(scores: dict) -> float:
    """Sum of 3 dimensions."""
    return (
        scores.get("direct_relevance", 0)
        + scores.get("complementary_value", 0)
        + scores.get("serendipity", 0)
    )


def phase_analyze():
    """Analyze judge scores, compare single vs multi total value."""
    if not JUDGE_CACHE.exists():
        print(f"ERROR: Judge cache not found: {JUDGE_CACHE}")
        print("Run with --judge first")
        sys.exit(1)

    with open(JUDGE_CACHE, encoding="utf-8") as f:
        judge_data = json.load(f)

    print("=" * 70)
    print("EXP-008 Phase 3: Analysis — Single vs Multi total value")
    print("=" * 70)

    # Per-query analysis
    per_query = []
    single_totals = []
    multi_totals = []

    for entry in judge_data:
        query = entry["query"]
        level = entry["level"]
        scores = entry.get("scores", {})

        if not scores:
            print(f"\n  SKIP [{level}] \"{query}\" — no scores (error)")
            continue

        # Calculate total value for single top-10
        s_value = 0.0
        s_direct = 0.0
        s_complement = 0.0
        s_serendipity = 0.0
        s_count = 0
        for owner in entry["single_owners"]:
            if owner in scores:
                s = scores[owner]
                s_value += _total_value(s)
                s_direct += s.get("direct_relevance", 0)
                s_complement += s.get("complementary_value", 0)
                s_serendipity += s.get("serendipity", 0)
                s_count += 1

        # Calculate total value for multi top-10
        m_value = 0.0
        m_direct = 0.0
        m_complement = 0.0
        m_serendipity = 0.0
        m_count = 0
        for owner in entry["multi_owners"]:
            if owner in scores:
                s = scores[owner]
                m_value += _total_value(s)
                m_direct += s.get("direct_relevance", 0)
                m_complement += s.get("complementary_value", 0)
                m_serendipity += s.get("serendipity", 0)
                m_count += 1

        delta = m_value - s_value

        print(f"\n  [{level}] \"{query}\"")
        print(f"    Single: total={s_value:.0f} (direct={s_direct:.0f}, complement={s_complement:.0f}, serendipity={s_serendipity:.0f}) [{s_count} agents]")
        print(f"    Multi:  total={m_value:.0f} (direct={m_direct:.0f}, complement={m_complement:.0f}, serendipity={m_serendipity:.0f}) [{m_count} agents]")
        print(f"    Delta:  {delta:+.0f} {'✓ multi better' if delta > 0 else '✗ single better' if delta < 0 else '= tie'}")

        # Structural metrics
        high_serendipity_single = sum(
            1 for o in entry["single_owners"]
            if o in scores and scores[o].get("serendipity", 0) >= 3
        )
        high_serendipity_multi = sum(
            1 for o in entry["multi_owners"]
            if o in scores and scores[o].get("serendipity", 0) >= 3
        )

        single_totals.append(s_value)
        multi_totals.append(m_value)

        per_query.append({
            "query": query,
            "level": level,
            "single_total_value": s_value,
            "multi_total_value": m_value,
            "delta": delta,
            "single_breakdown": {
                "direct": s_direct,
                "complement": s_complement,
                "serendipity": s_serendipity,
            },
            "multi_breakdown": {
                "direct": m_direct,
                "complement": m_complement,
                "serendipity": m_serendipity,
            },
            "high_serendipity_single": high_serendipity_single,
            "high_serendipity_multi": high_serendipity_multi,
            "expected_hit_precision": {
                "single": entry.get("single_expected_hits", 0),
                "multi": entry.get("multi_expected_hits", 0),
            } if "single_expected_hits" in entry else None,
        })

    # Aggregate
    single_arr = np.array(single_totals)
    multi_arr = np.array(multi_totals)
    n = len(single_arr)

    if n == 0:
        print("\n  ERROR: No valid queries to analyze")
        return

    # Paired bootstrap CI
    deltas = multi_arr - single_arr
    rng = np.random.RandomState(42)
    n_bootstrap = 10000
    boot_means = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(deltas, size=n, replace=True)
        boot_means[i] = np.mean(sample)
    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))
    mean_delta = float(np.mean(deltas))
    significant = (ci_lower > 0) or (ci_upper < 0)

    # Per-level aggregation
    level_results = {}
    for level in ["L1", "L2", "L3", "L4"]:
        level_single = [pq["single_total_value"] for pq in per_query if pq["level"] == level]
        level_multi = [pq["multi_total_value"] for pq in per_query if pq["level"] == level]
        if level_single:
            level_results[level] = {
                "single_mean": float(np.mean(level_single)),
                "multi_mean": float(np.mean(level_multi)),
                "delta_mean": float(np.mean(np.array(level_multi) - np.array(level_single))),
                "n": len(level_single),
            }

    # Multi wins / ties / losses
    multi_wins = int(np.sum(deltas > 0))
    ties = int(np.sum(deltas == 0))
    single_wins = int(np.sum(deltas < 0))

    # Aggregate serendipity comparison
    total_high_s_single = sum(pq["high_serendipity_single"] for pq in per_query)
    total_high_s_multi = sum(pq["high_serendipity_multi"] for pq in per_query)

    print("\n" + "=" * 70)
    print("AGGREGATE RESULTS")
    print("=" * 70)
    print(f"\n  Queries analyzed: {n}")
    print(f"\n  Total Value (sum of 3 dimensions across top-10):")
    print(f"    Single mean: {float(np.mean(single_arr)):.1f}")
    print(f"    Multi  mean: {float(np.mean(multi_arr)):.1f}")
    print(f"    Delta:       {mean_delta:+.1f}, 95% CI [{ci_lower:+.1f}, {ci_upper:+.1f}]")
    print(f"    Significant: {'YES' if significant else 'NO'}")
    print(f"\n  Win/Tie/Loss:  Multi {multi_wins} / {ties} / {single_wins} Single")
    print(f"\n  High serendipity (≥3) agents:")
    print(f"    Single: {total_high_s_single} total")
    print(f"    Multi:  {total_high_s_multi} total")
    print(f"\n  Per-level:")
    for level, lr in sorted(level_results.items()):
        print(f"    {level}: single={lr['single_mean']:.1f}, multi={lr['multi_mean']:.1f}, delta={lr['delta_mean']:+.1f} (n={lr['n']})")

    # H1 verdict
    h1_supported = mean_delta >= 0 and ci_lower >= 0
    h1_verdict = "SUPPORTED" if h1_supported else "NOT SUPPORTED (but see analysis)"
    print(f"\n  H1 (multi total_value ≥ single): {h1_verdict}")

    # Insight: compare precision@K verdict with total_value verdict
    print(f"\n  Comparison of two evaluation frameworks:")
    print(f"    precision@K (EXP-007):  multi WORSE by -30pp (significant)")
    print(f"    total_value (EXP-008):  multi {'BETTER' if mean_delta > 0 else 'WORSE'} by {mean_delta:+.1f}")
    if mean_delta > 0:
        print(f"    → DIVERGENT VERDICTS: precision@K says multi is worse,")
        print(f"      but LLM judge says multi finds more total value.")
        print(f"      This confirms ADR-013: search metrics undervalue response-paradigm systems.")

    # Save results
    result = {
        "experiment": "EXP-008",
        "hypothesis": "H1: multi total_value >= single total_value (LLM-as-Judge)",
        "date": time.strftime("%Y-%m-%d"),
        "config": {
            "judge_model": JUDGE_MODEL,
            "encoder": "bge-m3-1024d",
            "projector": "simhash-10000d",
            "n_agents": 447,
            "n_queries": n,
            "top_k": TOP_K,
            "scoring_dimensions": ["direct_relevance", "complementary_value", "serendipity"],
            "value_range_per_agent": "3-15 (sum of 3 dimensions, each 1-5)",
        },
        "results": {
            "total_value": {
                "single_mean": float(np.mean(single_arr)),
                "multi_mean": float(np.mean(multi_arr)),
                "single_std": float(np.std(single_arr)),
                "multi_std": float(np.std(multi_arr)),
            },
            "paired_bootstrap": {
                "mean_delta": mean_delta,
                "ci_95_lower": ci_lower,
                "ci_95_upper": ci_upper,
                "significant": significant,
            },
            "win_tie_loss": {
                "multi_wins": multi_wins,
                "ties": ties,
                "single_wins": single_wins,
            },
            "high_serendipity_agents": {
                "single_total": total_high_s_single,
                "multi_total": total_high_s_multi,
            },
            "per_level": level_results,
            "h1_supported": h1_supported,
        },
        "comparison_with_precision_k": {
            "precision_k_verdict": "multi significantly worse (-30pp)",
            "total_value_verdict": f"multi {'better' if mean_delta > 0 else 'worse'} ({mean_delta:+.1f})",
            "verdicts_diverge": mean_delta > 0,
        },
        "per_query": per_query,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  Results saved: {RESULT_FILE}")


# ================================================================
# Main
# ================================================================

def main():
    args = sys.argv[1:]
    if "--match" in args:
        asyncio.run(phase_match())
    elif "--judge" in args:
        asyncio.run(phase_judge())
    else:
        phase_analyze()


if __name__ == "__main__":
    main()
