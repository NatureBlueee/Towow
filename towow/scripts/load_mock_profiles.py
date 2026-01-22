#!/usr/bin/env python3
"""
Mock 用户档案加载脚本

用于加载和管理 Mock 用户 Profile，支持：
1. 查看所有预设的 Mock 用户
2. 导出 Mock 用户到 JSON 文件
3. 从 JSON 文件导入自定义用户
4. 生成压力测试用的随机用户

使用方法:
    python -m scripts.load_mock_profiles list          # 列出所有用户
    python -m scripts.load_mock_profiles export        # 导出到 JSON
    python -m scripts.load_mock_profiles import <file> # 从文件导入
    python -m scripts.load_mock_profiles generate 100  # 生成 100 个随机用户
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.secondme_mock import (
    MOCK_PROFILES,
    SecondMeMockService,
    SimpleRandomMockClient
)


# 预定义的 Mock 用户档案（扩展版，包含更多场景）
EXTENDED_MOCK_PROFILES: Dict[str, Dict[str, Any]] = {
    # 技术类用户
    "tech_leader_01": {
        "user_id": "tech_leader_01",
        "display_name": "TechLead",
        "name": "技术负责人 - 张明",
        "capabilities": ["架构设计", "技术评审", "团队管理", "技术分享"],
        "location": "北京",
        "availability": "工作日晚上",
        "personality": "严谨专业，乐于分享技术经验",
        "interests": ["系统架构", "技术管理", "开源项目"],
        "decision_style": "技术导向，看重方案可行性和技术价值"
    },
    "frontend_dev_01": {
        "user_id": "frontend_dev_01",
        "display_name": "FrontendDev",
        "name": "前端开发 - 李小红",
        "capabilities": ["React", "Vue", "小程序", "TypeScript"],
        "location": "深圳",
        "availability": "周末优先",
        "personality": "热爱技术，追求极致用户体验",
        "interests": ["前端工程化", "性能优化", "设计系统"],
        "decision_style": "看重项目技术栈和学习机会"
    },
    "backend_dev_01": {
        "user_id": "backend_dev_01",
        "display_name": "BackendDev",
        "name": "后端开发 - 王大力",
        "capabilities": ["Python", "Go", "微服务", "数据库"],
        "location": "杭州",
        "availability": "灵活",
        "personality": "稳重务实，注重代码质量",
        "interests": ["分布式系统", "高并发", "云原生"],
        "decision_style": "看重技术挑战和项目稳定性"
    },

    # 产品/设计类用户
    "product_manager_01": {
        "user_id": "product_manager_01",
        "display_name": "PM",
        "name": "产品经理 - 陈思思",
        "capabilities": ["需求分析", "产品设计", "用户研究", "数据分析"],
        "location": "上海",
        "availability": "工作日",
        "personality": "逻辑清晰，善于沟通协调",
        "interests": ["产品方法论", "用户增长", "商业模式"],
        "decision_style": "用户价值导向，看重产品影响力"
    },
    "ux_designer_01": {
        "user_id": "ux_designer_01",
        "display_name": "UXDesigner",
        "name": "UX设计师 - 林小美",
        "capabilities": ["交互设计", "用户研究", "原型设计", "设计系统"],
        "location": "广州",
        "availability": "按项目排期",
        "personality": "创意丰富，注重用户体验细节",
        "interests": ["用户体验", "设计思维", "可用性测试"],
        "decision_style": "看重设计空间和用户价值"
    },

    # 运营/市场类用户
    "community_manager_01": {
        "user_id": "community_manager_01",
        "display_name": "CommunityMgr",
        "name": "社区运营 - 赵小琳",
        "capabilities": ["社群管理", "内容运营", "活动策划", "用户增长"],
        "location": "北京",
        "availability": "全职可用",
        "personality": "活泼开朗，善于社交和沟通",
        "interests": ["社群运营", "用户增长", "内容营销"],
        "decision_style": "看重项目曝光度和社交价值"
    },
    "content_creator_01": {
        "user_id": "content_creator_01",
        "display_name": "ContentCreator",
        "name": "内容创作者 - 孙小文",
        "capabilities": ["技术写作", "视频制作", "公众号运营", "知识分享"],
        "location": "远程",
        "availability": "灵活",
        "personality": "表达能力强，热爱知识分享",
        "interests": ["技术写作", "知识付费", "个人品牌"],
        "decision_style": "看重内容价值和个人品牌建设"
    },

    # 商业/资源类用户
    "investor_01": {
        "user_id": "investor_01",
        "display_name": "Investor",
        "name": "天使投资人 - 钱多多",
        "capabilities": ["投资评估", "资源对接", "商业咨询", "行业洞察"],
        "location": "上海",
        "availability": "需要预约",
        "personality": "商业敏锐，资源丰富",
        "interests": ["早期投资", "AI赛道", "创业孵化"],
        "decision_style": "看重商业价值和团队潜力"
    },
    "startup_founder_01": {
        "user_id": "startup_founder_01",
        "display_name": "Founder",
        "name": "创业者 - 周小明",
        "capabilities": ["创业经验", "团队管理", "融资路演", "商业模式"],
        "location": "北京",
        "availability": "周末",
        "personality": "激情满满，执行力强",
        "interests": ["创业方法论", "团队建设", "商业创新"],
        "decision_style": "看重项目潜力和合作价值"
    },

    # 特殊场景用户
    "student_01": {
        "user_id": "student_01",
        "display_name": "Student",
        "name": "在校学生 - 小张",
        "capabilities": ["学习能力强", "时间充裕", "执行力强"],
        "location": "北京",
        "availability": "课余时间",
        "personality": "积极上进，求知欲强",
        "interests": ["技术学习", "实习机会", "项目经验"],
        "decision_style": "看重学习机会和实践价值"
    }
}


def list_profiles(include_extended: bool = False) -> None:
    """列出所有 Mock 用户档案"""
    print("\n=== 预设 Mock 用户档案 ===\n")

    profiles = dict(MOCK_PROFILES)
    if include_extended:
        profiles.update(EXTENDED_MOCK_PROFILES)

    for user_id, profile in profiles.items():
        print(f"[{user_id}] {profile.get('name', profile.get('display_name', 'Unknown'))}")
        print(f"  - 能力: {', '.join(profile.get('capabilities', []))}")
        print(f"  - 位置: {profile.get('location', 'N/A')}")
        print(f"  - 可用时间: {profile.get('availability', 'N/A')}")
        print(f"  - 性格: {profile.get('personality', 'N/A')}")
        print(f"  - 决策风格: {profile.get('decision_style', 'N/A')}")
        print()

    print(f"共 {len(profiles)} 个用户档案")


def export_profiles(output_path: Optional[str] = None, include_extended: bool = False) -> None:
    """导出 Mock 用户档案到 JSON 文件"""
    profiles = dict(MOCK_PROFILES)
    if include_extended:
        profiles.update(EXTENDED_MOCK_PROFILES)

    if output_path is None:
        output_path = project_root / "data" / "mock_profiles.json"
    else:
        output_path = Path(output_path)

    # 确保目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    print(f"已导出 {len(profiles)} 个用户档案到: {output_path}")


def import_profiles(input_path: str) -> Dict[str, Dict[str, Any]]:
    """从 JSON 文件导入用户档案"""
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"错误: 文件不存在 - {input_path}")
        return {}

    with open(input_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    print(f"已导入 {len(profiles)} 个用户档案")

    # 验证档案格式
    required_fields = ["user_id", "capabilities"]
    for user_id, profile in profiles.items():
        missing = [f for f in required_fields if f not in profile]
        if missing:
            print(f"  警告: [{user_id}] 缺少字段: {missing}")

    return profiles


def generate_stress_profiles(count: int = 100, output_path: Optional[str] = None) -> None:
    """生成压力测试用的随机用户档案"""
    client = SimpleRandomMockClient(seed=42)  # 固定种子保证可重复
    profiles = client.generate_random_profiles(count)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2)

        print(f"已生成 {count} 个随机用户档案到: {output_path}")
    else:
        print(f"已生成 {count} 个随机用户档案（内存中）")
        print("\n前 5 个用户:")
        for i, (user_id, profile) in enumerate(list(profiles.items())[:5]):
            print(f"  [{user_id}] 能力: {profile['capabilities']}, 位置: {profile['location']}")


def demo_usage() -> None:
    """演示如何使用 Mock 服务"""
    import asyncio

    async def run_demo():
        print("\n=== SecondMe Mock 服务演示 ===\n")

        # 1. 使用规则 Mock
        print("1. 使用 SecondMeMockService（规则 Mock）")
        mock_service = SecondMeMockService()

        # 理解需求
        demand_result = await mock_service.understand_demand(
            raw_input="想组织一场 AI 技术分享活动，在北京，大概 20 人规模",
            user_id="alice"
        )
        print(f"   需求理解: {json.dumps(demand_result, ensure_ascii=False, indent=4)}")

        # 生成响应
        response = await mock_service.generate_response(
            user_id="alice",
            demand=demand_result,
            profile=await mock_service.get_user_profile("alice")
        )
        print(f"   Alice 的响应: {json.dumps(response, ensure_ascii=False, indent=4)}")

        # 2. 使用随机 Mock（压力测试）
        print("\n2. 使用 SimpleRandomMockClient（压力测试）")
        random_client = SimpleRandomMockClient(seed=42)

        # 快速生成多个响应
        for i in range(3):
            resp = await random_client.generate_response(
                user_id=f"user_{i}",
                demand={"surface_demand": "测试需求"},
                profile={}
            )
            print(f"   User_{i} 响应: {resp['decision']}, 理由: {resp['reasoning']}")

        print("\n演示完成!")

    asyncio.run(run_demo())


def main():
    parser = argparse.ArgumentParser(
        description="Mock 用户档案管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m scripts.load_mock_profiles list
  python -m scripts.load_mock_profiles list --extended
  python -m scripts.load_mock_profiles export -o profiles.json
  python -m scripts.load_mock_profiles import custom_profiles.json
  python -m scripts.load_mock_profiles generate 100 -o stress_profiles.json
  python -m scripts.load_mock_profiles demo
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有 Mock 用户")
    list_parser.add_argument(
        "--extended", "-e",
        action="store_true",
        help="包含扩展的 Mock 用户"
    )

    # export 命令
    export_parser = subparsers.add_parser("export", help="导出用户档案到 JSON")
    export_parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径"
    )
    export_parser.add_argument(
        "--extended", "-e",
        action="store_true",
        help="包含扩展的 Mock 用户"
    )

    # import 命令
    import_parser = subparsers.add_parser("import", help="从 JSON 导入用户档案")
    import_parser.add_argument(
        "file",
        type=str,
        help="输入文件路径"
    )

    # generate 命令
    generate_parser = subparsers.add_parser("generate", help="生成随机用户档案")
    generate_parser.add_argument(
        "count",
        type=int,
        default=100,
        nargs="?",
        help="生成数量（默认 100）"
    )
    generate_parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径"
    )

    # demo 命令
    subparsers.add_parser("demo", help="演示 Mock 服务用法")

    args = parser.parse_args()

    if args.command == "list":
        list_profiles(include_extended=args.extended)
    elif args.command == "export":
        export_profiles(output_path=args.output, include_extended=args.extended)
    elif args.command == "import":
        import_profiles(args.file)
    elif args.command == "generate":
        generate_stress_profiles(count=args.count, output_path=args.output)
    elif args.command == "demo":
        demo_usage()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
