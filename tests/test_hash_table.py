"""SPEC.md 6절 8~29번. 충돌은 흉내 내지 않고 실제 키로 만든다.

한 글자 키의 호너 해시는 ord(c) mod M이다. M = 11에서
  a(97), l(108), w(119), V(86)는 9번 칸, b(98)는 10번 칸, c(99)는 0번 칸이다.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hash_table import HashTable, horner, horner_steps


def polynomial(key, m):
    """호너 방식을 쓰지 않고 다항식을 그대로 계산한 값. 기댓값을 따로 구하는 데 쓴다."""
    n = len(key)
    return sum(ord(c) * 31 ** (n - 1 - i) for i, c in enumerate(key)) % m


def is_prime(n):
    return n > 1 and all(n % d for d in range(2, int(n ** 0.5) + 1))


class HornerTests(unittest.TestCase):
    def test_empty_string_is_zero(self):
        self.assertEqual(horner("", 97), 0)

    def test_single_character_is_code_mod_m(self):
        self.assertEqual(horner("a", 11), 97 % 11)
        self.assertEqual(horner("b", 11), 10)
        self.assertEqual(horner("c", 11), 0)

    def test_order_matters_lecture_values(self):
        # 주제 08의 01_hash_function 출력 (M = 97)
        self.assertEqual(horner("stop", 97), 9)
        self.assertEqual(horner("pots", 97), 79)
        self.assertEqual(horner("tops", 97), 3)
        self.assertEqual(horner("opts", 97), 58)

    def test_known_collisions(self):
        self.assertEqual(horner("spot", 97), 49)
        self.assertEqual(horner("post", 97), 49)
        for m in (5, 11, 97, 4093):
            self.assertEqual(horner("Aa", m), horner("BB", m))  # 65*31+97 == 66*31+66

    def test_matches_polynomial(self):
        for key in ("https://www.yonsei.ac.kr", "a" * 3000, "한글 키 🙂", "x"):
            for m in (1, 2, 11, 97, 4093):
                with self.subTest(key=key[:20], m=m):
                    self.assertEqual(horner(key, m), polynomial(key, m))

    def test_result_is_in_range(self):
        for m in (1, 2, 7, 11, 4093):
            for key in ("", "a", "zzzz", "https://github.com", "가나다"):
                self.assertTrue(0 <= horner(key, m) < m)

    def test_m_31_only_sees_last_character(self):
        # 크기 조정이 31의 배수를 건너뛰는 이유
        self.assertEqual(horner("https://a.com/x", 31), horner("ftp://zzz/x", 31))

    def test_non_string_key_raises_type_error(self):
        for bad in (1, None, b"a", ("a",), 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    horner(bad, 11)

    def test_steps_end_at_the_hash(self):
        key, m = "https://github.com", 11
        steps = horner_steps(key, m)
        self.assertEqual(len(steps), len(key))
        self.assertEqual(steps[-1][3], horner(key, m))
        self.assertEqual(horner_steps("", m), [])

    def test_each_step_follows_the_formula(self):
        prev = 0
        for ch, code, before, after in horner_steps("stop", 97):
            self.assertEqual(code, ord(ch))
            self.assertEqual(before, prev)
            self.assertEqual(after, (31 * before + code) % 97)
            prev = after
        self.assertEqual(prev, 9)


class HashTableContractTests(unittest.TestCase):
    """충돌을 어떻게 풀든 해시 테이블이면 지켜야 하는 것."""

    table_class = HashTable

    def make(self, **kwargs):
        return self.table_class(**kwargs)

    # 8
    def test_empty_table(self):
        t = self.make()
        self.assertEqual(len(t), 0)
        self.assertIsNone(t.get("nope"))
        self.assertEqual(t.get("nope", "기본값"), "기본값")
        self.assertNotIn("nope", t)
        self.assertEqual(t.find("nope")[:2], (False, None))
        self.assertEqual(t.capacity, 11)
        self.assertEqual(t.load_factor, 0)

    # 9
    def test_put_then_get(self):
        t = self.make()
        t.put("https://github.com", "1")
        self.assertEqual(t.get("https://github.com"), "1")
        self.assertIn("https://github.com", t)
        self.assertEqual(len(t), 1)
        found, value, cost = t.find("https://github.com")
        self.assertEqual((found, value), (True, "1"))
        self.assertGreaterEqual(cost, 1)

    # 10
    def test_same_key_updates_value(self):
        t = self.make()
        t.put("k", 1)
        t.put("k", 2)
        self.assertEqual(t.get("k"), 2)
        self.assertEqual(len(t), 1)

    # 11
    def test_none_value_is_still_present(self):
        t = self.make()
        t.put("k", None)
        self.assertIsNone(t.get("k", "기본값"))
        self.assertIn("k", t)
        self.assertEqual(t.find("k")[:2], (True, None))
        self.assertEqual(len(t), 1)

    # 12
    def test_empty_string_key(self):
        t = self.make()
        t.put("", "빈 키")
        self.assertEqual(t.get(""), "빈 키")
        self.assertIn("", t)

    # 13
    def test_non_string_key_raises_type_error(self):
        t = self.make()
        for bad in (1, None, b"a", ("a",)):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    t.put(bad, 1)
                with self.assertRaises(TypeError):
                    t.get(bad)
                with self.assertRaises(TypeError):
                    t.find(bad)
                with self.assertRaises(TypeError):
                    bad in t
        self.assertEqual(len(t), 0)

    def test_values_can_be_anything(self):
        t = self.make()
        for i, value in enumerate((0, "", [], (1, 2), 3.5, False)):
            t.put(f"k{i}", value)
            self.assertEqual(t.get(f"k{i}", "기본값"), value)

    # 16
    def test_colliding_keys_all_survive(self):
        t = self.make(capacity=11, max_load=None)
        for i, key in enumerate(("a", "l", "w", "V", "Aa", "BB")):
            t.put(key, i)
        for i, key in enumerate(("a", "l", "w", "V", "Aa", "BB")):
            self.assertEqual(t.get(key), i)
        self.assertEqual(len(t), 6)
        self.assertNotIn("K", t)  # K(75)도 9번 칸이지만 넣지 않았다

    def test_update_of_a_colliding_key_touches_only_that_key(self):
        t = self.make(capacity=11, max_load=None)
        for key in ("a", "l", "w"):
            t.put(key, key.upper())
        t.put("l", "바뀜")
        self.assertEqual([t.get(k) for k in ("a", "l", "w")], ["A", "바뀜", "W"])
        self.assertEqual(len(t), 3)

    # 19
    def test_bad_capacity_raises_value_error(self):
        for bad in (0, -1, 1.5, "11", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.make(capacity=bad)

    def test_bad_max_load_raises_value_error(self):
        for bad in (0, -0.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.make(max_load=bad)

    # 20
    def test_grows_when_load_exceeds_max_load(self):
        t = self.make(capacity=11, max_load=0.75)
        keys = [f"https://example.com/{i}" for i in range(9)]
        for i, key in enumerate(keys[:8]):
            t.put(key, i)
        self.assertEqual(t.capacity, 11)       # 8/11 = 0.73
        t.put(keys[8], 8)
        self.assertEqual(t.capacity, 23)       # 9/11 = 0.82 > 0.75
        self.assertEqual(len(t), 9)
        for i, key in enumerate(keys):
            self.assertEqual(t.get(key), i)
        self.assertAlmostEqual(t.load_factor, 9 / 23)

    # 21
    def test_does_not_grow_at_exactly_max_load(self):
        t = self.make(capacity=4, max_load=0.75)
        for key in ("p", "q", "r"):
            t.put(key, 1)
        self.assertEqual(t.capacity, 4)        # 3/4 == 0.75, 넘지 않았다
        t.put("s", 1)
        self.assertEqual(t.capacity, 11)       # 2*4+1 = 9 이상의 가장 작은 소수
        for key in ("p", "q", "r", "s"):
            self.assertIn(key, t)

    # 22
    def test_update_never_resizes(self):
        t = self.make(capacity=4, max_load=0.75)
        for key in ("p", "q", "r"):
            t.put(key, 1)
        for _ in range(10):
            t.put("p", 2)
        self.assertEqual(t.capacity, 4)
        self.assertEqual(len(t), 3)

    # 24
    def test_grown_capacity_is_prime_and_skips_31(self):
        t = self.make(capacity=15, max_load=0.5)
        for i in range(8):
            t.put(f"k{i}", i)
        self.assertEqual(t.capacity, 37)       # 2*15+1 = 31은 건너뛴다
        t = self.make()
        seen = [t.capacity]
        for i in range(2000):
            t.put(f"https://example.com/{i}", i)
            if t.capacity != seen[-1]:
                seen.append(t.capacity)
        self.assertGreater(len(seen), 5)
        for m in seen[1:]:
            self.assertTrue(is_prime(m), m)
            self.assertNotEqual(m % 31, 0)
        self.assertEqual(seen[:5], [11, 23, 47, 97, 197])

    def test_capacity_one_grows_to_three(self):
        t = self.make(capacity=1, max_load=0.5)
        t.put("a", 1)
        self.assertEqual(t.capacity, 3)        # 2*1+1 = 3
        self.assertEqual(t.get("a"), 1)

    # 25
    def test_capacity_one(self):
        t = self.make(capacity=1)
        for i in range(30):
            t.put(f"k{i}", i)
        for i in range(30):
            self.assertEqual(t.get(f"k{i}"), i)
        self.assertEqual(len(t), 30)

    # 26
    def test_thousand_keys(self):
        t = self.make()
        for i in range(1000):
            t.put(f"https://example.com/page/{i}", i)
        self.assertEqual(len(t), 1000)
        for i in range(1000):
            self.assertEqual(t.get(f"https://example.com/page/{i}"), i)
        for i in range(1000, 1200):
            self.assertNotIn(f"https://example.com/page/{i}", t)
        self.assertAlmostEqual(t.load_factor, 1000 / t.capacity)

    # 27
    def test_long_and_unicode_keys(self):
        t = self.make()
        long_key = "https://example.com/" + "a" * 3000
        for key in (long_key, long_key + "b", "한글 키", "🙂", "🙂🙂"):
            t.put(key, key[-1])
        for key in (long_key, long_key + "b", "한글 키", "🙂", "🙂🙂"):
            self.assertEqual(t.get(key), key[-1])
        self.assertEqual(len(t), 5)


class ChainingTests(unittest.TestCase):
    """개별 체이닝에만 해당하는 것."""

    def nine(self):
        """M = 11의 9번 칸에 a, l, w를 차례로 넣은 테이블."""
        t = HashTable(capacity=11, max_load=None)
        for i, key in enumerate(("a", "l", "w"), start=1):
            t.put(key, i)
        return t

    # 8
    def test_find_in_empty_bucket_costs_zero(self):
        self.assertEqual(HashTable().find("nope"), (False, None, 0))
        self.assertEqual(self.nine().find("c"), (False, None, 0))   # 0번 칸은 비어 있다

    # 17
    def test_new_node_goes_to_the_front(self):
        self.assertEqual(self.nine().buckets()[9], [("w", 3), ("l", 2), ("a", 1)])

    # 18
    def test_compared_nodes(self):
        t = self.nine()
        self.assertEqual(t.find("w"), (True, 3, 1))     # 맨 앞
        self.assertEqual(t.find("l"), (True, 2, 2))
        self.assertEqual(t.find("a"), (True, 1, 3))     # 맨 뒤
        self.assertEqual(t.find("V"), (False, None, 3))  # 같은 칸, 없는 키

    def test_update_keeps_the_node_in_place(self):
        t = self.nine()
        t.put("a", "바뀜")
        self.assertEqual(t.buckets()[9], [("w", 3), ("l", 2), ("a", "바뀜")])

    def test_default_max_load_is_one(self):
        t = HashTable()
        self.assertEqual(t.max_load, 1.0)
        for i in range(11):
            t.put(f"k{i}", i)
        self.assertEqual(t.capacity, 11)       # 11/11 = 1.0, 넘지 않았다
        self.assertEqual(t.load_factor, 1.0)
        t.put("k11", 11)
        self.assertEqual(t.capacity, 23)       # 12/11 > 1.0
        for i in range(12):
            self.assertEqual(t.get(f"k{i}"), i)

    # 23
    def test_no_resize_when_max_load_is_none(self):
        t = HashTable(capacity=5, max_load=None)
        for i in range(20):
            t.put(f"k{i}", i)
        self.assertEqual(t.capacity, 5)
        self.assertEqual(t.load_factor, 4.0)
        for i in range(20):
            self.assertEqual(t.get(f"k{i}"), i)

    # 25
    def test_single_bucket_is_one_long_list(self):
        t = HashTable(capacity=1, max_load=None)
        for i in range(10):
            t.put(f"k{i}", i)
        self.assertEqual(len(t.buckets()), 1)
        self.assertEqual(len(t.buckets()[0]), 10)
        self.assertEqual(t.find("없는 키"), (False, None, 10))
        self.assertEqual(t.find("k0"), (True, 0, 10))   # 처음 넣은 것이 맨 뒤

    # 28
    def test_buckets_match_the_hash(self):
        t = HashTable()
        for i in range(300):
            t.put(f"https://example.com/{i}", i)
        buckets = t.buckets()
        self.assertEqual(len(buckets), t.capacity)
        self.assertEqual(sum(len(b) for b in buckets), len(t))
        for index, bucket in enumerate(buckets):
            for key, value in bucket:
                self.assertEqual(horner(key, t.capacity), index)
                self.assertEqual(t.get(key), value)

    def test_load_above_one_is_allowed_by_max_load(self):
        t = HashTable(capacity=11, max_load=3)
        for i in range(33):
            t.put(f"k{i}", i)
        self.assertEqual(t.capacity, 11)        # 33/11 == 3, 넘지 않았다
        t.put("k33", 33)
        self.assertEqual(t.capacity, 23)


if __name__ == "__main__":
    unittest.main()
