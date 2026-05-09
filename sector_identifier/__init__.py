# 题材识别层包入口
# 主调用链入口：identify_sectors(processed_items, hotrank_raw) → sector_result
# 其余导出为向后兼容，供旧路径 from sector_identifier import X 继续有效

from sector_identifier.rules import (
    SECTOR_KEYWORDS,
    HOTRANK_MAPPING,
    MILITARY_FALSE_POSITIVE_SIGNALS,
    is_military_false_positive,
    match_sectors_detail,
    hotrank_name_to_sector,
    parse_hotrank,
)
from sector_identifier.conclusions import make_sector_conclusion
from sector_identifier.evidence import preserve_sector_evidence
from sector_identifier.output import build_sector_output
from sector_identifier.downstream import (
    get_sector_weighted, get_sector_matched_kws,
    get_unmatched, get_hotrank_list, get_sector_to_hotrank,
)
from sector_identifier.report import format_summary as format_sector_summary
from sector_identifier.entry import identify_sectors


def match_sectors(item: dict) -> list:
    """向后兼容包装：只返回板块名列表。"""
    return list(match_sectors_detail(item).keys())


__all__ = [
    # 主调用链
    'identify_sectors',
    # 向后兼容（旧路径 from sector_identifier import X 继续有效）
    'SECTOR_KEYWORDS', 'HOTRANK_MAPPING', 'MILITARY_FALSE_POSITIVE_SIGNALS',
    'is_military_false_positive', 'match_sectors_detail', 'match_sectors',
    'hotrank_name_to_sector', 'parse_hotrank',
    # 包内子模块供单元测试或工具调用
    'make_sector_conclusion', 'preserve_sector_evidence',
    'build_sector_output', 'get_sector_weighted', 'get_sector_matched_kws',
    'get_unmatched', 'get_hotrank_list', 'get_sector_to_hotrank',
    'format_sector_summary',
]
