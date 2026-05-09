# cli.py — 早盘扫描命令行入口
#
# 使用方式：
#   python cli.py run      # 执行完整早盘扫描（同 skill 触发词）
#   python cli.py check    # 检查环境配置是否就绪
#   python cli.py doctor   # 完整诊断（Python 版本 + 包 + 环境）
#   python cli.py          # 显示帮助
#
# 与 skill 入口（run.py）的区别：
#   CLI（cli.py）：供人类和脚本直接调用，有完整命令行参数，适合 cron / CI / 终端
#   Skill（run.py）：供 Claude Code 通过触发词调用，无命令行参数，适合对话式调用
#   两者均经过 assert_ready() 环境门禁，最终调用同一个 pipeline.run_pipeline()

import argparse
import sys
import os


# ── 子命令实现 ────────────────────────────────────────────


def cmd_run(args):
    """执行完整早盘扫描流程。"""
    from pipeline import run_pipeline
    run_pipeline()


def cmd_check(args):
    """检查环境配置，输出结构化结果。"""
    from checks import check_env

    result = check_env()

    # .env 文件
    env_ok = result['env_file']['ok']
    print(f"[.env 文件]    {'OK  ' if env_ok else 'MISS'}  {result['env_file']['path']}")

    # Cookie
    cookie_ok = result['cookie']['ok']
    print(f"[雪球 Cookie]  {'OK' if cookie_ok else 'MISS  → XUEQIU_COOKIE 未填写'}")

    # Agent 层
    agent_on = result['agent']['enabled']
    print(f"[Agent 层]     {'启用' if agent_on else '关闭  → AGENT_LAYER_ENABLED=false'}")

    # LLM
    if agent_on:
        llm_ok       = result['llm']['ok']
        llm_provider = result['llm']['provider'] or '(未设置)'
        print(f"[LLM 服务商]   {'OK' if llm_ok else 'ERR'}   provider={llm_provider}")
    else:
        print(f"[LLM 服务商]   跳过（Agent 层未启用）")

    # 汇总
    print()
    if result['ready']:
        print('[OK] 环境就绪，可以运行  python cli.py run')
    else:
        print('[FAIL] 以下问题需要修复：')
        for i, err in enumerate(result['errors'], 1):
            print(f'\n  {i}. {err}')
        print(f'\n  配置文件：.env（参考 .env.example）')

    if result['warnings']:
        print()
        for w in result['warnings']:
            print(f'  [WARN]  {w}')

    sys.exit(0 if result['ready'] else 1)


def cmd_doctor(args):
    """完整诊断：Python 版本 + 依赖包 + 环境配置。"""
    from checks import check_env, check_packages

    # Python 版本
    v = sys.version_info
    py_ok = v >= (3, 8)
    print(f"[Python]    {'OK' if py_ok else 'ERR'}  {sys.version.split()[0]}  (需要 3.8+)")

    # 依赖包
    pkg = check_packages()
    if pkg['ok']:
        print(f"[依赖包]    OK   {len(pkg['installed'])} 个均已安装")
    else:
        print(f"[依赖包]    MISS 缺少：{', '.join(pkg['missing'])}")
        print(f"           修复：pip install {' '.join(pkg['missing'])}")

    # 环境配置（复用 check 逻辑，但合并输出）
    print()
    cmd_check(args)


# ── 入口 ──────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python cli.py',
        description='早盘热点扫描 — 命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
命令说明：
  run      执行完整早盘扫描，输出报告到 reports/ 目录
  check    检查 .env 配置是否就绪（不执行扫描）
  doctor   完整诊断：Python 版本 + 依赖包 + 环境配置

示例：
  python cli.py run
  python cli.py check
  python cli.py doctor

触发词方式（Claude Code skill）：
  在 Claude Code 对话中输入"启动早盘扫描"即可触发，无需命令行。
""",
    )
    sub = parser.add_subparsers(dest='command', metavar='<command>')
    sub.add_parser('run',    help='执行完整早盘扫描')
    sub.add_parser('check',  help='检查环境配置')
    sub.add_parser('doctor', help='完整诊断（Python + 包 + 环境）')
    return parser


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.command == 'run':
        cmd_run(args)
    elif args.command == 'check':
        cmd_check(args)
    elif args.command == 'doctor':
        cmd_doctor(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()
