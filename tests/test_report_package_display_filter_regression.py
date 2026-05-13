import unittest

from editorial_layer.report_package import build_report_package


class ReportPackageDisplayFilterRegressionTest(unittest.TestCase):
    def test_report_package_keeps_only_dictionary_valid_candidates_in_display(self):
        sector = {
            'name': '半导体',
            'group': '已知强势主线',
            'trigger_points': [],
            'logic_summary_short': '',
            'logic_summary_lines': [],
            'stock_candidates': [
                {
                    'name': '博士眼镜',
                    'code': '',
                    'mention_count': 1,
                    'authenticity': '蹭概念',
                    'authenticity_evidence': '与半导体无关',
                    'core_reason': '概念炒作',
                },
                {
                    'name': '石英股份',
                    'code': '',
                    'mention_count': 1,
                    'authenticity': '核心股',
                    'authenticity_evidence': '半导体材料核心受益',
                    'core_reason': '半导体材料核心受益',
                },
                {
                    'name': '安全带来新能源',
                    'code': '',
                    'mention_count': 1,
                    'authenticity': '蹭概念',
                    'authenticity_evidence': '非法名称',
                    'core_reason': '应被隐藏',
                },
            ],
            'dominant_signals_dist': {'neutral': 1},
            'core_logic_units': [
                {
                    'unit_type': 'single',
                    'title': '半导体题材分支',
                    'summary': 'Theme summary.',
                    'stock_branches': [
                        {'stock_name': '博士眼镜', 'stock_code': ''},
                        {'stock_name': '石英股份', 'stock_code': ''},
                        {'stock_name': '安全带来新能源', 'stock_code': ''},
                    ],
                }
            ],
        }

        pkg = build_report_package({
            'date': '2026-05-13',
            'confidence': 'normal',
            'source_stats': [],
            'market_context': {},
            'stock_pool_by_sector': {'半导体': sector['stock_candidates']},
            'hidden_signals': [],
            'final_recommendations': {'conclusion_text': 'ok'},
            'top_sectors': [sector],
            'all_sectors': [sector],
        })

        display_sector = pkg['report_views']['top_sectors'][0]
        display_names = [item['name'] for item in display_sector['stock_candidates']]
        logic_text = ' '.join(display_sector.get('logic_summary_lines', []))

        self.assertIn('石英股份', display_names)
        self.assertIn('博士眼镜', display_names)
        self.assertNotIn('安全带来新能源', display_names)
        self.assertIn('石英股份', logic_text)
        self.assertIn('博士眼镜', logic_text)
        self.assertNotIn('安全带来新能源', logic_text)


if __name__ == '__main__':
    unittest.main()
