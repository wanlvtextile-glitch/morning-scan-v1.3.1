# 编辑层：最终结论结构构建
# 构建 final_recommendations：主线 / 发酵候选 / 观察列表 + Claude 占位结论。
# 被谁调用：editorial_layer/entry.py

from output_layer.rules import (
    GROUP_已知强势主线, GROUP_次日发酵候选, GROUP_人气先行信号,
)


def build_final_recommendations(sectors_with_group: list) -> dict:
    """
    从已归组板块中抽取：
      primary_lines   - 已知强势主线板块名列表（今日主盯）
      candidate_lines - 次日发酵候选板块名列表（观察是否启动）
      watch_list      - 人气先行信号板块名列表（等待跟进确认）
      conclusion_text - None，由 Claude 在 Step 7 补全一段话
    """
    primary    = [s['name'] for s in sectors_with_group if s.get('group') == GROUP_已知强势主线]
    candidates = [s['name'] for s in sectors_with_group if s.get('group') == GROUP_次日发酵候选]
    watch      = [s['name'] for s in sectors_with_group if s.get('group') == GROUP_人气先行信号]

    return {
        'primary_lines':    primary[:3],
        'candidate_lines':  candidates[:3],
        'watch_list':       watch,
        'conclusion_text':  None,   # Claude 在 Step 7 补全
    }
