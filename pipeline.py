# pipeline.py — 早盘扫描全流程串联层
#
# 职责：将 Python 自动化的两个阶段串联为一条命令，并在结束时打印
#       结构化 handoff 提示，引导 Claude 继续执行 Step 3-7。
#
# Step 1  采集层  collect()      → raw_news.json
# Step 2  分析层  run_analysis() → analysis_result.json + reports/草稿.md
# Step 3-7        由 Claude 负责（WebSearch / 正宗度 / 覆盖 / 写终稿）
#
# 调用方式：
#   python pipeline.py                        # 直接运行
#   from pipeline import run_pipeline         # 被 run.py 调用

import os
import sys

from collector import collect
from analyzer import run_analysis


# ── 启动前配置校验 ────────────────────────────────────────

def _load_env_for_check():
    """加载 .env，仅用于启动检查（不覆盖已有系统变量）"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(env_path):
        return False
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
    return True


def _check_config():
    """
    启动前校验必填配置项。任一项缺失则打印明确错误并退出，不进入采集流程。
    校验项：
      1. .env 文件存在
      2. XUEQIU_COOKIE 非空
      3. AGENT_LAYER_ENABLED=true 时，对应 LLM API Key 非空
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.exists(env_path):
        print('\n[启动失败] 找不到 .env 配置文件')
        print('  请执行：cp .env.example .env')
        print('  然后填写 XUEQIU_COOKIE 和 LLM 配置后重新运行')
        sys.exit(1)

    _load_env_for_check()

    errors = []

    # 校验雪球 Cookie
    cookie = os.environ.get('XUEQIU_COOKIE', '').strip()
    if not cookie:
        errors.append(
            'XUEQIU_COOKIE 未填写（雪球数据源必需）\n'
            '    获取方式：浏览器登录 xueqiu.com → F12 → Network\n'
            '              → 任意 xueqiu.com 请求 → Request Headers → 复制 Cookie 值\n'
            '    填写位置：.env 文件第一行 XUEQIU_COOKIE='
        )

    # 校验 LLM 配置（仅在 AGENT_LAYER_ENABLED=true 时）
    agent_enabled = os.environ.get('AGENT_LAYER_ENABLED', 'false').lower() == 'true'
    if agent_enabled:
        provider = os.environ.get('LLM_PROVIDER', '').strip()
        if not provider:
            errors.append(
                'AGENT_LAYER_ENABLED=true 但 LLM_PROVIDER 未填写\n'
                '    请在 .env 中取消选择的服务商注释并填入 API Key\n'
                '    或设置 AGENT_LAYER_ENABLED=false 跳过 Agent 层（报告会缺少个股分析）'
            )
        elif provider == 'anthropic':
            if not os.environ.get('ANTHROPIC_API_KEY', '').strip():
                errors.append(
                    'LLM_PROVIDER=anthropic 但 ANTHROPIC_API_KEY 未填写\n'
                    '    注册：console.anthropic.com → API Keys → 生成 Key（格式 sk-ant-api03-...）\n'
                    '    或设置 AGENT_LAYER_ENABLED=false 跳过 Agent 层'
                )
        elif provider == 'openai':
            if not os.environ.get('OPENAI_API_KEY', '').strip():
                errors.append(
                    'LLM_PROVIDER=openai 但 OPENAI_API_KEY 未填写\n'
                    '    请填写对应服务商（DeepSeek / 智谱 / 小米等）的 API Key\n'
                    '    或设置 AGENT_LAYER_ENABLED=false 跳过 Agent 层'
                )
            if not os.environ.get('OPENAI_BASE_URL', '').strip():
                errors.append(
                    'LLM_PROVIDER=openai 但 OPENAI_BASE_URL 未填写\n'
                    '    示例：OPENAI_BASE_URL=https://api.deepseek.com/v1\n'
                    '    请填写服务商提供的 Base URL'
                )
        else:
            errors.append(
                f'LLM_PROVIDER="{provider}" 不支持，仅支持 anthropic 或 openai'
            )

    if errors:
        print('\n[启动失败] 请先完成以下配置，再重新运行：\n')
        for i, msg in enumerate(errors, 1):
            print(f'  {i}. {msg}\n')
        print('  配置文件：.env（参考 .env.example）')
        sys.exit(1)

    print('[配置检查] OK')


# ── 内部工具 ─────────────────────────────────────────────

def _build_source_stats(collector_output) -> list:
    """将 CollectorOutput.results 转为 analyzer 期望的 source_stats 格式"""
    return [
        {
            'name':          r.name,
            'source_type':   r.source_type,
            'is_main':       r.is_main_source,
            'fetch_success': r.fetch_success,
            'item_count':    r.item_count,
            'error_type':    r.error_type,
        }
        for r in collector_output.results
    ]


def _sep(title: str = ''):
    line = '─' * 60
    print(f'\n{line}')
    if title:
        print(f'  {title}')
        print(line)


def _print_handoff(collector_output, analysis_result: dict):
    """
    Python 两阶段完成后，打印结构化摘要，引导 Claude 执行 Step 3-7。
    """
    # editorial_result['all_sectors'] 含 group 字段；analysis_result['sectors'] 不含
    editorial = analysis_result.get('editorial_result', {})
    sectors    = editorial.get('all_sectors', analysis_result.get('sectors', []))
    confidence = collector_output.confidence
    date_str   = analysis_result.get('generated_at', '')[:10] or 'unknown'

    _sep('Pipeline 完成 · Claude 请继续执行 Step 3-7')

    # ── 采集状态 ──
    print(f'置信度：{confidence}  '
          f'主源成功：{collector_output.main_success_count}/4  '
          f'总条目：{len(collector_output.all_items)} 条')
    for r in collector_output.results:
        icon = '[OK]' if r.fetch_success else '[FAIL]'
        print(f'  {icon} {r.name}  {r.item_count} 条'
              + (f'  ({r.error_type})' if r.error_type else ''))

    # ── 分析结果摘要 ──
    print(f'\n板块总数：{len(sectors)} 个')
    groups: dict = {}
    for s in sectors:
        g = s.get('group', '未分组')
        groups[g] = groups.get(g, 0) + 1
    GROUP_ORDER = ['已知强势主线', '次日发酵候选', '人气先行信号', '排除项', '未分组']
    for g in GROUP_ORDER:
        if g in groups:
            names = [s['name'] for s in sectors if s.get('group') == g]
            print(f'  {g}（{groups[g]}）：{", ".join(names)}')

    # ── hotrank_only 提醒 ──
    hotrank_only = [
        sig for sig in analysis_result.get('hotrank_signals', [])
        if sig.get('signal_type') == 'hotrank_only'
    ]
    if hotrank_only:
        names = [sig['hotrank_name'] for sig in hotrank_only]
        print(f'\n!! hotrank_only 板块（Step 4 必须 WebSearch 补充）：{", ".join(names)}')

    # ── 输出文件 ──
    print(f'\n输出文件：')
    print(f'  analysis_result.json')
    if date_str:
        print(f'  reports/{date_str}-morning-scan.md（Python 草稿）')

    # ── 接棒指令 ──
    print(f'\n接棒指令（Claude 按顺序执行）：')
    print(f'  Step 3  Read analysis_result.json，核查各板块字段')
    print(f'  Step 4  WebSearch：市场背景 + 美股 + hotrank_only 专项')
    print(f'  Step 5  正宗度判断（逐只个股，需证据）')
    print(f'  Step 6  审核 Python 结论，有偏差时覆盖并注明原因')
    print(f'  Step 7  补全草稿四项内容 → Write 写入 reports/{date_str}-morning-scan.md')
    if confidence == 'low':
        print(f'\n⚠️  置信度 low：报告头部须加"仅 1 个主源成功，结果供参考"')
    elif confidence == 'none':
        print(f'\n❌  置信度 none：不输出正式报告，仅输出 WebSearch 观察项')

    _sep()


# ── 公开入口 ─────────────────────────────────────────────

def run_pipeline() -> dict:
    """
    早盘扫描全流程串联层（Python 阶段）。
    返回 analysis_result dict（含 report_result）。
    """
    _check_config()

    _sep('Step 1 · 数据采集')
    collector_output = collect()

    source_stats = _build_source_stats(collector_output)

    _sep('Step 2 · 分析管道')
    analysis_result = run_analysis(
        items               = collector_output.all_items,
        confidence          = collector_output.confidence,
        source_stats        = source_stats,
        time_window_start   = collector_output.time_window_start,
    )

    _print_handoff(collector_output, analysis_result)

    return analysis_result


if __name__ == '__main__':
    run_pipeline()
