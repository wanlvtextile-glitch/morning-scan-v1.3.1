import unittest

from editorial_layer.stock_merger import merge_stock_candidates
from preprocessor.cluster import build_logic_units


def _item(idx: int, title: str, content: str) -> dict:
    return {
        'original_id': f'pp-{idx:06d}',
        'title': title,
        'content': content,
        'content_preview': content[:80],
        'is_recap': False,
        'catalyst_type': 'product',
    }


class EntityNameTighteningRegressionTest(unittest.TestCase):
    def test_preprocessor_filters_sentence_like_pseudo_entities(self):
        items = [
            _item(1, '平治信息：Token工厂即将上线', '平治信息推出Token工厂模块。'),
            _item(2, 'KK的核心原因是其核心原材料', '这里只是观点表达，不是公司名。'),
            _item(3, '由广汽集团与华为乾崑联合打造的独立高端智能新能源汽车品牌启境汽车', '品牌消息，不是上市公司名。'),
            _item(4, '早盘急杀出粤电力', '情绪描述，不是实体抽取。'),
        ]

        logic_units = build_logic_units(items)
        branch_names = {
            branch['stock_name']
            for unit in logic_units
            for branch in unit.get('stock_branches', [])
        }

        self.assertIn('平治信息', branch_names)
        self.assertNotIn('KK的核心原因是其核心原材料', branch_names)
        self.assertNotIn('联合打造的独立高端智能新能源', branch_names)
        self.assertNotIn('早盘急杀出粤电力', branch_names)

    def test_editorial_filters_institutional_or_sentence_like_names(self):
        sector = {
            'core_logic_units': [
                {
                    'unit_key': 'theme::AI算力',
                    'summary': 'AI compute branches.',
                    'stock_branches': [
                        {
                            'stock_name': '平治信息',
                            'stock_code': '',
                            'branch_reason': 'Valid company.',
                            'recap_count': 0,
                            'catalyst_count': 1,
                            'dominant_signal': 'catalyst_only',
                        },
                        {
                            'stock_name': '国联民生电子',
                            'stock_code': '',
                            'branch_reason': 'Institution tag.',
                            'recap_count': 0,
                            'catalyst_count': 1,
                            'dominant_signal': 'catalyst_only',
                        },
                        {
                            'stock_name': '机器人和商业航天跟随科技',
                            'stock_code': '',
                            'branch_reason': 'Sentence-like phrase.',
                            'recap_count': 0,
                            'catalyst_count': 1,
                            'dominant_signal': 'catalyst_only',
                        },
                    ],
                }
            ],
        }

        result = merge_stock_candidates(sector)
        names = [item['name'] for item in result]

        self.assertIn('平治信息', names)
        self.assertNotIn('国联民生电子', names)
        self.assertNotIn('机器人和商业航天跟随科技', names)


if __name__ == '__main__':
    unittest.main()
