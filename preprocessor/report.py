# 报告展示层
# 输入：preprocessor/output.py 的结果 dict
# 输出：可打印摘要字符串
# 被谁调用：analyzer.py（日志打印）


def format_summary(result: dict) -> str:
    stats = result.get('stats', {})
    original = stats.get('original_news', 0)
    after    = stats.get('after_dedup', 0)
    removed  = stats.get('removed', 0)
    processed = result.get('processed_items', [])
    signal_stats = result.get('signal_stats', {})
    recap_n   = sum(1 for x in processed if x.get('is_recap'))
    cat_n     = sum(1 for x in processed if x.get('catalyst_type'))
    logic_n   = len(result.get('logic_units', []))
    event_n   = signal_stats.get('event_cluster_count', 0)
    theme_n   = signal_stats.get('theme_cluster_count', 0)
    return (
        f'[预处理] 原始 {original} 条 → 去重后 {after} 条（移除 {removed}）'
        f'  复盘 {recap_n} 条  有催化 {cat_n} 条'
        f'  逻辑单元 {logic_n} 个（事件簇 {event_n} / 题材簇 {theme_n}）'
    )
