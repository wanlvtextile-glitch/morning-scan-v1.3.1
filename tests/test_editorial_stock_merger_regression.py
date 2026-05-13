import unittest

from editorial_layer.stock_merger import merge_stock_candidates


class EditorialStockMergerRegressionTest(unittest.TestCase):
    def test_logic_branches_are_the_only_source(self):
        sector = {
            'core_logic_units': [
                {
                    'unit_key': 'theme::liquid',
                    'summary': 'Liquid cooling theme extends through supplier branches.',
                    'stock_branches': [
                        {
                            'stock_name': '润建股份',
                            'stock_code': '',
                            'branch_reason': 'Liquid cooling and compute-network construction exposure.',
                            'recap_count': 0,
                            'catalyst_count': 2,
                            'dominant_signal': 'catalyst_only',
                        },
                        {
                            'stock_name': '深南电路',
                            'stock_code': '',
                            'branch_reason': 'High-speed board and server supply-chain exposure.',
                            'recap_count': 0,
                            'catalyst_count': 1,
                            'dominant_signal': 'catalyst_only',
                        },
                    ],
                }
            ],
        }

        result = merge_stock_candidates(sector)
        by_name = {item['name']: item for item in result}

        self.assertIn('润建股份', by_name)
        self.assertIn('深南电路', by_name)

        runjian = by_name['润建股份']
        self.assertEqual(runjian['match_type'], 'logic_branch')
        self.assertEqual(runjian['core_reason'], 'Liquid cooling and compute-network construction exposure.')
        self.assertEqual(runjian['source_summary'], 'Liquid cooling theme extends through supplier branches.')
        self.assertEqual(runjian['mention_count'], 2)

        shennan = by_name['深南电路']
        self.assertEqual(shennan['match_type'], 'logic_branch')
        self.assertEqual(shennan['core_reason'], 'High-speed board and server supply-chain exposure.')

    def test_non_a_share_or_sentence_like_names_are_dropped(self):
        sector = {
            'core_logic_units': [
                {
                    'unit_key': 'theme::mixed',
                    'summary': 'Mixed branches.',
                    'stock_branches': [
                        {
                            'stock_name': '三星电子',
                            'stock_code': '',
                            'branch_reason': 'Non-A-share company should be excluded.',
                            'recap_count': 0,
                            'catalyst_count': 1,
                            'dominant_signal': 'catalyst_only',
                        },
                        {
                            'stock_name': '为其提供用于下一代通信',
                            'stock_code': '',
                            'branch_reason': 'Sentence fragment should be excluded.',
                            'recap_count': 0,
                            'catalyst_count': 1,
                            'dominant_signal': 'catalyst_only',
                        },
                        {
                            'stock_name': '中国长城',
                            'stock_code': '',
                            'branch_reason': 'Valid A-share company should remain.',
                            'recap_count': 1,
                            'catalyst_count': 0,
                            'dominant_signal': 'recap_only',
                        },
                    ],
                }
            ],
        }

        result = merge_stock_candidates(sector)
        names = [item['name'] for item in result]

        self.assertIn('中国长城', names)
        self.assertNotIn('三星电子', names)
        self.assertNotIn('为其提供用于下一代通信', names)


if __name__ == '__main__':
    unittest.main()
