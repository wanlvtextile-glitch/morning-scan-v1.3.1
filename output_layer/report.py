# 输出层 Markdown 报告渲染
# build_markdown(report_payload)          → 旧路径，向后兼容
# build_markdown_from_package(pkg)        → 新路径，消费 report_package，还原 v3 报告结构增强版
# build_brief_markdown(pkg)              → 新路径，简报摘要
# 被谁调用：output_layer/entry.py

from datetime import datetime
from output_layer.rules import (
    GROUP_已知强势主线, GROUP_次日发酵候选,
    GROUP_排除项, GROUP_ORDER,
)


# ── 星级显示 ─────────────────────────────────────────────

def _stars(n: int) -> str:
    return '⭐' * max(1, min(n, 5))


def _render_logic_summary_lines(sector: dict, max_lines: int = 3) -> list:
    summary_lines = sector.get('logic_summary_lines', []) or []
    if summary_lines:
        lines = [f'- **逻辑解释**：{summary_lines[0]}']
        lines.extend(f'- {line}' for line in summary_lines[1:max_lines])
        return lines

    short = sector.get('logic_summary_short', '')
    if short:
        return [f'- **逻辑解释**：{short}']
    return []


# ── 单板块渲染（按栏目有差异）───────────────────────────

def _render_sector_主线(s: dict) -> str:
    """已知强势主线：重点展示持续性 + 风险 + 个股候选"""
    lines = [f'### {s["name"]}']
    lines.append(f'- **阶段**：{s.get("stage", "-")}  **热度**：{_stars(s.get("star_rating", 1))}')
    lines.append(f'- **持续性**：{s.get("continuation_score", "-")}')
    reasons = s.get('continuation_reasons', [])
    if reasons:
        lines.append(f'- **支撑**：{"；".join(reasons)}')
    risks = s.get('continuation_risks', [])
    if risks:
        lines.append(f'- **风险**：{"；".join(risks)}')
    lines.append('')
    lines.append(_render_stock_candidates_table(s.get('stock_candidates', [])))
    ar = s.get('agent_review')
    if ar and ar.get('note'):
        lines.append(f'\n> **审核备注**（置信度：{ar.get("confidence", "-")}）：{ar["note"]}')
    return '\n'.join(lines)


def _render_sector_发酵(s: dict) -> str:
    """次日发酵候选：重点展示发酵评分 + 触发点 + 个股候选"""
    lines = [f'### {s["name"]}']
    lines.append(f'- **阶段**：{s.get("stage", "-")}  **热度**：{_stars(s.get("star_rating", 1))}')
    lines.append(f'- **发酵概率**：{s.get("fermentation_score", "-")}')
    reasons = s.get('fermentation_reasons', [])
    if reasons:
        lines.append(f'- **依据**：{"；".join(reasons)}')
    triggers = s.get('trigger_points', [])
    if triggers:
        lines.append('- **盘中验证点**：')
        for tp in triggers:
            lines.append(f'  - {tp}')
    lines.append('')
    lines.append(_render_stock_candidates_table(s.get('stock_candidates', [])))
    ar = s.get('agent_review')
    if ar and ar.get('note'):
        lines.append(f'\n> **审核备注**（置信度：{ar.get("confidence", "-")}）：{ar["note"]}')
    return '\n'.join(lines)


def _render_sector_排除(s: dict) -> str:
    """排除项：简明说明排除原因"""
    lines = [f'### {s["name"]}']
    lines.append(f'- **阶段**：{s.get("stage", "-")}  **排除原因**：{s.get("group_reason", "-")}')
    risks = s.get('continuation_risks', [])[:2]
    if risks:
        lines.append(f'- **风险**：{"；".join(risks)}')
    return '\n'.join(lines)


_SECTOR_RENDERER = {
    GROUP_已知强势主线: _render_sector_主线,
    GROUP_次日发酵候选: _render_sector_发酵,
    GROUP_排除项:      _render_sector_排除,
}


# ── 栏目标题 ─────────────────────────────────────────────

_GROUP_HEADING = {
    GROUP_已知强势主线: '## 一、已知强势主线',
    GROUP_次日发酵候选: '## 二、次日发酵候选',
    GROUP_排除项:      '## 三、排除项',
}

_GROUP_INTRO = {
    GROUP_已知强势主线: '前一日已有明确兑现或多源共振，今日关注能否继续加强。',
    GROUP_次日发酵候选: '信号初现或人气先行，今日有望从弱共识走向强共识，关注触发条件。',
    GROUP_排除项:      '前一日已高潮且续弱，或复盘帖主导无新增催化，今日不作重点。',
}


# ── 市场背景简版 ─────────────────────────────────────────

def _render_background(payload: dict) -> str:
    confidence = payload.get('confidence', 'unknown')
    dedup      = payload.get('dedup_stats', {})
    sources    = payload.get('source_stats', [])
    date       = payload.get('date', '')

    conf_map = {'normal': '正常（主要来源均有效）', 'low': '偏低（部分来源失效）',
                'none': '极低（主要来源均失效）', 'unknown': '未知'}
    conf_str = conf_map.get(confidence, confidence)

    lines = ['## 市场背景']
    lines.append(f'- **扫描日期**：{date}')
    lines.append(f'- **数据置信度**：{conf_str}')

    if dedup:
        lines.append(
            f'- **采集量**：原始 {dedup.get("original_news", 0)} 条 → '
            f'去重后 {dedup.get("after_dedup", 0)} 条'
            f'（移除 {dedup.get("removed", 0)} 条重复）'
        )

    active_sources = [s['name'] for s in sources if s.get('fetch_success') and s.get('item_count', 0) > 0]
    if active_sources:
        lines.append(f'- **有效来源**：{"、".join(active_sources)}')

    lines.append('')
    lines.append('> 市场背景详细分析（隔夜联动、宏观背景）请在 Step 2 人工补充。')
    return '\n'.join(lines)


# ── 盘中验证点汇总 ───────────────────────────────────────

def _render_trigger_summary(trigger_summary: list) -> str:
    if not trigger_summary:
        return '## 盘中验证点汇总\n\n暂无明确验证点。'

    lines = ['## 盘中验证点汇总', '']
    # 按板块分组展示
    by_sector: dict = {}
    for t in trigger_summary:
        by_sector.setdefault(t['sector'], []).append(t['point'])
    for sector, points in by_sector.items():
        lines.append(f'**{sector}**')
        for p in points:
            lines.append(f'- {p}')
    return '\n'.join(lines)


# ── 完整 Markdown 渲染 ───────────────────────────────────

def build_markdown(report_payload: dict) -> str:
    date   = report_payload.get('date', '')
    groups = report_payload.get('groups', {})

    sections = [f'# 早盘扫描报告 · {date}', '']

    # 市场背景
    sections.append(_render_background(report_payload))
    sections.append('')

    # 四个栏目
    for group in GROUP_ORDER:
        sectors = groups.get(group, [])
        renderer = _SECTOR_RENDERER[group]
        heading  = _GROUP_HEADING[group]
        intro    = _GROUP_INTRO[group]

        sections.append(heading)
        sections.append('')
        sections.append(f'> {intro}')
        sections.append('')

        if not sectors:
            sections.append('_当前无符合条件的板块。_')
        else:
            for s in sectors:
                sections.append(renderer(s))
                sections.append('')
        sections.append('')

    # 盘中验证点汇总
    sections.append(_render_trigger_summary(report_payload.get('trigger_summary', [])))
    sections.append('')
    sections.append('---')
    sections.append(f'*由系统自动生成 · {report_payload.get("generated_at", "")}*')

    return '\n'.join(sections)


# ══════════════════════════════════════════════════════════════
# 新路径：消费 report_package（editorial_layer 产出）
# ══════════════════════════════════════════════════════════════

def _render_source_snapshot(pkg: dict) -> str:
    """渲染数据采集状态表"""
    snapshot = pkg.get('source_snapshot', [])
    ctx      = pkg.get('market_context', {})
    dedup    = ctx.get('dedup_stats', {})

    lines = ['## 数据采集状态', '']
    lines.append('| 来源 | 状态 | 条目数 |')
    lines.append('|------|------|--------|')

    main_ok = 0
    main_total = 0
    for s in snapshot:
        status = s.get('status', '❌')
        if s.get('is_main'):
            main_total += 1
            if status in ('✅', '⚠️'):
                main_ok += 1
        lines.append(f'| {s["name"]} | {status} | {s.get("item_count", 0)} 条 |')

    lines.append('')
    conf_map = {'normal': '正常', 'low': '低', 'none': '无数据', 'unknown': '未知'}
    conf_str = conf_map.get(ctx.get('confidence', 'unknown'), '未知')
    lines.append(f'主源成功（✅+⚠️）：{main_ok}/{main_total or 0}　置信度：{conf_str}')

    if dedup:
        orig = dedup.get('original_news', 0)
        after = dedup.get('after_dedup', 0)
        removed = dedup.get('removed', 0)
        lines.append(f'去重：{orig} → {after} 条（移除 {removed} 条重复）')

    return '\n'.join(lines)


def _render_market_context_pkg(pkg: dict) -> str:
    """渲染市场背景（A股指数和美股数据由 Python 自动填充）"""
    ctx    = pkg.get('market_context', {})
    meta   = pkg.get('meta', {})
    date   = meta.get('date', '')
    conf_map = {'normal': '正常（主要来源均有效）', 'low': '偏低（部分来源失效）',
                'none': '极低（主要来源均失效）', 'unknown': '未知'}
    conf_str          = conf_map.get(ctx.get('confidence', 'unknown'), '未知')
    last_trading_date = ctx.get('last_trading_date', '')
    us_market_date    = ctx.get('us_market_date', '')
    indices           = ctx.get('indices')    # dict | None
    us_markets        = ctx.get('us_markets') # list | None

    lines = ['## 市场背景', '']
    lines.append(f'- **扫描日期**：{date}')
    if last_trading_date:
        lines.append(f'- **A股上一交易日**：{last_trading_date}')
    if us_market_date:
        lines.append(f'- **隔夜美股日期**：{us_market_date}')
    lines.append(f'- **数据置信度**：{conf_str}')
    lines.append('')

    # A股指数
    lines.append('### A股指数')
    lines.append('')
    lines.append('| 指数 | 昨收 | 涨跌 |')
    lines.append('|------|------|------|')
    if indices:
        for name, v in indices.items():
            lines.append(f'| {name} | {v["price"]} | {v["change_pct"]} |')
    else:
        lines.append('| 上证指数 | — | — |')
        lines.append('| 深证成指 | — | — |')
        lines.append('| 创业板指 | — | — |')
        lines.append('')
        lines.append('> ⚠️ A股指数采集失败，请通过 WebSearch 补充')
    lines.append('')

    # 美股关键标的
    us_label = f'{us_market_date} ' if us_market_date else '隔夜'
    lines.append(f'### {us_label}美股关键标的')
    lines.append('')
    if us_markets:
        lines.append('| 标的 | 说明 | 收盘价 | 涨跌幅 |')
        lines.append('|------|------|--------|--------|')
        for item in us_markets:
            lines.append(
                f'| {item["symbol"]} | {item["name"]} '
                f'| {item["price"]} | {item["change_pct"]} |'
            )
    else:
        lines.append('> ⚠️ 美股数据采集失败，已略去')

    return '\n'.join(lines)


def _render_stock_candidates_table(candidates: list) -> str:
    """渲染个股候选表"""
    if not candidates:
        return '_（本次扫描未识别到个股候选）_'

    lines = []
    lines.append('| 名称 | 提及数 | 驱动 | 正宗度 | 正宗度依据 | 核心理由 |')
    lines.append('|------|--------|------|--------|-----------|---------|')
    for c in candidates:
        name     = c.get('name', '')
        cnt      = c.get('mention_count', 0)
        driver   = c.get('driver_display', '人气讨论')
        auth     = c.get('authenticity') or '—'
        evidence = c.get('authenticity_evidence') or '—'
        reason   = c.get('core_reason') or '—'
        lines.append(f'| {name} | {cnt} | {driver} | {auth} | {evidence} | {reason} |')
    return '\n'.join(lines)


def _render_top_sectors(pkg: dict) -> str:
    """渲染热点板块 Top N"""
    top_sectors = pkg.get('report_views', {}).get('top_sectors', [])
    if not top_sectors:
        return '## 🔥 热点板块\n\n_暂无明确主线，请参考分组全景。_'

    lines = ['## 🔥 热点板块 Top 3', '']

    for i, s in enumerate(top_sectors[:3], 1):
        name  = s.get('name', '')
        stars = _stars(s.get('star_rating', 1))
        hr    = s.get('hotrank')
        hr_str = f'，人气榜：#{hr["rank"]}' if hr else ''
        stage = s.get('stage', '-')
        cont  = s.get('continuation_score', '-')
        ferm  = s.get('fermentation_score', '-')
        grp   = s.get('group', '')

        lines.append(f'### #{i} {name}（热度：{stars}{hr_str}）')
        lines.append(f'> 分组：{grp} ｜ 阶段：{stage} ｜ 持续性：{cont} ｜ 发酵概率：{ferm}')
        lines.append('')

        # 个股候选表
        candidates = s.get('stock_candidates', [])
        lines.append(_render_stock_candidates_table(candidates))
        lines.append('')

    return '\n'.join(lines)


def _render_hidden_signals_pkg(pkg: dict) -> str:
    """渲染人气榜隐藏信号"""
    signals = pkg.get('report_views', {}).get('hidden_signals', [])
    if not signals:
        return ''

    lines = ['## ⚠️ 人气榜隐藏信号', '']
    lines.append('| 人气排名 | 人气榜板块 | 涨跌幅 | 说明 | 关注标的 |')
    lines.append('|---------|-----------|-------|------|--------|')
    for sig in signals:
        rank    = sig.get('rank', '?')
        hname   = sig.get('hotrank_name', '')
        chg     = sig.get('change_pct', '')
        summary = sig.get('websearch_summary') or '—'
        stocks  = sig.get('focus_stocks', '') or '—'
        lines.append(f'| #{rank} | {hname} | {chg} | {summary} | {stocks} |')
    return '\n'.join(lines)


def _render_groups_section(pkg: dict) -> str:
    """渲染分组全景"""
    groups = pkg.get('report_views', {}).get('groups', {})

    sections = ['## 分组全景', '']
    for group in GROUP_ORDER:
        renderer = _SECTOR_RENDERER[group]
        heading  = _GROUP_HEADING[group]
        intro    = _GROUP_INTRO[group]
        sectors  = groups.get(group, [])

        sections.append(heading)
        sections.append('')
        sections.append(f'> {intro}')
        sections.append('')

        if not sectors:
            sections.append('_当前无符合条件的板块。_')
        else:
            for s in sectors:
                sections.append(renderer(s))
                sections.append('')
        sections.append('')

    return '\n'.join(sections)


def _render_conclusion(pkg: dict) -> str:
    """渲染扫描结论"""
    rec     = pkg.get('report_views', {}).get('final_recommendations', {})
    primary = rec.get('primary_lines', [])
    cands   = rec.get('candidate_lines', [])
    text    = rec.get('conclusion_text')

    lines = ['## 扫描结论', '']
    if text:
        lines.append(text)
        lines.append('')
    if primary:
        lines.append(f'**今日主盯**：{"、".join(primary)}')
    if cands:
        lines.append(f'**发酵观察**：{"、".join(cands)}')
    return '\n'.join(lines)


def _completeness_issues(pkg: dict) -> list:
    """
    返回报告完成度不足的问题列表（空列表 = 完整）。
    检查项：
      - conclusion_text 是否已填
      - top_sectors 中各个股的 authenticity 是否已填
    """
    issues = []
    views = pkg.get('report_views', {})
    rec   = views.get('final_recommendations', {})
    if not rec.get('conclusion_text'):
        issues.append('扫描结论未生成')
    from editorial_layer.stock_merger import is_valid_candidate_name
    for s in views.get('top_sectors', []):
        invalids = [c.get('name', '') for c in s.get('stock_candidates', [])
                 if not is_valid_candidate_name(c.get('name', ''), c.get('code', ''))]
        if invalids:
            issues.append(f'{s["name"]} 存在非法个股名称：{"、".join(invalids)}')
        nulls = [c.get('name', '') for c in s.get('stock_candidates', [])
                 if c.get('authenticity') is None]
        if nulls:
            issues.append(f'{s["name"]} 个股正宗度未完成：{"、".join(nulls)}')
    return issues


def _render_reference_sources(pkg: dict) -> str:
    """渲染参考来源"""
    meta              = pkg.get('meta', {})
    ctx               = pkg.get('market_context', {})
    last_trading_date = ctx.get('last_trading_date', '') or meta.get('date', '')
    indices           = ctx.get('indices')
    us_markets        = ctx.get('us_markets')
    index_src  = 'akshare 自动采集' if indices    else 'Claude WebSearch 补充（akshare 采集失败）'
    us_src     = 'akshare 自动采集' if us_markets else 'Claude WebSearch 补充（akshare 采集失败）'
    return (
        '## 参考来源\n'
        '- 本地结构化结果：`raw_news.json`、`analysis_result.json`\n'
        f'- A股指数（{last_trading_date}）：{index_src}\n'
        f'- 美股关键标的：{us_src}'
    )


def build_markdown_from_package(pkg: dict) -> str:
    """
    新路径渲染函数：消费 report_package，输出老 v3 格式增强版 Markdown。
    比旧版新增：数据采集状态表 / 热点 Top3（含个股候选占位表）/ 隐藏信号表 / 结论 / 来源。
    """
    meta     = pkg.get('meta', {})
    date     = meta.get('date', '')
    gen_at   = meta.get('generated_at', '')
    time_str = gen_at[11:16] if len(gen_at) >= 16 else ''

    conf     = meta.get('confidence', 'unknown')
    issues   = _completeness_issues(pkg)
    sections = []

    # 标题（草稿标记）
    draft_tag = ' [草稿]' if issues else ''
    sections.append(f'# 早盘热点扫描 · {date}{draft_tag}')
    if time_str:
        sections.append(f'生成时间：{time_str}')
    sections.append('')

    # 完成度警告
    if issues:
        sections.append('> **[草稿]** 以下字段尚未完成，报告为草稿状态：')
        for iss in issues:
            sections.append(f'> - {iss}')
        sections.append('')

    # 置信度告警
    if conf == 'low':
        sections.append('> ⚠️ 仅 1 个主源成功，结果置信度低，仅供参考')
        sections.append('')
    elif conf == 'none':
        sections.append('> ❌ 数据采集失败，无法生成正式报告，以下为 WebSearch 观察项。')
        sections.append('')

    # 数据采集状态
    sections.append(_render_source_snapshot(pkg))
    sections.append('')

    # 市场背景
    sections.append(_render_market_context_pkg(pkg))
    sections.append('')
    sections.append('---')
    sections.append('')

    # 热点板块 Top 3
    sections.append(_render_top_sectors(pkg))
    sections.append('')
    sections.append('---')
    sections.append('')

    # 人气榜隐藏信号
    hidden = _render_hidden_signals_pkg(pkg)
    if hidden:
        sections.append(hidden)
        sections.append('')
        sections.append('---')
        sections.append('')

    # 分组全景（Python 草稿）
    sections.append(_render_groups_section(pkg))
    sections.append('')

    # 盘中验证点汇总
    trigger_summary = pkg.get('report_views', {}).get('trigger_summary', [])
    sections.append(_render_trigger_summary(trigger_summary))
    sections.append('')
    sections.append('---')
    sections.append('')

    # 扫描结论
    sections.append(_render_conclusion(pkg))
    sections.append('')
    sections.append('---')
    sections.append('')

    # 参考来源
    sections.append(_render_reference_sources(pkg))
    sections.append('')
    sections.append('---')
    sections.append(f'*由系统自动生成 · {gen_at}*')

    return '\n'.join(sections)


def build_brief_markdown(pkg: dict) -> str:
    """
    简报摘要：一页快速预览，含核心方向表 + 隐藏信号 + 结论要点。
    供 pipeline handoff 后快速预览使用。
    """
    meta    = pkg.get('meta', {})
    date    = meta.get('date', '')
    views   = pkg.get('report_views', {})
    top     = views.get('top_sectors', [])
    hidden  = views.get('hidden_signals', [])
    rec     = views.get('final_recommendations', {})

    issues    = _completeness_issues(pkg)
    draft_tag = ' [草稿]' if issues else ''
    lines = [f'# 早盘扫描简报 · {date}{draft_tag}', '']

    # 核心方向表
    lines.append('## 核心方向')
    lines.append('')
    lines.append('| # | 板块 | 热度 | 阶段 | 持续性 | 发酵概率 | 分组 |')
    lines.append('|---|------|------|------|--------|---------|------|')
    for i, s in enumerate(top, 1):
        name  = s.get('name', '')
        stars = _stars(s.get('star_rating', 1))
        stage = s.get('stage', '-')
        cont  = s.get('continuation_score', '-')
        ferm  = s.get('fermentation_score', '-')
        grp   = s.get('group', '-')
        lines.append(f'| {i} | {name} | {stars} | {stage} | {cont} | {ferm} | {grp} |')

    lines.append('')

    # 人气榜隐藏信号
    if hidden:
        lines.append('## 人气榜隐藏信号')
        lines.append('')
        lines.append('| 排名 | 板块 | 涨幅 |')
        lines.append('|------|------|------|')
        for sig in hidden:
            lines.append(
                f'| #{sig.get("rank", "?")} | {sig.get("hotrank_name", "")} | {sig.get("change_pct", "")} |'
            )
        lines.append('')

    # 结论要点（优先使用 agent 生成的 conclusion_text）
    lines.append('## 结论要点')
    lines.append('')
    conclusion = rec.get('conclusion_text')
    primary    = rec.get('primary_lines', [])
    cands      = rec.get('candidate_lines', [])
    if conclusion:
        lines.append(conclusion)
        lines.append('')
    if primary:
        lines.append(f'**今日主盯**：{"、".join(primary)}')
    if cands:
        lines.append(f'**发酵观察**：{"、".join(cands)}')

    lines.append('')
    lines.append(f'*简报 · {meta.get("generated_at", "")}*')

    return '\n'.join(lines)
