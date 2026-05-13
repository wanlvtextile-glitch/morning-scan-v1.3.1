import unittest

from editorial_layer.stock_merger import merge_stock_candidates


class EditorialStockFilterRegressionTest(unittest.TestCase):
    def test_merge_stock_candidates_filters_pseudo_stock_names(self):
        sector = {
            'core_logic_units': [
                {
                    'unit_key': 'theme::AI算力',
                    'summary': 'AI compute branches.',
                    'stock_branches': [
                        {
                            'stock_name': '更新机构纪要',
                            'stock_code': '',
                            'branch_reason': 'Should be filtered.',
                            'recap_count': 0,
                            'catalyst_count': 1,
                            'dominant_signal': 'catalyst_only',
                        },
                        {
                            'stock_name': '意华股份',
                            'stock_code': '',
                            'branch_reason': 'Valid company.',
                            'recap_count': 0,
                            'catalyst_count': 1,
                            'dominant_signal': 'catalyst_only',
                        },
                    ],
                }
            ],
        }

        result = merge_stock_candidates(sector)
        names = [item['name'] for item in result]

        self.assertIn('意华股份', names)
        self.assertNotIn('更新机构纪要', names)


if __name__ == '__main__':
    unittest.main()
