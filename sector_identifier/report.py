# 报告展示层
# 输入：sector_result（sector_identifier/entry.py 的输出对象）
# 返回：可打印摘要字符串
# 被谁调用：analyzer.py（日志打印）


def format_summary(sector_result: dict) -> str:
    n_sectors   = len(sector_result.get('sector_weighted', {}))
    n_unmatched = len(sector_result.get('unmatched', []))
    return f'[题材识别] 命中板块：{n_sectors} 个  未分类：{n_unmatched} 条'
