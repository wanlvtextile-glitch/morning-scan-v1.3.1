import unittest

from sector_identifier.rules import match_sectors_detail


class SectorIdentifierNoiseRegressionTest(unittest.TestCase):
    def test_keyword_bundle_without_company_entity_is_filtered(self):
        item = {
            'title': 'CPU、自主可控、PCB',
            'content': '这里只是投资感悟，不是具体公司。',
        }
        self.assertEqual(match_sectors_detail(item), {})

    def test_digest_style_title_without_company_entity_is_filtered(self):
        item = {
            'title': '20260512今日段子',
            'content': '这是一篇段子汇总，不是股票。',
        }
        self.assertEqual(match_sectors_detail(item), {})

    def test_real_company_news_still_matches_sector(self):
        item = {
            'title': '意华股份官宣研发液冷cage',
            'content': '意华股份研发液冷cage，用于华为昇腾。',
        }
        result = match_sectors_detail(item)
        self.assertIn('AI算力', result)


if __name__ == '__main__':
    unittest.main()
