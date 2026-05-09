# 报告展示层
# 输入：dual_score_result（dual_score/entry.py 的输出对象）
# 返回：可打印摘要字符串
# 被谁调用：analyzer._analyze()（日志打印）


def format_summary(dual_score_result: dict) -> str:
    scored  = dual_score_result.get('scored_sectors', [])
    stats   = dual_score_result.get('scoring_stats', {})
    cont_s  = stats.get('continuation', {})
    ferm_s  = stats.get('fermentation', {})

    lines = [f'\n[双评分] {len(scored)} 个板块完成评分']
    lines.append(
        f'  持续性：高 {cont_s.get("高", 0)} | '
        f'中 {cont_s.get("中", 0)} | 低 {cont_s.get("低", 0)}'
    )
    lines.append(
        f'  发酵概率：高 {ferm_s.get("高", 0)} | '
        f'中 {ferm_s.get("中", 0)} | 低 {ferm_s.get("低", 0)}'
    )

    for s in scored:
        name  = s.get('name', '?')
        cont  = s.get('continuation_score', '-')
        ferm  = s.get('fermentation_score', '-')
        stage = s.get('stage', '-')
        lines.append(f'  {name:<8} 阶段={stage}  持续性={cont}  发酵概率={ferm}')

    return '\n'.join(lines)
