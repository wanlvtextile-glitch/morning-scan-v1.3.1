import unittest

from analysis.entry import run_analysis_pipeline


class AnalysisRegressionTest(unittest.TestCase):
    def test_analysis_pipeline_outputs_logic_unit_fields_only(self):
        sector_result = {
            'sector_weighted': {
                'Semi': [
                    {
                        'title': 'Supplier order expands',
                        'content': 'Semi supply chain keeps getting stronger.',
                        'content_preview': 'Semi supply chain keeps getting stronger.',
                        'source': 'source-a',
                        'heat': 9,
                        '_weight': 1.0,
                        '_exclusive': True,
                        'catalyst_type': 'product',
                        'is_recap': False,
                        'url': 'https://example.com/1',
                        'published_at': '2026-05-12T08:00:00+08:00',
                        'unit_key': 'theme::Semi',
                    },
                    {
                        'title': 'Capital follows the theme',
                        'content': 'Capital keeps validating the same sector logic.',
                        'content_preview': 'Capital keeps validating the same sector logic.',
                        'source': 'source-b',
                        'heat': 7,
                        '_weight': 1.0,
                        '_exclusive': True,
                        'catalyst_type': 'capital',
                        'is_recap': False,
                        'url': 'https://example.com/2',
                        'published_at': '2026-05-12T08:10:00+08:00',
                        'unit_key': 'theme::Semi',
                    },
                ]
            },
            'sector_matched_kws': {'Semi': ['supplier', 'capital']},
            'sector_to_hotrank': {},
            'hotrank_list': [],
            'unmatched': [],
        }

        logic_units = [
            {
                'unit_key': 'theme::Semi',
                'unit_type': 'theme_cluster',
                'title': 'Semi core theme',
                'summary': 'Semi logic extends through supplier branches.',
                'dominant_signal': 'catalyst_only',
                'signal_confidence': 'high',
                'related_symbols_or_sectors': ['Semi'],
                'stock_branches': [
                    {
                        'stock_name': 'Supplier A',
                        'stock_code': '',
                        'branch_reason': 'Direct beneficiary of the supplier theme.',
                        'recap_count': 0,
                        'catalyst_count': 2,
                        'dominant_signal': 'catalyst_only',
                    }
                ],
                'recap_count': 0,
                'catalyst_count': 2,
                'catalyst_type_dist': {'product': 2},
                'decision_reason': 'same theme cluster',
            }
        ]

        result = run_analysis_pipeline(
            sector_result=sector_result,
            dedup_stats={'original_news': 2, 'after_dedup': 2, 'removed': 0},
            confidence='normal',
            source_stats=[{'name': 'source-a', 'fetch_success': True, 'item_count': 1}],
            preprocess_context={
                'logic_units': logic_units,
                'signal_stats': {'theme_cluster_count': 1},
                'dedup_decisions': [{'original_id': 'pp-000001', 'decision_type': 'keep'}],
            },
        )

        self.assertIn('source_stats', result)
        self.assertIn('dedup_stats', result)
        self.assertIn('preprocess_signal_stats', result)
        self.assertIn('dedup_decisions', result)
        self.assertEqual(result['preprocess_signal_stats']['theme_cluster_count'], 1)
        self.assertEqual(len(result['dedup_decisions']), 1)

        sector = result['sectors'][0]
        self.assertNotIn('top_items', sector)
        self.assertNotIn('stock_mentions', sector)
        self.assertIn('logic_unit_count', sector)
        self.assertIn('core_logic_units', sector)
        self.assertEqual(sector['logic_unit_count'], 1)
        self.assertEqual(sector['core_logic_units'][0]['unit_key'], 'theme::Semi')
        self.assertEqual(sector['core_logic_units'][0]['stock_branches'][0]['stock_name'], 'Supplier A')


if __name__ == '__main__':
    unittest.main()
