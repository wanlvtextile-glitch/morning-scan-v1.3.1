# agents/impl/info_enrichment.py
# InfoEnrichmentAgent：Node 3（hotrank_summary）+ Node 4（hotrank_stocks）+ Node 9（stock_supplement）
# 职责：信息填充——为 hotrank 生成背景摘要和关注个股，为主线板块补充遗漏个股

import json

from agents.base import BaseAgent
from agents.interface import ScanAgentInterface


class InfoEnrichmentAgent(BaseAgent, ScanAgentInterface):

    def enrich(self, state) -> None:
        agent_cfg = self._config.agents.get('info_enrichment', {})
        if not agent_cfg.get('enabled', True):
            return

        nodes      = agent_cfg.get('nodes', {})
        hs_enabled = nodes.get('hotrank_summary',  {}).get('enabled', True)
        hk_enabled = nodes.get('hotrank_stocks',   {}).get('enabled', True)
        sp_enabled = nodes.get('stock_supplement', {}).get('enabled', True)
        sp_max     = nodes.get('stock_supplement', {}).get('max_sectors', 5)
        max_calls  = self._config.cost_control.get('max_llm_calls_per_run', 40)

        # ── Node 3 + 4：hotrank 摘要 + 关注个股 ────────────────
        for task in state.pending.get('hotrank_tasks', []):
            if self.call_count >= max_calls:
                break

            sig = state.get_hidden_signal(task['hotrank_idx'])
            if sig is None:
                continue

            summary = None
            if hs_enabled:
                summary = self._node3_hotrank_summary(task, state)
                if summary:
                    sig['websearch_summary'] = summary

            if hk_enabled and self.call_count < max_calls:
                stocks = self._node4_hotrank_stocks(task, summary or '')
                if stocks:
                    sig['focus_stocks'] = stocks

        # ── Node 9：补股 ────────────────────────────────────────
        if not sp_enabled:
            return

        for task in list(state.pending.get('supplement_tasks', []))[:sp_max]:
            if self.call_count >= max_calls:
                break

            sector = state.get_editorial_sector(task['sector_idx'])
            if sector is None:
                continue

            existing = [c.get('name', '') for c in sector.get('stock_candidates', [])]
            new_candidates = self._node9_supplement(task, state, existing)
            if new_candidates:
                sector['stock_candidates'].extend(new_candidates)

    # ── Node 3 ──────────────────────────────────────────────────

    def _node3_hotrank_summary(self, task: dict, state) -> str | None:
        prompt = self._load_prompt('hotrank_summary.txt')
        ctx = {
            'sector_name': task['hotrank_name'],
            'rank':        task['rank'],
            'change_pct':  task['change_pct'],
            'scan_date':   state.meta.get('scan_date', ''),
        }
        messages = [
            {'role': 'system', 'content': prompt},
            {'role': 'user',   'content': json.dumps(ctx, ensure_ascii=False)},
        ]
        text = self._call_llm(messages)
        if not text:
            return None
        data = self._parse_json(text)
        if isinstance(data, dict):
            return data.get('summary')
        return None

    # ── Node 4 ──────────────────────────────────────────────────

    def _node4_hotrank_stocks(self, task: dict, summary: str) -> str | None:
        prompt = self._load_prompt('hotrank_stocks.txt')
        ctx = {
            'sector_name': task['hotrank_name'],
            'background':  summary or '',
        }
        messages = [
            {'role': 'system', 'content': prompt},
            {'role': 'user',   'content': json.dumps(ctx, ensure_ascii=False)},
        ]
        text = self._call_llm(messages)
        if not text:
            return None
        data = self._parse_json(text)
        if isinstance(data, dict):
            return data.get('focus_stocks')
        return None

    # ── Node 9 ──────────────────────────────────────────────────

    def _node9_supplement(self, task: dict, state, existing_names: list) -> list:
        prompt = self._load_prompt('stock_supplement.txt')

        max_items = self._config.node_cfg('info_enrichment', 'stock_supplement').get('max_items', 15)
        items = state.get_sector_items(
            task['sector_name'],
            max_n=max_items,
            fields=['title', 'content_preview'],
            exclude_recap=True,
        )
        ctx = {
            'sector_name':     task['sector_name'],
            'group':           task['group'],
            'existing_stocks': existing_names,
            'top_items':       items,
        }
        messages = [
            {'role': 'system', 'content': prompt},
            {'role': 'user',   'content': json.dumps(ctx, ensure_ascii=False)},
        ]
        text = self._call_llm(messages)
        if not text:
            return []
        data = self._parse_json(text)
        if not isinstance(data, dict):
            return []

        raw = data.get('new_candidates', [])
        if not isinstance(raw, list):
            return []

        result = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = item.get('name', '').strip()
            if not name or name in existing_names:
                continue
            result.append({
                'code':                  item.get('code', ''),
                'name':                  name,
                'mention_count':         1,
                'heat_sum':              0,
                'sources':               [],
                'sample_context':        item.get('reason', ''),
                'match_type':            'agent_supplement',
                'catalyst_types':        [],
                'driver_display':        item.get('driver', '人气讨论'),
                'authenticity':          None,
                'authenticity_evidence': None,
                'core_reason':           None,
                'source_summary':        None,
                'source':                'agent_supplement',
            })
        return result
