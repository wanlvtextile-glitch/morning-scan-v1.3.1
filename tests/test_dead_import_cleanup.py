"""
死代码清理回归测试。
RED 阶段：断言已删除的符号不再污染各模块命名空间。
GREEN 阶段：删除对应 import 后通过。
"""
import unittest


class AnalyzerDeadImportTest(unittest.TestCase):

    def test_analysis_scorer_symbols_not_in_analyzer(self):
        """compute_star_rating / compute_stage 已从 analyzer 顶层移除。"""
        import analyzer
        self.assertFalse(hasattr(analyzer, 'compute_star_rating'))
        self.assertFalse(hasattr(analyzer, 'compute_stage'))

    def test_preprocessor_helpers_not_in_analyzer(self):
        """annotate_items / deduplicate / normalize_title / strip_html 已从 analyzer 移除。"""
        import analyzer
        for name in ('annotate_items', 'deduplicate', 'normalize_title', 'strip_html'):
            self.assertFalse(
                hasattr(analyzer, name),
                msg=f'analyzer 不应暴露 preprocessor 内部符号 {name!r}',
            )

    def test_sector_identifier_helpers_not_in_analyzer(self):
        """hotrank_name_to_sector 等 5 个 sector_identifier 符号已从 analyzer 移除。"""
        import analyzer
        for name in (
            'hotrank_name_to_sector',
            'is_military_false_positive',
            'match_sectors',
            'match_sectors_detail',
            'parse_hotrank',
        ):
            self.assertFalse(
                hasattr(analyzer, name),
                msg=f'analyzer 不应暴露 sector_identifier 内部符号 {name!r}',
            )

    def test_run_analysis_still_callable(self):
        """清理后 run_analysis 仍然存在且可调用。"""
        from analyzer import run_analysis
        self.assertTrue(callable(run_analysis))


class OrchestratorDeadImportTest(unittest.TestCase):

    def test_time_not_in_orchestrator_namespace(self):
        """import time as _time 已从 orchestrator 移除。"""
        import collector.orchestrator as orch
        self.assertFalse(
            hasattr(orch, '_time'),
            msg='orchestrator 不应保留未使用的 _time 别名',
        )

    def test_run_collection_still_callable(self):
        """清理后 run_collection 仍然存在且可调用。"""
        from collector.orchestrator import run_collection
        self.assertTrue(callable(run_collection))


class AnalysisEntryDeadImportTest(unittest.TestCase):

    def test_os_not_in_analysis_entry(self):
        """import os 已从 analysis.entry 移除。"""
        import analysis.entry as entry
        self.assertFalse(hasattr(entry, 'os'))

    def test_optional_not_in_analysis_entry(self):
        """from typing import Optional 已从 analysis.entry 移除。"""
        import analysis.entry as entry
        self.assertFalse(hasattr(entry, 'Optional'))

    def test_strip_html_not_in_analysis_entry(self):
        """from preprocessor.rules import strip_html 已从 analysis.entry 移除。"""
        import analysis.entry as entry
        self.assertFalse(hasattr(entry, 'strip_html'))

    def test_run_analysis_pipeline_still_callable(self):
        """清理后 run_analysis_pipeline 仍然存在且可调用。"""
        from analysis.entry import run_analysis_pipeline
        self.assertTrue(callable(run_analysis_pipeline))

    def test_build_sector_summaries_still_callable(self):
        """清理后 build_sector_summaries 仍然存在且可调用。"""
        from analysis.entry import build_sector_summaries
        self.assertTrue(callable(build_sector_summaries))


if __name__ == '__main__':
    unittest.main()
