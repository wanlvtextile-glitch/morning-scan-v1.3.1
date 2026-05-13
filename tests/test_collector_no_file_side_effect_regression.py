import inspect
import unittest

from collector.models import CollectorOutput, NewsItem, SourceResult


class CollectorNoFileSideEffectRegressionTest(unittest.TestCase):
    def test_collector_output_has_time_window_end_field(self):
        """CollectorOutput 必须携带 time_window_end，供 pipeline 序列化用。"""
        import dataclasses
        fields = {f.name for f in dataclasses.fields(CollectorOutput)}
        self.assertIn('time_window_end', fields)

    def test_collector_output_time_window_end_defaults_to_empty(self):
        output = CollectorOutput(
            confidence='normal',
            main_success_count=1,
            main_source_total=1,
            results=[],
            all_items=[],
        )
        self.assertEqual(output.time_window_end, '')

    def test_collect_signature_has_no_output_path(self):
        """collect() 不再负责写文件，接口里不应出现 output_path 参数。"""
        from collector.entry import collect
        sig = inspect.signature(collect)
        self.assertNotIn('output_path', sig.parameters)


if __name__ == '__main__':
    unittest.main()
