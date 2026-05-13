import unittest

from analysis.entry import build_sector_summaries


class AnalysisSectorIsolationRegressionTest(unittest.TestCase):
    def test_theme_logic_units_are_isolated_to_their_own_sector(self):
        shared_item = {
            'title': 'Liquid cooling and compute theme',
            'content': 'Shared content',
            'content_preview': 'Shared content',
            'source': 'source-a',
            'heat': 10,
            '_weight': 0.5,
            '_exclusive': False,
            'catalyst_type': 'product',
            'is_recap': False,
            'url': 'https://example.com/shared',
            'published_at': '2026-05-13T08:00:00+08:00',
            'unit_key': 'theme::AI算力',
        }
        semi_item = {
            'title': 'Semiconductor only',
            'content': 'Semi supply chain',
            'content_preview': 'Semi supply chain',
            'source': 'source-b',
            'heat': 9,
            '_weight': 1.0,
            '_exclusive': True,
            'catalyst_type': 'product',
            'is_recap': False,
            'url': 'https://example.com/semi',
            'published_at': '2026-05-13T08:10:00+08:00',
            'unit_key': 'single::semi',
        }

        sector_result = {
            'sector_weighted': {
                'AI算力': [shared_item],
                '半导体': [shared_item, semi_item],
            },
            'sector_matched_kws': {'AI算力': ['算力'], '半导体': ['芯片']},
            'sector_to_hotrank': {},
        }
        logic_units = [
            {
                'unit_key': 'theme::AI算力',
                'unit_type': 'theme_cluster',
                'title': 'AI算力',
                'summary': 'AI compute branches fan out.',
                'dominant_signal': 'catalyst_only',
                'signal_confidence': 'high',
                'related_symbols_or_sectors': ['AI算力'],
                'stock_branches': [{'stock_name': '意华股份', 'stock_code': '', 'branch_reason': 'Liquid cooling'}],
                'recap_count': 0,
                'catalyst_count': 2,
                'catalyst_type_dist': {'product': 2},
                'decision_reason': 'theme cluster',
            },
            {
                'unit_key': 'single::semi',
                'unit_type': 'single',
                'title': '半导体',
                'summary': 'Semiconductor only.',
                'dominant_signal': 'catalyst_only',
                'signal_confidence': 'medium',
                'related_symbols_or_sectors': ['半导体'],
                'stock_branches': [],
                'recap_count': 0,
                'catalyst_count': 1,
                'catalyst_type_dist': {'product': 1},
                'decision_reason': 'single item',
            },
        ]

        summaries = build_sector_summaries(sector_result, logic_units=logic_units)
        by_name = {item['name']: item for item in summaries}

        ai_units = [unit['unit_key'] for unit in by_name['AI算力']['core_logic_units']]
        semi_units = [unit['unit_key'] for unit in by_name['半导体']['core_logic_units']]

        self.assertIn('theme::AI算力', ai_units)
        self.assertNotIn('theme::AI算力', semi_units)
        self.assertIn('single::semi', semi_units)


if __name__ == '__main__':
    unittest.main()
