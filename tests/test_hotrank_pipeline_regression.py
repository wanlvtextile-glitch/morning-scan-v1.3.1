import unittest

from analyzer import _split_hotrank_items
from analysis.entry import build_hotrank_only, build_hotrank_signals
from sector_identifier.rules import hotrank_name_to_sector, parse_hotrank


class HotrankPipelineRegressionTest(unittest.TestCase):
    def test_split_hotrank_items_prefers_source_type(self):
        all_items = [
            {'source': '同花顺人气榜', 'source_type': 'hotrank', 'title': '风电设备'},
            {'source': '淘股吧', 'source_type': 'forum', 'title': '普通新闻'},
            {'source': '同花顺热榜', 'source_type': 'forum', 'title': '错误旧名不应混入'},
        ]

        hotrank_items, news_items = _split_hotrank_items(all_items)

        self.assertEqual([item['title'] for item in hotrank_items], ['风电设备'])
        self.assertEqual([item['title'] for item in news_items], ['普通新闻', '错误旧名不应混入'])

    def test_parse_hotrank_extracts_change_pct_and_sector_mapping(self):
        hotrank_items = [
            {'heat': 1, 'title': '其他电源设备', 'content': '人气榜排名第1，涨跌幅：4.50%'},
            {'heat': 2, 'title': '通信服务', 'content': '人气榜排名第2，涨跌幅：-1.20%'},
        ]

        hotrank_list, sector_to_hotrank = parse_hotrank(hotrank_items)

        self.assertEqual(hotrank_list[0]['change_pct'], '4.50%')
        self.assertEqual(hotrank_list[1]['change_pct'], '-1.20%')
        self.assertEqual(hotrank_name_to_sector('其他电源设备'), '新能源')
        self.assertEqual(hotrank_name_to_sector('通信服务'), 'AI算力')
        self.assertEqual(sector_to_hotrank['新能源']['name'], '其他电源设备')
        self.assertEqual(sector_to_hotrank['AI算力']['name'], '通信服务')

    def test_hotrank_only_sector_is_built_for_low_news_coverage(self):
        sector_result = {
            'hotrank_list': [
                {'rank': 1, 'name': '其他电源设备', 'change_pct': '4.50%'},
                {'rank': 2, 'name': '通信服务', 'change_pct': '-1.20%'},
            ],
            'sector_to_hotrank': {
                '新能源': {'rank': 1, 'name': '其他电源设备', 'change_pct': '4.50%'},
                'AI算力': {'rank': 2, 'name': '通信服务', 'change_pct': '-1.20%'},
            },
        }
        existing = [
            {
                'name': 'AI算力',
                'effective_count': 1.0,
                'hotrank': None,
                'needs_websearch': False,
            }
        ]

        summaries = build_hotrank_only(sector_result, existing)
        signals = build_hotrank_signals(sector_result['hotrank_list'], summaries)
        by_name = {item['name']: item for item in summaries}

        self.assertTrue(by_name['新能源']['needs_websearch'])
        self.assertEqual(by_name['新能源']['hotrank']['rank'], 1)
        self.assertTrue(by_name['AI算力']['needs_websearch'])
        self.assertEqual(by_name['AI算力']['hotrank']['rank'], 2)
        self.assertEqual(signals[0]['mapped_sector'], '新能源')
        self.assertEqual(signals[0]['signal_type'], 'hotrank_only')


if __name__ == '__main__':
    unittest.main()
