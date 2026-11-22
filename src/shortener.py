"""URL 단축기 (SPEC.md 4절). 코드는 일련번호를 base62로 바꾼 것이다."""
from urllib.parse import urlsplit

from base62 import encode
from hash_table import HashTable

MAX_URL_LENGTH = 2048
RESERVED = ("table", "shorten")  # 서버 경로와 겹치는 코드


def clean_url(url):
    """앞뒤 공백을 자른 URL을 돌려준다. 받을 수 없는 주소면 ValueError."""
    if not isinstance(url, str):
        raise TypeError("URL은 문자열이어야 한다")
    url = url.strip()
    if url == "":
        raise ValueError("주소가 비어 있습니다")
    if len(url) > MAX_URL_LENGTH:
        raise ValueError(f"주소가 너무 깁니다 ({MAX_URL_LENGTH}자까지)")
    for ch in url:
        if ch.isspace() or ord(ch) < 32 or ord(ch) == 127:
            raise ValueError("주소 가운데에 공백이나 제어 문자가 있습니다")
    try:
        parts = urlsplit(url)
    except ValueError:  # 대괄호가 안 맞는 주소 등
        raise ValueError("주소 형식이 잘못되었습니다") from None
    if parts.scheme not in ("http", "https"):
        raise ValueError("http:// 또는 https:// 로 시작하는 주소만 받습니다")
    if not parts.hostname:
        raise ValueError("주소에 호스트가 없습니다")
    return url


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
        """원래 URL. 준 적 없는 코드는 None."""
        return self.by_code.get(code)
