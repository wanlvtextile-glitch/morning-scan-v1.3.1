import uuid
from datetime import datetime


class ScanState:
    """
    Shared state for the agent layer.

    preprocess:
      - processed_items
      - logic_units
      - signal_stats
      - dedup_decisions

    analysis:
      - sectors
      - hotrank
      - hotrank_signals
      - scoring_stats

    editorial:
      - all sectors after editorial grouping / stock merge
      - hidden signals
      - final recommendations
    """

    def __init__(self, meta, preprocess, analysis, editorial, pending):
        self.meta = meta
        self.preprocess = preprocess
        self.analysis = analysis
        self.editorial = editorial
        self.pending = pending

    def get_logic_unit(self, unit_key: str) -> dict:
        return self.preprocess.get('logic_unit_map', {}).get(unit_key, {})

    def get_sector_logic_units(
        self,
        sector_name: str,
        max_n: int = 8,
        fields: list = None,
    ) -> list:
        sector = self.get_analysis_sector(sector_name)
        core_units = sector.get('core_logic_units', []) if sector else []
        result = []

        for core in core_units[:max_n]:
            unit_key = core.get('unit_key', '')
            unit = self.get_logic_unit(unit_key) or core
            if fields:
                result.append(_project_logic_unit(unit, fields))
            else:
                result.append(_project_logic_unit(unit, None))
        return result

    def get_preprocess_signal_stats(self) -> dict:
        return self.preprocess.get('signal_stats', {})

    def get_analysis_sector(self, sector_name: str) -> dict:
        for s in self.analysis.get('sectors', []):
            if s.get('name') == sector_name:
                return s
        return {}

    def get_editorial_sector(self, sector_idx: int) -> dict:
        sectors = self.editorial.get('all_sectors', [])
        if 0 <= sector_idx < len(sectors):
            return sectors[sector_idx]
        return {}

    def get_hidden_signal(self, hotrank_idx: int) -> dict:
        signals = self.editorial.get('hidden_signals', [])
        if 0 <= hotrank_idx < len(signals):
            return signals[hotrank_idx]
        return {}


def assemble_state(
    analysis_result: dict,
    editorial_result: dict,
    processed_items: list,
    logic_units: list | None = None,
    signal_stats: dict | None = None,
    dedup_decisions: list | None = None,
) -> ScanState:
    for sig in editorial_result.get('hidden_signals', []):
        sig.setdefault('focus_stocks', None)

    for sector in editorial_result.get('all_sectors', []):
        sector.setdefault('agent_review', None)

    pending = _build_pending(editorial_result)

    meta = {
        'run_id': str(uuid.uuid4()),
        'scan_date': analysis_result.get('generated_at', '')[:10] or 'unknown',
        'generated_at': datetime.now().isoformat(),
        'version': '1.3',
        'confidence': analysis_result.get('confidence', 'unknown'),
        'agent_enabled': None,
        'agent_calls_made': 0,
        'agent_duration_sec': 0,
    }

    logic_units = logic_units or []
    signal_stats = signal_stats or {}
    dedup_decisions = dedup_decisions or []

    preprocess_state = {
        'time_window_start': analysis_result.get('time_window_start', ''),
        'dedup_stats': analysis_result.get('dedup_stats', {}),
        'source_stats': analysis_result.get('source_stats', []),
        'processed_items': processed_items,
        'logic_units': logic_units,
        'logic_unit_map': {
            unit.get('unit_key', ''): unit
            for unit in logic_units
            if unit.get('unit_key')
        },
        'signal_stats': signal_stats,
        'dedup_decisions': dedup_decisions,
    }

    analysis_state = {
        'sectors': analysis_result.get('sectors', []),
        'hotrank': analysis_result.get('hotrank', []),
        'hotrank_signals': analysis_result.get('hotrank_signals', []),
        'scoring_stats': analysis_result.get('scoring_stats', {}),
    }

    return ScanState(
        meta=meta,
        preprocess=preprocess_state,
        analysis=analysis_state,
        editorial=editorial_result,
        pending=pending,
    )


_AGENT_TARGET_GROUPS = ('已知强势主线', '次日发酵候选')


def _build_pending(editorial_result: dict) -> dict:
    hotrank_tasks = []
    supplement_tasks = []
    review_tasks = []
    auth_tasks = []

    for idx, sig in enumerate(editorial_result.get('hidden_signals', [])):
        if sig.get('signal_type') == 'hotrank_only':
            hotrank_tasks.append({
                'hotrank_idx': idx,
                'rank': sig.get('rank', 0),
                'hotrank_name': sig.get('hotrank_name', ''),
                'change_pct': sig.get('change_pct', ''),
            })

    for idx, sector in enumerate(editorial_result.get('all_sectors', [])):
        group = sector.get('group', '')
        star_rating = sector.get('star_rating', 0)
        sector_name = sector.get('name', '')
        stage = sector.get('stage', '')
        cont = sector.get('continuation_score', '')
        stage_sigs = sector.get('stage_signals', [])

        if group in _AGENT_TARGET_GROUPS:
            supplement_tasks.append({
                'sector_idx': idx,
                'sector_name': sector_name,
                'group': group,
            })

        if star_rating >= 3 or group in _AGENT_TARGET_GROUPS:
            review_tasks.append({
                'sector_idx': idx,
                'sector_name': sector_name,
                'group': group,
                'python_stage': stage,
                'python_group': group,
                'python_continuation_score': cont,
                'stage_signals': stage_sigs,
            })

        candidates = sector.get('stock_candidates', [])
        pending_auth = [c for c in candidates if c.get('authenticity') is None]
        if group in _AGENT_TARGET_GROUPS and pending_auth:
            auth_tasks.append({
                'sector_idx': idx,
                'sector_name': sector_name,
                'group': group,
                'candidate_count': len(pending_auth),
            })

    conclusion_needed = (
        editorial_result.get('final_recommendations', {}).get('conclusion_text') is None
    )

    return {
        'hotrank_tasks': hotrank_tasks,
        'supplement_tasks': supplement_tasks,
        'review_tasks': review_tasks,
        'auth_tasks': auth_tasks,
        'conclusion_needed': conclusion_needed,
    }


def _project_logic_unit(unit: dict, fields: list | None) -> dict:
    stock_branches = [
        {
            'stock_name': branch.get('stock_name', ''),
            'stock_code': branch.get('stock_code', ''),
            'branch_reason': branch.get('branch_reason', ''),
            'recap_count': branch.get('recap_count', 0),
            'catalyst_count': branch.get('catalyst_count', 0),
            'dominant_signal': branch.get('dominant_signal', 'neutral'),
        }
        for branch in unit.get('stock_branches', [])[:6]
    ]

    projected = {
        'unit_key': unit.get('unit_key', ''),
        'unit_type': unit.get('unit_type', 'single'),
        'title': unit.get('title', ''),
        'summary': unit.get('summary', ''),
        'dominant_signal': unit.get('dominant_signal', 'neutral'),
        'signal_confidence': unit.get('signal_confidence', 'low'),
        'related_symbols_or_sectors': unit.get('related_symbols_or_sectors', []),
        'stock_branches': stock_branches,
        'recap_count': unit.get('recap_count', 0),
        'catalyst_count': unit.get('catalyst_count', 0),
        'catalyst_type_dist': unit.get('catalyst_type_dist', {}),
        'decision_reason': unit.get('decision_reason', ''),
    }
    if fields is None:
        return projected
    return {k: projected.get(k) for k in fields}
