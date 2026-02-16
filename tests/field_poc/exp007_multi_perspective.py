"""
EXP-007: 多视角查询生成效果实验

假说: H1: 多视角查询在 L3 命中率 ≥ 基线(单查询) + 20 个百分点
设计: 配对实验 — 同一 Field、同一查询集
变量: 单查询 vs 多视角查询(原始 + 共振 + 互补 + 干涉，合并去重 top-10)
控制: BGE-M3-1024d + SimHash(D=10000), 447 agents, 20 queries

两阶段执行：
  Phase 1 — 生成视角（需要 API key）:
    cd backend && source venv/bin/activate
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... PYTHONPATH=. python ../tests/field_poc/exp007_multi_perspective.py --generate

  Phase 2 — 跑匹配对比（用缓存的视角，无需 API）:
    cd backend && source venv/bin/activate
    PYTHONPATH=. python ../tests/field_poc/exp007_multi_perspective.py
"""

from __future__ import annotations

import asyncio
import json
import os
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
    MultiPerspectiveGenerator,
    SimHashProjector,
    load_all_profiles,
)

try:
    from tests.field_poc.test_queries import TEST_QUERIES
except ModuleNotFoundError:
    from test_queries import TEST_QUERIES

# 配置
BGE_M3_LOCAL = str(BACKEND_DIR / "models" / "bge-m3")
SIMHASH_D = 10_000
SIMHASH_SEED = 42
TOP_K = 10

CACHE_FILE = Path(__file__).parent / "results" / "EXP-007_perspectives_cache.json"
RESULT_FILE = Path(__file__).parent / "results" / "EXP-007_multi_perspective.json"

_SCENE_PREFIXES = ("h_", "s_", "r_", "m_")


def _strip_prefix(owner: str) -> str:
    for prefix in _SCENE_PREFIXES:
        if owner.startswith(prefix):
            return owner[len(prefix):]
    return owner


def evaluate_query_owners(owner_results: list, query_spec: dict) -> dict:
    raw_owners = [r.owner for r in owner_results[:TOP_K]]
    result_owners = [_strip_prefix(o) for o in raw_owners]
    expected = set(query_spec["expected_hits"])
    min_hits = query_spec["min_hits"]

    if not expected:
        return {"passed": True, "hits": 0, "expected": 0, "hit_rate": 1.0, "result_owners": result_owners}

    matched = expected & set(result_owners)
    hits = len(matched)
    return {
        "passed": hits >= min_hits,
        "hits": hits,
        "expected": len(expected),
        "hit_rate": hits / len(expected),
        "result_owners": result_owners,
        "matched_expected": list(matched),
    }


def evaluate_merged_owners(
    all_owner_results: list[list], query_spec: dict
) -> dict:
    """合并多次 match_owners 结果，按最高分去重取 top-K。"""
    # owner → max score across all queries
    owner_best_score: dict[str, float] = {}
    for results in all_owner_results:
        for r in results:
            if r.owner not in owner_best_score or r.score > owner_best_score[r.owner]:
                owner_best_score[r.owner] = r.score

    # Sort by score descending, take top-K
    sorted_owners = sorted(owner_best_score.items(), key=lambda x: x[1], reverse=True)
    top_owners = [owner for owner, _ in sorted_owners[:TOP_K]]
    result_owners = [_strip_prefix(o) for o in top_owners]

    expected = set(query_spec["expected_hits"])
    min_hits = query_spec["min_hits"]

    if not expected:
        return {"passed": True, "hits": 0, "expected": 0, "hit_rate": 1.0, "result_owners": result_owners}

    matched = expected & set(result_owners)
    hits = len(matched)
    return {
        "passed": hits >= min_hits,
        "hits": hits,
        "expected": len(expected),
        "hit_rate": hits / len(expected),
        "result_owners": result_owners,
        "matched_expected": list(matched),
    }


def paired_bootstrap_ci(
    baseline_scores: np.ndarray, variant_scores: np.ndarray,
    n_bootstrap: int = 10000, alpha: float = 0.05, seed: int = 42,
) -> tuple[float, float, float]:
    rng = np.random.RandomState(seed)
    deltas = variant_scores - baseline_scores
    boot_means = np.empty(n_bootstrap)
    n = len(deltas)
    for i in range(n_bootstrap):
        sample = rng.choice(deltas, size=n, replace=True)
        boot_means[i] = np.mean(sample)
    lower = float(np.percentile(boot_means, 100 * alpha / 2))
    upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return float(np.mean(deltas)), lower, upper


# ================================================================
# Phase 1: 生成视角（需要 API key）
# ================================================================

async def generate_perspectives():
    """用 LLM 为每条查询生成 3 个视角，保存到缓存文件。"""
    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: TOWOW_ANTHROPIC_API_KEY not set")
        sys.exit(1)

    from towow.infra.llm_client import ClaudePlatformClient
    llm = ClaudePlatformClient(api_key=api_key, model="claude-sonnet-4-5-20250929", max_tokens=1024)
    generator = MultiPerspectiveGenerator(llm)

    print("=" * 70)
    print("EXP-007 Phase 1: Generating multi-perspective queries")
    print("=" * 70)

    cache = []
    for i, q in enumerate(TEST_QUERIES):
        query_text = q["query"]
        print(f"\n  Q{i+1:02d} [{q['level']}]: \"{query_text}\"")

        result = await generator.generate(query_text)
        entry = {
            "query": query_text,
            "level": q["level"],
            "resonance": result.resonance,
            "complement": result.complement,
            "interference": result.interference,
        }
        cache.append(entry)
        print(f"    共振: {result.resonance[:60]}...")
        print(f"    互补: {result.complement[:60]}...")
        print(f"    干涉: {result.interference[:60]}...")

    CACHE_FILE.parent.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"\nPerspectives cached to: {CACHE_FILE}")
    print(f"Total LLM calls: {len(TEST_QUERIES)}")


# ================================================================
# Phase 2: 跑匹配对比
# ================================================================

async def run_experiment():
    # 加载缓存的视角
    if not CACHE_FILE.exists():
        print(f"ERROR: Cache not found: {CACHE_FILE}")
        print("Run with --generate first to create perspectives cache")
        sys.exit(1)

    with open(CACHE_FILE, encoding="utf-8") as f:
        perspectives = json.load(f)

    print("=" * 70)
    print("EXP-007: 多视角查询生成效果实验")
    print("=" * 70)
    print(f"  Loaded {len(perspectives)} cached perspectives")

    # 加载 Field
    print("\nLoading agent profiles...")
    profiles = load_all_profiles()
    print(f"  Loaded {len(profiles)} agents")

    print("\nInitializing BGE-M3 + SimHash field...")
    enc = BgeM3Encoder(model_path=BGE_M3_LOCAL)
    proj = SimHashProjector(input_dim=enc.dim, D=SIMHASH_D, seed=SIMHASH_SEED)
    pipe = EncodingPipeline(enc, proj)
    field = MemoryField(pipe)

    print(f"Depositing {len(profiles)} profiles...")
    t0 = time.time()
    for agent_id, text in profiles.items():
        await field.deposit(text, owner=agent_id)
    print(f"  Done in {time.time()-t0:.1f}s")

    # 运行配对查询
    print(f"\nRunning {len(TEST_QUERIES)} paired queries...")
    print()

    results_single = []
    results_multi = []
    by_level = defaultdict(lambda: {"single": [], "multi": []})

    for i, q in enumerate(TEST_QUERIES):
        query_text = q["query"]
        level = q["level"]
        p = perspectives[i]

        # 基线：单查询
        owners_single = await field.match_owners(query_text, k=TOP_K)
        eval_single = evaluate_query_owners(owners_single, q)

        # 变体：多视角（原始 + 3 扩展）
        all_results = [owners_single]  # 复用基线结果
        for perspective_query in [p["resonance"], p["complement"], p["interference"]]:
            owners_p = await field.match_owners(perspective_query, k=TOP_K)
            all_results.append(owners_p)
        eval_multi = evaluate_merged_owners(all_results, q)

        results_single.append(eval_single)
        results_multi.append(eval_multi)
        by_level[level]["single"].append(eval_single)
        by_level[level]["multi"].append(eval_multi)

        s_mark = "PASS" if eval_single["passed"] else "FAIL"
        m_mark = "PASS" if eval_multi["passed"] else "FAIL"
        print(
            f"  [{level}] Q{i+1:02d}: \"{query_text[:30]}...\""
            f"  single={eval_single['hits']}/{eval_single['expected']} [{s_mark}]"
            f"  multi={eval_multi['hits']}/{eval_multi['expected']} [{m_mark}]"
        )

    # 汇总
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    print("\n--- Level Pass Rate ---")
    print(f"{'Level':>6}  {'Single':>10}  {'Multi':>10}  {'Delta':>10}")
    print("-" * 42)

    level_data = {}
    for level in ["L1", "L2", "L3", "L4"]:
        if level not in by_level:
            continue
        s_pass = sum(1 for r in by_level[level]["single"] if r["passed"])
        m_pass = sum(1 for r in by_level[level]["multi"] if r["passed"])
        total = len(by_level[level]["single"])
        s_rate = s_pass / total
        m_rate = m_pass / total
        delta = m_rate - s_rate
        level_data[level] = {"single": s_rate, "multi": m_rate}
        print(f"  {level:>4}  {s_pass}/{total} ({s_rate:.0%})  {m_pass}/{total} ({m_rate:.0%})  {delta:+.0%}")

    s_total_pass = sum(1 for r in results_single if r["passed"])
    m_total_pass = sum(1 for r in results_multi if r["passed"])
    n_queries = len(TEST_QUERIES)
    print(f"  {'ALL':>4}  {s_total_pass}/{n_queries} ({s_total_pass/n_queries:.0%})  {m_total_pass}/{n_queries} ({m_total_pass/n_queries:.0%})  {(m_total_pass-s_total_pass)/n_queries:+.0%}")

    # Hit Rate
    print("\n--- Hit Rate ---")
    s_hits = sum(r["hits"] for r in results_single)
    m_hits = sum(r["hits"] for r in results_multi)
    s_exp = sum(r["expected"] for r in results_single)
    m_exp = sum(r["expected"] for r in results_multi)
    s_hr = s_hits / s_exp if s_exp else 0
    m_hr = m_hits / m_exp if m_exp else 0
    print(f"  Single: {s_hits}/{s_exp} = {s_hr:.1%}")
    print(f"  Multi:  {m_hits}/{m_exp} = {m_hr:.1%}")
    print(f"  delta:  {m_hr - s_hr:+.1%}")

    # Bootstrap CI
    print("\n--- Paired Bootstrap CI ---")
    s_rates = np.array([r["hit_rate"] for r in results_single])
    m_rates = np.array([r["hit_rate"] for r in results_multi])
    mean_delta, ci_low, ci_high = paired_bootstrap_ci(s_rates, m_rates)
    sig = "SIGNIFICANT" if (ci_low > 0 or ci_high < 0) else "NOT significant"
    print(f"  mean delta: {mean_delta:+.4f}")
    print(f"  95% CI: [{ci_low:+.4f}, {ci_high:+.4f}]")
    print(f"  → {sig}")

    # L3 specific (hypothesis target)
    print("\n--- L3 Focus (Hypothesis Target) ---")
    l3_s_rate = level_data.get("L3", {}).get("single", 0)
    l3_m_rate = level_data.get("L3", {}).get("multi", 0)
    l3_delta = l3_m_rate - l3_s_rate
    l3_h1 = l3_delta >= 0.20
    print(f"  L3 single: {l3_s_rate:.0%}")
    print(f"  L3 multi:  {l3_m_rate:.0%}")
    print(f"  L3 delta:  {l3_delta:+.0%}")
    print(f"  H1 (L3 delta ≥ +20pp): {'SUPPORTED' if l3_h1 else 'NOT YET SUPPORTED'}")

    # Per-query delta
    print("\n--- Per-Query Delta ---")
    improved, degraded, same = [], [], []
    for i, q in enumerate(TEST_QUERIES):
        delta = m_rates[i] - s_rates[i]
        if delta > 0.001:
            improved.append((i, q["query"], delta, q["level"]))
        elif delta < -0.001:
            degraded.append((i, q["query"], delta, q["level"]))
        else:
            same.append((i, q["query"], q["level"]))

    if improved:
        print(f"\n  Improved ({len(improved)}):")
        for idx, query, d, level in improved:
            print(f"    [{level}] Q{idx+1:02d} \"{query[:40]}\" +{d:.2f}")
    if degraded:
        print(f"\n  Degraded ({len(degraded)}):")
        for idx, query, d, level in degraded:
            print(f"    [{level}] Q{idx+1:02d} \"{query[:40]}\" {d:.2f}")
    if same:
        print(f"\n  Same ({len(same)}):")
        for idx, query, level in same:
            print(f"    [{level}] Q{idx+1:02d} \"{query[:40]}\"")

    # 保存结果
    result_data = {
        "experiment": "EXP-007",
        "hypothesis": "H1: Multi-perspective L3 hit rate >= single-query + 20pp",
        "date": time.strftime("%Y-%m-%d"),
        "config": {
            "encoder": "bge-m3-1024d",
            "projector": "simhash-10000d",
            "n_agents": len(profiles),
            "n_queries": n_queries,
            "top_k": TOP_K,
            "merge_strategy": "max_score_dedup",
            "perspectives": "original + resonance + complement + interference",
        },
        "results": {
            "level_pass_rate": level_data,
            "overall_pass_rate": {
                "single": s_total_pass / n_queries,
                "multi": m_total_pass / n_queries,
            },
            "hit_rate": {"single": s_hr, "multi": m_hr},
            "paired_bootstrap": {
                "mean_delta": mean_delta,
                "ci_95_lower": ci_low,
                "ci_95_upper": ci_high,
                "significant": sig == "SIGNIFICANT",
            },
            "l3_hypothesis": {
                "single": l3_s_rate,
                "multi": l3_m_rate,
                "delta": l3_delta,
                "threshold": 0.20,
                "supported": l3_h1,
            },
        },
        "perspectives_used": perspectives,
        "per_query": [
            {
                "query": q["query"],
                "level": q["level"],
                "single_hits": results_single[i]["hits"],
                "multi_hits": results_multi[i]["hits"],
                "expected": results_single[i]["expected"],
                "single_passed": results_single[i]["passed"],
                "multi_passed": results_multi[i]["passed"],
            }
            for i, q in enumerate(TEST_QUERIES)
        ],
    }

    RESULT_FILE.parent.mkdir(exist_ok=True)
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {RESULT_FILE}")

    # 结论
    print("\n" + "=" * 70)
    overall_delta = (m_total_pass - s_total_pass) / n_queries
    if overall_delta > 0:
        print(f"CONCLUSION: 多视角查询提升 pass rate {overall_delta:+.0%}")
    elif overall_delta < 0:
        print(f"CONCLUSION: 多视角查询降低 pass rate {overall_delta:+.0%}")
    else:
        print("CONCLUSION: 多视角查询与单查询持平")
    print(f"  L3 delta: {l3_delta:+.0%} (threshold: +20pp)")
    print(f"  统计显著性: {sig}")
    print("=" * 70)


if __name__ == "__main__":
    if "--generate" in sys.argv:
        asyncio.run(generate_perspectives())
    else:
        asyncio.run(run_experiment())
