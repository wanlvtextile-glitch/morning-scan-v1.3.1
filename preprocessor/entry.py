# 预处理层入口
# 输入：原始 items 列表（新闻 + 论坛，不含人气榜）
# 输出：{processed_items, stats} dict
# 被谁调用：analyzer.py（_analyze 管道）

from preprocessor.cluster import build_logic_units, build_signal_stats
from preprocessor.rules import deduplicate_with_trace, make_content_preview, normalize_title
from preprocessor.conclusions import make_item_conclusion
from preprocessor.evidence import preserve_evidence
from preprocessor.output import build_output


def preprocess(items: list) -> dict:
    """
    完整预处理管道：
    单条轻量打标 → 基础去重 → logic_units 聚合 → 证据补全 → 构建输出。
    返回兼容旧接口并扩展新结构的 dict。
    """
    original = list(items)
    tagged_original = []
    for idx, item in enumerate(original, 1):
        conclusion = make_item_conclusion(item)
        preview = make_content_preview(item.get('title', ''), item.get('content', ''))
        enriched = preserve_evidence({
            **item,
            **conclusion,
            'content_preview': preview,
            'normalized_title': normalize_title(item.get('title', '')),
            'original_id': item.get('original_id') or f'pp-{idx:06d}',
            'preprocess_role': 'raw_tagged',
            'unit_key': '',
            'decision_type': 'keep',
        })
        tagged_original.append(enriched)

    deduped, removed_count, removed_items = deduplicate_with_trace(tagged_original)
    for item in removed_items:
        item['preprocess_role'] = 'exact_duplicate_removed'
        item['decision_type'] = 'drop_exact_duplicate'

    logic_units = build_logic_units(deduped)
    signal_stats = build_signal_stats(logic_units, removed_count)

    decision_lookup = {
        item['original_id']: {
            'original_id': item['original_id'],
            'normalized_title': item.get('normalized_title', ''),
            'decision_type': item.get('decision_type', 'keep'),
            'cluster_key': item.get('unit_key') or None,
            'reason': item.get('_dedup_reason', '') or item.get('preprocess_role', ''),
            'is_recap': item.get('is_recap', False),
            'is_new_catalyst': item.get('is_new_catalyst', False),
            'catalyst_type': item.get('catalyst_type'),
        }
        for item in removed_items
    }
    for item in deduped:
        decision_lookup[item['original_id']] = {
            'original_id': item['original_id'],
            'normalized_title': item.get('normalized_title', ''),
            'decision_type': item.get('decision_type', 'keep'),
            'cluster_key': item.get('unit_key') or None,
            'reason': item.get('preprocess_role', ''),
            'is_recap': item.get('is_recap', False),
            'is_new_catalyst': item.get('is_new_catalyst', False),
            'catalyst_type': item.get('catalyst_type'),
        }

    return build_output(
        original_items=original,
        processed_items=deduped,
        removed_count=removed_count,
        logic_units=logic_units,
        signal_stats=signal_stats,
        dedup_decisions=list(decision_lookup.values()),
    )
