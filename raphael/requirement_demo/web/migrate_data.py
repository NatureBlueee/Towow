#!/usr/bin/env python3
"""
数据迁移脚本 - 从 JSON 迁移到 SQLite

运行方式:
    python -m web.migrate_data

或者:
    python web/migrate_data.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 path
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

from web import database as db


def main():
    """执行数据迁移"""
    print("=" * 50)
    print("数据迁移: JSON -> SQLite")
    print("=" * 50)

    # JSON 文件路径
    json_file = project_dir / "data" / "user_agents.json"

    if not json_file.exists():
        print(f"\nJSON 文件不存在: {json_file}")
        print("没有需要迁移的数据。")
        return

    print(f"\n源文件: {json_file}")
    print(f"目标数据库: {db.DB_PATH}")

    # 确认
    response = input("\n确认执行迁移? (y/n): ")
    if response.lower() != "y":
        print("已取消迁移。")
        return

    # 执行迁移
    try:
        count = db.migrate_from_json(json_file)
        print(f"\n迁移完成! 共迁移 {count} 条用户记录。")

        # 显示迁移后的数据
        users = db.get_all_users()
        print(f"\n当前数据库中共有 {len(users)} 个用户:")
        for user in users:
            print(f"  - {user.agent_id}: {user.display_name}")

        # 询问是否备份原文件
        if json_file.exists():
            backup = input("\n是否备份并删除原 JSON 文件? (y/n): ")
            if backup.lower() == "y":
                backup_file = json_file.with_suffix(".json.bak")
                json_file.rename(backup_file)
                print(f"原文件已备份到: {backup_file}")

    except Exception as e:
        print(f"\n迁移失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
