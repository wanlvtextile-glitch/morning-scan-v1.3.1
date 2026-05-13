# 结构化输出层
# 输入：原始列表、标注后列表、移除数量
# 输出：预处理结果 dict
# 被谁调用：preprocessor/entry.py，preprocessor/downstream.py，preprocessor/report.py


def build_output(
    original_items: list,
    processed_items: list,
    removed_count: int,
    logic_units: list | None = None,
    signal_stats: dict | None = None,
    dedup_decisions: list | None = None,
) -> dict:
    return {
        'processed_items': processed_items,
        'stats': {
            'original_news': len(original_items),
            'after_dedup':   len(processed_items),
            'removed':       removed_count,
        },
        'logic_units': logic_units or [],
        'signal_stats': signal_stats or {},
        'dedup_decisions': dedup_decisions or [],
    }
