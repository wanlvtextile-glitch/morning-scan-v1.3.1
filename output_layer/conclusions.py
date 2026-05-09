# 输出层中间结论
# 输入：单个 sector dict（含双评分字段）
# 输出：{group, group_reason} 追加到 sector
# 被谁调用：output_layer/entry.py

from output_layer.rules import classify_group


def make_group_conclusion(sector: dict) -> dict:
    """对单个板块做归组判断，返回新 dict（不修改原始输入）。"""
    group, group_reason = classify_group(sector)
    return {**sector, 'group': group, 'group_reason': group_reason}
