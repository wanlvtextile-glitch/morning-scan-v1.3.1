# 中间结论层
# 输入：单条 item dict
# 输出：{sectors: {板块名: [命中kw]}, sector_names: [str], is_multi_sector: bool}
# 被谁调用：sector_identifier/entry.py

from sector_identifier.rules import match_sectors_detail


def make_sector_conclusion(item: dict) -> dict:
    detail = match_sectors_detail(item)
    return {
        'sectors':        detail,
        'sector_names':   list(detail.keys()),
        'is_multi_sector': len(detail) > 1,
    }
