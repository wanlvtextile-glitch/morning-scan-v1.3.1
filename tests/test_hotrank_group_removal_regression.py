import unittest

from editorial_layer.recommendations import build_final_recommendations
from editorial_layer.sector_builder import build_hidden_signals
from output_layer.report import build_brief_markdown, build_markdown_from_package
from output_layer.rules import GROUP_ORDER, GROUP_已知强势主线, classify_group


class HotrankGroupRemovalRegressionTest(unittest.TestCase):
    def test_group_order_excludes_hotrank_group(self):
        self.assertEqual(GROUP_ORDER, ['已知强势主线', '次日发酵候选', '排除项'])

    def test_hotrank_only_sector_falls_back_to_excluded_group(self):
        group, reason = classify_group({
            'stage': '启动',
            'continuation_score': '低',
            'fermentation_score': '低',
            'needs_websearch': True,
            'effective_count': 0.0,
            'hotrank': {'rank': 8, 'change_pct': '3.00%'},
        })

        self.assertEqual(group, '排除项')
        self.assertIn('信号不足', reason)

    def test_hidden_signals_still_render_without_standalone_group(self):
        hidden_signals = build_hidden_signals([
            {
                'signal_type': 'hotrank_only',
                'rank': 8,
                'hotrank_name': '消费电子',
                'change_pct': '3.00%',
                'focus_stocks': '立讯精密',
            }
        ])

        self.assertEqual(len(hidden_signals), 1)
        self.assertIsNone(hidden_signals[0]['websearch_summary'])

        pkg = {
            'meta': {
                'date': '2026-05-13',
                'generated_at': '2026-05-13T12:00:00',
                'confidence': 'normal',
            },
            'market_context': {
                'confidence': 'normal',
                'dedup_stats': {},
                'indices': None,
                'us_markets': None,
            },
            'source_snapshot': [],
            'report_views': {
                'top_sectors': [],
                'hidden_signals': hidden_signals,
                'groups': {
                    GROUP_已知强势主线: [],
                    '次日发酵候选': [],
                    '排除项': [],
                },
                'trigger_summary': [],
                'final_recommendations': {
                    'primary_lines': [],
                    'candidate_lines': [],
                    'watch_list': [],
                    'conclusion_text': '测试结论',
                },
            },
        }

        markdown = build_markdown_from_package(pkg)
        brief = build_brief_markdown(pkg)

        self.assertIn('人气榜隐藏信号', markdown)
        self.assertIn('消费电子', markdown)
        self.assertNotIn('人气先行信号', markdown)
        self.assertIn('人气榜隐藏信号', brief)
        self.assertNotIn('人气等待', brief)

    def test_final_recommendations_keep_compatible_empty_watch_list(self):
        recommendations = build_final_recommendations([
            {'name': 'AI算力', 'group': GROUP_已知强势主线},
            {'name': '消费', 'group': '次日发酵候选'},
        ])

        self.assertEqual(recommendations['primary_lines'], ['AI算力'])
        self.assertEqual(recommendations['candidate_lines'], ['消费'])
        self.assertEqual(recommendations['watch_list'], [])


if __name__ == '__main__':
    unittest.main()
