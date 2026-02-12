#!/usr/bin/env python3
"""
批量生成独特、个性化的 Agent 画像。

每个场景生成 100 个 agent，分 10 批 x 10 个。
每批用不同的"风格种子"确保多样性。
"""

import json
import os
import sys
import time
import random
from pathlib import Path
from anthropic import Anthropic

# ── 配置 ──

SCENES = {
    "hackathon": {
        "json_path": "apps/S1_hackathon/data/agents.json",
        "context": "黑客松组队场景",
        "fields": ["role", "skills", "bio", "experience", "hackathon_history", "availability", "interests"],
    },
    "skill_exchange": {
        "json_path": "apps/S2_skill_exchange/data/agents.json",
        "context": "技能交换场景",
        "fields": ["role", "skills", "bio", "can_teach", "want_to_learn", "availability", "style"],
    },
    "recruitment": {
        "json_path": "apps/R1_recruitment/data/agents.json",
        "context": "招聘/求职场景",
        "fields": ["role", "skills", "bio", "experience", "looking_for", "salary_range", "work_style"],
    },
    "matchmaking": {
        "json_path": "apps/M1_matchmaking/data/agents.json",
        "context": "交友/相亲场景",
        "fields": ["age", "occupation", "bio", "interests", "values", "ideal_match", "quirks"],
    },
}

# 每批的风格种子——确保 10 批风格完全不同
STYLE_SEEDS = [
    "这批人是互联网老炮、极客、赛博朋克爱好者。网名风格偏技术梗、英文混搭。性格张扬、自信甚至有点中二。",
    "这批人是文艺青年、独立创作者、数字游民。网名风格偏诗意、隐喻、小众。性格安静但有很深的想法。",
    "这批人是90后/00后、学生党、刚入行的新人。网名风格偏可爱、搞怪、二次元。性格活泼但有自己的执着。",
    "这批人是跨界人才——厨师转码、律师做设计、物理学家搞区块链。网名风格偏反差萌。经历很不寻常。",
    "这批人是海外华人、留学生、在国外工作的人。网名混合中英文甚至其他语言。视野国际化，思维方式和国内不同。",
    "这批人是35+的资深从业者、连续创业者、退役大厂人。网名可能很朴素或者很有年代感。说话老练、有深度。",
    "这批人是小众领域专家——声音设计、量子计算、手工皮具、城市探险。网名非常个性化。对自己的领域充满热情。",
    "这批人是反叛者、黑客精神信仰者、开源狂热分子。网名偏地下文化。态度鲜明，不走寻常路。",
    "这批人是跨性别/非二元性别/LGBTQ+群体中的技术人才。网名有创意、有态度。视角独特，注重包容性。",
    "这批人是来自非一线城市的实干派——三四线城市创业者、县城程序员、农村电商。网名接地气。经历真实且有故事感。",
]

BATCH_SIZE = 10
BATCHES_PER_SCENE = 10

def make_prompt(scene_id: str, scene_config: dict, batch_idx: int, existing_names: list[str]) -> str:
    style = STYLE_SEEDS[batch_idx % len(STYLE_SEEDS)]
    fields = scene_config["fields"]
    context = scene_config["context"]

    existing_str = ""
    if existing_names:
        sample = random.sample(existing_names, min(15, len(existing_names)))
        existing_str = f"\n\n已经有的网名（不要重复）：{', '.join(sample)}"

    return f"""你要为一个「{context}」生成 {BATCH_SIZE} 个完全独特的虚拟人物。

风格要求：{style}

核心原则：
1. 每个人必须有一个**独特的网名**（不是真名，是互联网昵称/ID），要有个性、有记忆点
2. 每个人的 bio 要像**真人写的自我介绍**，有口语感、有性格、有棱角，不要官方腔
3. skills 不要千篇一律，可以混搭意想不到的技能组合
4. 每个人之间要有明显差异——年龄、性格、经历、说话方式都不同
5. 不要用"热爱"、"专注"、"致力于"这些空话，用具体的、有画面感的描述
6. bio 控制在 50-120 字之间，要有个人特色，像这个人真的在打字介绍自己
{existing_str}

输出严格的 JSON 格式（不要 markdown 代码块），key 是 agent_id（用网名的拼音或英文缩写，snake_case），每个 agent 有以下字段：
- name: 网名（中文/英文/混搭都可以）
- {chr(10).join(f'- {f}' for f in fields)}

确保 skills 是数组，其他字段是字符串。

直接输出 JSON 对象，不要任何其他文字。"""


def generate_batch(client: Anthropic, prompt: str, model: str = "claude-sonnet-4-5-20250929") -> dict:
    """调用 Claude 生成一批 agent。"""
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0,  # 高温度增加多样性
    )
    text = resp.content[0].text.strip()
    # 清理可能的 markdown 代码块
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
    return json.loads(text)


def main():
    root = Path(__file__).resolve().parent.parent

    # 读取 API 配置
    env_path = root / "backend" / ".env"
    api_keys = []
    base_url = None
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("TOWOW_ANTHROPIC_API_KEYS="):
                raw = line.split("=", 1)[1]
                api_keys = [k.strip() for k in raw.split(",") if k.strip()]
            elif line.startswith("TOWOW_ANTHROPIC_BASE_URL="):
                base_url = line.split("=", 1)[1].strip() or None

    if not api_keys:
        print("错误：未找到 API keys")
        sys.exit(1)

    print(f"使用 {len(api_keys)} 个 API key, base_url={base_url or 'default'}")

    # 支持 --supplement 模式：加载已有 agent 并补充
    supplement_mode = "--supplement" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target_scenes = args if args else list(SCENES.keys())

    for scene_id in target_scenes:
        if scene_id not in SCENES:
            print(f"未知场景: {scene_id}")
            continue

        config = SCENES[scene_id]
        json_path = root / config["json_path"]
        all_agents = {}
        existing_names = []

        # 补充模式：加载已有数据
        if supplement_mode and json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                all_agents = json.load(f)
            existing_names = [v.get("name", k) for k, v in all_agents.items()]
            print(f"\n  📦 加载已有 {len(all_agents)} 个 agent")

        target_count = 100
        batches_needed = BATCHES_PER_SCENE
        if supplement_mode:
            deficit = max(0, target_count - len(all_agents))
            batches_needed = (deficit // BATCH_SIZE) + (2 if deficit > 0 else 0)  # 多跑几批容错
            if deficit == 0:
                print(f"  ✅ 已有 {len(all_agents)} 个，无需补充")
                continue

        print(f"\n{'='*60}")
        print(f"场景: {scene_id} ({config['context']})")
        print(f"目标: {json_path} (需补 {batches_needed} 批)")
        print(f"{'='*60}")

        for batch_idx in range(batches_needed):
            # 轮转 API key
            key = api_keys[batch_idx % len(api_keys)]
            key_label = key[-6:]

            client = Anthropic(api_key=key, base_url=base_url)

            prompt = make_prompt(scene_id, config, batch_idx, existing_names)

            print(f"\n  批次 {batch_idx + 1}/{BATCHES_PER_SCENE} (key ...{key_label}, 风格: {STYLE_SEEDS[batch_idx][:20]}...)")

            try:
                batch = generate_batch(client, prompt)
                count = len(batch)
                print(f"  ✓ 生成 {count} 个 agent: {', '.join(batch[k].get('name', k) for k in list(batch.keys())[:3])}...")

                # 检查重复
                dupes = set(batch.keys()) & set(all_agents.keys())
                if dupes:
                    print(f"  ⚠ 去重 {len(dupes)} 个重复 ID")
                    for d in dupes:
                        del batch[d]

                all_agents.update(batch)
                existing_names.extend(batch[k].get("name", k) for k in batch)

            except json.JSONDecodeError as e:
                print(f"  ✗ JSON 解析失败: {e}")
            except Exception as e:
                print(f"  ✗ 生成失败: {e}")

            # 防止速率限制
            time.sleep(1)

        # 写入文件
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_agents, f, ensure_ascii=False, indent=4)

        print(f"\n  ✓✓ {scene_id} 完成: {len(all_agents)} 个 agent → {json_path}")

    print(f"\n{'='*60}")
    print("全部完成！")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
