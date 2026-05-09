# 输出层结构化输出
# 输入：已归组的 sector 列表 + context 信息
# 输出：report_payload dict（结构化报告对象，供 report.py 渲染）
# 被谁调用：output_layer/entry.py

from datetime import datetime
from output_layer.rules import GROUP_ORDER


def build_report_payload(grouped_sectors: list, context: dict) -> dict:
    """
    构建结构化报告对象。

    grouped_sectors  : 每个 sector 已含 group / group_reason 字段
    context          : {date, confidence, dedup_stats, hotrank_signals, source_stats}

    输出 groups 字段按 GROUP_ORDER 排列，每个栏目只含归入该栏目的板块。
    """
    # 按栏目分组
    groups: dict = {g: [] for g in GROUP_ORDER}
    for s in grouped_sectors:
        g = s.get('group', '排除项')
        if g in groups:
            groups[g].append(s)

    # 盘中验证点：汇总所有非排除项板块的 trigger_points
    all_triggers = []
    for g in (g for g in GROUP_ORDER if g != '排除项'):
        for s in groups[g]:
            for tp in s.get('trigger_points', []):
                all_triggers.append({'sector': s['name'], 'point': tp})

    return {
        'generated_at':   datetime.now().isoformat(),
        'date':           context.get('date', datetime.now().strftime('%Y-%m-%d')),
        'confidence':     context.get('confidence', 'unknown'),
        'dedup_stats':    context.get('dedup_stats', {}),
        'source_stats':   context.get('source_stats', []),
        'groups':         groups,
        'trigger_summary': all_triggers,
        'hotrank_signals': context.get('hotrank_signals', []),
    }
