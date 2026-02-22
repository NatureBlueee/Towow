#!/usr/bin/env python3
"""
Prompt 预组装器。

在任何 LLM 接触之前，用代码将正确的名称、Profile 和上下文绑定到 prompt 模板中。
这是 Agent Teams 模式下"代码保障 > Prompt 保障"（Section 0.5）的核心实现。

脚本模式（run_real.py）中，名称通过 template.replace() 在代码层绑定。
Agent Teams 模式中，如果名称由 Lead Agent 传递，LLM 会引入编造名称（"雨洁"/"Frank"事件）。
本脚本在 Agent Teams 启动前运行，生成所有 prompt 的预组装版本，
Lead Agent 只需原样读取和传递，不需要也不应该修改名称。

用法:
    python assemble_prompts.py --config run_007/config.json

输出:
    run_007/assembled/
        name_registry.json           # 名称注册表（单一真相源）
        catalyst_system.txt          # 催化系统 prompt（participant_list 已填）
        endpoint_P01_system.txt      # 端侧系统 prompt（agent_name + profile 已填）
        endpoint_P03_system.txt
        ...
        delivery_P01_system.txt      # 交付系统 prompt（agent_name + profile 已填）
        delivery_P03_system.txt
        ...
        plan_profiles.txt            # Plan 生成器的参与者 profiles 拼装
        assembly_manifest.json       # 组装清单（供 Lead Agent 参考）

设计原理:
    1. 静态占位符（名称、Profile、参与者列表）在此处用代码绑定
    2. 动态占位符（catalyst_output、plan）留在原位，运行时由脚本/Agent 填充
    3. name_registry.json 是名称的唯一真相源，validate_names.py 用它做校验
    4. assembly_manifest.json 告诉 Lead Agent 每个阶段应该读哪些文件
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def extract_prompt_block(prompt_path: Path) -> str:
    """从 prompt markdown 文件中提取 ``` 包裹的 System Prompt 块。

    与 run_real.py 和 test_delivery.py 中的同名函数逻辑一致。
    """
    text = prompt_path.read_text(encoding="utf-8")
    pattern = r"## System Prompt\s*\n\s*```\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def load_config(config_path: Path) -> dict:
    """加载 config.json"""
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_name_registry(config: dict) -> dict:
    """从 config.json 构建名称注册表。

    返回:
        {
            "version": 1,
            "source": "config.json",
            "canonical": {"P01": "枫丝语", "P03": "西天取经的宝盖头", ...},
            "demand_source": "P02",
        }
    """
    canonical = {}
    for p in config.get("participants", []):
        pid = p["id"]
        name = p["name"]
        canonical[pid] = name

    return {
        "version": 1,
        "source": "config.json",
        "canonical": canonical,
        "demand_source": config.get("demand_source_profile", ""),
        "note": (
            "This is the single source of truth for participant names. "
            "All pipeline outputs must use names from this registry. "
            "Any name not listed here is a violation."
        ),
    }


def find_project_root(start: Path) -> Path:
    """从 start 向上查找包含 CLAUDE.md 的项目根目录。"""
    current = start.resolve()
    while current != current.parent:
        if (current / "CLAUDE.md").exists():
            return current
        current = current.parent
    # 回退：假设 cwd 就是项目根
    return Path.cwd()


def resolve_prompt_path(config: dict, prompt_key: str, config_dir: Path) -> Path | None:
    """解析 prompt 文件路径（相对于项目根目录）。"""
    prompt_files = config.get("prompt_files", {})
    if prompt_key not in prompt_files:
        return None
    rel_path = prompt_files[prompt_key]
    project_root = find_project_root(config_dir)
    return project_root / rel_path


def assemble_catalyst(config: dict, prompt_template: str) -> str:
    """组装催化系统 prompt。

    静态绑定:
        {{tension_context}} — 从 formulated_demand 文件读取
        {{participant_list}} — 从 config.participants 构建
        {{participant_count}} — 参与者人数
        {{pair_count}} — 配对数
    """
    # participant_list: 名称列表（顿号分隔）
    names = [p["name"] for p in config["participants"]]
    participant_list = "、".join(names)
    participant_count = str(len(names))
    pair_count = str(len(names) * (len(names) - 1) // 2)

    result = prompt_template
    result = result.replace("{{participant_list}}", participant_list)
    result = result.replace("{{participant_count}}", participant_count)
    result = result.replace("{{pair_count}}", pair_count)

    # tension_context 是从 formulated_demand 读取的，在运行时由 user message 传入
    # 但如果 config 指定了 formulated_demand 文件，也可以预绑定到系统 prompt
    # 注意：catalyst prompt 的 tension_context 在系统 prompt 中，不是 user message
    # 所以这里预绑定
    return result


def assemble_endpoint(config: dict, prompt_template: str, participant: dict, profile_text: str) -> str:
    """组装端侧系统 prompt。

    静态绑定:
        {{agent_name}} — 参与者名称
        {{profile}} — 参与者完整 Profile

    动态（保留）:
        {{tension_context}} — 运行时绑定（formulated_demand）
        {{catalyst_output_previous_round}} — 运行时绑定（上一轮催化输出）
    """
    result = prompt_template
    result = result.replace("{{agent_name}}", participant["name"])
    result = result.replace("{{profile}}", profile_text)
    # tension_context 留给运行时绑定（在 system prompt 中）
    return result


def assemble_delivery(config: dict, prompt_template: str, participant: dict, profile_text: str) -> str:
    """组装交付系统 prompt。

    静态绑定:
        {{agent_name}} — 参与者名称
        {{profile}} — 参与者完整 Profile

    动态（保留）:
        {{tension_context}} — 运行时绑定
        {{plan}} — 运行时绑定（Plan Generator 输出）
    """
    result = prompt_template
    result = result.replace("{{agent_name}}", participant["name"])
    result = result.replace("{{profile}}", profile_text)
    return result


def load_profile(participant: dict, config_dir: Path) -> str:
    """加载参与者 Profile 文件。"""
    profile_path_str = participant["file"]
    project_root = find_project_root(config_dir)
    profile_path = project_root / profile_path_str
    if not profile_path.exists():
        print(f"  WARNING: Profile not found: {profile_path}")
        return f"[Profile not found: {profile_path_str}]"
    return profile_path.read_text(encoding="utf-8")


def assemble_all(config_path: Path) -> dict:
    """执行完整的 prompt 预组装。

    返回 assembly_manifest。
    """
    config = load_config(config_path)
    config_dir = config_path.parent
    output_dir = config_dir / "assembled"
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": config.get("run_id", "unknown"),
        "assembled_at": None,  # 由调用方填充
        "name_registry": "name_registry.json",
        "stages": {},
    }

    # 1. 名称注册表
    registry = build_name_registry(config)
    registry_path = output_dir / "name_registry.json"
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  name_registry.json: {len(registry['canonical'])} participants")

    # 2. 催化系统 prompt
    catalyst_path = resolve_prompt_path(config, "catalyst", config_dir)
    if catalyst_path and catalyst_path.exists():
        catalyst_template = extract_prompt_block(catalyst_path)
        catalyst_assembled = assemble_catalyst(config, catalyst_template)
        catalyst_out = output_dir / "catalyst_system.txt"
        catalyst_out.write_text(catalyst_assembled, encoding="utf-8")
        manifest["stages"]["catalyst"] = {
            "system_prompt": "catalyst_system.txt",
            "static_bindings": ["participant_list", "participant_count", "pair_count"],
            "dynamic_bindings": ["tension_context (via user message)"],
        }
        print(f"  catalyst_system.txt: {len(catalyst_assembled)} chars")
    else:
        print(f"  WARNING: catalyst prompt not found: {catalyst_path}")

    # 3. 端侧系统 prompt（每人一个）
    endpoint_path = resolve_prompt_path(config, "endpoint", config_dir)
    endpoint_files = {}
    if endpoint_path and endpoint_path.exists():
        endpoint_template = extract_prompt_block(endpoint_path)
        for p in config["participants"]:
            profile_text = load_profile(p, config_dir)
            assembled = assemble_endpoint(config, endpoint_template, p, profile_text)
            fname = f"endpoint_{p['id']}_system.txt"
            (output_dir / fname).write_text(assembled, encoding="utf-8")
            endpoint_files[p["id"]] = fname
            print(f"  {fname}: {len(assembled)} chars ({p['name']})")
        manifest["stages"]["endpoint"] = {
            "files": endpoint_files,
            "static_bindings": ["agent_name", "profile"],
            "dynamic_bindings": [
                "tension_context (bind before R1)",
                "catalyst_output_previous_round (bind before R2+)",
            ],
        }
    else:
        print(f"  WARNING: endpoint prompt not found: {endpoint_path}")

    # 4. 交付系统 prompt（每人一个）
    # 寻找 delivery prompt
    delivery_prompt_path = resolve_prompt_path(config, "delivery", config_dir)
    if not delivery_prompt_path or not delivery_prompt_path.exists():
        # 尝试默认位置
        project_root = config_dir
        while project_root.name and not (project_root / "CLAUDE.md").exists():
            project_root = project_root.parent
            if project_root == project_root.parent:
                break
        delivery_prompt_path = project_root / "tests/crystallization_poc/prompts/delivery_v0.md"

    delivery_files = {}
    if delivery_prompt_path and delivery_prompt_path.exists():
        delivery_template = extract_prompt_block(delivery_prompt_path)
        for p in config["participants"]:
            profile_text = load_profile(p, config_dir)
            assembled = assemble_delivery(config, delivery_template, p, profile_text)
            fname = f"delivery_{p['id']}_system.txt"
            (output_dir / fname).write_text(assembled, encoding="utf-8")
            delivery_files[p["id"]] = fname
            print(f"  {fname}: {len(assembled)} chars ({p['name']})")
        manifest["stages"]["delivery"] = {
            "files": delivery_files,
            "static_bindings": ["agent_name", "profile"],
            "dynamic_bindings": [
                "tension_context (bind before generation)",
                "plan (bind before generation)",
            ],
        }
    else:
        print(f"  WARNING: delivery prompt not found: {delivery_prompt_path}")

    # 5. Plan 生成器的 profiles 拼装
    profiles_text = ""
    for p in config["participants"]:
        profile_text = load_profile(p, config_dir)
        # 用 canonical 名称作为标题，不是 ID
        profiles_text += f"### {p['id']}（{p['name']}）\n\n{profile_text}\n\n"
    plan_profiles_path = output_dir / "plan_profiles.txt"
    plan_profiles_path.write_text(profiles_text, encoding="utf-8")
    manifest["stages"]["plan"] = {
        "profiles": "plan_profiles.txt",
        "static_bindings": ["participant names in profile headers"],
        "dynamic_bindings": [
            "TRIGGER_CONTEXT",
            "CRYSTALLIZATION_TRANSCRIPT",
        ],
    }
    print(f"  plan_profiles.txt: {len(profiles_text)} chars")

    # 6. 写 manifest
    from datetime import datetime, timezone

    manifest["assembled_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path = output_dir / "assembly_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  assembly_manifest.json written")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Pre-assemble prompts with code-level name binding"
    )
    parser.add_argument(
        "--config", required=True, help="Path to config.json"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be generated, don't write files",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: config not found: {config_path}")
        sys.exit(1)

    print(f"Assembling prompts from: {config_path}")
    config = load_config(config_path)
    print(f"  Run: {config.get('run_id', 'unknown')}")
    print(f"  Participants: {len(config.get('participants', []))}")

    if args.dry_run:
        print("\n=== DRY RUN ===")
        registry = build_name_registry(config)
        print("\nName Registry:")
        for pid, name in registry["canonical"].items():
            print(f"  {pid} = {name}")
        print("\nWould generate:")
        print("  assembled/name_registry.json")
        print("  assembled/catalyst_system.txt")
        for p in config.get("participants", []):
            print(f"  assembled/endpoint_{p['id']}_system.txt")
            print(f"  assembled/delivery_{p['id']}_system.txt")
        print("  assembled/plan_profiles.txt")
        print("  assembled/assembly_manifest.json")
        return

    print("\nAssembling...")
    manifest = assemble_all(config_path)
    print(f"\nDone. {len(manifest['stages'])} stages assembled.")
    print(f"Output: {config_path.parent / 'assembled'}/")


if __name__ == "__main__":
    main()
