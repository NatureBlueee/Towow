"""
Phase 0 POC: 意图场匹配验证

步骤：
  1. 加载 447 个 Agent Profile（4 个 JSON 文件）
  2. 用 EmbeddingEncoder 批量编码所有 Profile
  3. 对 test_queries 中的每条查询编码 + 全量余弦匹配
  4. 计算命中率，输出报告

运行方式：
  cd backend && source venv/bin/activate
  python -m tests.field_poc.field_poc

或从项目根目录：
  cd backend && source venv/bin/activate
  PYTHONPATH=. python ../tests/field_poc/field_poc.py
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

# 确保 backend 在 sys.path 中
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from towow.hdc.encoder import EmbeddingEncoder
from towow.hdc.resonance import CosineResonanceDetector

# Import test queries - handle both module and direct execution
try:
    from tests.field_poc.test_queries import TEST_QUERIES
except ModuleNotFoundError:
    from test_queries import TEST_QUERIES


# ================================================================
# Agent Profile 加载
# ================================================================

AGENT_FILES = [
    PROJECT_ROOT / "apps" / "S1_hackathon" / "data" / "agents.json",
    PROJECT_ROOT / "apps" / "S2_skill_exchange" / "data" / "agents.json",
    PROJECT_ROOT / "apps" / "R1_recruitment" / "data" / "agents.json",
    PROJECT_ROOT / "apps" / "M1_matchmaking" / "data" / "agents.json",
]


def load_all_profiles() -> dict[str, str]:
    """加载所有 Agent Profile，返回 {agent_id: profile_text}。

    Profile text 是把所有字段拼成一段自然语言。
    跨场景同 ID 的 Agent 用场景前缀区分。
    """
    profiles: dict[str, str] = {}
    scene_prefixes = ["h_", "s_", "r_", "m_"]

    for filepath, prefix in zip(AGENT_FILES, scene_prefixes):
        if not filepath.exists():
            print(f"WARNING: {filepath} not found, skipping")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for agent_key, agent_data in data.items():
            # 用场景前缀避免跨场景 ID 冲突
            agent_id = f"{prefix}{agent_key}"

            # 把 Profile 拼成一段自然语言文本
            parts = []
            name = agent_data.get("name", "")
            role = agent_data.get("role", agent_data.get("occupation", ""))
            bio = agent_data.get("bio", "")
            skills = agent_data.get("skills", [])
            interests = agent_data.get("interests", [])

            if name:
                parts.append(name)
            if role:
                parts.append(role)
            if bio:
                parts.append(bio)
            if skills:
                parts.append("技能: " + ", ".join(str(s) for s in skills))
            if interests:
                parts.append("兴趣: " + ", ".join(str(s) for s in interests))

            # 场景特有字段
            for field in ["can_teach", "want_to_learn", "looking_for",
                          "experience", "hackathon_history", "ideal_match",
                          "values", "quirks", "work_style"]:
                val = agent_data.get(field)
                if val:
                    if isinstance(val, list):
                        parts.append(f"{field}: " + ", ".join(str(v) for v in val))
                    else:
                        parts.append(f"{field}: {val}")

            text = " | ".join(parts)
            if text.strip():
                profiles[agent_id] = text

    return profiles


# ================================================================
# POC 主逻辑
# ================================================================

async def run_poc():
    print("=" * 70)
    print("Phase 0 POC: 意图场匹配验证")
    print("=" * 70)

    # 1. 加载 Profile
    print("\n[1/4] 加载 Agent Profiles...")
    profiles = load_all_profiles()
    print(f"  加载了 {len(profiles)} 个 Agent Profile")

    # 2. 编码
    print("\n[2/4] 初始化编码器 + 批量编码...")
    encoder = EmbeddingEncoder()
    t0 = time.time()

    agent_ids = list(profiles.keys())
    agent_texts = [profiles[aid] for aid in agent_ids]
    agent_vectors_list = await encoder.batch_encode(agent_texts)

    encode_time = time.time() - t0
    print(f"  编码 {len(agent_ids)} 个 Profile 耗时: {encode_time:.2f}s")
    print(f"  平均每个: {encode_time / len(agent_ids) * 1000:.1f}ms")
    print(f"  向量维度: {agent_vectors_list[0].shape}")

    # 构建 agent_vectors dict
    agent_vectors: dict[str, np.ndarray] = {
        aid: vec for aid, vec in zip(agent_ids, agent_vectors_list)
    }

    # 3. 运行测试查询
    print("\n[3/4] 运行测试查询...")
    detector = CosineResonanceDetector()
    results = []

    for i, test in enumerate(TEST_QUERIES):
        query = test["query"]
        t0 = time.time()

        # 编码查询
        query_vec = await encoder.encode(query)

        # 全量匹配
        activated, _ = await detector.detect(
            demand_vector=query_vec,
            agent_vectors=agent_vectors,
            k_star=10,
            min_score=0.0,
        )
        match_time = time.time() - t0

        # 计算命中率
        # test_queries 中的 expected_hits 不带场景前缀，需要模糊匹配
        top10_raw_ids = [aid for aid, _ in activated]
        top10_base_ids = [aid.split("_", 1)[1] if "_" in aid else aid
                          for aid in top10_raw_ids]

        hits = []
        for expected_id in test["expected_hits"]:
            # 检查是否在 top10 中（去掉场景前缀后匹配）
            if expected_id in top10_base_ids:
                hits.append(expected_id)

        hit_count = len(hits)
        expected_count = len(test["expected_hits"])
        min_required = test["min_hits"]
        passed = hit_count >= min_required

        result = {
            "index": i,
            "query": query,
            "level": test["level"],
            "top10": [(aid, f"{score:.4f}") for aid, score in activated],
            "hits": hits,
            "hit_count": hit_count,
            "expected_count": expected_count,
            "min_required": min_required,
            "passed": passed,
            "match_time_ms": match_time * 1000,
        }
        results.append(result)

        # 输出每条结果
        status = "PASS" if passed else "FAIL"
        print(f"\n  [{test['level']}] Q{i+1}: \"{query}\"")
        print(f"    {status} — {hit_count}/{expected_count} hits "
              f"(min {min_required}) | {match_time*1000:.1f}ms")
        print(f"    Top-5:")
        for rank, (aid, score) in enumerate(activated[:5], 1):
            base_id = aid.split("_", 1)[1] if "_" in aid else aid
            marker = " <<<" if base_id in test["expected_hits"] else ""
            # 截取 profile 前 60 字符
            profile_preview = profiles.get(aid, "")[:60]
            print(f"      {rank}. [{score:.4f}] {aid}: {profile_preview}...{marker}")

    # 4. 汇总报告
    print("\n" + "=" * 70)
    print("[4/4] 汇总报告")
    print("=" * 70)

    by_level = {}
    for r in results:
        level = r["level"]
        by_level.setdefault(level, []).append(r)

    total_pass = sum(1 for r in results if r["passed"])
    total = len(results)

    for level in sorted(by_level):
        level_results = by_level[level]
        level_pass = sum(1 for r in level_results if r["passed"])
        level_total = len(level_results)
        level_hits = sum(r["hit_count"] for r in level_results)
        level_expected = sum(r["expected_count"] for r in level_results)
        avg_time = sum(r["match_time_ms"] for r in level_results) / level_total

        print(f"\n  {level}: {level_pass}/{level_total} queries passed")
        print(f"    Total hits: {level_hits}/{level_expected}")
        print(f"    Avg time: {avg_time:.1f}ms")

        for r in level_results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"    {status} Q{r['index']+1}: \"{r['query']}\" "
                  f"({r['hit_count']}/{r['expected_count']})")

    print(f"\n  Overall: {total_pass}/{total} queries passed")

    # 写入结果 JSON
    output_path = PROJECT_ROOT / "tests" / "field_poc" / "poc_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  结果写入: {output_path}")

    return results


if __name__ == "__main__":
    asyncio.run(run_poc())
