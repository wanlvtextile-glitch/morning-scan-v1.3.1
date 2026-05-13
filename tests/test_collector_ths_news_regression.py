import json
import unittest

from collector.sources import _extract_js_array


class ThsNewsRegressionTest(unittest.TestCase):
    def test_extract_js_array_ignores_brackets_inside_string_content(self):
        entries = [
            {
                "title": "normal",
                "content": "headline with ] bracket and [ marker inside string",
                "pubDate": "2026/05/13 08:01",
            },
            {
                "title": "second",
                "content": "plain content",
                "pubDate": "2026/05/13 08:02",
            },
        ]
        text = f'var thsRss = {{pubDate:"2026/05/13 08:10", item:{json.dumps(entries, ensure_ascii=False)}}};'

        extracted = _extract_js_array(text, ('"item":', 'item:'))
        parsed = json.loads(extracted)

        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['content'], entries[0]['content'])
        self.assertEqual(parsed[1]['title'], 'second')


if __name__ == '__main__':
    unittest.main()
