# 题材识别层入口
# 输入：processed_items 列表（预处理层输出）+ hotrank_raw 列表
# 输出：{sector_weighted, sector_matched_kws, unmatched, hotrank_list, sector_to_hotrank}
# 被谁调用：analyzer.py（_analyze 管道）

from collections import defaultdict
from sector_identifier.rules import match_sectors_detail, parse_hotrank
from sector_identifier.output import build_sector_output


def identify_sectors(processed_items: list, hotrank_raw: list) -> dict:
    """
    板块聚类（带 cross-sector 权重）+ 人气榜解析。
    每条新闻命中 N 个板块时，对每板块贡献权重 1/N。
    """
    sector_weighted: dict    = defaultdict(list)
    sector_matched_kws: dict = defaultdict(set)
    unmatched: list          = []

    for item in processed_items:
        detail = match_sectors_detail(item)
        if not detail:
            unmatched.append(item)
            continue
        weight = 1.0 / len(detail)
        for sector, kws in detail.items():
            sector_weighted[sector].append({
                **item,
                '_weight':    weight,
                '_exclusive': len(detail) == 1,
            })
            sector_matched_kws[sector].update(kws)

    hotrank_list, sector_to_hotrank = parse_hotrank(hotrank_raw)

    return build_sector_output(
        sector_weighted, sector_matched_kws, unmatched,
        hotrank_list, sector_to_hotrank,
    )
