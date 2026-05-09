# agents/impl/semantic_judgment.py
# SemanticJudgmentAgent：Node 8（review）+ Node 5（stock_auth）+ Node 7（conclusion）
# 职责：语义判断——审核 Python 判断、判断正宗度、生成综合结论

import json

from agents.base import BaseAgent
from agents.interface import ScanAgentInterface


class SemanticJudgmentAgent(BaseAgent, ScanAgentInterface):

    def enrich(self, state) -> None:
        agent_cfg = self._config.agents.get('semantic_judgment', {})
        if not agent_cfg.get('enabled', True):
            return

        nodes      = agent_cfg.get('nodes', {})
        rv_enabled = nodes.get('review',     {}).get('enabled', True)
        at_enabled = nodes.get('stock_auth', {}).get('enabled', True)
        cl_enabled = nodes.get('conclusion', {}).get('enabled', True)
        rv_max     = nodes.get('review',     {}).get('max_items', 8)
        at_max     = nodes.get('stock_auth', {}).get('max_sectors', 5)
        max_calls  = self._config.cost_control.get('max_llm_calls_per_run', 40)

        # ── Node 8：板块审核 ──────────────────────────────────
        if rv_enabled:
            for task in list(state.pending.get('review_tasks', []))[:rv_max]:
                if self.call_count >= max_calls:
                    break
                sector = state.get_editorial_sector(task['sector_idx'])
                if sector is None:
                    continue
                review = self._node8_review(task, state)
                if review:
                    sector['agent_review'] = review

        # ── Node 5：正宗度判断 ────────────────────────────────
        if at_enabled:
            for task in list(state.pending.get('auth_tasks', []))[:at_max]:
                if self.call_count >= max_calls:
                    break
                sector = state.get_editorial_sector(task['sector_idx'])
                if sector is None:
                    continue
                results = self._node5_auth(task, sector)
                if not results:
                    continue
                for r in results:
                    if not isinstance(r, dict):
                        continue
                    for c in sector.get('stock_candidates', []):
                        if c.get('authenticity') is not None:
                            continue
                        name_match = c.get('name') == r.get('name')
                        code_match = c.get('code') and c.get('code') == r.get('code')
                        if name_match or code_match:
                            c['authenticity']          = r.get('authenticity')
                            c['authenticity_evidence'] = r.get('authenticity_evidence')
                            c['core_reason']           = r.get('core_reason')
                            break

        # ── Node 7：综合结论 ──────────────────────────────────
        if (cl_enabled
                and state.pending.get('conclusion_needed')
                and self.call_count < max_calls):
            conclusion = self._node7_conclusion(state)
            if conclusion:
                state.editorial['final_recommendations']['conclusion_text'] = conclusion

    # ── Node 8 ──────────────────────────────────────────────────

    def _node8_review(self, task: dict, state) -> dict | None:
        prompt    = self._load_prompt('review.txt')
        max_items = self._config.node_cfg('semantic_judgment', 'review').get('max_items', 8)

        items = state.get_sector_items(
            task['sector_name'],
            max_n=max_items,
            fields=['title', 'content_preview', 'source', 'is_recap'],
        )
        ctx = {
            'sector_name':               task['sector_name'],
            'python_stage':              task.get('python_stage', ''),
            'python_group':              task.get('python_group', ''),
            'python_continuation_score': task.get('python_continuation_score', ''),
            'stage_signals':             task.get('stage_signals', []),
            'top_items':                 items,
        }
        messages = [
            {'role': 'system', 'content': prompt},
            {'role': 'user',   'content': json.dumps(ctx, ensure_ascii=False)},
        ]
        text = self._call_llm(messages)
        if not text:
            return None
        data = self._parse_json(text)
        if isinstance(data, dict) and 'note' in data:
            return {
                'note':       str(data.get('note', '')),
                'confidence': str(data.get('confidence', 'low')),
            }
        return None

    # ── Node 5 ──────────────────────────────────────────────────

    def _node5_auth(self, task: dict, sector: dict) -> list | None:
        prompt = self._load_prompt('stock_auth.txt')
        candidates = [
            {
                'code':           c.get('code', ''),
                'name':           c.get('name', ''),
                'sample_context': c.get('sample_context', '')[:200],
            }
            for c in sector.get('stock_candidates', [])
            if c.get('authenticity') is None
        ]
        if not candidates:
            return None
        ctx = {
            'sector_name': task['sector_name'],
            'group':       task['group'],
            'candidates':  candidates,
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
            return data.get('results', [])
        if isinstance(data, list):
            return data
        return None

    # ── Node 7 ──────────────────────────────────────────────────

    def _node7_conclusion(self, state) -> str | None:
        prompt    = self._load_prompt('conclusion.txt')
        editorial = state.editorial

        top_sectors = [
            {
                'name':               s.get('name'),
                'stage':              s.get('stage'),
                'group':              s.get('group'),
                'star_rating':        s.get('star_rating'),
                'continuation_score': s.get('continuation_score'),
                'fermentation_score': s.get('fermentation_score'),
            }
            for s in editorial.get('all_sectors', [])
            if s.get('star_rating', 0) >= 3
        ][:5]

        mc        = editorial.get('market_context', {})
        a_indices = mc.get('a_indices', [])
        us_mkts   = mc.get('us_markets', []) or []
        a_brief   = '、'.join(
            f"{x.get('name')} {x.get('price')} {x.get('change_pct', '')}"
            for x in (a_indices or []) if isinstance(x, dict)
        )
        us_brief  = '、'.join(
            f"{x.get('name')} {x.get('change_pct', '')}"
            for x in us_mkts if isinstance(x, dict)
        )

        recs = editorial.get('final_recommendations', {})
        ctx  = {
            'scan_date':       state.meta.get('scan_date', ''),
            'top_sectors':     top_sectors,
            'market_brief':    {'a_indices': a_brief, 'us_brief': us_brief},
            'primary_lines':   recs.get('primary_lines', []),
            'candidate_lines': recs.get('candidate_lines', []),
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
            return data.get('conclusion_text')
        return None
