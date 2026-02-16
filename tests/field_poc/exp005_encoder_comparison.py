"""
EXP-005: BGE-M3 vs mpnet 编码器配对实验

假说: H1: BGE-M3-1024d 在 L1-L4 的 Level Pass Rate ≥ mpnet-768d
设计: 配对实验 — 同一查询集、同一 Agent Profile、同一 SimHash 参数
变量: 唯一变量是编码器 (mpnet-768d vs bge-m3-1024d)
控制: SimHash D=10000, seed=42, chunked bundle, 447 agents, 20 queries

运行:
  cd backend && source venv/bin/activate
  PYTHONPATH=. python ../tests/field_poc/exp005_encoder_comparison.py
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
    MpnetEncoder,
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

# SimHash 参数（两个编码器共享）
SIMHASH_D = 10_000
SIMHASH_SEED = 42
TOP_K = 10

# 场景前缀：load_all_profiles() 返回 "h_zero_day"，TEST_QUERIES 用 "zero_day"
_SCENE_PREFIXES = ("h_", "s_", "r_", "m_")


def _strip_prefix(owner: str) -> str:
    """去掉场景前缀以匹配 TEST_QUERIES 中的 agent_id。"""
    for prefix in _SCENE_PREFIXES:
        if owner.startswith(prefix):
            return owner[len(prefix):]
    return owner


# ================================================================
# 评估函数
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
    """配对 bootstrap 置信区间。

    返回 (mean_delta, lower_ci, upper_ci)。
    如果 CI 不包含 0，则差异显著。
    """
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
    print("EXP-005: BGE-M3 vs mpnet 编码器配对实验")
    print("=" * 70)
    print()

    # ── 1. 加载 Agent Profiles ──
    print("Loading agent profiles...")
    profiles = load_all_profiles()
    print(f"  Loaded {len(profiles)} agents")

    # ── 2. 创建两套 Field ──
    print("\nInitializing encoders...")

    t0 = time.time()
    enc_mpnet = MpnetEncoder()
    t_mpnet_load = time.time() - t0
    print(f"  mpnet-768d loaded in {t_mpnet_load:.1f}s (dim={enc_mpnet.dim})")

    t0 = time.time()
    enc_bge = BgeM3Encoder(model_path=BGE_M3_LOCAL)
    t_bge_load = time.time() - t0
    print(f"  bge-m3-1024d loaded in {t_bge_load:.1f}s (dim={enc_bge.dim})")

    proj_mpnet = SimHashProjector(input_dim=enc_mpnet.dim, D=SIMHASH_D, seed=SIMHASH_SEED)
    proj_bge = SimHashProjector(input_dim=enc_bge.dim, D=SIMHASH_D, seed=SIMHASH_SEED)

    pipe_mpnet = EncodingPipeline(enc_mpnet, proj_mpnet)
    pipe_bge = EncodingPipeline(enc_bge, proj_bge)

    field_mpnet = MemoryField(pipe_mpnet)
    field_bge = MemoryField(pipe_bge)

    # ── 3. 灌入同一批 Profiles ──
    print(f"\nDepositing {len(profiles)} profiles into both fields...")

    t0 = time.time()
    for agent_id, text in profiles.items():
        await field_mpnet.deposit(text, owner=agent_id)
    t_mpnet_deposit = time.time() - t0
    print(f"  mpnet deposit: {t_mpnet_deposit:.1f}s ({len(profiles)/t_mpnet_deposit:.0f} agents/s)")

    t0 = time.time()
    for agent_id, text in profiles.items():
        await field_bge.deposit(text, owner=agent_id)
    t_bge_deposit = time.time() - t0
    print(f"  bge-m3 deposit: {t_bge_deposit:.1f}s ({len(profiles)/t_bge_deposit:.0f} agents/s)")

    # ── 4. 运行配对查询 ──
    print(f"\nRunning {len(TEST_QUERIES)} paired queries (Top-{TOP_K})...")
    print()

    results_mpnet = []
    results_bge = []
    by_level = defaultdict(lambda: {"mpnet": [], "bge": []})

    for i, q in enumerate(TEST_QUERIES):
        query_text = q["query"]
        level = q["level"]

        # 配对：同一查询在两个 Field 上匹配
        owners_mpnet = await field_mpnet.match_owners(query_text, k=TOP_K)
        owners_bge = await field_bge.match_owners(query_text, k=TOP_K)

        eval_mpnet = evaluate_query_owners(owners_mpnet, q)
        eval_bge = evaluate_query_owners(owners_bge, q)

        results_mpnet.append(eval_mpnet)
        results_bge.append(eval_bge)
        by_level[level]["mpnet"].append(eval_mpnet)
        by_level[level]["bge"].append(eval_bge)

        # 逐条打印
        mp_mark = "PASS" if eval_mpnet["passed"] else "FAIL"
        bg_mark = "PASS" if eval_bge["passed"] else "FAIL"
        print(
            f"  [{level}] Q{i+1:02d}: \"{query_text[:30]}...\""
            f"  mpnet={eval_mpnet['hits']}/{eval_mpnet['expected']} [{mp_mark}]"
            f"  bge={eval_bge['hits']}/{eval_bge['expected']} [{bg_mark}]"
        )

    # ── 5. 汇总统计 ──
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    # Level Pass Rate
    print("\n--- Level Pass Rate ---")
    print(f"{'Level':>6}  {'mpnet':>10}  {'bge-m3':>10}  {'Delta':>10}")
    print("-" * 42)

    for level in ["L1", "L2", "L3", "L4"]:
        if level not in by_level:
            continue
        mp_pass = sum(1 for r in by_level[level]["mpnet"] if r["passed"])
        bg_pass = sum(1 for r in by_level[level]["bge"] if r["passed"])
        mp_total = len(by_level[level]["mpnet"])
        bg_total = len(by_level[level]["bge"])
        mp_rate = mp_pass / mp_total if mp_total else 0
        bg_rate = bg_pass / bg_total if bg_total else 0
        delta = bg_rate - mp_rate
        print(f"  {level:>4}  {mp_pass}/{mp_total} ({mp_rate:.0%})  {bg_pass}/{bg_total} ({bg_rate:.0%})  {delta:+.0%}")

    # Overall Pass Rate
    mp_total_pass = sum(1 for r in results_mpnet if r["passed"])
    bg_total_pass = sum(1 for r in results_bge if r["passed"])
    n_queries = len(TEST_QUERIES)
    print(f"  {'ALL':>4}  {mp_total_pass}/{n_queries} ({mp_total_pass/n_queries:.0%})  {bg_total_pass}/{n_queries} ({bg_total_pass/n_queries:.0%})  {(bg_total_pass-mp_total_pass)/n_queries:+.0%}")

    # Hit Rate
    print("\n--- Hit Rate (total hits / total expected) ---")
    mp_total_hits = sum(r["hits"] for r in results_mpnet)
    bg_total_hits = sum(r["hits"] for r in results_bge)
    mp_total_expected = sum(r["expected"] for r in results_mpnet)
    bg_total_expected = sum(r["expected"] for r in results_bge)
    mp_hr = mp_total_hits / mp_total_expected if mp_total_expected else 0
    bg_hr = bg_total_hits / bg_total_expected if bg_total_expected else 0
    print(f"  mpnet:  {mp_total_hits}/{mp_total_expected} = {mp_hr:.1%}")
    print(f"  bge-m3: {bg_total_hits}/{bg_total_expected} = {bg_hr:.1%}")
    print(f"  delta:  {bg_hr - mp_hr:+.1%}")

    # Paired Bootstrap CI
    print("\n--- Paired Bootstrap CI (hit_rate per query) ---")
    mp_rates = np.array([r["hit_rate"] for r in results_mpnet])
    bg_rates = np.array([r["hit_rate"] for r in results_bge])
    mean_delta, ci_low, ci_high = paired_bootstrap_ci(mp_rates, bg_rates)
    sig = "SIGNIFICANT" if (ci_low > 0 or ci_high < 0) else "NOT significant"
    print(f"  mean delta: {mean_delta:+.4f}")
    print(f"  95% CI: [{ci_low:+.4f}, {ci_high:+.4f}]")
    print(f"  → {sig}")

    # ── 6. 逐查询对比（哪些变好了、哪些变差了）──
    print("\n--- Per-Query Delta (bge - mpnet hit_rate) ---")
    improved = []
    degraded = []
    same = []
    for i, q in enumerate(TEST_QUERIES):
        delta = bg_rates[i] - mp_rates[i]
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

    # ── 7. 保存结果 ──
    result_data = {
        "experiment": "EXP-005",
        "hypothesis": "H1: BGE-M3-1024d Level Pass Rate >= mpnet-768d",
        "date": time.strftime("%Y-%m-%d"),
        "config": {
            "baseline": {"encoder": "mpnet-768d", "dim": 768},
            "variant": {"encoder": "bge-m3-1024d", "dim": 1024},
            "simhash_D": SIMHASH_D,
            "simhash_seed": SIMHASH_SEED,
            "top_k": TOP_K,
            "n_agents": len(profiles),
            "n_queries": n_queries,
        },
        "results": {
            "level_pass_rate": {
                level: {
                    "mpnet": sum(1 for r in by_level[level]["mpnet"] if r["passed"]) / len(by_level[level]["mpnet"]),
                    "bge_m3": sum(1 for r in by_level[level]["bge"] if r["passed"]) / len(by_level[level]["bge"]),
                }
                for level in ["L1", "L2", "L3", "L4"]
                if level in by_level
            },
            "overall_pass_rate": {
                "mpnet": mp_total_pass / n_queries,
                "bge_m3": bg_total_pass / n_queries,
            },
            "hit_rate": {"mpnet": mp_hr, "bge_m3": bg_hr},
            "paired_bootstrap": {
                "mean_delta": mean_delta,
                "ci_95_lower": ci_low,
                "ci_95_upper": ci_high,
                "significant": sig == "SIGNIFICANT",
            },
        },
        "timing": {
            "mpnet_deposit_s": round(t_mpnet_deposit, 1),
            "bge_deposit_s": round(t_bge_deposit, 1),
        },
        "per_query": [
            {
                "query": q["query"],
                "level": q["level"],
                "mpnet_hits": results_mpnet[i]["hits"],
                "bge_hits": results_bge[i]["hits"],
                "expected": results_mpnet[i]["expected"],
                "mpnet_passed": results_mpnet[i]["passed"],
                "bge_passed": results_bge[i]["passed"],
            }
            for i, q in enumerate(TEST_QUERIES)
        ],
    }

    result_path = Path(__file__).parent / "results"
    result_path.mkdir(exist_ok=True)
    result_file = result_path / "EXP-005_encoder_comparison.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {result_file}")

    # ── 结论 ──
    print("\n" + "=" * 70)
    if bg_total_pass > mp_total_pass:
        print(f"CONCLUSION: BGE-M3 优于 mpnet (pass rate +{(bg_total_pass-mp_total_pass)/n_queries:.0%})")
    elif bg_total_pass < mp_total_pass:
        print(f"CONCLUSION: mpnet 优于 BGE-M3 (pass rate +{(mp_total_pass-bg_total_pass)/n_queries:.0%})")
    else:
        print("CONCLUSION: 两者持平")
    print(f"  统计显著性: {sig}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_experiment())
