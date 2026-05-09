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
    recap_n   = sum(1 for x in processed if x.get('is_recap'))
    cat_n     = sum(1 for x in processed if x.get('catalyst_type'))
    return (
        f'[预处理] 原始 {original} 条 → 去重后 {after} 条（移除 {removed}）'
        f'  复盘 {recap_n} 条  有催化 {cat_n} 条'
    )
