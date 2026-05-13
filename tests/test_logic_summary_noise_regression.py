import unittest

from editorial_layer.logic_summary import attach_logic_summary


class LogicSummaryNoiseRegressionTest(unittest.TestCase):
    def test_logic_summary_avoids_noisy_raw_titles(self):
        sector = {
            'dominant_signals_dist': {'neutral': 1},
            'core_logic_units': [
                {
                    'unit_type': 'single',
                    'title': '早盘急杀出粤电力，尾盘低吸金富科技',
                    'summary': '盘中情绪描述，不应直接进入核心线索。',
                    'stock_branches': [
                        {'stock_name': '金富科技'},
                    ],
                }
            ],
        }

        enriched = attach_logic_summary(sector)
        lines = enriched.get('logic_summary_lines', [])

        self.assertIn('分支：金富科技', lines)
        self.assertIn('核心线索：相关个股：金富科技', lines)
        self.assertNotIn('核心线索：早盘急杀出粤电力，尾盘低吸金富科技', lines)

    def test_logic_summary_avoids_market_recap_style_titles(self):
        sector = {
            'dominant_signals_dist': {'neutral': 1},
            'core_logic_units': [
                {
                    'unit_type': 'single',
                    'title': '今天商业航天没话说呀，里面没有几支涨停的是因为商业航天',
                    'summary': '行情概括：A股全天震荡分化，大盘小幅收绿。',
                    'stock_branches': [
                        {'stock_name': '金明精机'},
                        {'stock_name': '航天彩虹'},
                    ],
                }
            ],
        }

        enriched = attach_logic_summary(sector)
        lines = enriched.get('logic_summary_lines', [])

        self.assertIn('核心线索：相关个股：金明精机、航天彩虹', lines)
        self.assertNotIn('今天商业航天没话说呀，里面没有几支涨停的是因为商业航天', ' '.join(lines))
        self.assertNotIn('行情概括：A股全天震荡分化，大盘小幅收绿。', ' '.join(lines))


if __name__ == '__main__':
    unittest.main()
