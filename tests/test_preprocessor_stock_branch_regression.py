import unittest

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


class PreprocessorStockBranchRegressionTest(unittest.TestCase):
    def test_theme_cluster_uses_real_stock_entities_only(self):
        items = [
            _item(1, '意华股份！公司互动易官宣研发液冷cage', '意华股份研发液冷cage，用于华为昇腾。'),
            _item(2, '更新机构纪要：芝加哥算力期货重磅落地，润建股份迎来价值重估', '润建股份（002929）受益液冷服务器资产。'),
            _item(3, 'CPU、自主可控、PCB', '这里只是投资感悟，不是具体公司。'),
            _item(4, '20260512今日段子', '这是一篇段子汇总，不是股票。'),
        ]

        logic_units = build_logic_units(items)
        theme_units = [unit for unit in logic_units if unit.get('unit_type') == 'theme_cluster']
        self.assertEqual(len(theme_units), 1)

        branch_names = {branch['stock_name'] for branch in theme_units[0].get('stock_branches', [])}
        self.assertIn('意华股份', branch_names)
        self.assertIn('润建股份', branch_names)
        self.assertNotIn('更新机构纪要', branch_names)
        self.assertNotIn('CPU、自主可控、PCB', branch_names)
        self.assertNotIn('20260512今日段子', branch_names)


if __name__ == '__main__':
    unittest.main()
