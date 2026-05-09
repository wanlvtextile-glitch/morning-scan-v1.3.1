# 次日发酵评分闭环
# 回答：这个题材今天会不会从弱共识走向强共识？
# 输入：单个 sector dict（来自 analysis_result['sectors']）
# 输出：{fermentation_score, fermentation_reasons, trigger_points}
# 被谁调用：dual_score/entry.py

# ── v1.2 代理字段说明 ─────────────────────────────────
# 设计文档字段           → v1.2 代理
# freshness_score       → new_catalyst_count / max(item_count, 1)（新颖密度）
# hotrank_signal_type   → needs_websearch（True ≈ hotrank_only）
# low_level_expansion   → 暂无，v1.3 接入个股结构后补充
# expectation_gap_score → 暂无，v1.3 新增


def _freshness_density(sector: dict) -> float:
    """新颖密度：有明确催化的条目数 / 总条目数（用于代理 freshness_score）"""
    item_count = max(sector.get('item_count', 0), 1)
    return sector.get('new_catalyst_count', 0) / item_count


def _build_trigger_points(sector: dict) -> list:
    """
    根据当前可用信号生成盘中验证点。
    v1.3 接入个股结构（midcap_following / low_level_expansion）后可补充更精细规则。
    """
    points: list = []
    hotrank   = sector.get('hotrank')
    hr_rank   = hotrank.get('rank', 999) if hotrank else 999
    new_cat   = sector.get('new_catalyst_count', 0)
    src_count = sector.get('source_count', 0)
    needs_ws  = sector.get('needs_websearch', False)

    if needs_ws or hr_rank <= 5:
        points.append('开盘后若中军放量，则容易形成板块共振')

    if new_cat >= 2:
        points.append('催化密集，注意是否出现 2 只以上联动涨停')
    elif new_cat == 1:
        points.append('已有单条催化出现，关注催化能否持续发酵')

    if src_count == 1:
        points.append('当前仅单源覆盖，需观察其他来源是否跟进')

    if hr_rank <= 3 and src_count == 0:
        points.append('人气榜高位但新闻量极少，开盘情绪为主要观察指标')

    return points


def score_fermentation(sector: dict) -> dict:
    """
    对单个板块计算次日发酵评分。

    判断优先级（高→中→低）：
      高：预发酵/unknown 阶段 + 有新催化 + 人气先行（hotrank_only 或 rank<=5）
      中：预发酵/回流观察/unknown 阶段 + (有新催化 OR hotrank<=10) + 复盘占比低
      低：其余情况（已高潮 / 无催化且复盘主导）
    """
    stage      = sector.get('stage', 'unknown')
    recap_frac = sector.get('recap_fraction', 0.0)
    new_cat    = sector.get('new_catalyst_count', 0)
    needs_ws   = sector.get('needs_websearch', False)
    hotrank    = sector.get('hotrank')
    hr_rank    = hotrank.get('rank', 999) if hotrank else 999
    freshness  = _freshness_density(sector)

    reasons: list = []

    # ── 构建发酵依据 ──────────────────────────────────
    if needs_ws:
        reasons.append('人气榜先行，新闻覆盖尚不足，扩散空间仍在')
    elif hr_rank <= 5:
        reasons.append(f'人气榜先行（#{hr_rank}），市场开始预期但尚未共振')

    if new_cat >= 2:
        reasons.append(f'检测到 {new_cat} 条新增催化内容，催化密度较高')
    elif new_cat == 1:
        reasons.append('检测到 1 条新增催化内容，驱动开始出现')

    if stage == '预发酵':
        reasons.append('阶段判断为预发酵，扩散条件初步成立')
    elif stage == 'unknown':
        reasons.append('阶段信号不足，观察是否有扩散苗头')

    if recap_frac < 0.30:
        reasons.append('复盘型内容占比低，市场尚未形成"昨天已热"的惯性认知')

    # ── 评分判断 ─────────────────────────────────────
    stage_is_early = stage in ('预发酵', 'unknown')
    stage_is_possible = stage in ('预发酵', '回流观察', 'unknown')
    hotrank_leading = needs_ws or hr_rank <= 5

    if stage_is_early and new_cat >= 1 and hotrank_leading:
        score = '高'
    elif stage_is_possible and (new_cat >= 1 or hr_rank <= 10) and recap_frac < 0.50:
        score = '中'
    else:
        score = '低'

    # 无依据时补默认说明，确保 reasons 不为空
    if not reasons:
        reasons.append('当前缺乏明确发酵信号')

    trigger_points = _build_trigger_points(sector)

    return {
        'fermentation_score':   score,
        'fermentation_reasons': reasons,
        'trigger_points':       trigger_points,
    }
