"""SPEC.md 6절 46~56번. 빈 포트에 서버를 띄우고 실제로 요청을 보낸다."""
import contextlib
import http.client
import inspect
import io
import os
import re
import sys
import threading
import unittest
from unittest import mock
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import server as server_module
from server import make_server


class ServerTests(unittest.TestCase):
    table = "chaining"   # test_linear_probing.py가 "linear"로 바꿔 한 번 더 돌린다

    def setUp(self):
        self.server = make_server(port=0, host="127.0.0.1", table=self.table, quiet=True)
        self.port = self.server.server_port
        # 기본 poll_interval(0.5초)이면 테스트마다 끄는 데 0.5초씩 걸린다
        self.thread = threading.Thread(target=self.server.serve_forever, args=(0.01,), daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=()):
        """(상태 코드, Location 헤더, 본문 문자열)"""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            # Host를 직접 줄 때는 http.client가 붙이는 Host를 뺀다 (안 그러면 둘이 간다)
            conn.putrequest(method, path, skip_host=any(name.lower() == "host" for name, _ in headers))
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
        self.assertEqual(location, "https://www.yonsei.ac.kr/")   # 경로가 없으면 /를 붙여 저장한다

    def test_other_spellings_of_one_address_share_a_link(self):
        _, _, first = self.shorten("https://Example.com")
        _, _, second = self.shorten("HTTPS://EXAMPLE.COM:443/")
        for body in (first, second):
            self.assertIn(f'href="{self.me()}/1"', body)
            self.assertIn('<span class="url">https://example.com/</span>', body)   # 맞춘 주소를 보여 준다
        self.assertEqual(self.request("GET", "/1")[1], "https://example.com/")
        self.assertEqual(self.request("GET", "/2")[0], 404)
        _, _, table = self.request("GET", "/table")
        self.assertIn("N = 1", table)

    def test_address_read_differently_by_browsers_is_rejected(self):
        # 브라우저는 a.com으로, 파이썬은 evil.example로 읽는 주소
        for bad in ("http://a.com\\@evil.example/", "http://a.com:80:80/", "http://a.com:abc/"):
            with self.subTest(bad=bad):
                status, _, body = self.shorten(bad)
                self.assertEqual(status, 400)
                self.assertIn('role="alert"', body)
        self.assertEqual(self.request("GET", "/1")[0], 404)

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

    def test_target_without_leading_slash_is_not_a_code(self):
        self.shorten("https://a.com")
        self.assertEqual(self.request("GET", "/1")[0], 302)
        for target in ("x1", "Z1?q", "1"):
            with self.subTest(target=target):
                self.assertEqual(self.request("GET", target)[:2], (404, None))

    def test_bad_url_is_400_and_keeps_the_form(self):
        for bad in ("ftp://files.example.com", "example.com", "http://a.com/a b", "", "javascript:alert(1)"):
            with self.subTest(bad=bad):
                status, _, body = self.shorten(bad)
                self.assertEqual(status, 400)
                self.assertIn("<form", body)
        self.assertEqual(self.request("GET", "/1")[0], 404)     # 아무것도 저장되지 않았다
        _, _, body = self.shorten("ftp://files.example.com")          # 무엇이 잘못됐는지 보여 준다
        self.assertIn('role="alert">http:// 또는 https:// 로 시작하는 주소만 받습니다<', body)
        self.assertEqual(self.shorten("https://a.com")[0], 200)
        self.assertEqual(self.request("GET", "/1")[1], "https://a.com/")

    def test_missing_field_is_400(self):
        self.assertEqual(self.request("POST", "/shorten", "other=1")[0], 400)
        self.assertEqual(self.request("POST", "/shorten", "")[0], 400)

    def test_too_large_body_is_413(self):
        status, _, _ = self.request("POST", "/shorten", "url=" + "a" * 70000)
        self.assertEqual(status, 413)

    def test_body_limit_is_exactly_64_kib(self):
        prefix = "url=https://a.com/&pad="
        self.assertEqual(self.request("POST", "/shorten", prefix + "a" * (65536 - len(prefix)))[0], 200)
        self.assertEqual(self.request("POST", "/shorten", prefix + "a" * (65537 - len(prefix)))[0], 413)

    def test_body_that_is_not_utf8_is_400(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.putrequest("POST", "/shorten")
            conn.putheader("Content-Type", "application/x-www-form-urlencoded")
            conn.putheader("Content-Length", "6")
            conn.endheaders(b"url=\xff\xfe")
            self.assertEqual(conn.getresponse().status, 400)
        finally:
            conn.close()
        self.assertEqual(self.request("GET", "/")[0], 200)    # 서버는 살아 있다

    def test_bad_content_length_is_400(self):
        status, _, _ = self.request("POST", "/shorten", "url=x", headers=(("Content-Length", "abc"),))
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/shorten", "url=x", headers=(("Content-Length", "-5"),))
        self.assertEqual(status, 400)
        for length in ("+17", "1_7"):                  # int()는 받지만 HTTP의 길이는 ASCII 숫자뿐이다
            status, _, _ = self.request("POST", "/shorten", "url=https://a.com",
                                        headers=(("Content-Length", length),))
            self.assertEqual(status, 400, length)

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
        # 저장된 주소가 나오는 나머지 두 곳: 코드 -> URL 테이블과 302 본문
        for path in ("/table?which=code", "/1"):
            with self.subTest(path=path):
                _, _, body = self.request("GET", path)
                self.assertNotIn("<script>alert", body)
                self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)

    def test_rejected_input_cannot_break_out_of_the_value_attribute(self):
        status, _, body = self.shorten('x" onfocus="alert(1)')
        self.assertEqual(status, 400)
        self.assertIn('value="x&quot; onfocus=&quot;alert(1)"', body)

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
        # 저장된 키 https://github.com/ 의 호너 계산: 첫 글자 h(104), 0에서 시작. 마지막 h가 칸 번호다
        self.assertIn("<td>(31 × 0 + 104) mod 11</td><td>5</td>", body)
        self.assertIn("마지막 h = 2 → 2번 칸", body)
        self.assertIn("적재율 0.27", body)             # 3/11
        if self.table == "chaining":                  # 선형 탐지 화면에는 리스트가 없다
            self.assertIn("NULL", body)
            self.assertEqual(body.count("NULL"), 11)   # 칸마다 리스트의 끝
            self.assertIn("가장 긴 리스트 1", body)

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
        self.assertIn(f'href="{self.me()}/1"', body)   # 짧은 링크는 값(URL)이 아니라 키(코드)로 만든다

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
        plain = "http://user:pw@[::1]:8000/@a;b,c!$'()*+~?q=x+y"   # 뜻이 있는 글자는 그대로 보낸다
        self.shorten(plain)
        self.assertEqual(self.request("GET", "/3")[1], plain)

    def test_code_path_ignores_query_string(self):
        self.shorten("https://a.com")
        self.assertEqual(self.request("GET", "/1?utm=x")[1], "https://a.com/")

    def test_many_urls_grow_the_table(self):
        for i in range(30):
            self.assertEqual(self.shorten(f"https://example.com/{i}")[0], 200)
        _, _, body = self.request("GET", "/table")
        self.assertIn("N = 30", body)
        self.assertEqual(self.request("GET", "/u")[1], "https://example.com/29")   # 30번째 코드는 u

    def test_shortener_is_only_touched_while_holding_the_lock(self):
        # 동시 요청 테스트는 잠금이 없어도 거의 언제나 통과한다. 잠금을 쥐고 부르는지를 직접 본다
        seen = []
        shortener, lock = self.server.shortener, self.server.lock

        def spy(name, real):
            def wrapper(*args):
                seen.append((name, lock.locked()))
                return real(*args)
            return wrapper

        shortener.shorten = spy("shorten", shortener.shorten)
        shortener.expand = spy("expand", shortener.expand)
        with mock.patch.object(server_module, "table_html", spy("table", server_module.table_html)):
            self.shorten("https://a.com")
            self.request("GET", "/1")
            self.request("GET", "/table")
        self.assertEqual(sorted(frozenset(name for name, _ in seen)), ["expand", "shorten", "table"])
        self.assertEqual([entry for entry in seen if not entry[1]], [])

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


class DefaultsTests(unittest.TestCase):
    """make serve가 쓰는 기본값. 다른 테스트는 모두 host를 직접 준다."""

    def test_make_server_binds_to_all_interfaces_by_default(self):
        parameters = inspect.signature(make_server).parameters
        self.assertEqual(parameters["host"].default, "0.0.0.0")
        self.assertEqual(parameters["port"].default, 8000)
        self.assertEqual(parameters["table"].default, "chaining")

    def test_main_without_arguments(self):
        with mock.patch.object(sys, "argv", ["server.py"]), \
                mock.patch.object(server_module, "make_server") as fake, \
                contextlib.redirect_stdout(io.StringIO()):
            fake.return_value.server_port = 8000
            fake.return_value.serve_forever.side_effect = KeyboardInterrupt
            server_module.main()
        fake.assert_called_once_with(8000, "0.0.0.0", "chaining")
        fake.return_value.server_close.assert_called_once_with()

    def test_main_with_linear_table_and_port(self):
        with mock.patch.object(sys, "argv", ["server.py", "--port", "8123", "--table", "linear"]), \
                mock.patch.object(server_module, "make_server") as fake, \
                contextlib.redirect_stdout(io.StringIO()):
            fake.return_value.server_port = 8123
            fake.return_value.serve_forever.side_effect = KeyboardInterrupt
            server_module.main()
        fake.assert_called_once_with(8123, "0.0.0.0", "linear")


if __name__ == "__main__":
    unittest.main()
