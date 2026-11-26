"""URL 단축기 (SPEC.md 4절). 코드는 일련번호를 base62로 바꾼 것이다."""
from urllib.parse import urlsplit

from base62 import encode
from hash_table import HashTable

MAX_URL_LENGTH = 2048
RESERVED = ("table", "shorten")  # 서버 경로와 겹치는 코드


def clean_url(url):
    """앞뒤 공백을 자르고 한 모양으로 맞춘 URL을 돌려준다. 받을 수 없는 주소면 ValueError."""
    if not isinstance(url, str):
        raise TypeError("URL은 문자열이어야 한다")
    url = url.strip()
    if url == "":
        raise ValueError("주소가 비어 있습니다")
    for ch in url:
        if ch.isspace() or ord(ch) < 32 or 127 <= ord(ch) < 160:  # 공백, C0, DEL, C1
            raise ValueError("주소 가운데에 공백이나 제어 문자가 있습니다")
    if "\\" in url:  # 브라우저와 파이썬이 호스트를 다르게 읽는다
        raise ValueError("주소에 역슬래시를 쓸 수 없습니다")
    try:
        parts = urlsplit(url)
    except ValueError:  # 대괄호가 안 맞는 주소 등
        raise ValueError("주소 형식이 잘못되었습니다") from None
    if parts.scheme not in ("http", "https"):
        raise ValueError("http:// 또는 https:// 로 시작하는 주소만 받습니다")
    if not parts.hostname:
        raise ValueError("주소에 호스트가 없습니다")
    url = normalize(url)
    if len(url) > MAX_URL_LENGTH:  # 맞춘 뒤에 잰다. 저장되는 주소는 언제나 이 길이 이하다
        raise ValueError(f"주소가 너무 깁니다 ({MAX_URL_LENGTH}자까지)")
    return url


def normalize(url):
    """같은 곳을 가리키는 주소를 한 모양으로 맞춘다. clean_url의 검사를 통과한 주소만 받는다.

    스킴과 호스트의 ASCII 대문자는 소문자로, 기본 포트는 빼고, 경로가 없으면 /를 붙인다.
    경로·쿼리·# 뒤·사용자 정보는 뜻이 바뀔 수 있어 건드리지 않는다.
    포트가 0~65535의 숫자가 아니면 ValueError.
    """
    scheme, _, rest = url.partition("://")
    scheme = scheme.lower()
    end = len(rest)  # 호스트 부분은 /, ?, # 중 가장 먼저 나오는 것 앞까지다
    for mark in "/?#":
        at = rest.find(mark)
        if 0 <= at < end:
            end = at
    userinfo, at_sign, hostport = rest[:end].rpartition("@")
    if hostport.startswith("["):  # IPv6 주소는 대괄호 안에 :이 있다
        host, bracket, after = hostport.partition("]")
        host += bracket
        colon, port = after[:1], after[1:]
        if after and colon != ":":
            raise ValueError("주소 형식이 잘못되었습니다")
    else:
        host, colon, port = hostport.partition(":")
    if port and not (port.isascii() and port.isdigit() and int(port) <= 65535):
        raise ValueError("포트는 0부터 65535까지의 숫자여야 합니다")
    if port in ("", "80" if scheme == "http" else "443"):  # 번호 없는 포트와 기본 포트는 뺀다
        colon = port = ""
    # ASCII만 소문자로 바꾼다. 전체를 lower()하면 그리스어 Σ처럼 다른 도메인이 되는 글자가 있다
    host = "".join(ch.lower() if ch.isascii() else ch for ch in host)
    tail = rest[end:]
    if not tail.startswith("/"):
        tail = "/" + tail
    return f"{scheme}://{userinfo}{at_sign}{host}{colon}{port}{tail}"


class Shortener:
    def __init__(self, start=1, table_class=HashTable):
        if isinstance(start, bool) or not isinstance(start, int) or start < 1:
            raise ValueError("start는 1 이상의 정수여야 한다")
        self.by_url = table_class()   # URL -> 코드
        self.by_code = table_class()  # 코드 -> URL
        self._next = start

    def __len__(self):
        return len(self.by_code)

    def shorten(self, url):
        url = clean_url(url)
        code = self.by_url.get(url)
        if code is not None:
            return code
        code = encode(self._next)
        while code in RESERVED:
            self._next += 1
            code = encode(self._next)
        self._next += 1
        self.by_url.put(url, code)
        self.by_code.put(code, url)
        return code

    def expand(self, code):
        """저장된(한 모양으로 맞춘) URL. 준 적 없는 코드는 None."""
        return self.by_code.get(code)
