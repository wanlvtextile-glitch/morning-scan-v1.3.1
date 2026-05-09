# 结构化输出层
# 输入：原始列表、标注后列表、移除数量
# 输出：预处理结果 dict
# 被谁调用：preprocessor/entry.py，preprocessor/downstream.py，preprocessor/report.py


def build_output(original_items: list, annotated_items: list, removed_count: int) -> dict:
    return {
        'processed_items': annotated_items,
        'stats': {
            'original_news': len(original_items),
            'after_dedup':   len(annotated_items),
            'removed':       removed_count,
        },
    }
