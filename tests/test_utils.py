import unittest
from src.utils import parse_view_count, parse_duration_to_minutes, detect_language

class TestUtils(unittest.TestCase):
    def test_parse_view_count(self):
        cases = {
            '1,234 次观看': 1234,
            '12K views': 12000,
            '1.2M views': 1200000,
            '987 views': 987,
            '3.4万 次观看': 34000,
            '2.1亿 次观看': 210000000,
            '45k': 45000,
            '7m': 7000000,
            '1000000': 1000000,
        }
        for s, expected in cases.items():
            self.assertEqual(parse_view_count(s), expected, msg=f"parse_view_count('{s}')")

    def test_parse_duration_to_minutes(self):
        cases = {
            '12:34': 12,
            '1:23:45': 83,
            ' 8 ： 05 ': 8,
            '90': 90,
            '3分钟': 3,
            '00:59:59': 59,
        }
        for s, expected in cases.items():
            self.assertEqual(parse_duration_to_minutes(s), expected, msg=f"parse_duration_to_minutes('{s}')")

    def test_detect_language(self):
        self.assertEqual(detect_language("中文测试"), "cn")
        self.assertEqual(detect_language("日本語テスト"), "jp")
        self.assertEqual(detect_language("English title"), "en")

if __name__ == '__main__':
    unittest.main()
