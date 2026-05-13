# 编辑层：板块视图构建
# 构建 top_sectors（主要关注视图）和 hidden_signals（人气榜隐藏信号）。
# 被谁调用：editorial_layer/entry.py

from output_layer.rules import (
    GROUP_已知强势主线, GROUP_次日发酵候选,
)

TOP_SECTORS_MAX = 5   # 主要关注板块上限


def build_top_sectors(sectors_full: list) -> list:
    """
    从已归组、已有 stock_candidates 的板块列表中，选出主要关注板块：
      优先：已知强势主线（全部）
      补充：次日发酵候选（按 star_rating 降序，补到 TOP_SECTORS_MAX）
    返回列表保持原顺序（analysis 层已按热度排好序）。
    """
    主线 = [s for s in sectors_full if s.get('group') == GROUP_已知强势主线]
    发酵 = [s for s in sectors_full if s.get('group') == GROUP_次日发酵候选]

    top = 主线 + 发酵
    return top[:TOP_SECTORS_MAX]


def build_hidden_signals(hotrank_signals: list) -> list:
    """
    从 hotrank_signals 中取 signal_type='hotrank_only' 条目，
    添加 websearch_summary 占位字段（Claude 在 Step 4 填写）。
    """
    result = []
    for sig in hotrank_signals:
        if sig.get('signal_type') == 'hotrank_only':
            result.append({
                **sig,
                'websearch_summary': None,   # Claude 填充：专项查询摘要
            })
    return result
