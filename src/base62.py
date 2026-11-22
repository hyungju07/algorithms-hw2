"""base62 인코딩: 0 이상의 정수 <-> 0-9, a-z, A-Z 순서의 62진법 문자열."""

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode(n):
    """0 이상의 정수 n을 base62 문자열로 바꾼다. encode(0)은 "0"이다."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("encode()는 정수만 받는다")
    if n < 0:
        raise ValueError("encode()는 0 이상의 정수만 받는다")
    if n == 0:
        return ALPHABET[0]  # 아래 반복문은 0에서 한 번도 돌지 않아 ""가 된다
    digits = []
    while n > 0:
        n, r = divmod(n, BASE)
        digits.append(ALPHABET[r])
    return "".join(reversed(digits))  # 나머지를 아래에서 위로 읽는다


def decode(s):
    """base62 문자열을 정수로 되돌린다. "007"처럼 앞에 0이 붙어도 받는다."""
    if not isinstance(s, str):
        raise TypeError("decode()는 문자열만 받는다")
    if s == "":
        raise ValueError("빈 문자열은 base62 수가 아니다")
    n = 0
    for ch in s:
        d = ALPHABET.find(ch)
        if d < 0:
            raise ValueError(f"base62 글자가 아니다: {ch!r}")
        n = n * BASE + d
    return n
