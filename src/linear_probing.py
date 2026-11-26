"""선형 탐지 해시 테이블 (SPEC.md 7절). HashTable과 같은 인터페이스다."""
from hash_table import check_sizes, horner, next_capacity


class LinearProbingHashTable:
    """충돌하면 다음 칸을 보는 해시 테이블. 마지막 칸 다음은 0번 칸이다. 키는 문자열."""

    def __init__(self, capacity=11, max_load=0.7):
        check_sizes(capacity, max_load)
        if max_load is not None and max_load >= 1:
            raise ValueError("선형 탐지의 max_load는 1보다 작아야 한다")
        self.capacity = capacity
        self.max_load = max_load
        self._keys = [None] * capacity    # None이 빈칸이다. 키는 문자열뿐이라 겹치지 않는다
        self._values = [None] * capacity
        self._n = 0

    def __len__(self):
        return self._n

    def __contains__(self, key):
        return self.find(key)[0]

    @property
    def load_factor(self):
        return self._n / self.capacity

    def _probe(self, key):
        """(칸 번호, 들여다본 칸 수).

        칸은 key가 있는 칸이거나 처음 만난 빈칸이다. 많아야 M칸을 보고,
        가득 찬 테이블에 key가 없으면 칸 번호가 -1이다.
        """
        i = horner(key, self.capacity)
        for looked in range(1, self.capacity + 1):
            if self._keys[i] is None or self._keys[i] == key:
                return i, looked
            i = (i + 1) % self.capacity
        return -1, self.capacity

    def find(self, key):
        """(찾았는가, 값, 들여다본 칸 수). 멈추게 한 빈칸도 센다."""
        i, looked = self._probe(key)
        if i >= 0 and self._keys[i] is not None:
            return True, self._values[i], looked
        return False, None, looked

    def get(self, key, default=None):
        found, value, _ = self.find(key)
        return value if found else default

    def put(self, key, value):
        i, _ = self._probe(key)
        if i < 0:
            raise OverflowError("테이블이 가득 찼다")
        if self._keys[i] is not None:
            self._values[i] = value
            return
        self._keys[i] = key
        self._values[i] = value
        self._n += 1
        if self.max_load is not None and self._n / self.capacity > self.max_load:
            self._resize(next_capacity(self.capacity))

    def _resize(self, capacity):
        old_keys, old_values = self._keys, self._values
        self.capacity = capacity
        self._keys = [None] * capacity
        self._values = [None] * capacity
        for key, value in zip(old_keys, old_values):
            if key is not None:
                i, _ = self._probe(key)
                self._keys[i] = key
                self._values[i] = value

    def slots(self):
        """0번 칸부터, 칸마다 None(빈칸) 또는 (키, 값)."""
        return [None if key is None else (key, value)
                for key, value in zip(self._keys, self._values)]
