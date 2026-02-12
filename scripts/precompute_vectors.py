#!/usr/bin/env python3
"""Pre-compute agent vectors locally using sentence-transformers.

Run this on a dev machine (has torch + sentence-transformers) and commit
the output .npz file. Production loads vectors from file — no model needed.

Usage:
    cd backend && source venv/bin/activate
    python ../scripts/precompute_vectors.py
"""

import asyncio
import json
import sys
from pathlib import Path

import numpy as np

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_DIR / "backend"
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_FILE = DATA_DIR / "agent_vectors.npz"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(PROJECT_DIR))


def _profile_to_text(profile: dict) -> str:
    """Convert an agent profile to a text string for encoding."""
    text_parts = []
    for field in ("self_introduction", "bio", "role"):
        val = profile.get(field)
        if val:
            text_parts.append(str(val))
    skills = profile.get("skills")
    if isinstance(skills, list) and skills:
        text_parts.append(", ".join(str(s) for s in skills))
    for shade in profile.get("shades", []):
        desc = shade.get("description", "") or shade.get("name", "")
        if desc:
            text_parts.append(desc)
    return " ".join(text_parts)


async def main():
    from towow.hdc.encoder import EmbeddingEncoder
    from towow.infra import AgentRegistry

    # Load agents (same as server.py)
    registry = AgentRegistry()

    # Load sample agents from JSON
    from apps.app_store.backend.app import _load_sample_agents
    apps_dir = PROJECT_DIR / "apps"
    _load_sample_agents(registry, apps_dir, llm_client=None)

    # Restore SecondMe users
    users_dir = DATA_DIR / "secondme_users"
    if users_dir.exists():
        for fp in sorted(users_dir.glob("*.json")):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                registry.register_agent(
                    agent_id=data["agent_id"],
                    adapter=None,
                    source="SecondMe",
                    scene_ids=data.get("scene_ids", []),
                    display_name=data["profile"].get("name", data["agent_id"]),
                    profile_data=data["profile"],
                )
            except Exception as e:
                print(f"  Skip {fp.name}: {e}")

    print(f"Registry: {registry.agent_count} agents")

    encoder = EmbeddingEncoder()
    agent_ids = []
    vectors = []
    skipped = 0

    all_ids = list(registry.all_agent_ids)
    BATCH_SIZE = 64

    for i in range(0, len(all_ids), BATCH_SIZE):
        batch_ids = all_ids[i:i + BATCH_SIZE]
        batch_texts = []
        batch_valid_ids = []

        for aid in batch_ids:
            try:
                profile = await registry.get_profile(aid)
            except Exception:
                skipped += 1
                continue
            text = _profile_to_text(profile)
            if not text.strip():
                text = aid
            batch_texts.append(text)
            batch_valid_ids.append(aid)

        if batch_texts:
            batch_vecs = await encoder.batch_encode(batch_texts)
            for aid, vec in zip(batch_valid_ids, batch_vecs):
                agent_ids.append(aid)
                vectors.append(vec)

        print(f"  Encoded {min(i + BATCH_SIZE, len(all_ids))}/{len(all_ids)} agents...")

    # Save as .npz
    np.savez_compressed(
        OUTPUT_FILE,
        agent_ids=np.array(agent_ids, dtype=object),
        vectors=np.stack(vectors),
    )

    file_size = OUTPUT_FILE.stat().st_size / 1024
    print(f"\nDone: {len(agent_ids)} agents encoded, {skipped} skipped")
    print(f"Saved to {OUTPUT_FILE} ({file_size:.0f} KB)")
    print(f"Vector shape: {vectors[0].shape}, dtype: {vectors[0].dtype}")


if __name__ == "__main__":
    asyncio.run(main())
