#!/usr/bin/env python3
"""
名称一致性校验门。

扫描结晶管道输出文件，检测任何不在 name_registry 中的参与者名称。
这是 Agent Teams 模式下的代码级保障——名称绑定不依赖 LLM 忠实度。

用法:
    python validate_names.py --config run_007/config.json --output run_007/output/

    # 只校验特定文件
    python validate_names.py --config run_007/config.json --files run_007/output/plan.md

    # 从 name_registry.json 校验（无需完整 config）
    python validate_names.py --registry run_007/assembled/name_registry.json --output run_007/output/

设计原理:
    run_real.py 脚本模式中，名称通过 template.replace() 在代码层绑定。
    Agent Teams 模式中，名称由 LLM 传递，可能引入编造名称。
    本脚本在每个阶段输出后运行，检测任何 LLM 引入的非法名称。
    这是 "代码保障 > Prompt 保障" (Section 0.5) 在管道中的具体实现。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def build_name_registry(config: dict) -> dict:
    """从 config.json 构建名称注册表。

    返回: {
        "canonical": {id: name},      # 正式名称（唯一真相源）
        "allowed": set[str],          # 所有允许出现的名称/ID
        "forbidden_patterns": list,   # 明确禁止的模式
    }
    """
    canonical = {}
    allowed = set()

    # 参与者
    participants = config.get("participants", [])
    for p in participants:
        pid = p.get("id", "")
        name = p.get("name", "")
        canonical[pid] = name
        allowed.add(pid)
        allowed.add(name)

    # 需求方
    demand_source = config.get("demand_source_profile", "")
    if demand_source:
        allowed.add(demand_source)

    # 从 state.json 补充需求方名称（如果有）
    # 这部分可以扩展

    return {
        "canonical": canonical,
        "allowed": allowed,
    }


def load_name_registry(registry_path: Path) -> dict:
    """从 name_registry.json 加载"""
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    allowed = set()
    for pid, name in data.get("canonical", {}).items():
        allowed.add(pid)
        allowed.add(name)
    data["allowed"] = allowed
    return data


def extract_potential_names(text: str, canonical: dict) -> list[dict]:
    """从文本中提取可能是参与者名称的片段。

    策略：
    1. 搜索 "P0X（名称）" 模式——最精确，几乎无误报
    2. 搜索独立的疑似人名引用（中文2-4字名 / 英文名）——仅作为补充

    不再使用 "P0X 空格+词" 模式——误报率太高（"P05 提供"、"P01 +"等）。
    名称污染的核心传播模式是 "P0X（名称）"，模式 1 足以捕获。
    """
    findings = []

    # 模式 1: "P0X（名称）" 或 "P0X（名称，别名）"
    # 这是 LLM 最常用的名称引用格式，也是 Agent Teams 名称污染的核心传播路径
    pattern_id_name = re.compile(r'(P\d+)\s*[（(]\s*([^）)]+)\s*[）)]')
    for match in pattern_id_name.finditer(text):
        pid = match.group(1)
        raw_name_part = match.group(2).strip()

        # 如果括号中包含逗号/顿号分隔的多个名称，逐个拆分检查
        # 例如 "P01（雨洁，枫丝语）" → 检查 "雨洁" 和 "枫丝语"
        sub_names = re.split(r'[,，、]', raw_name_part)
        for sub_name in sub_names:
            sub_name = sub_name.strip()
            if not sub_name:
                continue
            findings.append({
                "type": "id_with_name",
                "id": pid,
                "name_found": sub_name,
                "context": text[max(0, match.start()-20):match.end()+20],
                "position": match.start(),
            })

    return findings


def validate_file(filepath: Path, registry: dict) -> list[dict]:
    """校验单个文件中的名称一致性。

    返回违规列表。
    """
    text = filepath.read_text(encoding="utf-8")
    canonical = registry["canonical"]
    allowed = registry["allowed"]

    violations = []

    findings = extract_potential_names(text, canonical)

    for f in findings:
        pid = f["id"]
        name_found = f["name_found"]

        # 检查这个 name 是否合法
        if name_found not in allowed:
            # 检查是否是 canonical name 的一部分（如 "西天取经的宝盖头" 被截断为 "宝盖头"）
            is_partial = False
            for a in allowed:
                if name_found in a or a in name_found:
                    is_partial = True
                    break

            # 检查 ID 是否有对应的 canonical 名称
            expected = canonical.get(pid, None)

            violations.append({
                "file": filepath.name,
                "id": pid,
                "name_found": name_found,
                "expected": expected,
                "type": f["type"],
                "context": f["context"],
                "position": f["position"],
                "is_partial_match": is_partial,
                "severity": "warning" if is_partial else "error",
            })

    return violations


def validate_directory(output_dir: Path, registry: dict) -> list[dict]:
    """校验整个输出目录"""
    all_violations = []

    # 按优先级排序的文件列表
    priority_files = [
        "plan.md",
        "relationship_map.md",
        "transcript.md",
    ]

    # 先检查高优先级文件
    for fname in priority_files:
        fpath = output_dir / fname
        if fpath.exists():
            violations = validate_file(fpath, registry)
            all_violations.extend(violations)

    # 检查 round 文件
    for fpath in sorted(output_dir.glob("round_*.md")):
        violations = validate_file(fpath, registry)
        all_violations.extend(violations)

    # 检查 delivery 文件
    for fpath in sorted(output_dir.glob("delivery_*.md")):
        violations = validate_file(fpath, registry)
        all_violations.extend(violations)

    return all_violations


def generate_name_registry_file(config: dict, output_path: Path):
    """从 config.json 生成 name_registry.json"""
    registry = build_name_registry(config)
    data = {
        "version": 1,
        "source": "config.json",
        "canonical": registry["canonical"],
        "note": "This is the single source of truth for participant names. "
                "All pipeline outputs must use names from this registry. "
                "Any name not listed here is a violation.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def print_report(violations: list[dict], canonical: dict):
    """打印校验报告"""
    if not violations:
        print("PASS: All names consistent with registry.")
        return True

    errors = [v for v in violations if v["severity"] == "error"]
    warnings = [v for v in violations if v["severity"] == "warning"]

    print(f"FAIL: {len(errors)} errors, {len(warnings)} warnings")
    print()

    if errors:
        print("=== ERRORS (non-canonical names) ===")
        for v in errors:
            expected = v["expected"] or "unknown"
            print(f"  [{v['file']}] {v['id']} → found \"{v['name_found']}\", expected \"{expected}\"")
            print(f"    Context: ...{v['context']}...")
            print()

    if warnings:
        print("=== WARNINGS (partial matches) ===")
        for v in warnings:
            expected = v["expected"] or "unknown"
            print(f"  [{v['file']}] {v['id']} → found \"{v['name_found']}\", expected \"{expected}\"")
            print()

    # 摘要
    print("=== Name Registry ===")
    for pid, name in canonical.items():
        print(f"  {pid} = {name}")

    return False


def main():
    parser = argparse.ArgumentParser(description="Validate name consistency in crystallization pipeline outputs")
    parser.add_argument("--config", help="Path to config.json (extracts registry from it)")
    parser.add_argument("--registry", help="Path to name_registry.json (direct)")
    parser.add_argument("--output", help="Output directory to scan")
    parser.add_argument("--files", nargs="+", help="Specific files to validate")
    parser.add_argument("--generate-registry", help="Generate name_registry.json from config and exit",
                        metavar="OUTPUT_PATH")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # 生成 registry 模式
    if args.generate_registry:
        if not args.config:
            print("ERROR: --config required with --generate-registry")
            sys.exit(1)
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        data = generate_name_registry_file(config, Path(args.generate_registry))
        print(f"Generated: {args.generate_registry}")
        print(f"Participants: {len(data['canonical'])}")
        for pid, name in data["canonical"].items():
            print(f"  {pid} = {name}")
        return

    # 构建 registry
    if args.registry:
        registry = load_name_registry(Path(args.registry))
    elif args.config:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        registry = build_name_registry(config)
    else:
        print("ERROR: --config or --registry required")
        sys.exit(1)

    # 校验
    violations = []
    if args.files:
        for f in args.files:
            violations.extend(validate_file(Path(f), registry))
    elif args.output:
        violations.extend(validate_directory(Path(args.output), registry))
    else:
        print("ERROR: --output or --files required")
        sys.exit(1)

    # 输出
    if args.json:
        print(json.dumps(violations, ensure_ascii=False, indent=2))
    else:
        passed = print_report(violations, registry["canonical"])
        if not passed:
            sys.exit(1)


if __name__ == "__main__":
    main()
