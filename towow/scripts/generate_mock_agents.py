#!/usr/bin/env python3
"""
Mock Agent 档案生成脚本

生成100个多样化的Mock Agent简介数据，用于测试和演示。

数据维度：
- 地区：覆盖一线城市、新一线城市、二线城市、远程
- 能力：技术、设计、产品、运营、商业等多领域
- 兴趣：AI、创业、投资、技术、社交等
- 协作风格：积极主动、谨慎评估、技术导向、商业思维等

使用方法:
    python -m scripts.generate_mock_agents           # 生成并打印前10个
    python -m scripts.generate_mock_agents --save    # 保存到data目录
    python -m scripts.generate_mock_agents --db      # 写入数据库
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============== 数据池定义 ==============

# 地区分布（权重）
LOCATIONS = {
    "北京": 15,
    "上海": 15,
    "深圳": 12,
    "杭州": 10,
    "广州": 8,
    "成都": 6,
    "武汉": 5,
    "南京": 5,
    "西安": 4,
    "苏州": 4,
    "重庆": 3,
    "天津": 3,
    "青岛": 2,
    "长沙": 2,
    "郑州": 2,
    "远程": 4,
}

# 可用时间
AVAILABILITY_OPTIONS = [
    "工作日可用",
    "周末优先",
    "晚上和周末",
    "灵活安排",
    "需提前预约",
    "全职可用",
    "按项目排期",
    "每周固定几天",
    "仅周末",
    "工作日晚间",
]

# 能力类别及具体能力
CAPABILITY_CATEGORIES = {
    "技术-后端": [
        "Python开发", "Go语言", "Java开发", "Node.js",
        "微服务架构", "数据库设计", "API设计", "分布式系统",
        "云原生", "DevOps", "系统架构", "性能优化"
    ],
    "技术-前端": [
        "React", "Vue", "TypeScript", "小程序开发",
        "Web性能优化", "前端工程化", "移动端H5", "跨端开发"
    ],
    "技术-数据": [
        "数据分析", "机器学习", "数据可视化", "Python数据处理",
        "SQL", "数据挖掘", "推荐系统", "NLP"
    ],
    "技术-AI": [
        "大模型应用", "Prompt工程", "AI Agent", "RAG开发",
        "AI产品开发", "模型微调", "AI工具开发"
    ],
    "设计": [
        "UI设计", "UX设计", "交互设计", "视觉设计",
        "品牌设计", "产品原型", "设计系统", "用户研究"
    ],
    "产品": [
        "产品经理", "需求分析", "用户研究", "数据分析",
        "产品规划", "竞品分析", "增长策略", "产品运营"
    ],
    "运营": [
        "社群运营", "内容运营", "活动策划", "用户增长",
        "社交媒体", "品牌营销", "内容创作", "KOL合作"
    ],
    "商业": [
        "商业策划", "融资路演", "投资咨询", "资源对接",
        "商业模式", "市场调研", "商务拓展", "创业指导"
    ],
    "资源": [
        "场地资源", "人脉资源", "媒体资源", "供应链资源",
        "技术资源", "投资资源", "政府资源", "高校资源"
    ],
}

# 兴趣标签
INTERESTS = [
    "AI/大模型", "创业", "投资理财", "技术社区", "开源项目",
    "知识分享", "行业研究", "Web3", "元宇宙", "智能硬件",
    "SaaS产品", "出海业务", "消费品牌", "教育科技", "医疗健康",
    "金融科技", "企业服务", "跨境电商", "内容创作", "社群建设",
    "产品设计", "用户体验", "数据驱动", "敏捷开发", "远程协作",
]

# 性格特征
PERSONALITY_TRAITS = [
    ("积极主动", "执行力强"),
    ("稳重务实", "注重细节"),
    ("创意丰富", "善于创新"),
    ("逻辑清晰", "分析能力强"),
    ("善于沟通", "协调能力强"),
    ("技术导向", "追求卓越"),
    ("商业敏锐", "资源丰富"),
    ("乐于分享", "乐于助人"),
    ("深度思考", "独立见解"),
    ("学习能力强", "适应性强"),
    ("细心周到", "注重质量"),
    ("快速行动", "结果导向"),
]

# 决策风格
DECISION_STYLES = [
    "快速决策，倾向于参与有挑战的项目",
    "谨慎评估，看重项目可行性和风险控制",
    "技术导向，关注技术深度和学习价值",
    "商业思维，看重商业价值和投资回报",
    "用户导向，关注用户价值和产品影响力",
    "数据驱动，需要看到数据和逻辑支撑",
    "关系导向，看重合作伙伴和团队氛围",
    "目标导向，关注项目目标是否明确",
    "资源导向，看重能带来的资源和人脉",
    "学习导向，看重能获得的成长和经验",
    "创新导向，喜欢尝试新事物和新方向",
    "稳健风格，偏好风险可控的项目",
]

# 姓氏
SURNAMES = [
    "张", "王", "李", "刘", "陈", "杨", "黄", "赵", "周", "吴",
    "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗",
    "郑", "梁", "谢", "宋", "唐", "许", "韩", "冯", "邓", "曹",
]

# 名字（单字和双字）
GIVEN_NAMES = [
    "伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "洋",
    "勇", "艳", "杰", "娟", "涛", "明", "超", "秀英", "华", "丹",
    "鑫", "晨", "宇", "浩", "辉", "婷", "文", "思", "雪", "峰",
    "志强", "小明", "小红", "大伟", "建国", "国强", "志明", "海涛",
    "晓峰", "晓红", "小龙", "小虎", "明明", "亮亮", "佳佳", "蕾蕾",
]

# 描述模板
DESCRIPTION_TEMPLATES = [
    "{years}年{domain}经验，专注于{focus}领域，擅长{strength}",
    "资深{role}，在{domain}方向有丰富经验，{achievement}",
    "{domain}从业者，热爱{interest}，希望结识更多志同道合的伙伴",
    "曾在{company}从事{role}工作，现专注于{focus}方向",
    "{interest}爱好者，拥有{years}年{domain}经验，{personality}",
]

# 公司类型
COMPANY_TYPES = [
    "大厂", "独角兽", "创业公司", "外企", "国企",
    "咨询公司", "投资机构", "自由职业", "高校/研究机构",
]


# ============== 生成函数 ==============

def weighted_choice(options: Dict[str, int]) -> str:
    """根据权重随机选择"""
    total = sum(options.values())
    r = random.randint(1, total)
    cumulative = 0
    for option, weight in options.items():
        cumulative += weight
        if r <= cumulative:
            return option
    return list(options.keys())[-1]


def generate_name() -> tuple[str, str]:
    """生成中文姓名和英文ID"""
    surname = random.choice(SURNAMES)
    given_name = random.choice(GIVEN_NAMES)
    full_name = f"{surname}{given_name}"

    # 生成拼音风格的ID（简化）
    pinyin_map = {
        "张": "zhang", "王": "wang", "李": "li", "刘": "liu", "陈": "chen",
        "杨": "yang", "黄": "huang", "赵": "zhao", "周": "zhou", "吴": "wu",
        "徐": "xu", "孙": "sun", "马": "ma", "朱": "zhu", "胡": "hu",
        "郭": "guo", "何": "he", "高": "gao", "林": "lin", "罗": "luo",
        "郑": "zheng", "梁": "liang", "谢": "xie", "宋": "song", "唐": "tang",
        "许": "xu", "韩": "han", "冯": "feng", "邓": "deng", "曹": "cao",
    }
    surname_pinyin = pinyin_map.get(surname, surname.lower())
    display_name = f"{surname_pinyin.capitalize()}{random.randint(100, 999)}"

    return full_name, display_name


def generate_capabilities() -> List[str]:
    """生成能力列表"""
    # 随机选择1-2个类别
    categories = random.sample(list(CAPABILITY_CATEGORIES.keys()), k=random.randint(1, 2))

    capabilities = []
    for cat in categories:
        # 每个类别选择2-4个能力
        caps = random.sample(CAPABILITY_CATEGORIES[cat], k=min(random.randint(2, 4), len(CAPABILITY_CATEGORIES[cat])))
        capabilities.extend(caps)

    return capabilities[:6]  # 最多6个能力


def generate_interests() -> List[str]:
    """生成兴趣列表"""
    return random.sample(INTERESTS, k=random.randint(2, 4))


def generate_personality() -> str:
    """生成性格描述"""
    traits = random.choice(PERSONALITY_TRAITS)
    return f"{traits[0]}，{traits[1]}"


def generate_description(
    capabilities: List[str],
    interests: List[str],
    personality: str
) -> str:
    """生成个人描述"""
    years = random.randint(2, 15)

    # 根据能力推断领域
    if any("开发" in c or "架构" in c or "Python" in c or "Go" in c for c in capabilities):
        domain = "技术开发"
        role = "技术工程师"
    elif any("设计" in c for c in capabilities):
        domain = "设计"
        role = "设计师"
    elif any("产品" in c or "需求" in c for c in capabilities):
        domain = "产品"
        role = "产品经理"
    elif any("运营" in c or "增长" in c for c in capabilities):
        domain = "运营"
        role = "运营专家"
    else:
        domain = "互联网"
        role = "从业者"

    template = random.choice(DESCRIPTION_TEMPLATES)

    return template.format(
        years=years,
        domain=domain,
        role=role,
        focus=capabilities[0] if capabilities else domain,
        strength=capabilities[1] if len(capabilities) > 1 else capabilities[0],
        interest=interests[0] if interests else "技术",
        personality=personality.split("，")[0],
        company=random.choice(COMPANY_TYPES),
        achievement="曾参与多个成功项目"
    )


def generate_agent_profile(index: int) -> Dict[str, Any]:
    """生成单个Agent档案"""
    name, display_name = generate_name()
    capabilities = generate_capabilities()
    interests = generate_interests()
    personality = generate_personality()

    user_id = f"agent_{index:03d}"

    return {
        "user_id": user_id,
        "display_name": display_name,
        "name": name,
        "capabilities": capabilities,
        "location": weighted_choice(LOCATIONS),
        "availability": random.choice(AVAILABILITY_OPTIONS),
        "personality": personality,
        "interests": interests,
        "decision_style": random.choice(DECISION_STYLES),
        "description": generate_description(capabilities, interests, personality),
        "metadata": {
            "source": "generated",
            "version": "1.0",
            "index": index
        }
    }


def generate_mock_agents(count: int = 100, seed: int = 42) -> List[Dict[str, Any]]:
    """
    生成指定数量的Mock Agent档案

    Args:
        count: 生成数量
        seed: 随机种子（保证可重复性）

    Returns:
        Agent档案列表
    """
    random.seed(seed)
    agents = []

    for i in range(count):
        agent = generate_agent_profile(i + 1)
        agents.append(agent)

    return agents


def convert_to_db_format(agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    转换为数据库 AgentProfile 格式

    Args:
        agents: 原始Agent档案列表

    Returns:
        符合 database/models.py AgentProfile 格式的数据列表
    """
    db_agents = []

    for agent in agents:
        db_agent = {
            "id": str(uuid4()),
            "name": agent["name"],
            "agent_type": "user_agent",
            "description": agent.get("description", ""),
            "capabilities": {
                "skills": agent.get("capabilities", []),
                "interests": agent.get("interests", []),
                "location": agent.get("location"),
                "availability": agent.get("availability"),
            },
            "pricing_info": {},
            "config": {
                "user_id": agent["user_id"],
                "display_name": agent["display_name"],
                "personality": agent.get("personality"),
                "decision_style": agent.get("decision_style"),
            },
            "is_active": True,
            "rating": round(random.uniform(4.0, 5.0), 1),
            "total_collaborations": random.randint(0, 50),
        }
        db_agents.append(db_agent)

    return db_agents


def analyze_diversity(agents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析数据多样性"""
    from collections import Counter

    locations = Counter(a["location"] for a in agents)
    availability = Counter(a["availability"] for a in agents)

    all_capabilities = []
    for a in agents:
        all_capabilities.extend(a.get("capabilities", []))
    capability_counts = Counter(all_capabilities)

    all_interests = []
    for a in agents:
        all_interests.extend(a.get("interests", []))
    interest_counts = Counter(all_interests)

    return {
        "total_agents": len(agents),
        "location_distribution": dict(locations),
        "availability_distribution": dict(availability),
        "top_capabilities": dict(capability_counts.most_common(10)),
        "top_interests": dict(interest_counts.most_common(10)),
        "unique_locations": len(locations),
        "unique_capabilities": len(capability_counts),
        "unique_interests": len(interest_counts),
    }


# ============== CLI ==============

def main():
    parser = argparse.ArgumentParser(
        description="生成Mock Agent档案数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m scripts.generate_mock_agents               # 生成并打印
  python -m scripts.generate_mock_agents --save        # 保存到文件
  python -m scripts.generate_mock_agents --count 200   # 生成200个
  python -m scripts.generate_mock_agents --analyze     # 分析多样性
        """
    )

    parser.add_argument(
        "--count", "-n",
        type=int,
        default=100,
        help="生成数量（默认100）"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=42,
        help="随机种子（默认42）"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="保存到data/mock_agents.json"
    )
    parser.add_argument(
        "--save-db-format",
        action="store_true",
        help="保存为数据库格式（data/mock_agents_db.json）"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="分析数据多样性"
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=5,
        help="预览显示数量（默认5）"
    )

    args = parser.parse_args()

    print(f"\n=== 生成 {args.count} 个 Mock Agent 档案 ===\n")
    print(f"随机种子: {args.seed}")

    # 生成数据
    agents = generate_mock_agents(count=args.count, seed=args.seed)

    # 预览
    print(f"\n前 {min(args.preview, len(agents))} 个 Agent:\n")
    for agent in agents[:args.preview]:
        print(f"[{agent['user_id']}] {agent['name']} ({agent['display_name']})")
        print(f"  - 地点: {agent['location']}")
        print(f"  - 能力: {', '.join(agent['capabilities'])}")
        print(f"  - 兴趣: {', '.join(agent['interests'])}")
        print(f"  - 风格: {agent['decision_style'][:30]}...")
        print()

    # 分析多样性
    if args.analyze:
        print("\n=== 数据多样性分析 ===\n")
        analysis = analyze_diversity(agents)
        print(f"总数: {analysis['total_agents']}")
        print(f"覆盖地区: {analysis['unique_locations']} 个")
        print(f"能力类型: {analysis['unique_capabilities']} 种")
        print(f"兴趣标签: {analysis['unique_interests']} 种")
        print(f"\n地区分布: {json.dumps(analysis['location_distribution'], ensure_ascii=False, indent=2)}")
        print(f"\nTop 10 能力: {json.dumps(analysis['top_capabilities'], ensure_ascii=False, indent=2)}")
        print(f"\nTop 10 兴趣: {json.dumps(analysis['top_interests'], ensure_ascii=False, indent=2)}")

    # 保存原始格式
    if args.save:
        output_dir = project_root / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "mock_agents.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(agents, f, ensure_ascii=False, indent=2)

        print(f"\n已保存到: {output_path}")

    # 保存数据库格式
    if args.save_db_format:
        output_dir = project_root / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "mock_agents_db.json"

        db_agents = convert_to_db_format(agents)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(db_agents, f, ensure_ascii=False, indent=2)

        print(f"已保存数据库格式到: {output_path}")

    print(f"\n生成完成! 共 {len(agents)} 个 Agent 档案")


if __name__ == "__main__":
    main()
