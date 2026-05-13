# 输出层入口
# 输入：editorial_result（editorial_layer 输出）
# 输出：{report_package, markdown, brief_markdown}
# 被谁调用：analyzer._analyze()

from output_layer.report import build_markdown_from_package, build_brief_markdown
from output_layer.logic_render import inject_brief_logic_summary, inject_logic_explanations


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
    markdown       = inject_logic_explanations(build_markdown_from_package(report_package), report_package)
    brief_markdown = inject_brief_logic_summary(build_brief_markdown(report_package), report_package)

    return {
        'report_package': report_package,
        'markdown':       markdown,
        'brief_markdown': brief_markdown,
    }
