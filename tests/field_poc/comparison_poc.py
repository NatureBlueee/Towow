"""
SimHash + Bundle 对比 POC

对比 4 种编码策略 × 2 种相似度变体 = 8 组数据：

策略矩阵（编码方式 × 模型）：
  A: MiniLM-384d + Flat Encode（整段拼接，一次 encode）
  B: MiniLM-384d + Chunked Bundle（拆分 Profile，逐块 encode，bundle 叠加）
  C: mpnet-768d + Flat Encode
  D: mpnet-768d + Chunked Bundle

相似度变体：
  dense:  原始浮点向量 + cosine similarity
  binary: SimHash → 10,000 维二进制 + Hamming similarity

运行方式：
  cd backend && source venv/bin/activate
  PYTHONPATH=. python ../tests/field_poc/comparison_poc.py
"""

import asyncio
import json
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

# Import from sibling modules
try:
    from tests.field_poc.field_poc import load_all_profiles
    from tests.field_poc.test_queries import TEST_QUERIES
    from tests.field_poc.hdc import (
        SimHash,
        hamming_similarity,
        batch_hamming_similarity,
        bundle_binary,
        bundle_dense,
        cosine_similarity,
    )
except ModuleNotFoundError:
    from field_poc import load_all_profiles
    from test_queries import TEST_QUERIES
    from hdc import (
        SimHash,
        hamming_similarity,
        batch_hamming_similarity,
        bundle_binary,
        bundle_dense,
        cosine_similarity,
    )


# ================================================================
# Agent JSON 文件路径（用于 chunked 编码）
# ================================================================

AGENT_FILES = [
    (PROJECT_ROOT / "apps" / "S1_hackathon" / "data" / "agents.json", "h_"),
    (PROJECT_ROOT / "apps" / "S2_skill_exchange" / "data" / "agents.json", "s_"),
    (PROJECT_ROOT / "apps" / "R1_recruitment" / "data" / "agents.json", "r_"),
    (PROJECT_ROOT / "apps" / "M1_matchmaking" / "data" / "agents.json", "m_"),
]


def load_profile_chunks() -> dict[str, list[str]]:
    """加载所有 Agent Profile 并拆分为语义块。

    返回 {agent_id: [chunk1, chunk2, ...]}
    每个 chunk 是一段独立有语义的文本。

    拆分策略（对应架构文档 Section 6.1.5）：
    - name + role 合为一个 chunk（身份）
    - bio 是一个 chunk（自我描述）
    - 每个 skill 单独一个 chunk（独立能力维度）
    - 每个 interest 单独一个 chunk
    - 其他场景字段各自一个 chunk
    """
    chunks: dict[str, list[str]] = {}

    for filepath, prefix in AGENT_FILES:
        if not filepath.exists():
            print(f"WARNING: {filepath} not found, skipping")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for agent_key, agent_data in data.items():
            agent_id = f"{prefix}{agent_key}"
            agent_chunks: list[str] = []

            # 身份 chunk: name + role
            name = agent_data.get("name", "")
            role = agent_data.get("role", agent_data.get("occupation", ""))
            identity = " ".join(filter(None, [name, role]))
            if identity.strip():
                agent_chunks.append(identity)

            # Bio chunk
            bio = agent_data.get("bio", "")
            if bio.strip():
                agent_chunks.append(bio)

            # 每个 skill 单独一个 chunk
            for skill in agent_data.get("skills", []):
                s = str(skill).strip()
                if s:
                    agent_chunks.append(s)

            # 每个 interest 单独一个 chunk
            for interest in agent_data.get("interests", []):
                s = str(interest).strip()
                if s:
                    agent_chunks.append(s)

            # 场景特有字段
            for field in ["can_teach", "want_to_learn", "looking_for",
                          "experience", "hackathon_history", "ideal_match",
                          "values", "quirks", "work_style", "style"]:
                val = agent_data.get(field)
                if val:
                    if isinstance(val, list):
                        for item in val:
                            s = str(item).strip()
                            if s:
                                agent_chunks.append(f"{field}: {s}")
                    else:
                        agent_chunks.append(f"{field}: {val}")

            if agent_chunks:
                chunks[agent_id] = agent_chunks

    return chunks


# ================================================================
# 编码策略
# ================================================================

async def encode_flat_dense(
    encoder: EmbeddingEncoder,
    profiles: dict[str, str],
) -> dict[str, np.ndarray]:
    """Flat encode: 整段 profile text → 一个 dense vector"""
    agent_ids = list(profiles.keys())
    texts = [profiles[aid] for aid in agent_ids]
    vectors = await encoder.batch_encode(texts)
    return {aid: vec for aid, vec in zip(agent_ids, vectors)}


async def encode_flat_binary(
    encoder: EmbeddingEncoder,
    profiles: dict[str, str],
    simhash: SimHash,
) -> dict[str, np.ndarray]:
    """Flat encode → SimHash: 整段 text → dense → binary"""
    agent_ids = list(profiles.keys())
    texts = [profiles[aid] for aid in agent_ids]
    vectors = await encoder.batch_encode(texts)
    vecs_array = np.stack(vectors)
    binary_vecs = simhash.batch_project(vecs_array)
    return {aid: bvec for aid, bvec in zip(agent_ids, binary_vecs)}


async def encode_chunked_dense(
    encoder: EmbeddingEncoder,
    chunks: dict[str, list[str]],
) -> dict[str, np.ndarray]:
    """Chunked bundle (dense): 每个 chunk 独立 encode → 平均+归一化 bundle"""
    result = {}
    # 收集所有 chunk texts 和对应的 agent_id
    all_texts: list[str] = []
    agent_chunk_ranges: list[tuple[str, int, int]] = []

    for agent_id, chunk_list in chunks.items():
        start = len(all_texts)
        all_texts.extend(chunk_list)
        end = len(all_texts)
        agent_chunk_ranges.append((agent_id, start, end))

    # 批量编码所有 chunk
    all_vectors = await encoder.batch_encode(all_texts)

    # 按 agent 分组 bundle
    for agent_id, start, end in agent_chunk_ranges:
        agent_vecs = all_vectors[start:end]
        result[agent_id] = bundle_dense(agent_vecs)

    return result


async def encode_chunked_binary(
    encoder: EmbeddingEncoder,
    chunks: dict[str, list[str]],
    simhash: SimHash,
) -> dict[str, np.ndarray]:
    """Chunked bundle (binary): 每个 chunk → dense → SimHash → binary bundle"""
    result = {}
    all_texts: list[str] = []
    agent_chunk_ranges: list[tuple[str, int, int]] = []

    for agent_id, chunk_list in chunks.items():
        start = len(all_texts)
        all_texts.extend(chunk_list)
        end = len(all_texts)
        agent_chunk_ranges.append((agent_id, start, end))

    # 批量编码所有 chunk
    all_vectors = await encoder.batch_encode(all_texts)
    all_vecs_array = np.stack(all_vectors)

    # 批量 SimHash
    all_binary = simhash.batch_project(all_vecs_array)

    # 按 agent 分组 binary bundle
    for agent_id, start, end in agent_chunk_ranges:
        agent_bins = all_binary[start:end]
        result[agent_id] = bundle_binary(agent_bins)

    return result


# ================================================================
# 匹配 + 评估
# ================================================================

def match_dense(
    query_vec: np.ndarray,
    agent_vecs: dict[str, np.ndarray],
    k: int = 10,
) -> list[tuple[str, float]]:
    """Dense cosine similarity Top-K"""
    scores = []
    for aid, avec in agent_vecs.items():
        sim = cosine_similarity(query_vec, avec)
        scores.append((aid, sim))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:k]


def match_binary(
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


def evaluate_topk(
    top_k: list[tuple[str, float]],
    test: dict,
) -> dict:
    """评估一条查询的 Top-K 结果"""
    top_raw_ids = [aid for aid, _ in top_k]
    top_base_ids = [
        aid.split("_", 1)[1] if "_" in aid else aid
        for aid in top_raw_ids
    ]

    hits = [
        eid for eid in test["expected_hits"]
        if eid in top_base_ids
    ]

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

MODELS = [
    ("MiniLM-384d", "paraphrase-multilingual-MiniLM-L12-v2", 384),
    ("mpnet-768d", "paraphrase-multilingual-mpnet-base-v2", 768),
]


async def run_comparison():
    print("=" * 70)
    print("SimHash + Bundle 对比 POC")
    print("=" * 70)

    # 加载数据
    print("\n[1] 加载 Agent Profiles...")
    profiles = load_all_profiles()
    chunks = load_profile_chunks()
    print(f"  {len(profiles)} 个 Profile (flat)")
    print(f"  {len(chunks)} 个 Profile (chunked)")

    total_chunks = sum(len(c) for c in chunks.values())
    avg_chunks = total_chunks / len(chunks) if chunks else 0
    print(f"  总 chunk 数: {total_chunks}, 平均每人: {avg_chunks:.1f} 个 chunk")

    all_results: dict[str, list[dict]] = {}

    for model_label, model_name, dim in MODELS:
        print(f"\n{'=' * 70}")
        print(f"[Model] {model_label} ({model_name})")
        print(f"{'=' * 70}")

        encoder = EmbeddingEncoder(model_name=model_name)
        simhash = SimHash(input_dim=dim, D=10_000, seed=42)

        # ---------- Strategy: Flat Dense ----------
        strategy_name = f"{model_label}-flat-dense"
        print(f"\n  [{strategy_name}] 编码中...")
        t0 = time.time()
        flat_dense_vecs = await encode_flat_dense(encoder, profiles)
        t_encode = time.time() - t0
        print(f"    编码耗时: {t_encode:.1f}s")

        results = []
        for test in TEST_QUERIES:
            qvec = await encoder.encode(test["query"])
            top_k = match_dense(qvec, flat_dense_vecs)
            ev = evaluate_topk(top_k, test)
            ev["query"] = test["query"]
            ev["level"] = test["level"]
            ev["top5"] = [(aid, f"{s:.4f}") for aid, s in top_k[:5]]
            results.append(ev)
        all_results[strategy_name] = results

        # ---------- Strategy: Flat Binary ----------
        strategy_name = f"{model_label}-flat-binary"
        print(f"\n  [{strategy_name}] 编码中...")
        t0 = time.time()
        flat_binary_vecs = await encode_flat_binary(encoder, profiles, simhash)
        t_encode = time.time() - t0
        print(f"    编码耗时: {t_encode:.1f}s")

        results = []
        for test in TEST_QUERIES:
            qvec = await encoder.encode(test["query"])
            qbin = simhash.project(qvec)
            top_k = match_binary(qbin, flat_binary_vecs)
            ev = evaluate_topk(top_k, test)
            ev["query"] = test["query"]
            ev["level"] = test["level"]
            ev["top5"] = [(aid, f"{s:.4f}") for aid, s in top_k[:5]]
            results.append(ev)
        all_results[strategy_name] = results

        # ---------- Strategy: Chunked Dense Bundle ----------
        strategy_name = f"{model_label}-chunk-dense"
        print(f"\n  [{strategy_name}] 编码中...")
        t0 = time.time()
        chunk_dense_vecs = await encode_chunked_dense(encoder, chunks)
        t_encode = time.time() - t0
        print(f"    编码耗时: {t_encode:.1f}s")

        results = []
        for test in TEST_QUERIES:
            qvec = await encoder.encode(test["query"])
            top_k = match_dense(qvec, chunk_dense_vecs)
            ev = evaluate_topk(top_k, test)
            ev["query"] = test["query"]
            ev["level"] = test["level"]
            ev["top5"] = [(aid, f"{s:.4f}") for aid, s in top_k[:5]]
            results.append(ev)
        all_results[strategy_name] = results

        # ---------- Strategy: Chunked Binary Bundle ----------
        strategy_name = f"{model_label}-chunk-binary"
        print(f"\n  [{strategy_name}] 编码中...")
        t0 = time.time()
        chunk_binary_vecs = await encode_chunked_binary(encoder, chunks, simhash)
        t_encode = time.time() - t0
        print(f"    编码耗时: {t_encode:.1f}s")

        results = []
        for test in TEST_QUERIES:
            qvec = await encoder.encode(test["query"])
            qbin = simhash.project(qvec)
            top_k = match_binary(qbin, chunk_binary_vecs)
            ev = evaluate_topk(top_k, test)
            ev["query"] = test["query"]
            ev["level"] = test["level"]
            ev["top5"] = [(aid, f"{s:.4f}") for aid, s in top_k[:5]]
            results.append(ev)
        all_results[strategy_name] = results

    # ================================================================
    # 汇总报告
    # ================================================================
    print("\n\n" + "=" * 90)
    print("对比报告")
    print("=" * 90)

    # 表头
    strategies = list(all_results.keys())
    levels = ["L1", "L2", "L3", "L4"]

    # 计算每个策略每个 level 的通过数
    summary = {}
    for sname, sresults in all_results.items():
        by_level = {}
        for r in sresults:
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

    # 打印对比表
    header = f"{'Strategy':<28}"
    for level in levels:
        header += f" | {level:>5}"
    header += f" | {'Total':>7} | {'Hits':>10}"
    print(f"\n{header}")
    print("-" * len(header))

    for sname in strategies:
        s = summary[sname]
        row = f"{sname:<28}"
        for level in levels:
            ld = s["by_level"].get(level, {"passed": 0, "total": 0})
            row += f" | {ld['passed']}/{ld['total']:>2}"
        row += f" | {s['total_passed']:>3}/{s['total_queries']:>2}"
        row += f" | {s['total_hits']:>3}/{s['total_expected']:>3}"
        print(row)

    # 逐查询对比（每个查询在不同策略下的表现）
    print(f"\n\n{'=' * 90}")
    print("逐查询对比")
    print("=" * 90)

    for i, test in enumerate(TEST_QUERIES):
        print(f"\n  Q{i+1} [{test['level']}]: \"{test['query']}\"")
        for sname in strategies:
            r = all_results[sname][i]
            status = "PASS" if r["passed"] else "FAIL"
            print(f"    {status} {sname:<28} {r['hit_count']}/{r['expected_count']} hits")

    # 写入结果
    output_path = PROJECT_ROOT / "tests" / "field_poc" / "comparison_results.json"
    output = {
        "summary": {
            sname: {
                "by_level": {
                    level: {
                        "passed": ld["passed"],
                        "total": ld["total"],
                        "hits": ld["hits"],
                        "expected": ld["expected"],
                    }
                    for level, ld in s["by_level"].items()
                },
                "total_passed": s["total_passed"],
                "total_queries": s["total_queries"],
                "total_hits": s["total_hits"],
                "total_expected": s["total_expected"],
            }
            for sname, s in summary.items()
        },
        "details": {
            sname: sresults
            for sname, sresults in all_results.items()
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n\n结果写入: {output_path}")


if __name__ == "__main__":
    asyncio.run(run_comparison())
