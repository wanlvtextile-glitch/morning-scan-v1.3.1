# output_layer 包初始化
# 主调用链：build_report
# 向后兼容：各子模块函数直接导入

# 主调用链
from output_layer.entry import build_report

# 子模块公开接口
from output_layer.conclusions import make_group_conclusion
from output_layer.output import build_report_payload
from output_layer.report import build_markdown
from output_layer.downstream import (
    get_report_payload,
    get_markdown,
    get_groups,
    get_trigger_summary,
)
from output_layer.rules import (
    classify_group,
    GROUP_已知强势主线,
    GROUP_次日发酵候选,
    GROUP_人气先行信号,
    GROUP_排除项,
    GROUP_ORDER,
)

__all__ = [
    # 主调用链
    'build_report',
    # 结论与构建
    'make_group_conclusion',
    'build_report_payload',
    'build_markdown',
    # 下游访问器
    'get_report_payload',
    'get_markdown',
    'get_groups',
    'get_trigger_summary',
    # 规则与常量
    'classify_group',
    'GROUP_已知强势主线',
    'GROUP_次日发酵候选',
    'GROUP_人气先行信号',
    'GROUP_排除项',
    'GROUP_ORDER',
]
