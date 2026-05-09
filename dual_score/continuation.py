# 持续性评分闭环
# 回答：昨天已强的题材，今天还能不能继续加强？
# 输入：单个 sector dict（来自 analysis_result['sectors']）
# 输出：{continuation_score, continuation_reasons, continuation_risks}
# 被谁调用：dual_score/entry.py

# ── v1.2 代理字段说明 ─────────────────────────────────
# 设计文档字段         → v1.2 代理
# catalyst_strength   → new_catalyst_count / max(item_count, 1)（催化密度）
# consensus_score     → recap_fraction（高复盘占比 ≈ 高一致性，反向指标）
# midcap_following    → multi_source_agreement（多源覆盖作为代理）
# overseas_linkage    → 暂无，v1.3 接入 WebSearch


def _catalyst_density(sector: dict) -> float:
    """催化密度：有明确催化的条目数 / 总条目数（用于代理 catalyst_strength）"""
    item_count = max(sector.get('item_count', 0), 1)
    return sector.get('new_catalyst_count', 0) / item_count


def score_continuation(sector: dict) -> dict:
    """
    对单个板块计算持续性评分。

    判断优先级（高→中→低）：
      高：已强阶段 + 催化密度充足 + 复盘占比低
      中：已强阶段 + 有任意一项支撑（有催化 OR 多源共振）+ 复盘占比尚可
      低：其余情况（已高潮且复盘主导 / unknown / 无催化且复盘高）
    """
    stage        = sector.get('stage', 'unknown')
    recap_frac   = sector.get('recap_fraction', 0.0)
    new_cat      = sector.get('new_catalyst_count', 0)
    multi_src    = sector.get('multi_source_agreement', False)
    src_count    = sector.get('source_count', 0)
    hotrank      = sector.get('hotrank')
    cat_density  = _catalyst_density(sector)

    reasons: list = []
    risks:   list = []

    # ── 构建支撑依据 ──────────────────────────────────
    if src_count >= 3:
        reasons.append(f'多源共振（{src_count}源），基础热度稳固')
    elif src_count >= 2:
        reasons.append(f'双源覆盖（{src_count}源），共振初步形成')

    if new_cat >= 1:
        reasons.append(f'仍有 {new_cat} 条带催化内容，有新增驱动')

    if hotrank and hotrank.get('rank', 999) <= 10:
        reasons.append(f'人气榜 #{hotrank["rank"]}，市场持续关注')

    if multi_src:
        reasons.append('机构级来源已有共振（3 源及以上）')

    # ── 构建风险提示 ──────────────────────────────────
    if recap_frac >= 0.60:
        risks.append(f'复盘型内容占比 {recap_frac:.0%}，新增信息密度低')
    elif recap_frac >= 0.40:
        risks.append(f'复盘型内容占比 {recap_frac:.0%}，旧逻辑复述偏多')

    if stage == '已高潮':
        risks.append('前一日已高一致，今天更偏分化择强')

    if new_cat == 0:
        risks.append('未检测到新增催化，缺乏上涨新驱动')

    if src_count <= 1:
        risks.append('仅单源覆盖，共振尚未形成')

    # ── 评分判断 ─────────────────────────────────────
    stage_is_active = stage in ('发酵中', '已高潮')
    eff = sector.get('effective_count', 0.0)

    if stage_is_active and cat_density >= 0.30 and recap_frac < 0.40:
        score = '高'
    elif stage_is_active and (new_cat >= 1 or multi_src) and recap_frac < 0.60:
        score = '中'
    elif not stage_is_active and eff >= 6 and src_count >= 2 and new_cat >= 1 and recap_frac < 0.50:
        # 高信号但阶段未能识别（如人气榜未映射），保守给中
        score = '中'
        risks.append('阶段未能从已知路径识别，判断依据为新闻量')
    else:
        score = '低'

    # 无支撑依据时补默认说明，确保 reasons 不为空
    if not reasons:
        reasons.append('当前阶段缺乏明确支撑信号')

    return {
        'continuation_score':   score,
        'continuation_reasons': reasons,
        'continuation_risks':   risks,
    }
