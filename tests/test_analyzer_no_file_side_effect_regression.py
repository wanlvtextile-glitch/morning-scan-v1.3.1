import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


def _make_sector():
    return {
        'name': '半导体', 'score': 80, 'star_rating': 3,
        'stage': 'rising', 'item_count': 5, 'effective_count': 4.5,
        'source_count': 2, 'hotrank': None, 'needs_websearch': False,
        'logic_unit_count': 2, 'event_cluster_count': 1, 'theme_cluster_count': 1,
    }


def _make_analysis_result():
    return {
        'generated_at': '2026-05-13T09:00:00',
        'sectors': [_make_sector()],
        'hotrank_signals': [],
        'source_stats': [],
        'dedup_stats': {},
    }


class AnalyzerNoFileSideEffectRegressionTest(unittest.TestCase):

    def _run_with_mocks(self, output_path):
        mock_state = MagicMock()
        mock_state.meta = {}
        mock_state.editorial = {}

        with patch('analyzer.preprocess', return_value={
            'processed_items': [],
            'stats': {'original_news': 0, 'removed': 0},
            'logic_units': [],
            'signal_stats': {},
            'dedup_decisions': [],
        }), \
        patch('analyzer.identify_sectors', return_value={}), \
        patch('analyzer.run_analysis_pipeline', return_value=_make_analysis_result()), \
        patch('analyzer.score_sectors', return_value={
            'scored_sectors': [_make_sector()],
            'scoring_stats': {},
        }), \
        patch('analyzer.build_editorial', return_value={'all_sectors': [], 'top_sectors': []}), \
        patch('agents.assemble_state', return_value=mock_state), \
        patch('agents.run_agents'), \
        patch('agents.write_scan_result', return_value=os.path.join(os.path.dirname(output_path), '2026-05-13-scan_result.json')), \
        patch('analyzer.build_report_from_editorial', return_value={
            'markdown': '# 报告',
            'brief_markdown': '# 简报',
            'report_package': {},
        }), \
        patch('editorial_layer.market_context._prev_us_trading_day', return_value=''):
            from analyzer import run_analysis
            return run_analysis(
                items=[{'title': 'test', 'content': '', 'source': 'src',
                        'source_type': 'news', 'url': '', 'published_at': '', 'heat': 0}],
                confidence='normal',
                source_stats=[],
                output_path=output_path,
                time_window_start='2026-05-13T09:00:00',
                report_dir=os.path.dirname(output_path),
            )

    def test_run_analysis_returns_analysis_json_payload(self):
        """run_analysis() 返回值必须包含 analysis_json_payload，供 pipeline 写文件用。"""
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, 'analysis_result.json')
            result = self._run_with_mocks(output_path)
            self.assertIn('analysis_json_payload', result)
            self.assertIn('sectors', result['analysis_json_payload'])

    def test_run_analysis_returns_report_result_with_markdown(self):
        """run_analysis() 返回值必须包含 report_result.markdown 和 brief_markdown。"""
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, 'analysis_result.json')
            result = self._run_with_mocks(output_path)
            self.assertIn('report_result', result)
            self.assertIn('markdown', result['report_result'])
            self.assertIn('brief_markdown', result['report_result'])

    def test_run_analysis_does_not_write_analysis_json(self):
        """analyzer 不再写 analysis_result.json，文件写入由 pipeline 负责。"""
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, 'analysis_result.json')
            self._run_with_mocks(output_path)
            self.assertFalse(
                os.path.exists(output_path),
                msg='analyzer 不应自行写入 analysis_result.json'
            )


if __name__ == '__main__':
    unittest.main()
