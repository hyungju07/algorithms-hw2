import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from base62 import ALPHABET, decode, encode


class EncodeTests(unittest.TestCase):
    def test_zero_is_the_digit_zero_not_empty(self):
        self.assertEqual(encode(0), "0")

    def test_alphabet_order_is_digits_lower_upper(self):
        self.assertEqual(ALPHABET, "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")

    def test_carry_to_next_digit(self):
        self.assertEqual(encode(62), "10")
        self.assertEqual(encode(63), "11")
        self.assertEqual(encode(3843), "ZZ")    # 62*62 - 1
        self.assertEqual(encode(3844), "100")   # 62*62

    def test_known_large_value(self):
        # 자릿수 6, 47, 36, 35, 14 -> 글자 6, L, A, z, e
        self.assertEqual(6 * 62**4 + 47 * 62**3 + 36 * 62**2 + 35 * 62 + 14, 100_000_000)
        self.assertEqual(encode(100_000_000), "6LAze")

    def test_negative_raises_value_error(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_non_integer_raises_type_error(self):
        for bad in (1.5, "7", None, True, [1]):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    encode(bad)


class DecodeTests(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)
        self.assertEqual(decode("100"), 3844)

    def test_leading_zeros_are_accepted(self):
        self.assertEqual(decode("007"), 7)

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            decode("")

    def test_invalid_character_raises_value_error(self):
        for bad in ("a-b", " 1", "1 ", "가", "+1", "-1", "1\n", "٣"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    decode(bad)

    def test_non_string_raises_type_error(self):
        for bad in (7, None, b"7", ["7"]):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    decode(bad)


class RoundTripTests(unittest.TestCase):
    def test_small_range(self):
        for n in range(5000):
            self.assertEqual(decode(encode(n)), n)

    def test_big_numbers(self):
        for n in (2**31 - 1, 2**64, 10**30, 62**10 - 1, 62**10):
            self.assertEqual(decode(encode(n)), n)

    def test_encoded_text_uses_only_alphabet_and_no_leading_zero(self):
        for n in range(1, 5000):
            s = encode(n)
            self.assertNotEqual(s[0], "0")
            for ch in s:
                self.assertIn(ch, ALPHABET)

    def test_longer_code_means_bigger_number(self):
        # 일련번호가 커지면 코드 길이는 줄지 않는다
        self.assertEqual([len(encode(n)) for n in (61, 62, 3843, 3844)], [1, 2, 2, 3])


if __name__ == "__main__":
    unittest.main()
