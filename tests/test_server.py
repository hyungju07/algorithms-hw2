"""SPEC.md 6절 46~52번. 빈 포트에 서버를 띄우고 실제로 요청을 보낸다."""
import http.client
import os
import re
import sys
import threading
import unittest
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from server import make_server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server(port=0, host="127.0.0.1", quiet=True)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=()):
        """(상태 코드, Location 헤더, 본문 문자열)"""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.putrequest(method, path)
            for name, value in headers:
                conn.putheader(name, value)
            if body is not None:
                data = body.encode("utf-8")
                conn.putheader("Content-Type", "application/x-www-form-urlencoded")
                if not any(name.lower() == "content-length" for name, _ in headers):
                    conn.putheader("Content-Length", str(len(data)))
                conn.endheaders(data)
            else:
                conn.endheaders()
            response = conn.getresponse()
            return response.status, response.getheader("Location"), response.read().decode("utf-8")
        finally:
            conn.close()

    def shorten(self, url, headers=()):
        return self.request("POST", "/shorten", urlencode([("url", url)]), headers)

    def me(self):
        return f"http://127.0.0.1:{self.port}"

    # 46
    def test_index_has_a_form(self):
        status, _, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("<form", body)
        self.assertIn('action="/shorten"', body)
        self.assertIn('name="url"', body)
        self.assertIn('href="/table"', body)

    # 47
    def test_shorten_then_follow_the_short_link(self):
        status, _, body = self.shorten("https://www.yonsei.ac.kr")
        self.assertEqual(status, 200)
        self.assertIn(f'href="{self.me()}/1"', body)
        self.assertIn("https://www.yonsei.ac.kr", body)
        status, location, _ = self.request("GET", "/1")
        self.assertEqual(status, 302)
        self.assertEqual(location, "https://www.yonsei.ac.kr")

    def test_same_url_gets_the_same_link(self):
        self.shorten("https://www.yonsei.ac.kr")
        self.shorten("https://github.com")
        _, _, body = self.shorten("  https://www.yonsei.ac.kr  ")
        self.assertIn(f'href="{self.me()}/1"', body)
        self.assertEqual(self.request("GET", "/3")[0], 404)

    # 48
    def test_unknown_code_is_404(self):
        for path in ("/1", "/zzz", "/0", "/01", "/favicon.ico", "/a/b", "/%EA%B0%80", "/table/"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 404)

    def test_bad_url_is_400_and_keeps_the_form(self):
        for bad in ("ftp://files.example.com", "example.com", "http://a.com/a b", "", "javascript:alert(1)"):
            with self.subTest(bad=bad):
                status, _, body = self.shorten(bad)
                self.assertEqual(status, 400)
                self.assertIn("<form", body)
        self.assertEqual(self.request("GET", "/1")[0], 404)     # 아무것도 저장되지 않았다
        self.assertEqual(self.shorten("https://a.com")[0], 200)
        self.assertEqual(self.request("GET", "/1")[1], "https://a.com")

    def test_missing_field_is_400(self):
        self.assertEqual(self.request("POST", "/shorten", "other=1")[0], 400)
        self.assertEqual(self.request("POST", "/shorten", "")[0], 400)

    def test_too_large_body_is_413(self):
        status, _, _ = self.request("POST", "/shorten", "url=" + "a" * 70000)
        self.assertEqual(status, 413)

    def test_bad_content_length_is_400(self):
        status, _, _ = self.request("POST", "/shorten", "url=x", headers=(("Content-Length", "abc"),))
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/shorten", "url=x", headers=(("Content-Length", "-5"),))
        self.assertEqual(status, 400)

    def test_post_to_other_path_is_404(self):
        self.assertEqual(self.request("POST", "/", "url=https://a.com")[0], 404)
        self.assertEqual(self.request("POST", "/1", "url=https://a.com")[0], 404)

    # 49
    def test_short_link_uses_forwarded_host(self):
        forwarded = (("X-Forwarded-Host", "fluffy-space-xyz-8000.app.github.dev"),
                     ("X-Forwarded-Proto", "https"))
        status, _, body = self.shorten("https://www.yonsei.ac.kr", forwarded)
        self.assertEqual(status, 200)
        self.assertIn('href="https://fluffy-space-xyz-8000.app.github.dev/1"', body)
        self.assertNotIn("127.0.0.1", body)
        self.assertNotIn("localhost", body)
        _, _, table = self.request("GET", "/table", headers=forwarded)
        self.assertIn('href="https://fluffy-space-xyz-8000.app.github.dev/1"', table)

    def test_host_header_is_used_without_a_proxy(self):
        _, _, body = self.shorten("https://a.com", (("Host", "short.example:8000"),))
        self.assertIn('href="http://short.example:8000/1"', body)

    def test_hostile_host_headers_are_not_echoed(self):
        for name in ("X-Forwarded-Host", "Host"):
            for bad in ('evil.example/"><script>alert(1)</script>', "a b", "evil.example/path", "<b>"):
                with self.subTest(name=name, bad=bad):
                    status, _, body = self.shorten("https://a.com", ((name, bad),))
                    self.assertEqual(status, 200)
                    self.assertNotIn("<script>", body)
                    self.assertNotIn("evil.example", body)
                    self.assertIn(f'href="http://localhost:{self.port}/1"', body)
        _, _, body = self.shorten("https://a.com", (("X-Forwarded-Proto", "javascript"),))
        self.assertIn(f'href="{self.me()}/1"', body)

    # 50
    def test_user_input_is_escaped(self):
        evil = 'http://a.com/<script>alert(1)</script>?q="x"&r=<b>'
        status, _, body = self.shorten(evil)
        self.assertEqual(status, 200)
        self.assertNotIn("<script>alert", body)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
        _, _, table = self.request("GET", "/table")
        self.assertNotIn("<script>alert", table)
        self.assertIn("&lt;script&gt;", table)
        status, _, body = self.shorten("<script>alert(2)</script>")
        self.assertEqual(status, 400)
        self.assertNotIn("<script>alert", body)

    # 51
    def test_table_shows_chains_and_horner_steps(self):
        for url in ("https://www.yonsei.ac.kr", "https://github.com", "https://learnus.yonsei.ac.kr"):
            self.shorten(url)
        status, _, body = self.request("GET", "/table")
        self.assertEqual(status, 200)
        for url in ("https://www.yonsei.ac.kr", "https://github.com", "https://learnus.yonsei.ac.kr"):
            self.assertIn(url, body)
        for code in ("1", "2", "3"):
            self.assertIn(f'href="{self.me()}/{code}"', body)
        self.assertIn("N = 3", body)
        self.assertIn("M = 11", body)
        self.assertIn("<details", body)
        # https://github.com 의 호너 계산: 첫 글자 h(104), 0에서 시작
        self.assertIn("(31 × 0 + 104) mod 11", body)

    def test_empty_table_page(self):
        status, _, body = self.request("GET", "/table")
        self.assertEqual(status, 200)
        self.assertIn("N = 0", body)

    def test_reverse_table_page(self):
        self.shorten("https://github.com")
        status, _, body = self.request("GET", "/table?which=code")
        self.assertEqual(status, 200)
        self.assertIn("https://github.com", body)
        self.assertIn("(31 × 0 + 49) mod 11", body)   # 키 "1"의 글자 코드는 49

    # 52
    def test_reserved_paths_are_not_codes(self):
        self.shorten("https://a.com")
        self.assertEqual(self.request("GET", "/table")[0], 200)
        status, location, _ = self.request("GET", "/shorten")
        self.assertEqual((status, location), (404, None))

    def test_redirect_location_is_ascii_safe(self):
        self.shorten("https://ko.wikipedia.org/wiki/해시_테이블")
        self.shorten("https://example.com/a%20b?x=1&y=%ED%95%9C#frag")
        self.assertEqual(self.request("GET", "/1")[1],
                         "https://ko.wikipedia.org/wiki/%ED%95%B4%EC%8B%9C_%ED%85%8C%EC%9D%B4%EB%B8%94")
        self.assertEqual(self.request("GET", "/2")[1], "https://example.com/a%20b?x=1&y=%ED%95%9C#frag")

    def test_code_path_ignores_query_string(self):
        self.shorten("https://a.com")
        self.assertEqual(self.request("GET", "/1?utm=x")[1], "https://a.com")

    def test_many_urls_grow_the_table(self):
        for i in range(30):
            self.assertEqual(self.shorten(f"https://example.com/{i}")[0], 200)
        _, _, body = self.request("GET", "/table")
        self.assertIn("N = 30", body)
        self.assertEqual(self.request("GET", "/u")[1], "https://example.com/29")   # 30번째 코드는 u

    def test_concurrent_requests_get_distinct_codes(self):
        codes = []

        def work(i):
            _, _, body = self.shorten(f"https://example.com/concurrent/{i}")
            codes.append(re.search(r'href="http://127\.0\.0\.1:\d+/([0-9a-zA-Z]+)"', body).group(1))

        threads = [threading.Thread(target=work, args=(i,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        self.assertEqual(len(codes), 40)
        self.assertEqual(len(sorted(frozenset(codes))), 40)
        self.assertEqual(len(self.server.shortener), 40)


if __name__ == "__main__":
    unittest.main()
