"""
EXP-006: MRL+BQL vs SimHash 投影管道配对实验

假说: H1: BGE-M3 MRL-512d + BQL 保留 ≥90% BGE-M3-1024d + SimHash 的 Level Pass Rate
设计: 配对实验 — 同一查询集、同一 Agent Profile
变量: 唯一变量是投影管道 (SimHash 10000d vs MRL+BQL 512-bit)
控制: 编码器 = BGE-M3（基线用全维 1024d，变体用 MRL 截断 512d）
       SimHash D=10000, seed=42, chunked bundle, 447 agents, 20 queries

额外指标: 存储效率 — 1250 bytes vs 64 bytes per intent (20x 压缩)

运行:
  cd backend && source venv/bin/activate
  PYTHONPATH=. python ../tests/field_poc/exp006_projector_comparison.py
"""

from __future__ import annotations

import asyncio
import json
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
    MrlBqlProjector,
    SimHashProjector,
    load_all_profiles,
)

# 测试查询
try:
    from tests.field_poc.test_queries import TEST_QUERIES
except ModuleNotFoundError:
    from test_queries import TEST_QUERIES

# BGE-M3 本地模型路径
BGE_M3_LOCAL = str(BACKEND_DIR / "models" / "bge-m3")

# 实验参数
SIMHASH_D = 10_000
SIMHASH_SEED = 42
MRL_DIM = 512  # MRL 截断维度
TOP_K = 10

# 场景前缀
_SCENE_PREFIXES = ("h_", "s_", "r_", "m_")


def _strip_prefix(owner: str) -> str:
    """去掉场景前缀以匹配 TEST_QUERIES 中的 agent_id。"""
    for prefix in _SCENE_PREFIXES:
        if owner.startswith(prefix):
            return owner[len(prefix):]
    return owner


# ================================================================
# 评估函数（与 EXP-005 一致）
# ================================================================


def evaluate_query_owners(
    owner_results: list, query_spec: dict
) -> dict:
    """评估 match_owners 的结果。"""
    raw_owners = [r.owner for r in owner_results[:TOP_K]]
    result_owners = [_strip_prefix(o) for o in raw_owners]
    expected = set(query_spec["expected_hits"])
    min_hits = query_spec["min_hits"]

    if not expected:
        return {
            "passed": True,
            "hits": 0,
            "expected": 0,
            "hit_rate": 1.0,
            "result_owners": result_owners,
        }

    matched = expected & set(result_owners)
    hits = len(matched)
    passed = hits >= min_hits

    return {
        "passed": passed,
        "hits": hits,
        "expected": len(expected),
        "hit_rate": hits / len(expected) if expected else 1.0,
        "result_owners": result_owners,
        "matched_expected": list(matched),
    }


def paired_bootstrap_ci(
    baseline_scores: np.ndarray,
    variant_scores: np.ndarray,
    n_bootstrap: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """配对 bootstrap 置信区间。"""
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
# 主实验
# ================================================================


async def run_experiment():
    print("=" * 70)
    print("EXP-006: MRL+BQL vs SimHash 投影管道配对实验")
    print("=" * 70)
    print()

    # ── 1. 加载 Agent Profiles ──
    print("Loading agent profiles...")
    profiles = load_all_profiles()
    print(f"  Loaded {len(profiles)} agents")

    # ── 2. 创建编码器（BGE-M3 两种配置）──
    print("\nInitializing encoders...")

    t0 = time.time()
    enc_full = BgeM3Encoder(model_path=BGE_M3_LOCAL)
    t_load_full = time.time() - t0
    print(f"  BGE-M3-1024d loaded in {t_load_full:.1f}s (dim={enc_full.dim})")

    t0 = time.time()
    enc_mrl = BgeM3Encoder(model_path=BGE_M3_LOCAL, truncate_dim=MRL_DIM)
    t_load_mrl = time.time() - t0
    print(f"  BGE-M3-{MRL_DIM}d (MRL) loaded in {t_load_mrl:.1f}s (dim={enc_mrl.dim})")

    # ── 3. 创建投影器 ──
    print("\nInitializing projectors...")
    proj_simhash = SimHashProjector(input_dim=enc_full.dim, D=SIMHASH_D, seed=SIMHASH_SEED)
    proj_bql = MrlBqlProjector(input_dim=enc_mrl.dim)
    print(f"  SimHash: D={SIMHASH_D}, packed_dim={proj_simhash.packed_dim} bytes")
    print(f"  MRL+BQL: D={proj_bql.D}, packed_dim={proj_bql.packed_dim} bytes")
    print(f"  Storage ratio: {proj_simhash.packed_dim / proj_bql.packed_dim:.1f}x")

    # ── 4. 创建管道 + Field ──
    pipe_simhash = EncodingPipeline(enc_full, proj_simhash)
    pipe_bql = EncodingPipeline(enc_mrl, proj_bql)

    field_simhash = MemoryField(pipe_simhash)
    field_bql = MemoryField(pipe_bql)

    # ── 5. 灌入同一批 Profiles ──
    print(f"\nDepositing {len(profiles)} profiles into both fields...")

    t0 = time.time()
    for agent_id, text in profiles.items():
        await field_simhash.deposit(text, owner=agent_id)
    t_simhash_deposit = time.time() - t0
    print(f"  SimHash deposit: {t_simhash_deposit:.1f}s ({len(profiles)/t_simhash_deposit:.0f} agents/s)")

    t0 = time.time()
    for agent_id, text in profiles.items():
        await field_bql.deposit(text, owner=agent_id)
    t_bql_deposit = time.time() - t0
    print(f"  MRL+BQL deposit: {t_bql_deposit:.1f}s ({len(profiles)/t_bql_deposit:.0f} agents/s)")

    # ── 6. 运行配对查询 ──
    print(f"\nRunning {len(TEST_QUERIES)} paired queries (Top-{TOP_K})...")
    print()

    results_simhash = []
    results_bql = []
    by_level = defaultdict(lambda: {"simhash": [], "bql": []})

    for i, q in enumerate(TEST_QUERIES):
        query_text = q["query"]
        level = q["level"]

        owners_simhash = await field_simhash.match_owners(query_text, k=TOP_K)
        owners_bql = await field_bql.match_owners(query_text, k=TOP_K)

        eval_simhash = evaluate_query_owners(owners_simhash, q)
        eval_bql = evaluate_query_owners(owners_bql, q)

        results_simhash.append(eval_simhash)
        results_bql.append(eval_bql)
        by_level[level]["simhash"].append(eval_simhash)
        by_level[level]["bql"].append(eval_bql)

        sh_mark = "PASS" if eval_simhash["passed"] else "FAIL"
        bq_mark = "PASS" if eval_bql["passed"] else "FAIL"
        print(
            f"  [{level}] Q{i+1:02d}: \"{query_text[:30]}...\""
            f"  simhash={eval_simhash['hits']}/{eval_simhash['expected']} [{sh_mark}]"
            f"  bql={eval_bql['hits']}/{eval_bql['expected']} [{bq_mark}]"
        )

    # ── 7. 汇总统计 ──
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    # Level Pass Rate
    print("\n--- Level Pass Rate ---")
    print(f"{'Level':>6}  {'SimHash':>12}  {'MRL+BQL':>12}  {'Delta':>10}  {'Retained':>10}")
    print("-" * 56)

    level_data = {}
    for level in ["L1", "L2", "L3", "L4"]:
        if level not in by_level:
            continue
        sh_pass = sum(1 for r in by_level[level]["simhash"] if r["passed"])
        bq_pass = sum(1 for r in by_level[level]["bql"] if r["passed"])
        sh_total = len(by_level[level]["simhash"])
        bq_total = len(by_level[level]["bql"])
        sh_rate = sh_pass / sh_total if sh_total else 0
        bq_rate = bq_pass / bq_total if bq_total else 0
        delta = bq_rate - sh_rate
        retained = bq_rate / sh_rate if sh_rate > 0 else float('inf')
        level_data[level] = {"simhash": sh_rate, "bql": bq_rate}
        print(f"  {level:>4}  {sh_pass}/{sh_total} ({sh_rate:.0%})  {bq_pass}/{bq_total} ({bq_rate:.0%})  {delta:+.0%}       {retained:.0%}")

    # Overall Pass Rate
    sh_total_pass = sum(1 for r in results_simhash if r["passed"])
    bq_total_pass = sum(1 for r in results_bql if r["passed"])
    n_queries = len(TEST_QUERIES)
    sh_overall = sh_total_pass / n_queries
    bq_overall = bq_total_pass / n_queries
    retained_overall = bq_overall / sh_overall if sh_overall > 0 else float('inf')
    print(f"  {'ALL':>4}  {sh_total_pass}/{n_queries} ({sh_overall:.0%})  {bq_total_pass}/{n_queries} ({bq_overall:.0%})  {(bq_overall-sh_overall):+.0%}       {retained_overall:.0%}")

    # Hit Rate
    print("\n--- Hit Rate ---")
    sh_total_hits = sum(r["hits"] for r in results_simhash)
    bq_total_hits = sum(r["hits"] for r in results_bql)
    sh_total_expected = sum(r["expected"] for r in results_simhash)
    bq_total_expected = sum(r["expected"] for r in results_bql)
    sh_hr = sh_total_hits / sh_total_expected if sh_total_expected else 0
    bq_hr = bq_total_hits / bq_total_expected if bq_total_expected else 0
    hr_retained = bq_hr / sh_hr if sh_hr > 0 else float('inf')
    print(f"  SimHash: {sh_total_hits}/{sh_total_expected} = {sh_hr:.1%}")
    print(f"  MRL+BQL: {bq_total_hits}/{bq_total_expected} = {bq_hr:.1%}")
    print(f"  delta:   {bq_hr - sh_hr:+.1%}")
    print(f"  retained: {hr_retained:.0%}")

    # Storage efficiency
    print("\n--- Storage Efficiency ---")
    print(f"  SimHash: {proj_simhash.packed_dim} bytes/intent")
    print(f"  MRL+BQL: {proj_bql.packed_dim} bytes/intent")
    print(f"  Compression: {proj_simhash.packed_dim / proj_bql.packed_dim:.1f}x")

    # Paired Bootstrap CI
    print("\n--- Paired Bootstrap CI (hit_rate per query) ---")
    sh_rates = np.array([r["hit_rate"] for r in results_simhash])
    bq_rates = np.array([r["hit_rate"] for r in results_bql])
    mean_delta, ci_low, ci_high = paired_bootstrap_ci(sh_rates, bq_rates)
    sig = "SIGNIFICANT" if (ci_low > 0 or ci_high < 0) else "NOT significant"
    print(f"  mean delta: {mean_delta:+.4f}")
    print(f"  95% CI: [{ci_low:+.4f}, {ci_high:+.4f}]")
    print(f"  → {sig}")

    # ── 8. 逐查询对比 ──
    print("\n--- Per-Query Delta (bql - simhash hit_rate) ---")
    improved = []
    degraded = []
    same = []
    for i, q in enumerate(TEST_QUERIES):
        delta = bq_rates[i] - sh_rates[i]
        if delta > 0:
            improved.append((i, q["query"], delta, q["level"]))
        elif delta < 0:
            degraded.append((i, q["query"], delta, q["level"]))
        else:
            same.append((i, q["query"], q["level"]))

    if improved:
        print(f"\n  Improved ({len(improved)}):")
        for idx, query, delta, level in improved:
            print(f"    [{level}] Q{idx+1:02d} \"{query[:40]}\" +{delta:.2f}")

    if degraded:
        print(f"\n  Degraded ({len(degraded)}):")
        for idx, query, delta, level in degraded:
            print(f"    [{level}] Q{idx+1:02d} \"{query[:40]}\" {delta:.2f}")

    if same:
        print(f"\n  Same ({len(same)}):")
        for idx, query, level in same:
            print(f"    [{level}] Q{idx+1:02d} \"{query[:40]}\"")

    # ── 9. 假说判定 ──
    h1_threshold = 0.90
    h1_pass = retained_overall >= h1_threshold
    print(f"\n--- Hypothesis Test ---")
    print(f"  H1: MRL+BQL retains ≥{h1_threshold:.0%} of SimHash pass rate")
    print(f"  Retained: {retained_overall:.1%}")
    print(f"  → H1 {'SUPPORTED' if h1_pass else 'REJECTED'}")

    # ── 10. 保存结果 ──
    result_data = {
        "experiment": "EXP-006",
        "hypothesis": "H1: MRL+BQL 512-bit retains >=90% of BGE-M3+SimHash pass rate",
        "date": time.strftime("%Y-%m-%d"),
        "config": {
            "baseline": {
                "encoder": "bge-m3-1024d",
                "projector": "simhash",
                "proj_D": SIMHASH_D,
                "bytes_per_intent": proj_simhash.packed_dim,
            },
            "variant": {
                "encoder": "bge-m3-512d (MRL)",
                "projector": "bql",
                "proj_D": proj_bql.D,
                "bytes_per_intent": proj_bql.packed_dim,
            },
            "simhash_seed": SIMHASH_SEED,
            "top_k": TOP_K,
            "n_agents": len(profiles),
            "n_queries": n_queries,
        },
        "results": {
            "level_pass_rate": {
                level: {
                    "simhash": level_data[level]["simhash"],
                    "bql": level_data[level]["bql"],
                }
                for level in ["L1", "L2", "L3", "L4"]
                if level in level_data
            },
            "overall_pass_rate": {
                "simhash": sh_overall,
                "bql": bq_overall,
                "retained": retained_overall,
            },
            "hit_rate": {
                "simhash": sh_hr,
                "bql": bq_hr,
                "retained": hr_retained,
            },
            "paired_bootstrap": {
                "mean_delta": mean_delta,
                "ci_95_lower": ci_low,
                "ci_95_upper": ci_high,
                "significant": sig == "SIGNIFICANT",
            },
            "storage": {
                "simhash_bytes": proj_simhash.packed_dim,
                "bql_bytes": proj_bql.packed_dim,
                "compression_ratio": proj_simhash.packed_dim / proj_bql.packed_dim,
            },
            "hypothesis_test": {
                "threshold": h1_threshold,
                "retained": retained_overall,
                "supported": h1_pass,
            },
        },
        "timing": {
            "simhash_deposit_s": round(t_simhash_deposit, 1),
            "bql_deposit_s": round(t_bql_deposit, 1),
        },
        "per_query": [
            {
                "query": q["query"],
                "level": q["level"],
                "simhash_hits": results_simhash[i]["hits"],
                "bql_hits": results_bql[i]["hits"],
                "expected": results_simhash[i]["expected"],
                "simhash_passed": results_simhash[i]["passed"],
                "bql_passed": results_bql[i]["passed"],
            }
            for i, q in enumerate(TEST_QUERIES)
        ],
    }

    result_path = Path(__file__).parent / "results"
    result_path.mkdir(exist_ok=True)
    result_file = result_path / "EXP-006_projector_comparison.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {result_file}")

    # ── 结论 ──
    print("\n" + "=" * 70)
    print(f"CONCLUSION: MRL+BQL retains {retained_overall:.0%} of SimHash precision")
    print(f"  with {proj_simhash.packed_dim / proj_bql.packed_dim:.0f}x storage reduction")
    print(f"  ({proj_simhash.packed_dim} → {proj_bql.packed_dim} bytes/intent)")
    if h1_pass:
        print(f"  H1 SUPPORTED: ≥90% retention threshold met")
    else:
        print(f"  H1 REJECTED: below 90% retention threshold")
    print(f"  Statistical significance: {sig}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_experiment())
