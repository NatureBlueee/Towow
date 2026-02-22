#!/usr/bin/env python3
"""
结晶协议全流程管道。

从 Profile + Intent 到 Delivery，全自动、全审计、可并行。

用法:
    cd backend && source venv/bin/activate
    python ../tests/crystallization_poc/simulations/real/run_pipeline.py \
        --config pipeline_config.json

Pipeline Config 最小示例:
    {
      "demand_owner": {"id": "P02", "name": "Chrisccc", "profile": "data/profiles/real/chrisccc.md"},
      "raw_intent": "...",
      "participants": [
        {"id": "P03", "name": "西天取经的宝盖头", "file": "data/profiles/real/pingdior.md"}
      ],
      "output_dir": "tests/crystallization_poc/simulations/real/run_007/"
    }

五个阶段:
    1. FORMULATE — 需求 formulation（T/I/B/E 编码）
    2. CRYSTALLIZE — 结晶协议（端侧×N 并行 + 催化串行 × 多轮）
    3. PLAN — 方案生成
    4. DELIVER — 反向投影（为每个参与者 + 需求方生成个性化交付件）
    5. PACKAGE — 打包分发（附 feedback 模板）

Stage 1-3 由 run_real.py 处理（生成 config.json → 调用 run_experiment）。
Stage 4-5 是本脚本新增。
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------

def load_env(env_path: str = None):
    """从 .env 文件加载环境变量（不覆盖已有的）"""
    if env_path is None:
        candidates = [
            Path(__file__).resolve().parent.parent.parent.parent.parent / "backend" / ".env",
            Path("backend/.env"),
            Path(".env"),
        ]
        for c in candidates:
            if c.exists():
                env_path = str(c)
                break
    if not env_path or not Path(env_path).exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key and key not in os.environ:
                    os.environ[key] = value


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def load_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def resolve_path(path_str: str, repo_root: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return repo_root / p


def extract_prompt_block(filepath: Path) -> str:
    """Extract content between first pair of ``` markers in a prompt markdown file."""
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
    if lines:
        return "\n".join(lines)
    # fallback: 搜索 ## System Prompt 后的 ``` 块
    pattern = r"## System Prompt\s*\n\s*```\s*\n(.*?)```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content


def get_next_run_id(state_path: Path) -> str:
    """从 state.json 推断下一个 RUN ID"""
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        runs = state.get("runs", [])
        max_num = 0
        for r in runs:
            rid = r.get("id", "")
            if rid.startswith("RUN-"):
                try:
                    max_num = max(max_num, int(rid.split("-")[1]))
                except ValueError:
                    pass
        return f"RUN-{max_num + 1:03d}"
    return "RUN-001"


# ---------------------------------------------------------------------------
# Stage 1-3: Crystallization (delegates to run_real.py)
# ---------------------------------------------------------------------------

def generate_crystallize_config(pipeline_config: dict, repo_root: Path, output_dir: Path) -> Path:
    """从 pipeline config 生成 run_real.py 兼容的 config.json"""
    demand_owner = pipeline_config["demand_owner"]
    participants = pipeline_config["participants"]

    # 计算配对数
    n = len(participants)
    pair_count = n * (n - 1) // 2

    # prompt 版本（默认 v2 基线）
    prompt_versions = pipeline_config.get("prompt_versions", {
        "formulation": "v1.1",
        "catalyst": "v2.1",
        "endpoint": "v2",
        "plan": "v0",
    })

    # prompt 文件路径
    prompt_files = pipeline_config.get("prompt_files", {
        "formulation": "tests/crystallization_poc/prompts/formulation_v1.1.md",
        "catalyst": "tests/crystallization_poc/prompts/catalyst_v2.1.md",
        "endpoint": "tests/crystallization_poc/prompts/endpoint_v2.md",
        "plan": "tests/crystallization_poc/prompts/plan_generator_v0.md",
    })

    # 已有的 formulated demand（可选，跳过 formulation 阶段）
    formulated_demand = pipeline_config.get("formulated_demand", None)

    run_id = pipeline_config.get("run_id", get_next_run_id(
        repo_root / "tests" / "crystallization_poc" / "state.json"
    ))
    demand_id = pipeline_config.get("demand_id", f"D-{demand_owner['id']}")
    model = pipeline_config.get("model", "claude-sonnet-4-6")

    # 计算每个参与者的 char_count
    for p in participants:
        if "char_count" not in p:
            profile_path = resolve_path(p["file"], repo_root)
            if profile_path.exists():
                p["char_count"] = profile_path.stat().st_size

    config = {
        "run_id": run_id,
        "demand_id": demand_id,
        "demand_source_profile": demand_owner["id"],
        "raw_intent": pipeline_config["raw_intent"],
        "participants": participants,
        "participant_count": n,
        "pair_count": pair_count,
        "prompt_versions": prompt_versions,
        "prompt_files": prompt_files,
        "model": model,
        "execution_mode": "Pipeline",
        "output_dir": str(output_dir / "output") + "/",
    }

    if formulated_demand:
        config["formulated_demand"] = formulated_demand

    # API 配置（可选代理）
    if "api" in pipeline_config:
        config["api"] = pipeline_config["api"]

    config["frozen_at"] = datetime.now().strftime("%Y-%m-%d")

    config_path = output_dir / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    return config_path


async def run_crystallization(config_path: Path, repo_root: Path) -> dict:
    """调用 run_real.py 的 run_experiment 函数"""
    # 动态导入 run_real.py
    run_real_path = Path(__file__).parent / "run_real.py"
    if not run_real_path.exists():
        print(f"ERROR: run_real.py not found at {run_real_path}")
        sys.exit(1)

    import importlib.util
    spec = importlib.util.spec_from_file_location("run_real", str(run_real_path))
    run_real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_real)

    await run_real.run_experiment(str(config_path), enable_novelty=False)

    # 读取生成的 metadata
    output_dir = config_path.parent / "output"
    metadata_path = output_dir / "metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    return {}


# ---------------------------------------------------------------------------
# Stage 4: Delivery (parallel)
# ---------------------------------------------------------------------------

def compose_delivery_prompt(
    prompt_template: str,
    agent_name: str,
    tension_context: str,
    plan: str,
    profile: str,
) -> str:
    """将占位符替换为实际内容"""
    result = prompt_template
    result = result.replace("{{agent_name}}", agent_name)
    result = result.replace("{{tension_context}}", tension_context)
    result = result.replace("{{plan}}", plan)
    result = result.replace("{{profile}}", profile)
    return result


async def deliver_single(
    client,
    agent_name: str,
    agent_id: str,
    prompt_template: str,
    tension_context: str,
    plan_text: str,
    profile_text: str,
    output_path: Path,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
) -> dict:
    """为单个参与者生成 Delivery 交付件"""
    full_prompt = compose_delivery_prompt(
        prompt_template=prompt_template,
        agent_name=agent_name,
        tension_context=tension_context,
        plan=plan_text,
        profile=profile_text,
    )

    start = time.time()
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=full_prompt,
            messages=[
                {
                    "role": "user",
                    "content": "请开始。阅读协作方案，从我的视角呈现对我有意义的发现。",
                }
            ],
        )
        result_text = response.content[0].text
        elapsed = time.time() - start

        # 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        header = f"# Delivery — {agent_name}\n\n"
        header += f"**Prompt 版本**: delivery_v0\n"
        header += f"**模型**: {model}\n"
        header += f"**Agent ID**: {agent_id}\n"
        header += f"**生成时间**: {datetime.now().isoformat()}\n"
        header += f"**耗时**: {elapsed:.1f}s\n\n---\n\n"

        output_path.write_text(header + result_text, encoding="utf-8")

        print(f"  [{agent_id}] {agent_name}: {len(result_text)} chars, {elapsed:.1f}s → {output_path.name}")
        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "chars": len(result_text),
            "time_s": round(elapsed, 1),
            "file": str(output_path.name),
            "status": "ok",
        }

    except Exception as e:
        elapsed = time.time() - start
        error_msg = str(e)
        print(f"  [{agent_id}] {agent_name}: ERROR ({elapsed:.1f}s) — {error_msg[:100]}")
        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "chars": 0,
            "time_s": round(elapsed, 1),
            "file": None,
            "status": "error",
            "error": error_msg,
        }


async def run_delivery(
    pipeline_config: dict,
    output_dir: Path,
    repo_root: Path,
    model: str = "claude-sonnet-4-6",
) -> list[dict]:
    """Stage 4: 为所有参与者 + 需求方并行生成 Delivery"""
    from anthropic import AsyncAnthropic

    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: TOWOW_ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # API 配置
    api_config = pipeline_config.get("api", {})
    base_url = api_config.get("base_url", None)
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncAnthropic(**client_kwargs)

    # 加载 delivery prompt 模板
    delivery_prompt_path = pipeline_config.get(
        "delivery_prompt",
        "tests/crystallization_poc/prompts/delivery_v0.md",
    )
    delivery_prompt_path = resolve_path(delivery_prompt_path, repo_root)
    prompt_template = extract_prompt_block(delivery_prompt_path)

    # 加载 plan 和 formulated demand
    crystallize_output = output_dir / "output"
    plan_text = load_text(crystallize_output / "plan.md")
    demand_text = load_text(crystallize_output / "formulated_demand.md")

    # 构建交付对象列表：参与者 + 需求方
    delivery_targets = []

    # 需求方
    demand_owner = pipeline_config["demand_owner"]
    delivery_targets.append({
        "id": demand_owner["id"],
        "name": demand_owner["name"],
        "profile_path": resolve_path(demand_owner["profile"], repo_root),
        "is_demand_owner": True,
    })

    # 参与者
    for p in pipeline_config["participants"]:
        delivery_targets.append({
            "id": p["id"],
            "name": p["name"],
            "profile_path": resolve_path(p["file"], repo_root),
            "is_demand_owner": False,
        })

    delivery_model = pipeline_config.get("delivery_model", model)
    delivery_max_tokens = pipeline_config.get("delivery_max_tokens", 4096)

    print(f"\n=== Stage 4: Delivery ({len(delivery_targets)} targets, parallel) ===")

    # 并行生成所有 delivery
    tasks = []
    for target in delivery_targets:
        profile_text = load_text(target["profile_path"])
        suffix = "_demand_owner" if target["is_demand_owner"] else ""
        output_path = crystallize_output / f"delivery_{target['id']}{suffix}.md"

        tasks.append(deliver_single(
            client=client,
            agent_name=target["name"],
            agent_id=target["id"],
            prompt_template=prompt_template,
            tension_context=demand_text,
            plan_text=plan_text,
            profile_text=profile_text,
            output_path=output_path,
            model=delivery_model,
            max_tokens=delivery_max_tokens,
        ))

    results = await asyncio.gather(*tasks)
    return list(results)


# ---------------------------------------------------------------------------
# Stage 5: Package
# ---------------------------------------------------------------------------

def run_package(
    pipeline_config: dict,
    output_dir: Path,
    delivery_results: list[dict],
    crystallize_meta: dict,
    repo_root: Path,
) -> Path:
    """Stage 5: 打包分发——生成 run summary + 附 feedback 模板"""
    crystallize_output = output_dir / "output"

    # 复制 feedback 模板到输出目录
    feedback_src = resolve_path(
        pipeline_config.get(
            "feedback_template",
            "tests/crystallization_poc/prompts/feedback_template_v0.md",
        ),
        repo_root,
    )
    if feedback_src.exists():
        feedback_dst = crystallize_output / "feedback_template.md"
        shutil.copy2(feedback_src, feedback_dst)
        print(f"  Feedback template → {feedback_dst.name}")

    # 生成 pipeline metadata
    pipeline_meta = {
        "pipeline_version": "v0.1",
        "generated_at": datetime.now().isoformat(),
        "demand_owner": pipeline_config["demand_owner"],
        "participant_count": len(pipeline_config["participants"]),
        "model": pipeline_config.get("model", "claude-sonnet-4-6"),
        "delivery_model": pipeline_config.get("delivery_model", pipeline_config.get("model", "claude-sonnet-4-6")),
        "stages": {
            "crystallization": {
                "status": "ok" if crystallize_meta else "unknown",
                "rounds": crystallize_meta.get("actual_rounds", None),
                "converged": crystallize_meta.get("converged", None),
            },
            "delivery": {
                "total": len(delivery_results),
                "ok": sum(1 for r in delivery_results if r["status"] == "ok"),
                "errors": sum(1 for r in delivery_results if r["status"] == "error"),
                "results": delivery_results,
            },
        },
    }

    meta_path = crystallize_output / "pipeline_metadata.json"
    meta_path.write_text(
        json.dumps(pipeline_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  Pipeline metadata → {meta_path.name}")

    # 生成分发索引
    index_lines = [
        f"# Pipeline 产出索引\n",
        f"**Run ID**: {pipeline_config.get('run_id', 'N/A')}",
        f"**需求方**: {pipeline_config['demand_owner']['name']} ({pipeline_config['demand_owner']['id']})",
        f"**参与者**: {len(pipeline_config['participants'])} 人",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 产出文件",
        f"",
        f"| 文件 | 说明 |",
        f"|------|------|",
        f"| `plan.md` | 协作方案（全文） |",
        f"| `formulated_demand.md` | 需求编码（T/I/B/E） |",
    ]

    for r in delivery_results:
        if r["file"]:
            role = "需求方" if "_demand_owner" in r["file"] else "参与者"
            index_lines.append(f"| `{r['file']}` | {r['agent_name']} 的交付件（{role}） |")

    index_lines.extend([
        f"| `feedback_template.md` | 反馈模板 |",
        f"| `transcript.md` | 完整对话记录 |",
        f"| `metadata.json` | 结晶运行元数据 |",
        f"| `pipeline_metadata.json` | 管道元数据 |",
        f"",
        f"## 分发清单",
        f"",
    ])

    for r in delivery_results:
        if r["file"]:
            index_lines.append(f"- [ ] {r['agent_name']} ({r['agent_id']}): 发送 `{r['file']}` + `feedback_template.md`")

    index_path = crystallize_output / "INDEX.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    print(f"  Distribution index → {index_path.name}")

    return index_path


# ---------------------------------------------------------------------------
# Main pipeline orchestrator
# ---------------------------------------------------------------------------

async def run_pipeline(config_path: str, skip_crystallize: bool = False, dry_run: bool = False):
    """全流程管道入口"""
    config_file = Path(config_path)
    if not config_file.is_absolute():
        config_file = Path.cwd() / config_file

    pipeline_config = json.loads(config_file.read_text(encoding="utf-8"))
    repo_root = Path(__file__).resolve().parents[4]

    # 确定输出目录
    output_dir_str = pipeline_config.get("output_dir", None)
    if output_dir_str:
        output_dir = resolve_path(output_dir_str, repo_root)
    else:
        run_id = pipeline_config.get("run_id", get_next_run_id(
            repo_root / "tests" / "crystallization_poc" / "state.json"
        ))
        pipeline_config["run_id"] = run_id
        output_dir = repo_root / "tests" / "crystallization_poc" / "simulations" / "real" / run_id.lower().replace("-", "_")

    output_dir.mkdir(parents=True, exist_ok=True)

    model = pipeline_config.get("model", "claude-sonnet-4-6")

    print(f"=== Crystallization Pipeline ===")
    print(f"Demand owner: {pipeline_config['demand_owner']['name']} ({pipeline_config['demand_owner']['id']})")
    print(f"Participants: {len(pipeline_config['participants'])}")
    print(f"Model: {model}")
    print(f"Output: {output_dir}")

    if dry_run:
        print("\n[DRY RUN] Generating config only, no API calls.")

    # ------------------------------------------------------------------
    # Stage 1-3: Crystallization (formulation + rounds + plan)
    # ------------------------------------------------------------------
    crystallize_meta = {}
    crystallize_output = output_dir / "output"

    if skip_crystallize:
        print(f"\n=== Stage 1-3: SKIPPED (--skip-crystallize) ===")
        # 读取已有的 metadata
        meta_path = crystallize_output / "metadata.json"
        if meta_path.exists():
            crystallize_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            print(f"  Loaded existing metadata: {crystallize_meta.get('actual_rounds', '?')} rounds, converged={crystallize_meta.get('converged', '?')}")
        # 检查必要文件
        for required in ["plan.md", "formulated_demand.md"]:
            if not (crystallize_output / required).exists():
                print(f"ERROR: {crystallize_output / required} not found. Cannot skip crystallization.")
                sys.exit(1)
    elif dry_run:
        # 只生成 config，不执行
        config_path = generate_crystallize_config(pipeline_config, repo_root, output_dir)
        print(f"\n=== Stage 1-3: Config generated (dry run) ===")
        print(f"  Config: {config_path}")
        print(f"  To run manually: python run_real.py --config {config_path}")
        return
    else:
        print(f"\n=== Stage 1-3: Crystallization ===")
        config_path = generate_crystallize_config(pipeline_config, repo_root, output_dir)
        print(f"  Config: {config_path}")
        crystallize_meta = await run_crystallization(config_path, repo_root)
        print(f"  Crystallization complete: {crystallize_meta.get('actual_rounds', '?')} rounds")

    # ------------------------------------------------------------------
    # Stage 4: Delivery (parallel)
    # ------------------------------------------------------------------
    if dry_run:
        print(f"\n=== Stage 4: Delivery (dry run) ===")
        print(f"  Would generate {len(pipeline_config['participants']) + 1} delivery files")
        return

    delivery_results = await run_delivery(pipeline_config, output_dir, repo_root, model)

    ok_count = sum(1 for r in delivery_results if r["status"] == "ok")
    err_count = sum(1 for r in delivery_results if r["status"] == "error")
    print(f"  Delivery complete: {ok_count} ok, {err_count} errors")

    # ------------------------------------------------------------------
    # Stage 5: Package
    # ------------------------------------------------------------------
    print(f"\n=== Stage 5: Package ===")
    index_path = run_package(pipeline_config, output_dir, delivery_results, crystallize_meta, repo_root)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'='*50}")
    print(f"Pipeline Complete")
    print(f"{'='*50}")
    print(f"Output directory: {crystallize_output}")
    print(f"Crystallization: {crystallize_meta.get('actual_rounds', '?')} rounds, converged={crystallize_meta.get('converged', '?')}")
    print(f"Delivery: {ok_count}/{len(delivery_results)} successful")
    print(f"Index: {index_path}")
    print(f"\nNext: Send each delivery file + feedback_template.md to the corresponding participant.")


def main():
    parser = argparse.ArgumentParser(description="Run crystallization pipeline end-to-end")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to pipeline_config.json",
    )
    parser.add_argument(
        "--skip-crystallize",
        action="store_true",
        help="Skip crystallization stages (use existing plan.md and formulated_demand.md)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate config only, no API calls",
    )
    args = parser.parse_args()

    load_env()

    asyncio.run(run_pipeline(
        args.config,
        skip_crystallize=args.skip_crystallize,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
