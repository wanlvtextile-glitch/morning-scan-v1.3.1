# 预处理层包入口
# 重导出全部旧接口（向后兼容）+ 新接口

from preprocessor.rules import (
    strip_html,
    normalize_title,
    deduplicate,
    deduplicate_with_trace,
    RECAP_SIGNALS,
    is_recap_item,
    CATALYST_PATTERNS,
    classify_catalyst,
)
from preprocessor.conclusions import make_item_conclusion
from preprocessor.evidence import preserve_evidence, EVIDENCE_FIELDS, EVIDENCE_DEFAULTS
from preprocessor.output import build_output
from preprocessor.downstream import (
    get_processed_items,
    get_stats,
    get_logic_units,
    get_signal_stats,
    get_dedup_decisions,
)
from preprocessor.report import format_summary
from preprocessor.entry import preprocess


def annotate_items(items: list) -> list:
    """向后兼容包装：对 items 逐条做结论标注，返回新列表。"""
    return [
        {**item, **make_item_conclusion(item)}
        for item in items
    ]


__all__ = [
    # 旧接口
    'strip_html', 'normalize_title', 'deduplicate', 'deduplicate_with_trace',
    'RECAP_SIGNALS', 'is_recap_item',
    'CATALYST_PATTERNS', 'classify_catalyst',
    'annotate_items',
    # 新接口
    'preprocess', 'make_item_conclusion', 'preserve_evidence',
    'EVIDENCE_FIELDS', 'EVIDENCE_DEFAULTS',
    'build_output',
    'get_processed_items', 'get_stats', 'get_logic_units', 'get_signal_stats', 'get_dedup_decisions',
    'format_summary',
]
