# 输出层判断规则
# 负责：板块栏目归类规则（纯函数）
# 输入：单个 sector dict（含双评分字段）
# 输出：(group_name: str, group_reason: str)
# 被谁调用：output_layer/conclusions.py

# ── 四个栏目 ─────────────────────────────────────────────
GROUP_已知强势主线 = '已知强势主线'
GROUP_次日发酵候选 = '次日发酵候选'
GROUP_人气先行信号 = '人气先行信号'
GROUP_排除项      = '排除项'

# 栏目展示顺序（报告中的固定排列）
GROUP_ORDER = [GROUP_已知强势主线, GROUP_次日发酵候选, GROUP_人气先行信号, GROUP_排除项]


def classify_group(sector: dict) -> tuple:
    """
    对单个板块判断所属栏目，每个板块仅归入唯一栏目。

    优先级（从高到低）：
      1. 已知强势主线：已强阶段 + 持续性可接受
      2. 次日发酵候选：发酵评分充分 + 未处于已高潮纯排除状态
      3. 人气先行信号：人气榜 only，新闻量极少
      4. 排除项：兜底（含已高潮续弱、复盘主导无催化）

    对照《项目3.1-结构增强闭环设计.md》§6.4 建议映射。
    """
    stage      = sector.get('stage', 'unknown')
    cont       = sector.get('continuation_score', '低')
    ferm       = sector.get('fermentation_score', '低')
    needs_ws   = sector.get('needs_websearch', False)
    eff        = sector.get('effective_count', 0.0)
    recap_frac = sector.get('recap_fraction', 0.0)
    new_cat    = sector.get('new_catalyst_count', 0)
    hotrank    = sector.get('hotrank')
    hr_rank    = hotrank['rank'] if hotrank else 999

    # ── 规则 1：已知强势主线 ────────────────────────────
    # stage in [已高潮, 发酵中] AND continuation_score in [高, 中]
    if stage in ('已高潮', '发酵中') and cont in ('高', '中'):
        return GROUP_已知强势主线, f'阶段={stage}，持续性={cont}'

    # ── 规则 2：次日发酵候选 ────────────────────────────
    # fermentation_score in [高, 中]，且未处于"已高潮续弱"的纯排除状态
    # （已高潮 + continuation=低 不走此规则，直接落入排除项）
    if ferm in ('高', '中') and not (stage == '已高潮' and cont == '低'):
        return GROUP_次日发酵候选, f'发酵概率={ferm}，阶段={stage}'

    # ── 规则 3：人气先行信号 ────────────────────────────
    # needs_websearch=True（hotrank_only，新闻量极少）
    # 或：人气榜 Top10 但有效新闻量 < 2
    if needs_ws or (hotrank and hr_rank <= 10 and eff < 2):
        return GROUP_人气先行信号, f'人气榜 #{hr_rank}，新闻覆盖不足（有效{eff:.1f}条）'

    # ── 规则 4：排除项（兜底）──────────────────────────
    # 包含：已高潮续弱、复盘主导无催化、其余未命中以上三条的板块
    if stage == '已高潮' and cont == '低':
        return GROUP_排除项, '前一日已高一致，持续性低，今日不作重点'
    if recap_frac >= 0.50 and new_cat == 0:
        return GROUP_排除项, f'复盘型内容占比 {recap_frac:.0%}，无新增催化'
    return GROUP_排除项, f'阶段={stage}，持续性={cont}，发酵概率={ferm}，信号不足'
