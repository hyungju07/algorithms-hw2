"""저장소 규칙 검사: src/ 안에서 dict, set, 내장 hash()를 쓰지 않는다 (SPEC.md 1절).

grep은 글자만 보므로 주석에도 걸리고 {} 리터럴은 놓친다. 여기서는 둘 다 본다.
"""
import ast
import glob
import os
import re
import unittest

SRC = os.path.join(os.path.dirname(__file__), "..", "src")
BANNED_NAMES = ("dict", "set", "frozenset", "hash")
BANNED_NODES = (ast.Dict, ast.Set, ast.DictComp, ast.SetComp)


def violations(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, BANNED_NODES):
            found.append((node.lineno, type(node).__name__))
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            found.append((node.lineno, node.id))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "collections":
                    found.append((node.lineno, "import collections"))
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "collections":
            found.append((node.lineno, "from collections"))
    return sorted(found)  # ast.walk는 줄 순서로 돌지 않는다


class RuleTests(unittest.TestCase):
    def sources(self):
        paths = sorted(glob.glob(os.path.join(SRC, "*.py")))
        self.assertTrue(paths, "src/에 파이썬 파일이 없다")
        for path in paths:
            with open(path, encoding="utf-8") as f:
                yield os.path.basename(path), f.read()

    def test_no_banned_builtins_or_literals(self):
        for name, source in self.sources():
            with self.subTest(file=name):
                self.assertEqual(violations(source), [])

    def test_instructor_grep_finds_nothing(self):
        # 안내문의 검사: grep -n "dict\|set(\|hash(" src/*.py
        for name, source in self.sources():
            for number, line in enumerate(source.splitlines(), start=1):
                with self.subTest(file=name, line=number):
                    self.assertIsNone(re.search(r"dict|set\(|hash\(", line), line)

    def test_the_checker_itself_catches_violations(self):
        bad = "a = {}\nb = {1}\nc = dict()\nd = hash('x')\ne = {k: 1 for k in 'ab'}\nfrom collections import Counter\n"
        self.assertEqual([line for line, _ in violations(bad)], [1, 2, 3, 4, 5, 6])
        self.assertEqual(violations("a = [1]\nb = f'{a}'\nc = (1, 2)\n"), [])


if __name__ == "__main__":
    unittest.main()
