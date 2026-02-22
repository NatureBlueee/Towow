"""
Delivery Prompt 验证脚本
用法: cd backend && source venv/bin/activate
      TOWOW_ANTHROPIC_API_KEY=sk-ant-... python ../tests/crystallization_poc/simulations/real/test_delivery.py \
          --profile ../data/profiles/real/chrisccc.md \
          --plan ../tests/crystallization_poc/simulations/real/run_006/output/plan.md \
          --demand ../tests/crystallization_poc/simulations/real/run_006/output/formulated_demand.md \
          --agent-name "Chrisccc" \
          --output ../tests/crystallization_poc/simulations/real/run_006/output/delivery_P02.md
"""

import argparse
import os
import re
import sys
from pathlib import Path


def load_env(env_path: str = None):
    """从 .env 文件加载环境变量（不覆盖已有的）"""
    if env_path is None:
        # 尝试多个位置
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


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_prompt_block(prompt_file: str) -> str:
    """从 prompt markdown 文件中提取 ``` 包裹的 System Prompt 块"""
    text = load_text(prompt_file)
    # 找到 ## System Prompt 后的第一个 ``` 块
    pattern = r"## System Prompt\s*\n\s*```\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # fallback: 整个文件
    return text


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


def call_api(system_prompt: str, model: str = "claude-sonnet-4-6", max_tokens: int = 4096) -> str:
    """调用 Anthropic API"""
    import anthropic

    api_key = os.environ.get("TOWOW_ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: TOWOW_ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Delivery prompt 是一个完整的 system prompt，不需要额外 user message
    # 但 API 要求至少一个 user message
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": "请开始。阅读协作方案，从我的视角呈现对我有意义的发现。",
            }
        ],
    )

    return response.content[0].text


def main():
    parser = argparse.ArgumentParser(description="Delivery Prompt 验证")
    parser.add_argument("--profile", required=True, help="参与者 Profile 文件路径")
    parser.add_argument("--plan", required=True, help="Plan 文件路径")
    parser.add_argument("--demand", required=True, help="Formulated Demand 文件路径")
    parser.add_argument("--agent-name", required=True, help="参与者名字")
    parser.add_argument(
        "--prompt",
        default=None,
        help="Delivery prompt 文件路径（默认自动定位）",
    )
    parser.add_argument("--output", required=True, help="输出文件路径")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="模型名称")
    parser.add_argument("--max-tokens", type=int, default=4096, help="最大输出 token")
    parser.add_argument("--dry-run", action="store_true", help="只输出组装后的 prompt，不调用 API")

    args = parser.parse_args()

    # 加载 .env（不覆盖已有环境变量）
    load_env()

    # 定位 delivery prompt
    if args.prompt:
        prompt_path = args.prompt
    else:
        # 自动定位
        script_dir = Path(__file__).parent
        prompt_path = script_dir.parent.parent / "prompts" / "delivery_v0.md"
        if not prompt_path.exists():
            # 尝试从项目根目录
            prompt_path = Path("tests/crystallization_poc/prompts/delivery_v0.md")

    print(f"Loading delivery prompt: {prompt_path}")
    prompt_template = extract_prompt_block(str(prompt_path))

    print(f"Loading plan: {args.plan}")
    plan = load_text(args.plan)

    print(f"Loading demand: {args.demand}")
    demand = load_text(args.demand)

    print(f"Loading profile: {args.profile} ({Path(args.profile).stat().st_size / 1024:.1f} KB)")
    profile = load_text(args.profile)

    # 组装完整 prompt
    full_prompt = compose_delivery_prompt(
        prompt_template=prompt_template,
        agent_name=args.agent_name,
        tension_context=demand,
        plan=plan,
        profile=profile,
    )

    print(f"Composed prompt: {len(full_prompt)} chars")

    if args.dry_run:
        print("\n=== DRY RUN: Composed Prompt ===\n")
        print(full_prompt[:2000])
        print(f"\n... ({len(full_prompt)} chars total)")
        return

    print(f"Calling API ({args.model}, max_tokens={args.max_tokens})...")
    result = call_api(full_prompt, model=args.model, max_tokens=args.max_tokens)

    # 保存输出
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = f"# Delivery — {args.agent_name}\n\n"
    header += f"**Prompt 版本**: delivery_v0\n"
    header += f"**模型**: {args.model}\n"
    header += f"**Profile**: {Path(args.profile).name}\n"
    header += f"**Plan**: {Path(args.plan).name}\n\n---\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + result)

    print(f"Output saved: {output_path} ({len(result)} chars)")


if __name__ == "__main__":
    main()
