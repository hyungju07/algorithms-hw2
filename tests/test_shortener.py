"""SPEC.md 6절 30~45번."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import decode, encode
from shortener import Shortener


class ShortenerTests(unittest.TestCase):
    def make(self, **kwargs):
        return Shortener(**kwargs)

    # 30
    def test_codes_are_serial_numbers_in_base62(self):
        s = self.make()
        self.assertEqual(s.shorten("https://www.yonsei.ac.kr"), "1")
        self.assertEqual(s.shorten("https://github.com"), "2")
        codes = [s.shorten(f"https://example.com/{i}") for i in range(3, 63)]
        self.assertEqual(codes[-2], "Z")    # 61번째
        self.assertEqual(codes[-1], "10")   # 62번째
        self.assertEqual(len(s), 62)

    # 31
    def test_same_url_gets_same_code(self):
        s = self.make()
        first = s.shorten("https://www.yonsei.ac.kr")
        s.shorten("https://github.com")
        self.assertEqual(s.shorten("https://www.yonsei.ac.kr"), first)
        self.assertEqual(len(s), 2)
        self.assertEqual(s.shorten("https://learnus.yonsei.ac.kr"), "3")  # 번호를 건너뛰지 않았다

    # 32
    def test_round_trip(self):
        s = self.make()
        urls = [f"https://example.com/page/{i}?q={i * 7}" for i in range(200)]
        codes = [s.shorten(u) for u in urls]
        self.assertEqual(len(s), 200)
        for url, code in zip(urls, codes):
            self.assertEqual(s.expand(code), url)
        self.assertEqual(sorted(codes, key=decode), codes)        # 일련번호 순서
        self.assertEqual([decode(c) for c in codes], list(range(1, 201)))  # 겹치는 코드가 없다

    # 33
    def test_unknown_code_is_none(self):
        s = self.make()
        s.shorten("https://www.yonsei.ac.kr")
        for code in ("999", "", "0", "01", "001", "a-b", "가", " 1", "1 ", "2"):
            with self.subTest(code=code):
                self.assertIsNone(s.expand(code))
        self.assertEqual(s.expand("1"), "https://www.yonsei.ac.kr")

    def test_expand_on_empty_shortener(self):
        self.assertIsNone(self.make().expand("1"))
        self.assertEqual(len(self.make()), 0)

    # 34
    def test_wrong_scheme_raises_value_error(self):
        s = self.make()
        for bad in ("ftp://files.example.com", "javascript:alert(1)", "example.com",
                    "//example.com", "www.example.com/path", "mailto:a@b.com",
                    "file:///etc/passwd", "httpx://example.com", "http:example.com",
                    "data:text/html,<script>alert(1)</script>"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    s.shorten(bad)
        self.assertEqual(len(s), 0)

    # 35
    def test_missing_host_raises_value_error(self):
        s = self.make()
        for bad in ("http://", "https://", "https:///path", "http://?q=1", "http://:8000", "http:///"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    s.shorten(bad)

    # 36
    def test_inner_whitespace_or_control_character_raises_value_error(self):
        s = self.make()
        for bad in ("http://a.com/a b", "http://a.com/a\tb", "http://a.com/a\nb",
                    "http://a .com", "http://a.com/\x00", "http://a.com/\x7f",
                    "http://a.com/\x1b", "http://a.com/\x80", "http://a.com/\x9f",
                    "http://a.com/a\r\nSet-Cookie: x=1", "http://a.com/a b"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    s.shorten(bad)

    # 37
    def test_outer_whitespace_is_trimmed(self):
        s = self.make()
        code = s.shorten("  https://a.com  ")
        self.assertEqual(s.shorten("https://a.com"), code)
        self.assertEqual(s.shorten("\thttps://a.com\n"), code)
        self.assertEqual(s.expand(code), "https://a.com")
        self.assertEqual(len(s), 1)

    # 38
    def test_length_limit(self):
        s = self.make()
        ok = "https://a.com/" + "x" * (2048 - 14)
        self.assertEqual(len(ok), 2048)
        code = s.shorten(ok)
        self.assertEqual(s.expand(code), ok)
        with self.assertRaises(ValueError):
            s.shorten(ok + "x")
        self.assertEqual(s.shorten("   " + ok + "   "), code)   # 자른 뒤의 길이로 잰다

    # 39
    def test_empty_and_non_string(self):
        s = self.make()
        for bad in ("", "   ", "\n\t"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    s.shorten(bad)
        for bad in (None, 123, b"https://a.com", ["https://a.com"]):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    s.shorten(bad)

    # 40
    def test_failed_shorten_does_not_use_a_serial_number(self):
        s = self.make()
        self.assertEqual(s.shorten("https://a.com"), "1")
        for bad in ("ftp://files.example.com", "", "http://a.com/a b"):
            with self.assertRaises(ValueError):
                s.shorten(bad)
        with self.assertRaises(TypeError):
            s.shorten(None)
        self.assertEqual(s.shorten("https://b.com"), "2")
        self.assertEqual(len(s), 2)

    # 41
    def test_uppercase_scheme_is_accepted_but_not_normalized(self):
        s = self.make()
        upper = s.shorten("HTTP://EXAMPLE.COM")
        lower = s.shorten("http://example.com")
        self.assertNotEqual(upper, lower)
        self.assertEqual(s.expand(upper), "HTTP://EXAMPLE.COM")
        self.assertEqual(s.shorten("HttpS://Example.com/Path"), "3")

    # 42
    def test_trailing_slash_is_a_different_url(self):
        s = self.make()
        self.assertNotEqual(s.shorten("http://a.com"), s.shorten("http://a.com/"))
        self.assertEqual(len(s), 2)

    # 43
    def test_query_fragment_and_unicode_come_back_unchanged(self):
        s = self.make()
        for url in ("https://example.com/search?q=해시+테이블&page=2#결과",
                    "https://ko.wikipedia.org/wiki/해시_테이블",
                    "https://example.com/a%20b?x=1&y=%ED%95%9C",
                    "http://localhost:8000/table",
                    "http://[::1]:8000/",
                    "https://user:pw@example.com:8443/path;p?q#f"):
            with self.subTest(url=url):
                self.assertEqual(s.expand(s.shorten(url)), url)

    # 44
    def test_reserved_codes_are_skipped(self):
        for word in ("table", "shorten"):
            with self.subTest(word=word):
                n = decode(word)
                s = self.make(start=n - 1)
                before = s.shorten("https://a.com")
                after = s.shorten("https://b.com")
                self.assertEqual(before, encode(n - 1))
                self.assertEqual(after, encode(n + 1))
                self.assertIsNone(s.expand(word))
                self.assertEqual(s.expand(after), "https://b.com")
                # 건너뛴 뒤에도 번호가 이어진다. 멈춰 있으면 다음 URL이 같은 코드를 받는다
                self.assertEqual(s.shorten("https://c.com"), encode(n + 2))
                self.assertEqual(s.expand(after), "https://b.com")
                self.assertEqual(len(s), 3)

    def test_len_counts_codes_not_serial_numbers(self):
        s = self.make(start=5)
        self.assertEqual(s.shorten("https://a.com"), "5")
        self.assertEqual(len(s), 1)

    def test_start_must_be_a_positive_integer(self):
        for bad in (0, -1, 1.5, "1", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.make(start=bad)

    # 45
    def test_expand_non_string_raises_type_error(self):
        s = self.make()
        s.shorten("https://a.com")
        for bad in (123, None, b"1"):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    s.expand(bad)

    def test_two_shorteners_do_not_share_state(self):
        a, b = self.make(), self.make()
        a.shorten("https://a.com")
        self.assertIsNone(b.expand("1"))
        self.assertEqual(b.shorten("https://b.com"), "1")


if __name__ == "__main__":
    unittest.main()
