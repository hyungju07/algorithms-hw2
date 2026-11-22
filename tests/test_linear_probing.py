"""SPEC.md 7절 57~68번. 같은 테스트를 선형 탐지 테이블에도 돌리고, 선형 탐지만의 사례를 더한다.

M = 11에서 한 글자 키의 칸: a, l, w, V, K는 9번, b, m, x는 10번, c는 0번, d는 1번, e는 2번.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# 클래스를 이 모듈의 이름으로 들여오면 같은 테스트가 두 번 수집된다. 모듈째 들여온다.
import test_hash_table
import test_server
import test_shortener
from hash_table import HashTable, horner
from linear_probing import LinearProbingHashTable
from shortener import Shortener


# 57
class LinearProbingContractTests(test_hash_table.HashTableContractTests):
    table_class = LinearProbingHashTable


class LinearProbingTests(unittest.TestCase):
    def nine(self):
        """M = 11에서 9번 칸으로 가는 a, l, w, V를 차례로 넣은 테이블."""
        t = LinearProbingHashTable(capacity=11, max_load=None)
        for i, key in enumerate(("a", "l", "w", "V"), start=1):
            t.put(key, i)
        return t

    # 58
    def test_find_in_empty_table_looks_at_one_slot(self):
        self.assertEqual(LinearProbingHashTable().find("nope"), (False, None, 1))

    # 59, 60
    def test_collision_moves_to_next_slot_and_wraps_around(self):
        slots = self.nine().slots()
        self.assertEqual(len(slots), 11)
        self.assertEqual(slots[9], ("a", 1))
        self.assertEqual(slots[10], ("l", 2))
        self.assertEqual(slots[0], ("w", 3))      # 끝 칸 다음은 0번 칸
        self.assertEqual(slots[1], ("V", 4))
        self.assertEqual(slots[2:9], [None] * 7)

    def test_wrap_around_from_the_last_slot(self):
        t = LinearProbingHashTable(capacity=11, max_load=None)
        for key in ("b", "m", "x"):                # 모두 10번(마지막) 칸
            t.put(key, key.upper())
        self.assertEqual(t.slots()[10], ("b", "B"))
        self.assertEqual(t.slots()[0], ("m", "M"))
        self.assertEqual(t.slots()[1], ("x", "X"))
        self.assertEqual([t.get(k) for k in ("b", "m", "x")], ["B", "M", "X"])
        self.assertEqual(t.find("x"), (True, "X", 3))

    # 61
    def test_probed_slots(self):
        t = self.nine()
        self.assertEqual(t.find("a"), (True, 1, 1))
        self.assertEqual(t.find("l"), (True, 2, 2))
        self.assertEqual(t.find("w"), (True, 3, 3))
        self.assertEqual(t.find("V"), (True, 4, 4))
        self.assertEqual(t.find("K"), (False, None, 5))   # 9, 10, 0, 1을 지나 2번 빈칸
        self.assertEqual(t.find("c"), (False, None, 3))   # 0번 w, 1번 V, 2번 빈칸
        self.assertEqual(t.find("d"), (False, None, 2))
        self.assertEqual(t.find("e"), (False, None, 1))   # 2번은 처음부터 빈칸

    def test_a_key_can_be_pushed_out_of_its_home_slot_by_another_cluster(self):
        t = self.nine()
        t.put("c", "0번이 집")                             # 0번은 w, 1번은 V가 차지했다
        self.assertEqual(t.slots()[2], ("c", "0번이 집"))
        self.assertEqual(t.find("c"), (True, "0번이 집", 3))

    # 62
    def test_full_table(self):
        t = LinearProbingHashTable(capacity=4, max_load=None)
        keys = ("p", "q", "r", "s")
        for i, key in enumerate(keys):
            t.put(key, i)
        self.assertEqual(len(t), 4)
        self.assertEqual(t.load_factor, 1.0)
        self.assertNotIn(None, t.slots())
        for i, key in enumerate(keys):
            self.assertEqual(t.get(key), i)
        self.assertEqual(t.find("없는 키"), (False, None, 4))   # 네 칸을 다 보고 끝난다
        self.assertNotIn("없는 키", t)
        self.assertEqual(t.get("없는 키", "기본값"), "기본값")
        before = t.slots()
        with self.assertRaises(OverflowError):
            t.put("t", 99)
        self.assertEqual(t.slots(), before)
        self.assertEqual(len(t), 4)
        t.put("q", "바뀜")                                     # 있는 키는 가득 차도 바꿀 수 있다
        self.assertEqual(t.get("q"), "바뀜")
        self.assertEqual(len(t), 4)
        self.assertEqual(t.capacity, 4)

    def test_full_table_of_one(self):
        t = LinearProbingHashTable(capacity=1, max_load=None)
        t.put("only", 1)
        self.assertEqual(t.find("only"), (True, 1, 1))
        self.assertEqual(t.find("other"), (False, None, 1))
        with self.assertRaises(OverflowError):
            t.put("other", 2)

    def test_fill_exactly_to_capacity_without_error(self):
        t = LinearProbingHashTable(capacity=11, max_load=None)
        for i in range(11):
            t.put(f"k{i}", i)
        self.assertEqual(len(t), 11)
        for i in range(11):
            self.assertEqual(t.get(f"k{i}"), i)

    # 63
    def test_max_load_must_be_below_one(self):
        for bad in (1, 1.0, 1.5, 4):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    LinearProbingHashTable(max_load=bad)
        LinearProbingHashTable(max_load=0.99)

    # 64
    def test_default_max_load_is_half(self):
        t = LinearProbingHashTable()
        for i in range(5):
            t.put(f"k{i}", i)
        self.assertEqual(t.capacity, 11)       # 5/11 = 0.45
        t.put("k5", 5)
        self.assertEqual(t.capacity, 23)       # 6/11 = 0.55 > 0.5
        for i in range(6):
            self.assertEqual(t.get(f"k{i}"), i)

    # 65
    def test_no_holes_between_home_slot_and_actual_slot(self):
        for max_load in (0.5, 0.9, None):
            with self.subTest(max_load=max_load):
                t = LinearProbingHashTable(capacity=331, max_load=max_load)
                for i in range(300):
                    t.put(f"https://example.com/{i}", i)
                slots = t.slots()
                self.assertEqual(len(slots), t.capacity)
                self.assertEqual(sum(1 for s in slots if s is not None), len(t))
                for index, slot in enumerate(slots):
                    if slot is None:
                        continue
                    key, value = slot
                    home = horner(key, t.capacity)
                    distance = (index - home) % t.capacity
                    for step in range(distance):
                        self.assertIsNotNone(slots[(home + step) % t.capacity])
                    self.assertEqual(t.find(key), (True, value, distance + 1))

    # 66
    def test_update_keeps_the_slot(self):
        t = self.nine()
        before = [s and s[0] for s in t.slots()]
        t.put("w", "바뀜")
        self.assertEqual([s and s[0] for s in t.slots()], before)
        self.assertEqual(t.slots()[0], ("w", "바뀜"))
        self.assertEqual(len(t), 4)

    def test_same_keys_same_answers_as_chaining(self):
        chaining, probing = HashTable(), LinearProbingHashTable()
        keys = [f"https://example.com/{i % 150}" for i in range(400)]   # 중복 포함
        for i, key in enumerate(keys):
            chaining.put(key, i)
            probing.put(key, i)
        self.assertEqual(len(probing), len(chaining))
        for key in keys + ["https://example.com/없음", ""]:
            self.assertEqual(probing.find(key)[:2], chaining.find(key)[:2])


# 67
class LinearShortenerTests(test_shortener.ShortenerTests):
    def make(self, **kwargs):
        return Shortener(table_class=LinearProbingHashTable, **kwargs)

    def test_it_really_uses_linear_probing(self):
        s = self.make()
        self.assertIsInstance(s.by_url, LinearProbingHashTable)
        self.assertIsInstance(s.by_code, LinearProbingHashTable)
        self.assertIsNot(s.by_url, s.by_code)


class DefaultShortenerTests(unittest.TestCase):
    def test_default_table_is_chaining(self):
        self.assertIsInstance(Shortener().by_url, HashTable)
        self.assertIsInstance(Shortener().by_code, HashTable)


# 68
class LinearServerTests(test_server.ServerTests):
    table = "linear"

    def test_table_page_shows_slots_and_probes(self):
        # M = 11에서 두 주소 모두 4번 칸이다. 둘째는 5번 칸으로 밀린다.
        self.assertEqual(horner("https://www.yonsei.ac.kr", 11), 4)
        self.assertEqual(horner("https://library.yonsei.ac.kr", 11), 4)
        self.shorten("https://www.yonsei.ac.kr")
        self.shorten("https://library.yonsei.ac.kr")
        status, _, body = self.request("GET", "/table")
        self.assertEqual(status, 200)
        self.assertIn("선형 탐지", body)
        self.assertNotIn("개별 체이닝", body)
        self.assertIn("빈칸", body)
        self.assertNotIn("NULL", body)
        self.assertIn("처음 칸 4 → 지금 칸 4 · 들여다본 칸 1", body)
        self.assertIn("처음 칸 4 → 지금 칸 5 · 들여다본 칸 2", body)
        self.assertIn("가장 긴 무리 2", body)

    def test_server_really_uses_linear_probing(self):
        self.assertIsInstance(self.server.shortener.by_url, LinearProbingHashTable)


class ServerTableChoiceTests(unittest.TestCase):
    def test_chaining_page_says_chaining(self):
        server = test_server.make_server(port=0, host="127.0.0.1", quiet=True)
        try:
            self.assertIsInstance(server.shortener.by_url, HashTable)
        finally:
            server.server_close()

    def test_unknown_table_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            test_server.make_server(port=0, host="127.0.0.1", table="tree", quiet=True)


if __name__ == "__main__":
    unittest.main()
