# run.py — Skill 入口（Claude Code 触发词层）
#
# ┌─────────────────────────────────────────────────────────┐
# │  入口对比                                                │
# │  run.py  — Skill 入口：由 Claude Code 根据触发词自动调用 │
# │            适合对话式交互，无命令行参数                   │
# │  cli.py  — CLI 入口：供人类 / 脚本 / cron 直接调用       │
# │            python cli.py run / check / doctor            │
# │  两者均经过环境门禁，最终调用同一个 pipeline.run_pipeline │
# └─────────────────────────────────────────────────────────┘
#
# 用法（Skill 模式）：
#   python run.py "启动早盘扫描"
#   python run.py "早盘热点"
#   python run.py "扫描市场"

import sys

# Windows GBK 控制台不能直接渲染 UTF-8 emoji；强制重定向为 UTF-8，避免 UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 早盘扫描任务的触发关键词列表
# 用户输入包含其中任意一个即视为匹配
MORNING_SCAN_KEYWORDS = [
    '早盘扫描',
    '启动早盘',
    '早盘热点',
    '扫描市场',
    '市场扫描',
    '早盘分析',
]


def match_task(user_input: str):
    """
    识别用户输入对应的任务名。
    当前支持：'morning_scan'（早盘扫描）
    返回任务名字符串，无匹配则返回 None。
    """
    text = user_input.strip()
    for keyword in MORNING_SCAN_KEYWORDS:
        if keyword in text:
            return 'morning_scan'
    return None


def run_task(task_name: str):
    """根据任务名执行对应任务（委托 cli.cmd_run，共享配置检查和向导逻辑）"""
    if task_name == 'morning_scan':
        print(f'[触发] 任务：早盘扫描  →  启动全流程串联层')
        from cli import cmd_run
        cmd_run(None)
    else:
        # 当前只有一个任务，此分支供未来扩展时排查用
        print(f'[错误] 未知任务：{task_name}')
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print('用法：python run.py "<任务名>"')
        print('示例：python run.py "启动早盘扫描"')
        print(f'支持关键词：{"  /  ".join(MORNING_SCAN_KEYWORDS)}')
        sys.exit(0)

    user_input = sys.argv[1]
    task_name  = match_task(user_input)

    if task_name is None:
        print(f'[未识别] 输入："{user_input}"')
        print(f'支持的触发词：{"  /  ".join(MORNING_SCAN_KEYWORDS)}')
        sys.exit(1)

    run_task(task_name)


if __name__ == '__main__':
    main()
