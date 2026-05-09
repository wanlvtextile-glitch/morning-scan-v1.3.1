# 阶段判断规则（纯函数）
# 输入：板块 dict（含 effective_count / source_count / hotrank / recap_fraction 等字段）
# 输出：(stage_label: str, stage_signals: list[str])
# 被谁调用：analysis/entry.py，analyzer.py（通过 compute_stage 别名）


def apply_stage_rules(sector: dict) -> tuple:
    """
    基于板块的可计算离散信号，输出 (stage_label, stage_signals)。

    判断顺序（优先级从高到低）：
      1. 已高潮：多源 + 高热度 + 复盘主导
      2. 发酵中：多源共振 + 人气榜 Top10 + 非复盘主导
      3. 预发酵：人气先行有新催化，或单源新催化尚未升温
      4. unknown：以上条件均不满足

    回流观察需要历史 stage 状态，v1.2 Python 层无法自动判断，
    由 Claude 在报告中手动标注。
    """
    eff     = sector['effective_count']
    src     = sector['source_count']
    hotrank = sector.get('hotrank')
    hr_rank = hotrank['rank'] if hotrank else 999
    recap_f = sector.get('recap_fraction', 0.0)
    new_cat = sector.get('new_catalyst_count', 0)
    ws      = sector.get('needs_websearch', False)

    signals: list = []

    # 已高潮
    if src >= 3 and eff >= 6 and recap_f >= 0.50:
        signals.append(f'三源及以上覆盖（{src}源），整体热度高')
        signals.append(f'复盘型内容占比 {recap_f:.0%}，新增信息密度低')
        if new_cat == 0:
            signals.append('未检测到新增催化')
        return '已高潮', signals

    # 发酵中（人气榜路径：价格行为确认，无需文本多源）
    # 人气榜本身是独立的价格信号，与文本讨论量共同构成双信号确认
    if hr_rank <= 10 and eff >= 4 and recap_f < 0.50:
        if src >= 2:
            signals.append(f'多源共振（{src}源）')
        else:
            signals.append(f'新闻热度充足（有效 {eff:.1f} 条）')
        signals.append(f'人气榜 #{hr_rank}，市场行为确认（{hotrank["change_pct"]}）')
        if new_cat > 0:
            signals.append(f'检测到 {new_cat} 条带催化内容')
        return '发酵中', signals

    # 发酵中（新闻量充足路径：无人气榜映射但多源高量有催化）
    if src >= 2 and eff >= 6 and new_cat >= 1 and recap_f < 0.50:
        signals.append(f'多源共振（{src}源），有效条目充足（{eff:.1f}条）')
        signals.append(f'检测到 {new_cat} 条带催化内容')
        signals.append('人气榜未映射，依据新闻量判定')
        return '发酵中', signals

    # 预发酵
    is_hotrank_leading = ws or (hr_rank <= 5 and src <= 1)
    has_fresh_catalyst = new_cat >= 1

    if is_hotrank_leading and has_fresh_catalyst:
        signals.append('人气榜先行，新闻覆盖尚不足')
        signals.append(f'检测到 {new_cat} 条新增催化内容')
        return '预发酵', signals

    if has_fresh_catalyst and src == 1 and eff < 3:
        signals.append('新增催化出现，但讨论量尚未升温')
        signals.append('仅单源覆盖，共振尚未形成')
        return '预发酵', signals

    # unknown
    signals.append('信号不足，无法归入已知阶段')
    return 'unknown', signals


# 向后兼容别名（analyzer.py 使用 compute_stage 这个名字）
compute_stage = apply_stage_rules
