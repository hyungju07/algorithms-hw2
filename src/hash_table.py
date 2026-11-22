"""개별 체이닝 해시 테이블과 호너 해시 함수 (SPEC.md 3절)."""

R = 31


def horner(key, m):
    """h <- (31*h + 글자 코드) mod m 을 글자마다 한다. 결과는 0 이상 m-1 이하."""
    if not isinstance(key, str):
        raise TypeError("키는 문자열이어야 한다")
    h = 0
    for ch in key:
        h = (R * h + ord(ch)) % m
    return h


def horner_steps(key, m):
    """같은 계산의 중간 과정. 글자마다 (글자, 글자 코드, 계산 전 h, 계산 후 h)."""
    if not isinstance(key, str):
        raise TypeError("키는 문자열이어야 한다")
    steps = []
    h = 0
    for ch in key:
        after = (R * h + ord(ch)) % m
        steps.append((ch, ord(ch), h, after))
        h = after
    return steps


def check_sizes(capacity, max_load):
    """두 테이블이 함께 쓰는 생성자 인자 검사."""
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise ValueError("capacity는 1 이상의 정수여야 한다")
    if max_load is not None and not max_load > 0:
        raise ValueError("max_load는 0보다 큰 수이거나 None이어야 한다")


def _is_prime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def next_capacity(m):
    """2m+1 이상의 가장 작은 소수. 31의 배수면 마지막 글자만 보는 해시가 되므로 건너뛴다."""
    c = 2 * m + 1
    while not _is_prime(c) or c % R == 0:
        c += 1
    return c


class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, next):
        self.key = key
        self.value = value
        self.next = next


class HashTable:
    """칸마다 단일 연결 리스트를 두는 해시 테이블. 키는 문자열."""

    def __init__(self, capacity=11, max_load=0.75):
        check_sizes(capacity, max_load)
        self.capacity = capacity
        self.max_load = max_load
        self._heads = [None] * capacity
        self._n = 0

    def __len__(self):
        return self._n

    def __contains__(self, key):
        return self.find(key)[0]

    @property
    def load_factor(self):
        return self._n / self.capacity

    def find(self, key):
        """(찾았는가, 값, 비교한 노드 수). 빈 칸에서는 비교한 노드가 0개다."""
        cost = 0
        node = self._heads[horner(key, self.capacity)]
        while node is not None:
            cost += 1
            if node.key == key:
                return True, node.value, cost
            node = node.next
        return False, None, cost

    def get(self, key, default=None):
        found, value, _ = self.find(key)
        return value if found else default

    def put(self, key, value):
        i = horner(key, self.capacity)
        node = self._heads[i]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next
        self._heads[i] = _Node(key, value, self._heads[i])  # 맨 앞에 붙인다
        self._n += 1
        if self.max_load is not None and self._n / self.capacity > self.max_load:
            self._resize(next_capacity(self.capacity))

    def _resize(self, capacity):
        old = self._heads
        self.capacity = capacity
        self._heads = [None] * capacity
        for head in old:
            node = head
            while node is not None:
                following = node.next
                i = horner(node.key, capacity)
                node.next = self._heads[i]
                self._heads[i] = node
                node = following

    def buckets(self):
        """0번 칸부터, 칸마다 (키, 값)을 리스트 순서대로 담은 list."""
        result = []
        for head in self._heads:
            chain = []
            node = head
            while node is not None:
                chain.append((node.key, node.value))
                node = node.next
            result.append(chain)
        return result
