# 中间结论层
# 输入：单条 item dict
# 输出：结论 dict {is_recap, is_new_catalyst, catalyst_type}
# 被谁调用：preprocessor/entry.py

from preprocessor.rules import is_recap_item, classify_catalyst


def make_item_conclusion(item: dict) -> dict:
    catalyst_type = classify_catalyst(item)
    return {
        'is_recap':        is_recap_item(item),
        'is_new_catalyst': catalyst_type is not None,
        'catalyst_type':   catalyst_type,
    }
