# 输出层入口
# 输入（新路径）：editorial_result（editorial_layer 输出）
# 输入（旧路径）：scored_sectors + context（向后兼容，供现有测试使用）
# 输出：{report_package, markdown, brief_markdown}（新）或 {report_payload, markdown}（旧）
# 被谁调用：analyzer._analyze()

from output_layer.conclusions import make_group_conclusion
from output_layer.output import build_report_payload
from output_layer.report import build_markdown, build_markdown_from_package, build_brief_markdown


def build_report(scored_sectors: list, context: dict = None) -> dict:
    """
    旧接口（向后兼容）：归组 → 构建 payload → 渲染 Markdown。
    供现有测试和外部调用方继续使用，不做破坏性修改。

    scored_sectors : dual_score 层 scored_sectors 列表
    context        : {date, confidence, dedup_stats, hotrank_signals, source_stats}
    返回           : {report_payload: dict, markdown: str}
    """
    if context is None:
        context = {}

    grouped        = [make_group_conclusion(s) for s in scored_sectors]
    report_payload = build_report_payload(grouped, context)
    markdown       = build_markdown(report_payload)

    return {
        'report_payload': report_payload,
        'markdown':       markdown,
    }


def build_report_from_editorial(editorial_result: dict) -> dict:
    """
    新接口：消费 editorial_layer 输出，生成完整报告包。

    editorial_result : editorial_layer.entry.build_editorial() 的返回值
    返回 : {
        report_package : dict  — 完整结构化数据包（meta/source_snapshot/...）
        markdown       : str   — 主报告（老 v3 格式增强版，含个股表 Claude 占位）
        brief_markdown : str   — 简报（摘要视图，供快速预览）
    }
    """
    from editorial_layer.report_package import build_report_package

    report_package = build_report_package(editorial_result)
    markdown       = build_markdown_from_package(report_package)
    brief_markdown = build_brief_markdown(report_package)

    return {
        'report_package': report_package,
        'markdown':       markdown,
        'brief_markdown': brief_markdown,
    }
