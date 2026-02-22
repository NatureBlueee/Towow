#!/usr/bin/env python3
"""
通用结晶实验运行脚本。

读取 config.json 执行结晶实验，支持 3-8 人、任意 Profile、参数化模型和 token 配置。
端侧 Agent 并行调用（asyncio），催化 Agent 串行。

Prompt 架构（v1/v2）：
- 端侧: system prompt（角色+张力+Profile） + user message（R1 触发 / R2+ 催化观察）
- 催化: system prompt（角色+张力+参与者，R3+ 追加相变检测） + user message（各方回复+历史）
- 收敛后: 催化额外调用生成关系图谱

用法:
    cd backend && source venv/bin/activate
    TOWOW_PROXY_API_KEY=sk-... python ../tests/crystallization_poc/simulations/real/run_real.py --config run_002/config.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from anthropic import AsyncAnthropic


class NoveltyTracker:
    """Track information novelty per agent using embedding cosine similarity.

    Measures how much new information each round adds, compared to ALL previous
    rounds for the same agent. Novelty 1.0 = completely new, 0.0 = identical to history.
    """

    def __init__(self, encoder):
        self.encoder = encoder
        self.history: dict[str, list[np.ndarray]] = {}

    def measure(self, agent_id: str, text: str) -> float:
        vec = self.encoder.encode([text])[0]
        if agent_id not in self.history:
            self.history[agent_id] = [vec]
            return 1.0

        # Compare against ALL history (catches skip-repeat patterns)
        max_sim = max(
            float(np.dot(vec, prev) / (np.linalg.norm(vec) * np.linalg.norm(prev) + 1e-8))
            for prev in self.history[agent_id]
        )
        self.history[agent_id].append(vec)
        return round(1.0 - max_sim, 4)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def resolve_path(path_str: str, repo_root: Path) -> Path:
    """Resolve a path relative to repo root."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    return repo_root / p


def extract_prompt_block(filepath: Path) -> str:
    """Extract content between first pair of ``` markers."""
    content = load_text(filepath)
    in_block = False
    lines = []
    for line in content.split("\n"):
        if line.strip() == "```" and not in_block:
            in_block = True
            continue
        elif line.strip() == "```" and in_block:
            break
        elif in_block:
            lines.append(line)
    return "\n".join(lines)


def extract_all_prompt_blocks(filepath: Path) -> list[str]:
    """Extract all content blocks between ``` markers.

    Returns a list of strings, one per block. Used for prompts with
    multiple template sections (e.g. system + round2+ + convergence).
    """
    content = load_text(filepath)
    blocks = []
    current_block = []
    in_block = False
    for line in content.split("\n"):
        if line.strip() == "```" and not in_block:
            in_block = True
            current_block = []
            continue
        elif line.strip() == "```" and in_block:
            blocks.append("\n".join(current_block))
            in_block = False
        elif in_block:
            current_block.append(line)
    return blocks


def get_participant_info(participants: list[dict], exclude_name: str) -> str:
    """Build brief info of other participants."""
    lines = []
    for p in participants:
        if p["name"] != exclude_name:
            lines.append(f"- {p['brief']}")
    return "\n".join(lines)


def build_formulation_prompt(
    formulation_template: str,
    source_profile: str,
    raw_intent: str,
) -> str:
    """Build formulation prompt by filling template."""
    filled = formulation_template.replace("{{PROFILE}}", source_profile)
    filled = filled.replace("{{RAW_INTENT}}", raw_intent)
    return filled


def build_endpoint_messages(
    system_template: str,
    round2_template: str | None,
    owner_name: str,
    owner_profile: str,
    trigger_context: str,
    catalyst_observation: str | None,
    round_number: int,
) -> tuple[str, str]:
    """Build endpoint agent system prompt and user message.

    System prompt = role + tension + task + rules + profile (stable across rounds).
    User message = round trigger (R1) or catalyst observations (R2+).
    """
    system = system_template
    system = system.replace("{{agent_name}}", owner_name)
    system = system.replace("{{tension_context}}", trigger_context)
    system = system.replace("{{profile}}", owner_profile)

    if round_number == 1 or not catalyst_observation:
        user = f"这是第 {round_number} 轮。请输出你的三维投影。"
    else:
        if round2_template:
            user = round2_template.replace(
                "{{catalyst_output_previous_round}}", catalyst_observation
            )
            user += f"\n\n这是第 {round_number} 轮。"
        else:
            user = (
                f"上一轮主持人的观察：\n\n{catalyst_observation}\n\n"
                f"这是第 {round_number} 轮。请输出新的三维投影，只说新内容。"
            )

    return system, user


def build_catalyst_user_message(
    trigger_context: str,
    round_responses: dict[str, str],
    history: list[dict],
    round_number: int,
) -> str:
    msg = f"## 触发事件\n\n{trigger_context}\n\n"

    if history:
        msg += "## 历史上下文\n\n"
        for h in history:
            msg += f"### 第 {h['round']} 轮催化观察\n\n{h['observation']}\n\n"

    msg += f"## 第 {round_number} 轮 · 所有参与者的回复\n\n"
    for name, response in round_responses.items():
        msg += f"### {name}\n\n{response}\n\n"

    return msg


def build_plan_user_message(
    trigger_context: str,
    profiles: dict[str, str],
    transcript: str,
    plan_prompt_path: Path,
    relationship_map: str | None = None,
) -> str:
    template = extract_prompt_block(plan_prompt_path)

    profiles_text = ""
    for name, profile in profiles.items():
        profiles_text += f"### {name}\n\n{profile}\n\n"

    filled = template.replace("{{TRIGGER_CONTEXT}}", trigger_context)
    filled = filled.replace("{{PARTICIPANT_PROFILES}}", profiles_text)
    filled = filled.replace("{{CRYSTALLIZATION_TRANSCRIPT}}", transcript)

    if relationship_map:
        filled += f"\n\n## 催化最终关系图谱\n\n{relationship_map}"

    return filled


def check_convergence(observation: str) -> bool:
    """Check for convergence signals in catalyst output."""
    markers = [
        "本轮没有新发现",
        "没有新的发现",
        "没有新发现",
        "新发现数量：0",
        "新发现数量: 0",
        "0 个新发现",
        "零个新发现",
        "本轮没有新的关系发现",
        "信息差已基本消除",
    ]
    obs_lower = observation.lower()
    return any(m in obs_lower for m in markers)


async def call_llm(
    client: AsyncAnthropic,
    model: str,
    user: str,
    system: str | None = None,
    max_tokens: int = 4096,
    max_retries: int = 8,
) -> str:
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
        "betas": ["context-1m-2025-08-07"],
    }
    if system:
        kwargs["system"] = system

    for attempt in range(max_retries):
        try:
            response = await client.beta.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                wait = min(60 * (2 ** attempt), 300)
                print(f"\n  [RATE LIMIT] Wait {wait}s (attempt {attempt+1}/{max_retries})...", end="", flush=True)
                await asyncio.sleep(wait)
                print(" retrying", flush=True)
            else:
                raise
    raise RuntimeError(f"Failed after {max_retries} retries")


def load_manual_responses(manual_file: Path, round_number: int) -> dict[str, str] | None:
    """Load pre-written responses for a specific round."""
    if not manual_file.exists():
        return None
    data = json.loads(manual_file.read_text(encoding="utf-8"))
    return data.get(str(round_number))


async def run_endpoint_agent(
    client: AsyncAnthropic,
    endpoint_system_template: str,
    endpoint_round2_template: str | None,
    participant: dict,
    profile: str,
    trigger_context: str,
    catalyst_observation: str | None,
    round_number: int,
    model: str,
    max_tokens: int,
) -> tuple[str, str]:
    """Run a single endpoint agent. Returns (name, response)."""
    name = participant["name"]
    system, user = build_endpoint_messages(
        system_template=endpoint_system_template,
        round2_template=endpoint_round2_template,
        owner_name=name,
        owner_profile=profile,
        trigger_context=trigger_context,
        catalyst_observation=catalyst_observation,
        round_number=round_number,
    )
    response = await call_llm(client, model, user=user, system=system, max_tokens=max_tokens)
    return name, response


async def run_experiment(config_path: str, enable_novelty: bool = False):
    # Resolve paths
    config_file = Path(config_path)
    if not config_file.is_absolute():
        config_file = Path.cwd() / config_file
    run_dir = config_file.parent
    repo_root = Path(__file__).parents[4]

    config = json.loads(config_file.read_text(encoding="utf-8"))

    # API configuration: support proxy via config.api section
    api_config = config.get("api", {})
    api_key_env = api_config.get("api_key_env", "TOWOW_ANTHROPIC_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ValueError(f"{api_key_env} not set")

    client_kwargs = {"api_key": api_key}
    base_url = api_config.get("base_url")
    if base_url:
        client_kwargs["base_url"] = base_url
        print(f"Using API proxy: {base_url}")

    client = AsyncAnthropic(**client_kwargs)
    output_dir = run_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    run_id = config["run_id"]
    participants = config["participants"]
    models = config["models"]
    params = config["params"]
    prompts_config = config["prompts"]

    max_rounds = params.get("max_rounds", 6)
    convergence_threshold = params.get("convergence_threshold", 2)
    max_tokens_formulation = params.get("max_tokens_formulation", 2048)
    max_tokens_catalyst = params.get("max_tokens_catalyst", 6000)
    max_tokens_endpoint = params.get("max_tokens_endpoint", 2048)
    max_tokens_plan = params.get("max_tokens_plan", 4096)

    # Load participant profiles
    profiles = {}
    for p in participants:
        profile_path = resolve_path(p["profile_file"], repo_root)
        profiles[p["name"]] = load_text(profile_path)

    # Load prompts — multi-block extraction
    # Catalyst: [system, phase_transition (R3+), convergence_output]
    catalyst_prompt_path = resolve_path(prompts_config["catalyst"], repo_root)
    catalyst_blocks = extract_all_prompt_blocks(catalyst_prompt_path)
    catalyst_system_raw = catalyst_blocks[0] if catalyst_blocks else ""
    catalyst_phase_transition = catalyst_blocks[1] if len(catalyst_blocks) > 1 else None
    catalyst_convergence_template = catalyst_blocks[2] if len(catalyst_blocks) > 2 else None

    # Endpoint: [system, round2+]
    endpoint_prompt_path = resolve_path(prompts_config["endpoint"], repo_root)
    endpoint_blocks = extract_all_prompt_blocks(endpoint_prompt_path)
    endpoint_system_template = endpoint_blocks[0] if endpoint_blocks else ""
    endpoint_round2_template = endpoint_blocks[1] if len(endpoint_blocks) > 1 else None

    plan_prompt_path = resolve_path(prompts_config["plan_generator"], repo_root)

    # Manual responses
    manual_file = None
    if config.get("manual_responses"):
        manual_file = resolve_path(config["manual_responses"], run_dir)

    print(f"=== {run_id}: Crystallization Experiment ===")
    print(f"Participants ({len(participants)}): {', '.join(p['name'] for p in participants)}")
    print(f"Models: formulation={models.get('formulation', 'N/A')}, catalyst={models['catalyst']}, endpoint={models['endpoint']}")
    print(f"Max rounds: {max_rounds}, convergence: {convergence_threshold}")
    print(f"Max tokens: catalyst={max_tokens_catalyst}, endpoint={max_tokens_endpoint}")
    print(f"Endpoint blocks: {len(endpoint_blocks)}, Catalyst blocks: {len(catalyst_blocks)}")

    # Novelty tracking (optional diagnostic)
    novelty_tracker = None
    if enable_novelty:
        try:
            # Add backend to path for potential future encoder reuse
            backend_dir = repo_root / "backend"
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            from sentence_transformers import SentenceTransformer
            print("Loading encoder for novelty tracking...", end="", flush=True)
            st_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
            novelty_tracker = NoveltyTracker(st_model)
            print(" done")
        except ImportError:
            print("[SKIP] sentence-transformers not installed, novelty tracking disabled")
    print()

    # ==========================================
    # Step 0: Formulation
    # ==========================================
    demand = config["demand"]

    if "source_profile" in demand and demand["source_profile"] and "formulation" in prompts_config:
        print("--- Step 0: Formulation ---")
        form_start = time.time()

        source_profile_path = resolve_path(demand["source_profile"], repo_root)
        source_profile = load_text(source_profile_path)
        raw_intent = demand.get("raw_intent", demand.get("description", ""))

        formulation_prompt_path = resolve_path(prompts_config["formulation"], repo_root)
        formulation_template = extract_prompt_block(formulation_prompt_path)

        formulation_user = build_formulation_prompt(formulation_template, source_profile, raw_intent)

        print(f"  Source profile: {demand['source_profile']} ({len(source_profile)} chars)")
        print(f"  Raw intent: {raw_intent[:80]}...")
        print(f"  Calling formulation model...", end="", flush=True)

        trigger_context = await call_llm(
            client,
            models.get("formulation", models["endpoint"]),
            user=formulation_user,
            max_tokens=max_tokens_formulation,
        )

        # Save formulated demand
        (output_dir / "formulated_demand.md").write_text(
            f"# Formulated Demand\n\n**Raw intent**: {raw_intent}\n\n**Formulated**:\n\n{trigger_context}",
            encoding="utf-8",
        )
        print(f" {len(trigger_context)} chars ({time.time() - form_start:.1f}s)")
        print()
    else:
        # Fallback: use description or trigger_file directly
        if "trigger_file" in demand and demand["trigger_file"]:
            trigger_path = resolve_path(demand["trigger_file"], repo_root)
            trigger_context = load_text(trigger_path)
        else:
            trigger_context = demand.get("description", demand.get("raw_intent", ""))
        print(f"  [SKIP] Formulation: using raw trigger ({len(trigger_context)} chars)")
        print()

    # ==========================================
    # Fill catalyst system with tension + participants
    # ==========================================
    participant_names = [p["name"] for p in participants]
    catalyst_system_base = catalyst_system_raw
    catalyst_system_base = catalyst_system_base.replace("{{tension_context}}", trigger_context)
    catalyst_system_base = catalyst_system_base.replace("{{participant_list}}", "、".join(participant_names))

    # ==========================================
    # Crystallization Rounds
    # ==========================================
    history: list[dict] = []
    all_rounds: list[dict] = []
    consecutive_no_new = 0

    for round_num in range(1, max_rounds + 1):
        print(f"--- Round {round_num} ---")
        round_start = time.time()
        round_data = {"round": round_num, "responses": {}, "observation": "", "novelty": {}}

        prev_observation = history[-1]["observation"] if history else None

        # Check for manual responses this round
        manual = None
        if manual_file:
            manual = load_manual_responses(manual_file, round_num)

        # Parallel endpoint agent calls
        auto_participants = []
        for p in participants:
            name = p["name"]
            if manual and name in manual:
                print(f"  [MANUAL] {name}: {len(manual[name])} chars")
                round_data["responses"][name] = manual[name]
            else:
                auto_participants.append(p)

        if auto_participants:
            print(f"  Calling {len(auto_participants)} endpoint agents in parallel...", flush=True)
            tasks = [
                run_endpoint_agent(
                    client=client,
                    endpoint_system_template=endpoint_system_template,
                    endpoint_round2_template=endpoint_round2_template,
                    participant=p,
                    profile=profiles[p["name"]],
                    trigger_context=trigger_context,
                    catalyst_observation=prev_observation,
                    round_number=round_num,
                    model=models["endpoint"],
                    max_tokens=max_tokens_endpoint,
                )
                for p in auto_participants
            ]
            results = await asyncio.gather(*tasks)
            for name, response in results:
                round_data["responses"][name] = response
                if novelty_tracker:
                    n = novelty_tracker.measure(name, response)
                    round_data["novelty"][name] = n
                    print(f"    {name}: {len(response)} chars (novelty={n:.3f})")
                else:
                    print(f"    {name}: {len(response)} chars")

        # Build catalyst system (add phase transition for R3+)
        if round_num >= 3 and catalyst_phase_transition:
            catalyst_system = catalyst_system_base + "\n\n" + catalyst_phase_transition
        else:
            catalyst_system = catalyst_system_base

        # Sequential catalyst call
        print(f"  Calling catalyst...", end="", flush=True)
        catalyst_user = build_catalyst_user_message(
            trigger_context=trigger_context,
            round_responses=round_data["responses"],
            history=history,
            round_number=round_num,
        )

        observation = await call_llm(
            client,
            models["catalyst"],
            user=catalyst_user,
            system=catalyst_system,
            max_tokens=max_tokens_catalyst,
        )
        round_data["observation"] = observation
        if novelty_tracker:
            cat_novelty = novelty_tracker.measure("catalyst", observation)
            round_data["novelty"]["catalyst"] = cat_novelty
            print(f" {len(observation)} chars (novelty={cat_novelty:.3f})")
        else:
            print(f" {len(observation)} chars")

        # Check convergence
        converged = check_convergence(observation)
        if converged:
            consecutive_no_new += 1
            print(f"  >> Convergence signal: {consecutive_no_new}/{convergence_threshold}")
        else:
            consecutive_no_new = 0

        # Save round
        history.append({"round": round_num, "observation": observation})
        all_rounds.append(round_data)

        # Write round file immediately
        round_md = f"# 第 {round_num} 轮\n\n"
        for name, resp in round_data["responses"].items():
            round_md += f"## {name}\n\n{resp}\n\n---\n\n"
        round_md += f"## 催化观察\n\n{observation}\n\n"
        if round_data["novelty"]:
            round_md += f"## Novelty Scores\n\n"
            for agent_id, score in round_data["novelty"].items():
                round_md += f"- {agent_id}: {score:.4f}\n"
            round_md += "\n"
        (output_dir / f"round_{round_num}.md").write_text(round_md, encoding="utf-8")

        elapsed = time.time() - round_start
        print(f"  Round {round_num} completed in {elapsed:.1f}s")

        if consecutive_no_new >= convergence_threshold:
            print(f"\n=== Converged after {round_num} rounds ===\n")
            break
    else:
        print(f"\n=== Reached max rounds ({max_rounds}) without convergence ===\n")

    # ==========================================
    # Post-convergence: relationship map
    # ==========================================
    relationship_map = None
    if catalyst_convergence_template:
        print("--- Generating Relationship Map ---")
        conv_user = "## 历史上下文\n\n"
        for h in history:
            conv_user += f"### 第 {h['round']} 轮催化观察\n\n{h['observation']}\n\n"
        conv_user += "---\n\n" + catalyst_convergence_template

        relationship_map = await call_llm(
            client,
            models["catalyst"],
            user=conv_user,
            system=catalyst_system_base,
            max_tokens=max_tokens_catalyst,
        )
        (output_dir / "relationship_map.md").write_text(
            f"# 最终关系图谱\n\n{relationship_map}", encoding="utf-8"
        )
        print(f"  Relationship map: {len(relationship_map)} chars")

    # ==========================================
    # Build transcript + Plan generation
    # ==========================================
    transcript = ""
    for rd in all_rounds:
        transcript += f"# 第 {rd['round']} 轮\n\n"
        for name, resp in rd["responses"].items():
            transcript += f"## {name}\n\n{resp}\n\n"
        transcript += f"## 催化观察\n\n{rd['observation']}\n\n---\n\n"

    (output_dir / "transcript.md").write_text(transcript, encoding="utf-8")

    print("--- Plan Generation ---")
    plan_prompt = build_plan_user_message(
        trigger_context, profiles, transcript, plan_prompt_path,
        relationship_map=relationship_map,
    )
    plan = await call_llm(
        client,
        models["plan"],
        user=plan_prompt,
        max_tokens=max_tokens_plan,
    )
    (output_dir / "plan.md").write_text(f"# 协作方案\n\n{plan}", encoding="utf-8")
    print(f"  Plan generated: {len(plan)} chars")

    # ==========================================
    # Save metadata
    # ==========================================
    meta = {
        "run_id": run_id,
        "date": datetime.now().isoformat(),
        "participants": [p["name"] for p in participants],
        "participant_count": len(participants),
        "models": models,
        "params": params,
        "prompts": prompts_config,
        "profiles": {p["name"]: p["profile_file"] for p in participants},
        "demand": {
            "id": demand["id"],
            "raw_intent": demand.get("raw_intent", ""),
            "source_profile": demand.get("source_profile", ""),
            "formulated": trigger_context[:500] + "..." if len(trigger_context) > 500 else trigger_context,
        },
        "actual_rounds": len(all_rounds),
        "converged": consecutive_no_new >= convergence_threshold,
        "convergence_round": len(all_rounds) if consecutive_no_new >= convergence_threshold else None,
        "manual_responses_used": manual_file is not None,
        "has_relationship_map": relationship_map is not None,
        "novelty_enabled": novelty_tracker is not None,
        "novelty_scores": {
            f"round_{rd['round']}": rd.get("novelty", {})
            for rd in all_rounds
        } if novelty_tracker else None,
        "total_chars": sum(
            sum(len(r) for r in rd["responses"].values()) + len(rd["observation"])
            for rd in all_rounds
        ),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n=== {run_id} Complete ===")
    print(f"Output: {output_dir}")
    print(f"Rounds: {len(all_rounds)}, Converged: {meta['converged']}")
    print(f"Total chars: {meta['total_chars']}")
    files = "formulated_demand.md, round_1..{}, transcript.md, plan.md, metadata.json".format(len(all_rounds))
    if relationship_map:
        files += ", relationship_map.md"
    print(f"Files: {files}")


def main():
    parser = argparse.ArgumentParser(description="Run crystallization experiment")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to config.json (absolute or relative to cwd)",
    )
    parser.add_argument(
        "--novelty",
        action="store_true",
        help="Enable embedding novelty tracking (loads mpnet encoder, ~30s startup)",
    )
    args = parser.parse_args()
    asyncio.run(run_experiment(args.config, enable_novelty=args.novelty))


if __name__ == "__main__":
    main()
