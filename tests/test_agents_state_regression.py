import unittest

from agents.state import assemble_state


class AgentsStateRegressionTest(unittest.TestCase):
    def test_state_exposes_logic_units_only(self):
        analysis_result = {
            'generated_at': '2026-05-12T09:00:00+08:00',
            'confidence': 'normal',
            'dedup_stats': {'original_news': 2, 'after_dedup': 2, 'removed': 0},
            'source_stats': [{'name': 'source-a', 'fetch_success': True, 'item_count': 2}],
            'sectors': [
                {
                    'name': 'Semi',
                    'star_rating': 4,
                    'stage': '发酵中',
                    'continuation_score': '高',
                    'core_logic_units': [
                        {
                            'unit_key': 'theme::Semi',
                            'unit_type': 'theme_cluster',
                            'title': 'Semi core theme',
                            'summary': 'Theme keeps extending through supplier branches.',
                            'dominant_signal': 'catalyst_only',
                            'signal_confidence': 'high',
                        }
                    ],
                }
            ],
            'hotrank': [],
            'hotrank_signals': [],
            'scoring_stats': {},
        }
        editorial_result = {
            'hidden_signals': [],
            'all_sectors': [
                {
                    'name': 'Semi',
                    'group': '已知强势主线',
                    'star_rating': 4,
                    'stage': '发酵中',
                    'continuation_score': '高',
                    'stage_signals': [],
                    'stock_candidates': [],
                }
            ],
            'final_recommendations': {'conclusion_text': None},
        }
        processed_items = [
            {'title': 'Supplier order expands', 'heat': 9, 'is_recap': False, 'source': 'source-a'}
        ]
        logic_units = [
            {
                'unit_key': 'theme::Semi',
                'unit_type': 'theme_cluster',
                'title': 'Semi core theme',
                'summary': 'Theme keeps extending through supplier branches.',
                'dominant_signal': 'catalyst_only',
                'signal_confidence': 'high',
                'related_symbols_or_sectors': ['Semi'],
                'stock_branches': [
                    {
                        'stock_name': 'Supplier A',
                        'stock_code': '',
                        'branch_reason': 'Order growth is directly tied to the theme.',
                        'recap_count': 0,
                        'catalyst_count': 1,
                        'dominant_signal': 'catalyst_only',
                    }
                ],
                'recap_count': 0,
                'catalyst_count': 2,
                'catalyst_type_dist': {'product': 2},
                'decision_reason': 'same theme',
            }
        ]

        state = assemble_state(
            analysis_result=analysis_result,
            editorial_result=editorial_result,
            processed_items=processed_items,
            logic_units=logic_units,
            signal_stats={'theme_cluster_count': 1},
            dedup_decisions=[{'original_id': 'pp-1', 'decision_type': 'keep'}],
        )

        self.assertNotIn('fallback_sector_item_map', state.preprocess)
        self.assertNotIn('sector_item_map', state.preprocess)

        new_units = state.get_sector_logic_units('Semi', max_n=5)
        self.assertEqual(new_units[0]['unit_key'], 'theme::Semi')
        self.assertEqual(new_units[0]['stock_branches'][0]['stock_name'], 'Supplier A')
        self.assertNotIn('items', new_units[0])

        self.assertEqual(state.get_preprocess_signal_stats()['theme_cluster_count'], 1)
        self.assertTrue(state.pending['conclusion_needed'])


if __name__ == '__main__':
    unittest.main()
