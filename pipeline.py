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

from collector import collect
from analyzer import run_analysis


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
