"""
编码器对比实验：model × chunk_size

决策目标：选哪个编码器，配多大 chunk size。

模型候选：
  A: paraphrase-multilingual-mpnet-base-v2 (768d, 128 tokens) — 当前
  B: intfloat/multilingual-e5-large (1024d, 512 tokens)
  C: BAAI/bge-m3 (1024d, 8192 tokens)

Chunk size 候选：
  256 chars (当前), 512 chars, 1024 chars, 无限制(whole text)

每组使用 C_baseline 策略（Phase 3 winner）：profile_to_text → encode → match。

运行方式：
  cd backend && source venv/bin/activate
  PYTHONPATH=. python ../tests/field_poc/encoder_comparison_poc.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np

# ── Path setup ───────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from towow.field.profile_loader import load_all_profiles
from towow.field.projector import SimHashProjector, bundle_binary
from towow.field.chunker import split_chunks

try:
    from tests.field_poc.test_queries import TEST_QUERIES
    from tests.field_poc.test_profiles import FORMULATION_TESTS
except ModuleNotFoundError:
    from test_queries import TEST_QUERIES
    from test_profiles import FORMULATION_TESTS

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Suppress noisy logs
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# ── Scene prefix lookup ──────────────────────────────────
_SCENE_DIRS = [
    ("S1_hackathon", "h_"),
    ("S2_skill_exchange", "s_"),
    ("R1_recruitment", "r_"),
    ("M1_matchmaking", "m_"),
]


def build_id_lookup(agent_ids: list[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for aid in agent_ids:
        for prefix in ("h_", "s_", "r_", "m_"):
            if aid.startswith(prefix):
                bare = aid[len(prefix):]
                if bare not in lookup:
                    lookup[bare] = aid
                break
    return lookup


# ── Model configs ────────────────────────────────────────

MODELS = [
    {
        "name": "mpnet-768d",
        "model_id": "paraphrase-multilingual-mpnet-base-v2",
        "query_prefix": "",  # no prefix needed
    },
    {
        "name": "e5-large-1024d",
        "model_id": "intfloat/multilingual-e5-large",
        "query_prefix": "query: ",  # e5 models need "query: " prefix for queries
    },
    {
        "name": "bge-m3-1024d",
        "model_id": "BAAI/bge-m3",
        "query_prefix": "",
    },
]

CHUNK_SIZES = [256, 512, 1024, 99999]  # 99999 = effectively no chunking


# ── Core encoding logic (bypasses MemoryField for flexibility) ──

def encode_profile(
    text: str,
    encoder,
    projector: SimHashProjector,
    max_chars: int,
) -> np.ndarray:
    """Encode a profile text: chunk → encode → project → bundle."""
    chunks = split_chunks(text, max_chars=max_chars)
    if not chunks:
        raise ValueError("Empty text")

    if len(chunks) == 1:
        dense = encoder.encode(chunks[0])
        return projector.project(np.asarray(dense, dtype=np.float32))

    dense_vecs = encoder.encode(chunks)
    binary_vecs = projector.batch_project(np.asarray(dense_vecs, dtype=np.float32))
    import hashlib
    seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
    return bundle_binary(list(binary_vecs), seed=seed)


def encode_query(
    text: str,
    encoder,
    projector: SimHashProjector,
    query_prefix: str,
    max_chars: int,
) -> np.ndarray:
    """Encode a query text (with optional model-specific prefix)."""
    prefixed = f"{query_prefix}{text}" if query_prefix else text
    # Queries are short — usually single chunk
    dense = encoder.encode(prefixed)
    return projector.project(np.asarray(dense, dtype=np.float32))


# ── Evaluation ───────────────────────────────────────────

def evaluate_single(
    query_data: dict,
    top_owners: list[tuple[str, float]],
    id_lookup: dict[str, str],
    k: int = 10,
) -> dict:
    expected = query_data.get("expected_hits", [])
    min_hits = query_data.get("min_hits", 1)

    expected_prefixed = set()
    for bare_id in expected:
        if bare_id in id_lookup:
            expected_prefixed.add(id_lookup[bare_id])

    top_k_owners = set(owner for owner, _ in top_owners[:k])
    hits = expected_prefixed & top_k_owners
    hit_count = len(hits)

    return {
        "passed": hit_count >= min_hits,
        "hits": hit_count,
        "total_expected": len(expected),
        "min_hits": min_hits,
    }


# ── Run one configuration ────────────────────────────────

def run_config(
    model_name: str,
    model_id: str,
    query_prefix: str,
    chunk_size: int,
    profiles: dict[str, str],
    queries: list[dict],
    id_lookup: dict[str, str],
) -> dict:
    """Run one (model, chunk_size) configuration."""
    from sentence_transformers import SentenceTransformer

    chunk_label = str(chunk_size) if chunk_size < 99999 else "full"
    config_name = f"{model_name}_chunk{chunk_label}"
    logger.info("\n  === %s ===", config_name)

    # Load model
    t0 = time.time()
    encoder = SentenceTransformer(model_id)
    dim = encoder.get_sentence_embedding_dimension()
    max_seq = encoder.max_seq_length
    load_time = time.time() - t0
    logger.info("    Model loaded: dim=%d, max_seq=%d (%.1fs)", dim, max_seq, load_time)

    # Create projector for this dim
    projector = SimHashProjector(input_dim=dim)

    # Encode all profiles
    t0 = time.time()
    agent_vectors: dict[str, np.ndarray] = {}
    for agent_id, text in profiles.items():
        if text.strip():
            agent_vectors[agent_id] = encode_profile(text, encoder, projector, chunk_size)
    encode_time = time.time() - t0
    logger.info("    Encoded %d profiles (%.1fs)", len(agent_vectors), encode_time)

    # Build candidate matrix
    agent_ids = list(agent_vectors.keys())
    if not agent_ids:
        return {"config": config_name, "results": [], "error": "No profiles encoded"}

    candidate_matrix = np.array(
        [agent_vectors[aid] for aid in agent_ids], dtype=np.uint8
    )

    # Run queries
    results = []
    t0 = time.time()
    for q in queries:
        query_vec = encode_query(q["query"], encoder, projector, query_prefix, chunk_size)
        scores = projector.batch_similarity(query_vec, candidate_matrix)

        # Top-k owners
        k = 10
        actual_k = min(k, len(agent_ids))
        if actual_k >= len(agent_ids):
            top_indices = np.argsort(scores)[::-1]
        else:
            top_indices = np.argpartition(scores, -actual_k)[-actual_k:]
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        top_owners = [(agent_ids[i], float(scores[i])) for i in top_indices[:k]]

        r = evaluate_single(q, top_owners, id_lookup)
        results.append(r)
    query_time = time.time() - t0
    logger.info("    Queried %d queries (%.1fs)", len(queries), query_time)

    # Cleanup model to free memory
    del encoder
    import torch
    if hasattr(torch.mps, 'empty_cache'):
        torch.mps.empty_cache()
    import gc
    gc.collect()

    return {
        "config": config_name,
        "model": model_name,
        "chunk_size": chunk_size,
        "dim": dim,
        "max_seq": max_seq,
        "encode_time": round(encode_time, 1),
        "query_time": round(query_time, 1),
        "results": results,
    }


# ── Main ─────────────────────────────────────────────────

def main():
    logger.info("=" * 70)
    logger.info("Encoder Comparison: model × chunk_size")
    logger.info("=" * 70)

    # Load data
    logger.info("\n[1] Loading profiles...")
    profiles = load_all_profiles()
    logger.info("  %d profiles loaded", len(profiles))

    id_lookup = build_id_lookup(list(profiles.keys()))

    # Build query list (deduped — Phase 3 had duplicates)
    seen_queries = set()
    all_queries = []
    for q in TEST_QUERIES:
        if q["query"] not in seen_queries:
            seen_queries.add(q["query"])
            all_queries.append({
                "query": q["query"],
                "expected_hits": q["expected_hits"],
                "min_hits": q["min_hits"],
                "level": q["level"],
            })
    # Add unique FORMULATION_TESTS queries
    for q in FORMULATION_TESTS:
        if q["query"] not in seen_queries:
            seen_queries.add(q["query"])
            all_queries.append({
                "query": q["query"],
                "expected_hits": q["expected_hits"],
                "min_hits": q["min_hits"],
                "level": q["level"],
            })
    logger.info("  %d unique queries (L1=%d, L2=%d, L3=%d, L4=%d)",
                len(all_queries),
                sum(1 for q in all_queries if q["level"] == "L1"),
                sum(1 for q in all_queries if q["level"] == "L2"),
                sum(1 for q in all_queries if q["level"] == "L3"),
                sum(1 for q in all_queries if q["level"] == "L4"),
                )

    # Run all configurations
    logger.info("\n[2] Running configurations...")
    all_results = []

    for model_cfg in MODELS:
        for chunk_size in CHUNK_SIZES:
            try:
                result = run_config(
                    model_name=model_cfg["name"],
                    model_id=model_cfg["model_id"],
                    query_prefix=model_cfg["query_prefix"],
                    chunk_size=chunk_size,
                    profiles=profiles,
                    queries=all_queries,
                    id_lookup=id_lookup,
                )
                all_results.append(result)
            except Exception as e:
                logger.error("    FAILED: %s (chunk=%d): %s", model_cfg["name"], chunk_size, e)
                all_results.append({
                    "config": f"{model_cfg['name']}_chunk{chunk_size}",
                    "model": model_cfg["name"],
                    "chunk_size": chunk_size,
                    "error": str(e),
                    "results": [],
                })

    # Report
    logger.info("\n" + "=" * 70)
    logger.info("Results")
    logger.info("=" * 70)

    levels = ["L1", "L2", "L3", "L4"]

    # Header
    header = f"{'Config':<32} {'Pass':>8} {'Hits':>10}"
    for lv in levels:
        header += f" {lv:>8}"
    header += f" {'Encode':>8} {'Query':>8}"
    logger.info("\n" + header)
    logger.info("-" * len(header))

    for r in all_results:
        if r.get("error") and not r["results"]:
            logger.info(f"{r['config']:<32} {'ERROR':>8} {r.get('error', '')[:30]}")
            continue

        results = r["results"]
        total_pass = sum(1 for x in results if x["passed"])
        total_hits = sum(x["hits"] for x in results)
        total_expected = sum(x["total_expected"] for x in results)

        by_level = {}
        for q, x in zip(all_queries, results):
            lv = q["level"]
            by_level.setdefault(lv, {"pass": 0, "total": 0, "hits": 0, "expected": 0})
            by_level[lv]["total"] += 1
            by_level[lv]["expected"] += x["total_expected"]
            if x["passed"]:
                by_level[lv]["pass"] += 1
            by_level[lv]["hits"] += x["hits"]

        line = f"{r['config']:<32} {total_pass:>3}/{len(results):<3}"
        line += f" {total_hits:>4}/{total_expected:<4}"
        for lv in levels:
            d = by_level.get(lv, {"pass": 0, "total": 0})
            line += f" {d['pass']:>3}/{d['total']:<3}"
        line += f" {r.get('encode_time', '?'):>6}s"
        line += f" {r.get('query_time', '?'):>6}s"
        logger.info(line)

    # Best per model
    logger.info("\n--- Best chunk size per model ---")
    by_model: dict[str, list] = {}
    for r in all_results:
        if r["results"]:
            model = r.get("model", "?")
            by_model.setdefault(model, []).append(r)

    for model, configs in by_model.items():
        best = max(configs, key=lambda c: sum(1 for x in c["results"] if x["passed"]))
        total_pass = sum(1 for x in best["results"] if x["passed"])
        total_hits = sum(x["hits"] for x in best["results"])
        total_expected = sum(x["total_expected"] for x in best["results"])
        logger.info(f"  {model}: best={best['config']} "
                    f"pass={total_pass}/{len(best['results'])} "
                    f"hits={total_hits}/{total_expected}")

    # Save full results
    output_path = Path(__file__).parent / "encoder_comparison_results.json"
    save_data = {
        "metadata": {
            "num_queries": len(all_queries),
            "num_profiles": len(profiles),
            "models": [m["name"] for m in MODELS],
            "chunk_sizes": CHUNK_SIZES,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "configs": [],
    }
    for r in all_results:
        entry = {
            "config": r["config"],
            "model": r.get("model"),
            "chunk_size": r.get("chunk_size"),
            "dim": r.get("dim"),
            "max_seq": r.get("max_seq"),
            "encode_time": r.get("encode_time"),
            "query_time": r.get("query_time"),
            "error": r.get("error"),
            "summary": {
                "total_pass": sum(1 for x in r["results"] if x["passed"]) if r["results"] else 0,
                "total_queries": len(r["results"]),
                "total_hits": sum(x["hits"] for x in r["results"]) if r["results"] else 0,
                "total_expected": sum(x["total_expected"] for x in r["results"]) if r["results"] else 0,
            },
            "per_query": [
                {
                    "query": all_queries[i]["query"],
                    "level": all_queries[i]["level"],
                    "passed": x["passed"],
                    "hits": x["hits"],
                }
                for i, x in enumerate(r["results"])
            ] if r["results"] else [],
        }
        save_data["configs"].append(entry)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    logger.info("\nFull results saved to %s", output_path)


if __name__ == "__main__":
    main()
