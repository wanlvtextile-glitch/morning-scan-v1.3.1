import unittest


class OutputLayerSingleInterfaceRegressionTest(unittest.TestCase):

    def test_build_report_is_removed_from_output_layer_entry(self):
        """build_report（旧接口）已从 output_layer.entry 移除。"""
        import output_layer.entry as entry
        self.assertFalse(
            hasattr(entry, 'build_report'),
            msg='build_report 旧接口应已从 output_layer.entry 删除',
        )

    def test_build_report_from_editorial_is_the_only_public_entry(self):
        """build_report_from_editorial（新接口）仍然存在且可调用。"""
        from output_layer.entry import build_report_from_editorial
        self.assertTrue(callable(build_report_from_editorial))

    def test_build_report_not_in_output_layer_init(self):
        """build_report 不再从 output_layer 包顶层导出。"""
        import output_layer
        self.assertNotIn('build_report', output_layer.__all__)

    def test_analyzer_does_not_import_build_report(self):
        """analyzer.py 不再导入已删除的 build_report。"""
        import analyzer
        self.assertFalse(
            hasattr(analyzer, 'build_report'),
            msg='analyzer 不应保留 build_report 的引用',
        )


if __name__ == '__main__':
    unittest.main()
