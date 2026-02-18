#!/usr/bin/env python3
"""
SIM-001: 3-person crystallization simulation

Lina (documentary) + 赵维 (distributed systems) + Maya (organizational development)
Trigger: Manufacturing CEO brand transformation

Usage:
    cd backend && source venv/bin/activate
    TOWOW_ANTHROPIC_API_KEY=sk-ant-... python ../tests/crystallization_poc/simulations/sim001_3person/run_sim.py
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic

# --- Paths ---
BASE_DIR = Path(__file__).parent
REPO_ROOT = BASE_DIR.parents[3]
PROMPTS_DIR = REPO_ROOT / "tests" / "crystallization_poc" / "prompts"
PROFILES_DIR = REPO_ROOT / "data" / "profiles"
OUTPUT_DIR = BASE_DIR / "output"

# --- Configuration ---
ENDPOINT_MODEL = "claude-sonnet-4-5-20250929"
CATALYST_MODEL = "claude-sonnet-4-5-20250929"  # v0 uses sonnet; v1 will upgrade to opus
PLAN_MODEL = "claude-sonnet-4-5-20250929"
MAX_ROUNDS = 6
CONVERGENCE_THRESHOLD = 2  # consecutive rounds with no new findings

# --- Participants ---
PARTICIPANTS = [
    {"name": "Lina", "profile_file": "profile-synthetic-lina.md"},
    {"name": "赵维", "profile_file": "profile-synthetic-zhaowei.md"},
    {"name": "Maya", "profile_file": "profile-synthetic-maya.md"},
]

# Brief descriptions (what module 1 would provide)
PARTICIPANT_BRIEFS = {
    "Lina": "Lina：独立纪录片导演和品牌内容创作者。十几年影像经验，擅长拍摄真实商业故事。深圳。",
    "赵维": "赵维：分布式系统架构师，前蚂蚁金服中间件工程师。现做技术咨询工作室。杭州。",
    "Maya": "Maya Chen：组织发展（OD）顾问，精品咨询公司合伙人。擅长组织诊断和跨部门翻译。新加坡。",
}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_profiles() -> dict[str, str]:
    profiles = {}
    for p in PARTICIPANTS:
        profiles[p["name"]] = load_text(PROFILES_DIR / p["profile_file"])
    return profiles


def load_trigger() -> str:
    """Load trigger event, excluding analysis sections."""
    content = load_text(BASE_DIR / "trigger.md")
    lines = content.split("\n")
    result = []
    for line in lines:
        if line.startswith("## 张力分析"):
            break
        result.append(line)
    return "\n".join(result).strip()


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


def get_participant_info(current_name: str) -> str:
    info_lines = []
    for name, brief in PARTICIPANT_BRIEFS.items():
        if name != current_name:
            info_lines.append(f"- {brief}")
    return "\n".join(info_lines)


def build_endpoint_prompt(
    owner_name: str,
    owner_profile: str,
    trigger_context: str,
    catalyst_observation: str | None,
    round_number: int,
) -> str:
    participant_info = get_participant_info(owner_name)

    prompt = f"""你是 {owner_name} 的助理，对他/她的情况非常了解。现在你代表他/她参加一个讨论。

---

**关于这次讨论**

{trigger_context}

---

**其他参与者**

{participant_info}

---
"""
    if catalyst_observation:
        prompt += f"""**上一轮主持人的观察**

{catalyst_observation}

---
"""
    prompt += f"""**关于 {owner_name}**

{owner_profile}

---

**你的任务**

代表 {owner_name} 在这次讨论中发言。说什么由你自己判断。

一些方向供参考，但不必局限于此：

- 他/她在这件事上能做什么、有什么
- 他/她需要什么、希望对方能提供什么
- 他/她有什么顾虑或不能接受的条件
- 他/她看到这个讨论之后想到的任何事

说你觉得对其他人有用的话。不用面面俱到，也不用套格式。如果 {owner_name} 对某件事有强烈的感觉但说不清楚为什么，把这个感觉说出来也比沉默更有价值。

这是第 {round_number} 轮。"""
    return prompt


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
) -> str:
    template = extract_prompt_block(PROMPTS_DIR / "plan_generator_v0.md")

    profiles_text = ""
    for name, profile in profiles.items():
        profiles_text += f"### {name}\n\n{profile}\n\n"

    filled = template.replace("{{TRIGGER_CONTEXT}}", trigger_context)
    filled = filled.replace("{{PARTICIPANT_PROFILES}}", profiles_text)
    filled = filled.replace("{{CRYSTALLIZATION_TRANSCRIPT}}", transcript)
    return filled


def check_convergence(observation: str) -> bool:
    markers = [
        "本轮没有新发现",
        "没有新的发现",
        "没有新发现",
        "0 个新发现",
        "零个新发现",
    ]
    obs_lower = observation.lower()
    return any(m in obs_lower for m in markers)


def call_llm(
    client: Anthropic,
    model: str,
    user: str,
    system: str | None = None,
    max_tokens: int = 4096,
) -> str:
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    return response.content[0].text


def run_simulation():
    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("TOWOW_ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=api_key)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load materials
    profiles = load_profiles()
    trigger_context = load_trigger()
    catalyst_system = extract_prompt_block(PROMPTS_DIR / "catalyst_v0.md")

    print("=== SIM-001: 3-Person Crystallization ===")
    print(f"Participants: {', '.join(profiles.keys())}")
    print(f"Endpoint model: {ENDPOINT_MODEL}")
    print(f"Catalyst model: {CATALYST_MODEL}")
    print(f"Max rounds: {MAX_ROUNDS}")
    print()

    # State
    history: list[dict] = []
    all_rounds: list[dict] = []
    consecutive_no_new = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"--- Round {round_num} ---")
        round_start = time.time()
        round_data = {"round": round_num, "responses": {}, "observation": ""}

        prev_observation = history[-1]["observation"] if history else None

        # Call each endpoint agent
        for name in profiles:
            print(f"  Calling endpoint: {name}...", end="", flush=True)
            endpoint_prompt = build_endpoint_prompt(
                owner_name=name,
                owner_profile=profiles[name],
                trigger_context=trigger_context,
                catalyst_observation=prev_observation,
                round_number=round_num,
            )

            response = call_llm(
                client,
                ENDPOINT_MODEL,
                user=endpoint_prompt,
                max_tokens=2048,
            )
            round_data["responses"][name] = response
            print(f" {len(response)} chars")
            time.sleep(0.5)  # rate limiting

        # Call catalyst agent
        print(f"  Calling catalyst...", end="", flush=True)
        catalyst_user = build_catalyst_user_message(
            trigger_context=trigger_context,
            round_responses=round_data["responses"],
            history=history,
            round_number=round_num,
        )

        observation = call_llm(
            client,
            CATALYST_MODEL,
            user=catalyst_user,
            system=catalyst_system,
            max_tokens=3000,
        )
        round_data["observation"] = observation
        print(f" {len(observation)} chars")

        # Check convergence
        converged = check_convergence(observation)
        if converged:
            consecutive_no_new += 1
            print(f"  >> Convergence signal: {consecutive_no_new}/{CONVERGENCE_THRESHOLD}")
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
        (OUTPUT_DIR / f"round_{round_num}.md").write_text(round_md, encoding="utf-8")

        elapsed = time.time() - round_start
        print(f"  Round {round_num} completed in {elapsed:.1f}s")

        if consecutive_no_new >= CONVERGENCE_THRESHOLD:
            print(f"\n=== Converged after {round_num} rounds ===\n")
            break
    else:
        print(f"\n=== Reached max rounds ({MAX_ROUNDS}) without convergence ===\n")

    # Build full transcript
    transcript = ""
    for rd in all_rounds:
        transcript += f"# 第 {rd['round']} 轮\n\n"
        for name, resp in rd["responses"].items():
            transcript += f"## {name}\n\n{resp}\n\n"
        transcript += f"## 催化观察\n\n{rd['observation']}\n\n---\n\n"

    (OUTPUT_DIR / "transcript.md").write_text(transcript, encoding="utf-8")

    # Run plan generator
    print("--- Plan Generation ---")
    plan_prompt = build_plan_user_message(trigger_context, profiles, transcript)
    plan = call_llm(
        client,
        PLAN_MODEL,
        user=plan_prompt,
        max_tokens=4096,
    )
    (OUTPUT_DIR / "plan.md").write_text(f"# 协作方案\n\n{plan}", encoding="utf-8")
    print(f"  Plan generated: {len(plan)} chars")

    # Save metadata
    meta = {
        "experiment": "EXP-009",
        "simulation": "SIM-001",
        "date": datetime.now().isoformat(),
        "participants": [p["name"] for p in PARTICIPANTS],
        "endpoint_model": ENDPOINT_MODEL,
        "catalyst_model": CATALYST_MODEL,
        "plan_model": PLAN_MODEL,
        "max_rounds": MAX_ROUNDS,
        "actual_rounds": len(all_rounds),
        "converged": consecutive_no_new >= CONVERGENCE_THRESHOLD,
        "prompts": {
            "endpoint": "prompts/endpoint_v0.md",
            "catalyst": "prompts/catalyst_v0.md",
            "plan_generator": "prompts/plan_generator_v0.md",
        },
        "profiles": {p["name"]: p["profile_file"] for p in PARTICIPANTS},
    }
    (OUTPUT_DIR / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n=== SIM-001 Complete ===")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Rounds: {len(all_rounds)}")
    print(f"Converged: {meta['converged']}")
    print(f"Files: round_1..{len(all_rounds)}.md, transcript.md, plan.md, metadata.json")


if __name__ == "__main__":
    run_simulation()
