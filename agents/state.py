# agent_layer/state.py
# ScanState：统一数据契约
#   .meta        运行元信息（只读）
#   .preprocess  预处理文本池（只读）——含 processed_items + sector_item_map
#   .analysis    分析层结果（只读）
#   .editorial   编辑层结果（agent 写入 pending 字段）= editorial_result 原地引用
#   .pending     待补全任务队列（只读索引，agent 直接迭代）
#
# assemble_state(analysis_result, editorial_result, processed_items, sector_item_map)
#   → ScanState
# 被谁调用：agent_layer/entry.py

import uuid
from datetime import datetime


# ══════════════════════════════════════════════════════════
# ScanState
# ══════════════════════════════════════════════════════════

class ScanState:
    """
    统一 state 容器。

    不变量：
      1. analysis / preprocess 所有字段 agent 不得写入
      2. editorial 中已有判断字段（stage/group/scores）agent 不得修改
      3. output_layer 只消费 state.editorial，不接触 analysis/preprocess
    """

    def __init__(self, meta, preprocess, analysis, editorial, pending):
        self.meta       = meta        # dict
        self.preprocess = preprocess  # dict
        self.analysis   = analysis    # dict
        self.editorial  = editorial   # dict（editorial_result 原地引用）
        self.pending    = pending     # dict

    # ── 上下文提取 API ────────────────────────────────────

    def get_sector_items(
        self,
        sector_name: str,
        max_n: int = 20,
        fields: list = None,
        exclude_recap: bool = False,
    ) -> list:
        """
        从 preprocess.sector_item_map 取指定板块的全量 items，
        按 heat 降序，最多 max_n 条，只返回 fields 指定字段。

        Agent 调用示例：
            items = state.get_sector_items(
                '半导体', max_n=15,
                fields=['title', 'content_preview', 'source', 'is_recap'],
                exclude_recap=True,
            )
        """
        items = self.preprocess.get('sector_item_map', {}).get(sector_name, [])
        if exclude_recap:
            items = [x for x in items if not x.get('is_recap')]
        items_sorted = sorted(items, key=lambda x: x.get('heat', 0), reverse=True)[:max_n]
        if fields:
            return [{k: item.get(k) for k in fields} for item in items_sorted]
        return items_sorted

    def get_analysis_sector(self, sector_name: str) -> dict:
        """从 analysis.sectors 按名称查找板块（只读）。"""
        for s in self.analysis.get('sectors', []):
            if s.get('name') == sector_name:
                return s
        return {}

    def get_editorial_sector(self, sector_idx: int) -> dict:
        """从 editorial.all_sectors 按索引取板块（agent 写入目标）。"""
        sectors = self.editorial.get('all_sectors', [])
        if 0 <= sector_idx < len(sectors):
            return sectors[sector_idx]
        return {}

    def get_hidden_signal(self, hotrank_idx: int) -> dict:
        """从 editorial.hidden_signals 按索引取信号（agent 写入目标）。"""
        signals = self.editorial.get('hidden_signals', [])
        if 0 <= hotrank_idx < len(signals):
            return signals[hotrank_idx]
        return {}


# ══════════════════════════════════════════════════════════
# assemble_state
# ══════════════════════════════════════════════════════════

def assemble_state(
    analysis_result: dict,
    editorial_result: dict,
    processed_items: list,
    sector_item_map: dict,
) -> ScanState:
    """
    将各层结果组装为 ScanState。

    editorial_result 是原地引用（不复制）：
      - assemble_state 会在 editorial_result 中 setdefault 新增 pending 字段
      - agent 对 editorial_result 的写入对 state.editorial 立即可见
    """
    # ── 1. 在 editorial_result 中初始化所有 pending 字段 ──
    for sig in editorial_result.get('hidden_signals', []):
        sig.setdefault('focus_stocks', None)          # Node 4 写入

    for sector in editorial_result.get('all_sectors', []):
        sector.setdefault('agent_review', None)       # Node 8 写入

    # final_recommendations.conclusion_text 已在 build_final_recommendations 中初始化为 None

    # ── 2. 构建 pending 任务队列 ──────────────────────────
    pending = _build_pending(editorial_result)

    # ── 3. 构建各层 ───────────────────────────────────────
    meta = {
        'run_id':       str(uuid.uuid4()),
        'scan_date':    analysis_result.get('generated_at', '')[:10] or 'unknown',
        'generated_at': datetime.now().isoformat(),
        'version':      '1.3',
        'confidence':   analysis_result.get('confidence', 'unknown'),
        'agent_enabled':        None,   # 运行后由 entry.py 填写
        'agent_calls_made':     0,
        'agent_duration_sec':   0,
    }

    preprocess_state = {
        'time_window_start': analysis_result.get('time_window_start', ''),
        'dedup_stats':       analysis_result.get('dedup_stats', {}),
        'source_stats':      analysis_result.get('source_stats', []),
        'processed_items':   processed_items,    # 全量预处理条目
        'sector_item_map':   sector_item_map,    # sector_name → items
    }

    analysis_state = {
        'sectors':         analysis_result.get('sectors', []),
        'hotrank':         analysis_result.get('hotrank', []),
        'hotrank_signals': analysis_result.get('hotrank_signals', []),
        'scoring_stats':   analysis_result.get('scoring_stats', {}),
    }

    return ScanState(
        meta=meta,
        preprocess=preprocess_state,
        analysis=analysis_state,
        editorial=editorial_result,   # 原地引用
        pending=pending,
    )


# ══════════════════════════════════════════════════════════
# 内部：构建 pending 任务队列
# ══════════════════════════════════════════════════════════

_AGENT_TARGET_GROUPS = ('已知强势主线', '次日发酵候选')


def _build_pending(editorial_result: dict) -> dict:
    """
    扫描 editorial_result 中的 None 字段，生成任务队列。
    agent 直接迭代这些队列，不自己扫描 state。
    """
    hotrank_tasks    = []
    supplement_tasks = []
    review_tasks     = []
    auth_tasks       = []

    # hotrank 任务（Node 3+4）
    for idx, sig in enumerate(editorial_result.get('hidden_signals', [])):
        if sig.get('signal_type') == 'hotrank_only':
            hotrank_tasks.append({
                'hotrank_idx': idx,
                'rank':        sig.get('rank', 0),
                'hotrank_name': sig.get('hotrank_name', ''),
                'change_pct':  sig.get('change_pct', ''),
            })

    # 板块任务（Node 8、9、5）
    for idx, sector in enumerate(editorial_result.get('all_sectors', [])):
        group       = sector.get('group', '')
        star_rating = sector.get('star_rating', 0)
        sector_name = sector.get('name', '')
        stage       = sector.get('stage', '')
        cont        = sector.get('continuation_score', '')
        stage_sigs  = sector.get('stage_signals', [])

        # 补股任务：强/发酵板块（Node 9）
        if group in _AGENT_TARGET_GROUPS:
            supplement_tasks.append({
                'sector_idx':  idx,
                'sector_name': sector_name,
                'group':       group,
            })

        # 审核任务：star>=3 或强/发酵板块（Node 8）
        if star_rating >= 3 or group in _AGENT_TARGET_GROUPS:
            review_tasks.append({
                'sector_idx':              idx,
                'sector_name':             sector_name,
                'group':                   group,
                'python_stage':            stage,
                'python_group':            group,
                'python_continuation_score': cont,
                'stage_signals':           stage_sigs,
            })

        # 正宗度任务：强/发酵板块且有候选股待判断（Node 5）
        candidates = sector.get('stock_candidates', [])
        pending_auth = [c for c in candidates if c.get('authenticity') is None]
        if group in _AGENT_TARGET_GROUPS and pending_auth:
            auth_tasks.append({
                'sector_idx':    idx,
                'sector_name':   sector_name,
                'group':         group,
                'candidate_count': len(pending_auth),
            })

    # 结论任务（Node 7）
    conclusion_needed = (
        editorial_result.get('final_recommendations', {}).get('conclusion_text') is None
    )

    return {
        'hotrank_tasks':    hotrank_tasks,
        'supplement_tasks': supplement_tasks,
        'review_tasks':     review_tasks,
        'auth_tasks':       auth_tasks,
        'conclusion_needed': conclusion_needed,
    }
