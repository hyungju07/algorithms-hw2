"""단축 URL 웹 서버 (SPEC.md 5절). 표준 모듈 http.server만 쓴다.

    python3 src/server.py --port 8000      # 또는 make serve
"""
import argparse
import re
import threading
from html import escape as esc
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, quote

from hash_table import horner_steps
from shortener import MAX_URL_LENGTH, Shortener

MAX_BODY = 64 * 1024        # 이보다 큰 폼 본문은 413
DRAIN_LIMIT = 1024 * 1024   # 413을 보내기 전에 읽어서 버리는 양의 상한
CODE = re.compile(r"[0-9a-zA-Z]+")
HOST = re.compile(r"(?:[A-Za-z0-9.-]+|\[[0-9A-Fa-f:.]+\])(?::\d{1,5})?")
LOCATION_SAFE = "!#$%&'()*+,/:;=?@[]~"  # 여기에 없는 글자(한글, 따옴표, 꺾쇠)는 %XX로 보낸다

STYLE = """
body{font-family:system-ui,sans-serif;margin:0;background:#f8fafc;color:#0f172a;line-height:1.5}
main{max-width:960px;margin:0 auto;padding:16px}
h1{font-size:1.4rem}
a{color:#1d4ed8}
form{display:flex;gap:8px;flex-wrap:wrap}
label{flex-basis:100%;font-weight:600}
input{flex:1;min-width:0;padding:10px;font-size:1rem;border:1px solid #94a3b8;border-radius:6px}
button{padding:10px 16px;font-size:1rem;border:0;border-radius:6px;background:#2563eb;color:#fff}
.error{color:#b91c1c;font-weight:600}
.short a{font-size:1.3rem;font-weight:700}
.short a,.url,.key{word-break:break-all}
.ht{border-collapse:collapse;width:100%}
.ht>tbody>tr>th{width:2.5em;padding:8px;text-align:right;vertical-align:top;color:#475569;font-family:monospace}
.ht>tbody>tr{border-top:1px solid #e2e8f0}
.chain{display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start;padding:4px 0}
.node{border:1px solid #94a3b8;border-radius:6px;background:#fff;padding:6px 8px;max-width:100%;box-sizing:border-box}
.node summary{cursor:pointer}
.key{font-family:monospace;font-weight:600}
.val{margin:0 10px;color:#334155}
.arrow,.null{color:#64748b;font-family:monospace;padding-top:7px}
.steps{border-collapse:collapse;margin-top:6px;font-size:.85rem}
.steps td,.steps th{border:1px solid #cbd5e1;padding:2px 6px;text-align:right}
.steps caption{text-align:left;color:#475569;white-space:nowrap}
.why{font-weight:600;margin:6px 0 0}
"""


def page(title, body):
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{esc(title)}</title><style>{STYLE}</style></head>"
            f"<body><main><h1>{esc(title)}</h1>{body}</main></body></html>")


def form_html(value="", error=""):
    alert = f'<p class="error" role="alert">{esc(error)}</p>' if error else ""
    return (f'{alert}<form method="post" action="/shorten">'
            '<label for="url">줄일 주소</label>'
            f'<input id="url" name="url" type="url" required maxlength="{MAX_URL_LENGTH}" '
            f'placeholder="https://example.com/아주/긴/주소" value="{esc(value[:MAX_URL_LENGTH])}">'
            '<button type="submit">줄이기</button></form>'
            '<p><a href="/table">해시 테이블 보기</a></p>')


def steps_html(key, m):
    """호너 해시를 한 글자씩 계산한 표. 마지막 h가 그 키의 칸 번호다."""
    steps = horner_steps(key, m)
    rows = "".join(
        f"<tr><td>{i}</td><td><code>{esc(ch)}</code></td><td>{code}</td>"
        f"<td>(31 × {before} + {code}) mod {m}</td><td>{after}</td></tr>"
        for i, (ch, code, before, after) in enumerate(steps, start=1))
    last = steps[-1][3] if steps else 0
    return ('<table class="steps"><caption>h ← (31 × h + 글자 코드) mod M, h는 0에서 시작</caption>'
            "<tr><th>#</th><th>글자</th><th>코드</th><th>계산</th><th>h</th></tr>"
            f'{rows}</table><p class="why">마지막 h = {last} → {last}번 칸</p>')


def node_html(key, value, base, m, which):
    """노드 하나. 요약 줄에 키, 값, 짧은 링크가 보이고 펼치면 계산 근거가 나온다."""
    if which == "code":     # 코드 -> URL 테이블: 키가 코드
        code, label = key, f'URL <span class="url">{esc(value)}</span>'
    else:                   # URL -> 코드 테이블: 값이 코드
        code, label = value, f"코드 <code>{esc(value)}</code>"
    link = esc(f"{base}/{code}")
    return (f'<details class="node"><summary><span class="key">{esc(key)}</span>'
            f'<span class="val">{label}</span><a href="{link}">{link}</a></summary>'
            f"{steps_html(key, m)}</details>")


def table_html(shortener, base, which):
    # ponytail: 모든 칸과 모든 계산 표를 한 번에 그린다. URL이 수천 개를 넘으면 쪽을 나눈다.
    table = shortener.by_code if which == "code" else shortener.by_url
    m = table.capacity
    rows = []
    longest = 0
    for index, chain in enumerate(table.buckets()):
        longest = max(longest, len(chain))
        nodes = "".join(node_html(key, value, base, m, which) + '<span class="arrow">→</span>'
                        for key, value in chain)
        rows.append(f'<tr><th>{index}</th><td><div class="chain">{nodes}'
                    '<span class="null">NULL</span></div></td></tr>')
    name = "코드 → URL" if which == "code" else "URL → 코드"
    return (f'<p><a href="/">처음으로</a> · <a href="/table">URL → 코드</a> · '
            f'<a href="/table?which=code">코드 → URL</a></p>'
            f"<p><strong>{name} 테이블</strong> · 개별 체이닝 · N = {len(table)} · M = {m} · "
            f"적재율 {table.load_factor:.2f} · 가장 긴 리스트 {longest}</p>"
            "<p>왼쪽 숫자가 칸 번호입니다. 같은 칸에 떨어진 키는 연결 리스트로 이어집니다. "
            "노드를 누르면 그 칸에 떨어진 이유(호너 해시 계산)가 펼쳐집니다.</p>"
            f'<table class="ht"><tbody>{"".join(rows)}</tbody></table>')


class Handler(BaseHTTPRequestHandler):
    timeout = 10  # 말없이 붙어만 있는 연결은 끊는다

    def log_message(self, format, *args):
        if not self.server.quiet:
            super().log_message(format, *args)

    def base_url(self):
        """짧은 링크 앞에 붙일 주소. 프록시가 넘겨준 주소를 먼저 쓴다."""
        proto = self.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or ""
        host = host.split(",")[0].strip()
        if proto not in ("http", "https"):
            proto = "http"
        if not HOST.fullmatch(host):
            host = f"localhost:{self.server.server_port}"
        return f"{proto}://{host}"

    def send_page(self, status, title, body, location=None):
        data = page(title, body).encode("utf-8")
        self.send_response(status)
        if location is not None:
            self.send_header("Location", location)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def not_found(self):
        self.send_page(404, "찾을 수 없습니다",
                       '<p>그런 짧은 링크는 없습니다.</p><p><a href="/">처음으로</a></p>')

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/":
            self.send_page(200, "URL 단축기", form_html())
        elif path == "/table":
            which = "code" if ("which", "code") in parse_qsl(query) else "url"
            with self.server.lock:
                body = table_html(self.server.shortener, self.base_url(), which)
            self.send_page(200, "해시 테이블", body)
        else:
            code = path[1:]
            url = None
            if CODE.fullmatch(code):
                with self.server.lock:
                    url = self.server.shortener.expand(code)
            if url is None:
                self.not_found()
            else:
                self.send_page(302, "이동합니다", f'<p><a href="{esc(url)}">{esc(url)}</a></p>',
                               location=quote(url, safe=LOCATION_SAFE))

    def do_POST(self):
        if self.path.partition("?")[0] != "/shorten":
            return self.not_found()
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if length < 0:
            return self.send_page(400, "URL 단축기", form_html(error="요청의 길이를 알 수 없습니다."))
        if length > MAX_BODY:
            # 읽지 않고 닫으면 보내던 쪽이 응답을 받기 전에 연결이 끊긴다
            self.rfile.read(min(length, DRAIN_LIMIT))
            return self.send_page(413, "URL 단축기", form_html(error="요청이 너무 큽니다."))
        try:
            fields = parse_qsl(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
        except UnicodeDecodeError:
            return self.send_page(400, "URL 단축기", form_html(error="요청을 읽을 수 없습니다."))
        url = None
        for name, value in fields:
            if name == "url":
                url = value
                break
        if url is None:
            return self.send_page(400, "URL 단축기", form_html(error="주소를 넣어 주세요."))
        try:
            with self.server.lock:
                code = self.server.shortener.shorten(url)
                url = self.server.shortener.expand(code)
        except ValueError as error:
            return self.send_page(400, "URL 단축기", form_html(url, str(error)))
        link = esc(f"{self.base_url()}/{code}")
        self.send_page(200, "짧은 링크가 만들어졌습니다",
                       f'<p class="short"><a href="{link}">{link}</a></p>'
                       f'<p>원래 주소: <span class="url">{esc(url)}</span></p>'
                       '<p><a href="/">다른 주소 줄이기</a> · <a href="/table">해시 테이블 보기</a></p>')


class Server(ThreadingHTTPServer):
    request_queue_size = 128  # 기본값 5로는 한꺼번에 몰린 연결을 놓친다


def make_server(port=8000, host="0.0.0.0", quiet=False):
    server = Server((host, port), Handler)
    server.shortener = Shortener()
    server.lock = threading.Lock()  # 해시 테이블은 한 번에 한 요청만 건드린다
    server.quiet = quiet
    return server


def main():
    parser = argparse.ArgumentParser(description="URL 단축기 웹 서버")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    server = make_server(args.port, args.host)
    print(f"http://localhost:{server.server_port} 에서 기다립니다. 끄려면 Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 끕니다.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
