import unittest

from editorial_layer.logic_summary import attach_logic_summary


class LogicSummaryFilteredBranchesRegressionTest(unittest.TestCase):
    def test_logic_summary_prefers_filtered_stock_candidates(self):
        sector = {
            'dominant_signals_dist': {'neutral': 1},
            'stock_candidates': [
                {'name': '中国长城', 'code': ''},
                {'name': '深南电路', 'code': ''},
            ],
            'core_logic_units': [
                {
                    'unit_type': 'single',
                    'title': '商业航天板块的重磅消息',
                    'summary': 'Theme summary.',
                    'stock_branches': [
                        {'stock_name': '三星电子', 'stock_code': ''},
                        {'stock_name': '中国长城', 'stock_code': ''},
                        {'stock_name': '为其提供用于下一代通信', 'stock_code': ''},
                    ],
                }
            ],
        }

        enriched = attach_logic_summary(sector)
        lines = enriched.get('logic_summary_lines', [])
        joined = ' '.join(lines)

        self.assertIn('中国长城', joined)
        self.assertIn('深南电路', joined)
        self.assertNotIn('三星电子', joined)
        self.assertNotIn('为其提供用于下一代通信', joined)


if __name__ == '__main__':
    unittest.main()
