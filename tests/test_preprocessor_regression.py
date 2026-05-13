import unittest

from preprocessor.entry import preprocess


class PreprocessorRegressionTest(unittest.TestCase):
    def test_preprocess_keeps_new_structure_and_dedup_trace(self):
        items = [
            {
                'source': 'source-a',
                'title': 'Coolermaster 液冷供应链机会',
                'content': 'Coolermaster GPU liquid cooling demand is rising.',
            },
            {
                'source': 'source-a',
                'title': 'Coolermaster 液冷供应链机会',
                'content': 'Coolermaster GPU liquid cooling demand is rising.',
            },
            {
                'source': 'source-b',
                'title': 'AI 服务器 GPU 散热链条扩散',
                'content': 'GPU cooling and server demand continue to expand.',
            },
        ]

        result = preprocess(items)

        self.assertIn('processed_items', result)
        self.assertIn('stats', result)
        self.assertIn('logic_units', result)
        self.assertIn('signal_stats', result)
        self.assertIn('dedup_decisions', result)

        self.assertEqual(result['stats']['original_news'], 3)
        self.assertEqual(result['stats']['removed'], 1)
        self.assertEqual(result['signal_stats']['exact_duplicate_removed'], 1)
        self.assertEqual(len(result['processed_items']), 2)
        self.assertGreaterEqual(len(result['logic_units']), 1)

        decision_types = {x['decision_type'] for x in result['dedup_decisions']}
        self.assertIn('drop_exact_duplicate', decision_types)


if __name__ == '__main__':
    unittest.main()
