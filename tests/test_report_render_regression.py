import unittest

from output_layer.report import _completeness_issues, _render_source_snapshot, _render_stock_candidates_table


class ReportRenderRegressionTest(unittest.TestCase):
    def test_stock_candidate_table_omits_code_column(self):
        markdown = _render_stock_candidates_table([
            {
                'code': '002929',
                'name': '润建股份',
                'mention_count': 2,
                'driver_display': '催化驱动',
                'authenticity': '较正宗',
                'authenticity_evidence': '算力运维链',
                'core_reason': '液冷与算网建设相关',
            }
        ])

        self.assertIn('| 名称 | 提及数 | 驱动 | 正宗度 | 正宗度依据 | 核心理由 |', markdown)
        self.assertNotIn('| 代码 |', markdown)

    def test_completeness_issues_flags_invalid_top_sector_names(self):
        pkg = {
            'report_views': {
                'final_recommendations': {'conclusion_text': 'ok'},
                'top_sectors': [
                    {
                        'name': 'AI算力',
                        'stock_candidates': [
                            {'name': '三星电子', 'code': '', 'authenticity': '较正宗'},
                            {'name': '中国长城', 'code': '', 'authenticity': '较正宗'},
                        ],
                    }
                ],
            }
        }

        issues = _completeness_issues(pkg)
        self.assertTrue(any('存在非法个股名称' in issue for issue in issues))

    def test_source_snapshot_uses_dynamic_main_source_total(self):
        markdown = _render_source_snapshot({
            'source_snapshot': [
                {'name': 'A', 'status': '✅', 'item_count': 1, 'is_main': True},
                {'name': 'B', 'status': '⚠️', 'item_count': 1, 'is_main': True},
                {'name': 'C', 'status': '❌', 'item_count': 0, 'is_main': True},
                {'name': 'D', 'status': '✅', 'item_count': 1, 'is_main': False},
            ],
            'market_context': {'confidence': 'normal', 'dedup_stats': {}},
        })

        self.assertIn('主源成功（✅+⚠️）：2/3', markdown)


if __name__ == '__main__':
    unittest.main()
