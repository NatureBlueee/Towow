"""
Phase 3 实验：碎片级 deposit + Agent 聚合匹配

验证 Genome v0.3 核心声明：Multi Intent per Agent。
每个 Agent 的 Profile fields 是独立的意图碎片，match_owners 聚合。

三组对照：
  C_baseline: profile_to_text → 1 deposit per agent → match()
  A_single:   fields 分行拼接 → 1 deposit per agent → match()（field-level chunking）
  B_multi:    each field → separate deposit (same owner) → match_owners()

聚合策略子实验（B_multi）：
  max:       owner score = max of intent scores
  top3_avg:  owner score = mean of top 3 intent scores
  weighted:  owner score = Σ score_i * decay^i

运行方式：
  cd backend && source venv/bin/activate
  PYTHONPATH=. python ../tests/field_poc/phase3_multi_intent_poc.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

# ── Path setup ───────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ── V2 Field imports ────────────────────────────────────
from towow.field import (
    MpnetEncoder,
    SimHashProjector,
    EncodingPipeline,
    MemoryField,
)
from towow.field.profile_loader import load_all_profiles, profile_to_text

# ── Test data imports ────────────────────────────────────
try:
    from tests.field_poc.test_queries import TEST_QUERIES
    from tests.field_poc.test_profiles import FORMULATION_TESTS
except ModuleNotFoundError:
    from test_queries import TEST_QUERIES
    from test_profiles import FORMULATION_TESTS

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ── Scene config ─────────────────────────────────────────
_SCENE_DIRS = [
    ("S1_hackathon", "h_"),
    ("S2_skill_exchange", "s_"),
    ("R1_recruitment", "r_"),
    ("M1_matchmaking", "m_"),
]

_CORE_FIELDS = ["name", "role", "occupation", "bio"]
_LIST_FIELDS = ["skills", "interests"]
_EXTRA_FIELDS = [
    "can_teach", "want_to_learn", "looking_for",
    "experience", "ideal_match", "values",
    "quirks", "work_style",
]


# ── Data loading ─────────────────────────────────────────

def load_raw_agents() -> dict[str, dict]:
    """Load raw agent JSON data with scene prefixes."""
    apps_dir = PROJECT_ROOT / "apps"
    all_agents: dict[str, dict] = {}
    for scene_dir, prefix in _SCENE_DIRS:
        agents_file = apps_dir / scene_dir / "data" / "agents.json"
        if not agents_file.exists():
            continue
        with open(agents_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, agent_data in data.items():
            all_agents[f"{prefix}{key}"] = agent_data
    return all_agents


def extract_agent_fields(agent_data: dict) -> list[str]:
    """Extract meaningful text fields from agent profile data.

    Each field becomes an independent semantic unit.
    Returns list of non-empty field strings.
    """
    fields: list[str] = []

    # Identity: name + role/occupation
    name = agent_data.get("name", "").strip()
    role = (agent_data.get("role") or agent_data.get("occupation") or "").strip()
    if name and role:
        fields.append(f"{name}, {role}")
    elif name:
        fields.append(name)

    # Bio
    bio = (agent_data.get("bio") or "").strip()
    if bio:
        fields.append(bio)

    # List fields
    for field_name in _LIST_FIELDS:
        val = agent_data.get(field_name)
        if val and isinstance(val, list):
            joined = ", ".join(str(v).strip() for v in val if str(v).strip())
            if joined:
                fields.append(f"{field_name}: {joined}")

    # Extra fields
    for field_name in _EXTRA_FIELDS:
        val = agent_data.get(field_name)
        if not val:
            continue
        if isinstance(val, list):
            joined = ", ".join(str(v).strip() for v in val if str(v).strip())
            if joined:
                fields.append(f"{field_name}: {joined}")
        else:
            text = str(val).strip()
            if text:
                fields.append(f"{field_name}: {text}")

    return [f for f in fields if f.strip()]


# ── Agent ID matching ────────────────────────────────────

def build_id_lookup(agent_ids: list[str]) -> dict[str, str]:
    """Build unprefixed → prefixed agent_id lookup.

    expected_hits in test data use unprefixed IDs (e.g., "zero_day").
    Field stores prefixed IDs (e.g., "h_zero_day").
    """
    lookup: dict[str, str] = {}
    for aid in agent_ids:
        # Strip scene prefix (h_, s_, r_, m_)
        for prefix in ("h_", "s_", "r_", "m_"):
            if aid.startswith(prefix):
                bare = aid[len(prefix):]
                # First match wins (cross-scene duplicates handled by first-seen)
                if bare not in lookup:
                    lookup[bare] = aid
                break
    return lookup


# ── Aggregation strategies ───────────────────────────────

def aggregate_max(scores: list[float]) -> float:
    """Owner score = max of intent scores."""
    return max(scores) if scores else 0.0


def aggregate_top3_avg(scores: list[float]) -> float:
    """Owner score = mean of top 3 intent scores."""
    top = sorted(scores, reverse=True)[:3]
    return sum(top) / len(top) if top else 0.0


def aggregate_weighted(scores: list[float], decay: float = 0.5) -> float:
    """Owner score = weighted sum with exponential decay."""
    top = sorted(scores, reverse=True)
    total = 0.0
    weight_sum = 0.0
    for i, s in enumerate(top[:5]):  # cap at 5 to avoid diminishing returns
        w = decay ** i
        total += s * w
        weight_sum += w
    return total / weight_sum if weight_sum > 0 else 0.0


AGGREGATION_STRATEGIES = {
    "max": aggregate_max,
    "top3_avg": aggregate_top3_avg,
    "weighted": aggregate_weighted,
}


# ── Evaluation ───────────────────────────────────────────

def evaluate_query(
    query_data: dict,
    top_owners: list[tuple[str, float]],
    id_lookup: dict[str, str],
    k: int = 10,
) -> dict:
    """Evaluate a single query's results against expected hits.

    Returns:
        {passed, hits, total_expected, min_hits, matched_agents, scores}
    """
    expected = query_data.get("expected_hits", [])
    min_hits = query_data.get("min_hits", 1)

    # Map expected unprefixed IDs to prefixed
    expected_prefixed = set()
    for bare_id in expected:
        if bare_id in id_lookup:
            expected_prefixed.add(id_lookup[bare_id])

    # Check hits in top-k owners
    top_k_owners = [owner for owner, _ in top_owners[:k]]
    top_k_scores = {owner: score for owner, score in top_owners[:k]}

    hits = expected_prefixed & set(top_k_owners)
    hit_count = len(hits)
    passed = hit_count >= min_hits

    # Matched agents with scores for reporting
    matched = []
    for owner in hits:
        matched.append((owner, top_k_scores.get(owner, 0.0)))

    return {
        "passed": passed,
        "hits": hit_count,
        "total_expected": len(expected),
        "min_hits": min_hits,
        "matched_agents": sorted(matched, key=lambda x: -x[1]),
        "top_3": [(o, round(s, 4)) for o, s in top_owners[:3]],
    }


# ── Strategy population ─────────────────────────────────

async def populate_c_baseline(
    field: MemoryField, profiles: dict[str, str]
) -> None:
    """C_baseline: profile_to_text → 1 deposit per agent."""
    for agent_id, text in profiles.items():
        if text.strip():
            await field.deposit(text, owner=agent_id)


async def populate_a_single(
    field: MemoryField, raw_agents: dict[str, dict]
) -> None:
    """A_single: fields joined with newline → 1 deposit per agent.

    Newlines cause split_chunks to treat each field as separate chunk,
    which are then encoded individually and bundled by the pipeline.
    """
    for agent_id, agent_data in raw_agents.items():
        fields = extract_agent_fields(agent_data)
        if fields:
            text = "\n".join(fields)
            await field.deposit(text, owner=agent_id)


async def populate_b_multi(
    field: MemoryField, raw_agents: dict[str, dict]
) -> None:
    """B_multi: each field → separate deposit for same owner.

    Each field becomes an independent Intent in the field.
    match_owners() aggregates by owner at query time.
    """
    total_intents = 0
    for agent_id, agent_data in raw_agents.items():
        fields = extract_agent_fields(agent_data)
        for field_text in fields:
            await field.deposit(field_text, owner=agent_id)
            total_intents += 1
    logger.info("  B_multi: %d intents for %d agents (avg %.1f/agent)",
                total_intents, len(raw_agents), total_intents / len(raw_agents))


# ── Query execution ──────────────────────────────────────

async def run_match_strategy(
    field: MemoryField,
    query_text: str,
    k: int = 10,
) -> list[tuple[str, float]]:
    """Run match() and aggregate to owner level (for C_baseline / A_single).

    Uses max-score aggregation to get owner-level results.
    """
    results = await field.match(query_text, k=k * 5)  # fetch more for aggregation

    # Aggregate by owner
    owner_scores: dict[str, float] = {}
    for r in results:
        if r.owner not in owner_scores or r.score > owner_scores[r.owner]:
            owner_scores[r.owner] = r.score

    sorted_owners = sorted(owner_scores.items(), key=lambda x: -x[1])
    return sorted_owners[:k]


async def run_match_owners_strategy(
    field: MemoryField,
    query_text: str,
    k: int = 10,
    agg_fn=None,
) -> list[tuple[str, float]]:
    """Run match() and aggregate with custom aggregation function.

    For B_multi with different aggregation strategies.
    """
    if agg_fn is None:
        agg_fn = aggregate_max

    # Get all intent-level results
    total = await field.count()
    raw_k = min(total, k * 20)  # fetch many for proper aggregation
    results = await field.match(query_text, k=raw_k)

    # Group by owner
    owner_intents: dict[str, list[float]] = defaultdict(list)
    for r in results:
        owner_intents[r.owner].append(r.score)

    # Aggregate
    owner_scores = {
        owner: agg_fn(scores) for owner, scores in owner_intents.items()
    }

    sorted_owners = sorted(owner_scores.items(), key=lambda x: -x[1])
    return sorted_owners[:k]


# ── Main experiment ──────────────────────────────────────

async def run_experiment():
    """Run Phase 3 experiment: 3 strategies × 20+6 queries."""

    logger.info("=" * 70)
    logger.info("Phase 3: Multi-Intent per Agent Experiment")
    logger.info("=" * 70)

    # ── Step 1: Load data ────────────────────────────────
    logger.info("\n[1/5] Loading data...")
    raw_agents = load_raw_agents()
    profiles = load_all_profiles()
    logger.info("  Raw agents: %d", len(raw_agents))
    logger.info("  Profile texts: %d", len(profiles))

    # Build ID lookup
    all_ids = list(raw_agents.keys())
    id_lookup = build_id_lookup(all_ids)
    logger.info("  ID lookup: %d bare → prefixed mappings", len(id_lookup))

    # ── Step 2: Create shared pipeline ───────────────────
    logger.info("\n[2/5] Initializing encoding pipeline...")
    t0 = time.time()
    encoder = MpnetEncoder()
    projector = SimHashProjector(input_dim=encoder.dim)
    pipeline = EncodingPipeline(encoder, projector)
    logger.info("  Pipeline ready (%.1fs)", time.time() - t0)

    # ── Step 3: Populate 3 fields ────────────────────────
    logger.info("\n[3/5] Populating fields...")

    field_c = MemoryField(pipeline)
    field_a = MemoryField(pipeline)
    field_b = MemoryField(pipeline)

    t0 = time.time()
    logger.info("  C_baseline: depositing %d agents...", len(profiles))
    await populate_c_baseline(field_c, profiles)
    t_c = time.time() - t0
    logger.info("  C_baseline: %d intents (%.1fs)", await field_c.count(), t_c)

    t0 = time.time()
    logger.info("  A_single: depositing %d agents (field-level)...", len(raw_agents))
    await populate_a_single(field_a, raw_agents)
    t_a = time.time() - t0
    logger.info("  A_single: %d intents (%.1fs)", await field_a.count(), t_a)

    t0 = time.time()
    logger.info("  B_multi: depositing %d agents (multi-intent)...", len(raw_agents))
    await populate_b_multi(field_b, raw_agents)
    t_b = time.time() - t0
    logger.info("  B_multi: %d intents, %d owners (%.1fs)",
                await field_b.count(), await field_b.count_owners(), t_b)

    # ── Step 4: Run queries ──────────────────────────────
    logger.info("\n[4/5] Running queries...")

    all_queries = []
    for q in TEST_QUERIES:
        all_queries.append({
            "query": q["query"],
            "expected_hits": q["expected_hits"],
            "min_hits": q["min_hits"],
            "level": q["level"],
            "source": "test_queries",
        })
    for q in FORMULATION_TESTS:
        all_queries.append({
            "query": q["query"],
            "expected_hits": q["expected_hits"],
            "min_hits": q["min_hits"],
            "level": q["level"],
            "source": "formulation_tests",
        })

    # Results storage
    results = {
        "C_baseline": [],
        "A_single": [],
        "B_multi_max": [],
        "B_multi_top3_avg": [],
        "B_multi_weighted": [],
    }

    for i, q in enumerate(all_queries):
        query_text = q["query"]
        logger.info("  [%d/%d] %s \"%s\"",
                     i + 1, len(all_queries), q["level"], query_text)

        # C_baseline
        top_c = await run_match_strategy(field_c, query_text)
        results["C_baseline"].append(evaluate_query(q, top_c, id_lookup))

        # A_single
        top_a = await run_match_strategy(field_a, query_text)
        results["A_single"].append(evaluate_query(q, top_a, id_lookup))

        # B_multi with 3 aggregation strategies
        for strat_name, agg_fn in AGGREGATION_STRATEGIES.items():
            top_b = await run_match_owners_strategy(field_b, query_text, agg_fn=agg_fn)
            results[f"B_multi_{strat_name}"].append(evaluate_query(q, top_b, id_lookup))

    # ── Step 5: Report ───────────────────────────────────
    logger.info("\n[5/5] Results\n")
    report = generate_report(all_queries, results)
    logger.info(report)

    # Save results
    output_path = Path(__file__).parent / "phase3_results.json"
    save_results(output_path, all_queries, results)
    logger.info("\nResults saved to %s", output_path)

    return results


def generate_report(queries: list[dict], results: dict) -> str:
    """Generate human-readable report."""
    lines = []
    lines.append("=" * 70)
    lines.append("Phase 3 Results: Multi-Intent per Agent")
    lines.append("=" * 70)

    # ── Overall summary ──────────────────────────────────
    lines.append("\n## Overall (Pass / Total)")
    lines.append(f"{'Strategy':<22} {'Total':>8} {'L1':>8} {'L2':>8} {'L3':>8} {'L4':>8}")
    lines.append("-" * 62)

    levels = ["L1", "L2", "L3", "L4"]
    for strat_name, strat_results in results.items():
        total_pass = sum(1 for r in strat_results if r["passed"])
        total_count = len(strat_results)

        by_level = {}
        for q, r in zip(queries, strat_results):
            lv = q["level"]
            by_level.setdefault(lv, {"pass": 0, "total": 0})
            by_level[lv]["total"] += 1
            if r["passed"]:
                by_level[lv]["pass"] += 1

        parts = [f"{strat_name:<22}", f"{total_pass}/{total_count:>3}"]
        for lv in levels:
            d = by_level.get(lv, {"pass": 0, "total": 0})
            parts.append(f"  {d['pass']}/{d['total']:>2}")
        lines.append("".join(parts))

    # ── Hits summary ─────────────────────────────────────
    lines.append("\n## Hit Count (Hits / Total Expected)")
    lines.append(f"{'Strategy':<22} {'Total':>12} {'L1':>10} {'L2':>10} {'L3':>10} {'L4':>10}")
    lines.append("-" * 76)

    for strat_name, strat_results in results.items():
        total_hits = sum(r["hits"] for r in strat_results)
        total_expected = sum(r["total_expected"] for r in strat_results)

        by_level = {}
        for q, r in zip(queries, strat_results):
            lv = q["level"]
            by_level.setdefault(lv, {"hits": 0, "expected": 0})
            by_level[lv]["hits"] += r["hits"]
            by_level[lv]["expected"] += r["total_expected"]

        parts = [f"{strat_name:<22}", f"{total_hits:>4}/{total_expected:>4}"]
        for lv in levels:
            d = by_level.get(lv, {"hits": 0, "expected": 0})
            parts.append(f"  {d['hits']:>3}/{d['expected']:>3}")
        lines.append("".join(parts))

    # ── Per-query detail for L4 (most interesting) ───────
    lines.append("\n## L4 Detail (hardest queries)")
    lines.append("-" * 70)

    l4_queries = [(i, q) for i, q in enumerate(queries) if q["level"] == "L4"]
    for idx, q in l4_queries:
        lines.append(f"\nQuery: \"{q['query']}\"")
        lines.append(f"  Expected: {q['expected_hits'][:4]}...")
        for strat_name, strat_results in results.items():
            r = strat_results[idx]
            status = "PASS" if r["passed"] else "FAIL"
            top3_str = ", ".join(f"{o}={s}" for o, s in r["top_3"])
            lines.append(
                f"  {strat_name:<22} [{status}] hits={r['hits']}/{r['min_hits']}  "
                f"top3=[{top3_str}]"
            )

    # ── B_multi aggregation comparison ───────────────────
    lines.append("\n## B_multi Aggregation Comparison")
    lines.append("-" * 70)
    b_strats = ["B_multi_max", "B_multi_top3_avg", "B_multi_weighted"]
    for strat in b_strats:
        sr = results[strat]
        total_pass = sum(1 for r in sr if r["passed"])
        total_hits = sum(r["hits"] for r in sr)
        total_expected = sum(r["total_expected"] for r in sr)
        lines.append(
            f"  {strat:<22} pass={total_pass}/{len(sr)}  "
            f"hits={total_hits}/{total_expected}"
        )

    return "\n".join(lines)


def save_results(path: Path, queries: list[dict], results: dict) -> None:
    """Save full results as JSON for further analysis."""
    output = {
        "metadata": {
            "num_queries": len(queries),
            "strategies": list(results.keys()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "queries": [],
    }

    for i, q in enumerate(queries):
        entry = {
            "query": q["query"],
            "level": q["level"],
            "source": q["source"],
            "expected_hits": q["expected_hits"],
            "min_hits": q["min_hits"],
            "results": {},
        }
        for strat_name, strat_results in results.items():
            r = strat_results[i]
            entry["results"][strat_name] = {
                "passed": r["passed"],
                "hits": r["hits"],
                "matched_agents": [
                    {"agent_id": a, "score": round(s, 4)}
                    for a, s in r["matched_agents"]
                ],
                "top_3": [
                    {"agent_id": a, "score": s}
                    for a, s in r["top_3"]
                ],
            }
        output["queries"].append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(run_experiment())
