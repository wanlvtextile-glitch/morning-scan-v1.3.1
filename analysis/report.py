# 分析层报告展示
# 输入：analysis_result（analysis/entry.py 的输出对象）
# 返回：可打印摘要字符串
# 被谁调用：analyzer.py（日志打印）


def format_sector_line(s: dict) -> str:
    hr   = s.get('hotrank')
    hr_s = f'[人气#{hr["rank"]} {hr["name"]} {hr["change_pct"]}]' if hr else '[无人气榜]'
    ws   = ' [需WebSearch]' if s.get('needs_websearch') else ''
    logic_s = (
        f'  逻辑单元{s.get("logic_unit_count", 0)}'
        f'(事件{s.get("event_cluster_count", 0)}/题材{s.get("theme_cluster_count", 0)})'
    )
    return (
        f'  [{"*" * s["star_rating"]}] {s["name"]}({s["stage"]}): '
        f'{s["item_count"]}条(有效{s["effective_count"]:.1f})x{s["source_count"]}源 '
        f'{hr_s}{ws}{logic_s}'
    )


def format_hotrank_signal_line(sig: dict) -> str:
    icons = {'news_driven': 'OK', 'hotrank_weak': '~', 'hotrank_only': '!!'}
    tag   = icons.get(sig['signal_type'], '?')
    ms    = sig.get('mapped_sector') or '未映射'
    return (
        f'  [{tag}] #{sig["rank"]} {sig["hotrank_name"]} {sig["change_pct"]} '
        f'-> {ms} (有效{sig["effective_count"]:.1f}条)'
    )


def format_summary(analysis_result: dict) -> str:
    sectors         = analysis_result.get('sectors', [])
    hotrank_signals = analysis_result.get('hotrank_signals', [])
    lines = ['\n[分析结果] 板块排序（前8）：']
    for s in sectors[:8]:
        lines.append(format_sector_line(s))
    lines.append('\n[分析结果] 人气榜信号 Top10：')
    for sig in hotrank_signals:
        lines.append(format_hotrank_signal_line(sig))
    return '\n'.join(lines)
