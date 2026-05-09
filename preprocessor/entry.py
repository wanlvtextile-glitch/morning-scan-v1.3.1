# 预处理层入口
# 输入：原始 items 列表（新闻 + 论坛，不含人气榜）
# 输出：{processed_items, stats} dict
# 被谁调用：analyzer.py（_analyze 管道）

from preprocessor.rules import deduplicate, make_content_preview
from preprocessor.conclusions import make_item_conclusion
from preprocessor.evidence import preserve_evidence
from preprocessor.output import build_output


def preprocess(items: list) -> dict:
    """
    完整预处理管道：去重 → 结论标注 → content_preview生成 → 证据补全 → 构建输出。
    返回 {processed_items: list[dict], stats: dict}。
    """
    original = list(items)
    deduped, removed_count = deduplicate(original)

    annotated = []
    for item in deduped:
        conclusion = make_item_conclusion(item)
        preview    = make_content_preview(item.get('title', ''), item.get('content', ''))
        enriched   = preserve_evidence({**item, **conclusion, 'content_preview': preview})
        annotated.append(enriched)

    return build_output(original, annotated, removed_count)
