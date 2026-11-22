"""적재율에 따라 개별 체이닝의 탐색 비용이 어떻게 바뀌는지 잰다 (6단계).

칸 수를 4093으로 고정한 HashTable(max_load=None)에 무작위 URL을 넣으면서,
적재율마다 성공 탐색과 실패 탐색에서 비교한 노드 수의 평균을 잰다.
주제 08의 이론값은 성공 1 + α/2, 실패 α 다.

    make experiment      # 표를 찍고 results.csv, results.svg를 다시 만든다
"""
import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from hash_table import HashTable
from svgplot import line_chart

M = 4093                                    # 소수
ALPHAS = [k / 4 for k in range(1, 17)]      # 0.25, 0.5, ..., 4
TRIALS = 10                                 # 시드를 바꿔 가며 되풀이해 평균을 낸다
MISSES = 2000                               # 적재율마다 찾아볼 없는 키의 수
SEED = 2026                                 # 다시 돌려도 같은 숫자가 나온다

LETTERS = "abcdefghijklmnopqrstuvwxyz"
PATH_CHARS = LETTERS + "0123456789-_"
TLDS = ("com", "net", "org", "kr", "ac.kr", "io", "dev")


def random_url(rng):
    host = "".join(rng.choice(LETTERS) for _ in range(rng.randint(3, 12)))
    path = "/".join("".join(rng.choice(PATH_CHARS) for _ in range(rng.randint(1, 10)))
                    for _ in range(rng.randint(0, 3)))
    return f"{rng.choice(('http', 'https'))}://{host}.{rng.choice(TLDS)}/{path}"


def fresh_url(rng, table):
    """table에 없는 무작위 URL."""
    while True:
        url = random_url(rng)
        if url not in table:
            return url


def mean_cost(table, keys):
    return sum(table.find(key)[2] for key in keys) / len(keys)


def run_trial(make_table, alphas, rng):
    """테이블 하나를 채워 가며 적재율마다 (성공 평균, 실패 평균)을 잰다."""
    table = make_table()
    keys = []
    rows = []
    for alpha in alphas:
        while len(keys) < round(alpha * table.capacity):
            url = fresh_url(rng, table)
            table.put(url, len(keys))
            keys.append(url)
        misses = [fresh_url(rng, table) for _ in range(MISSES)]
        rows.append((mean_cost(table, keys), mean_cost(table, misses)))
    return rows


def average(trials):
    """trials[시행][적재율] = (성공, 실패) 를 적재율별 평균으로 줄인다."""
    return [tuple(sum(column) / len(column) for column in zip(*at_alpha))
            for at_alpha in zip(*trials)]


def chaining_theory(alpha):
    return 1 + alpha / 2, alpha


def main():
    rng = random.Random(SEED)
    trials = [run_trial(lambda: HashTable(capacity=M, max_load=None), ALPHAS, rng)
              for _ in range(TRIALS)]
    measured = average(trials)

    print(f"개별 체이닝 · M = {M} · 무작위 URL · {TRIALS}번 평균 · 실패 탐색 {MISSES}회 · seed {SEED}")
    print("적재율    키 수   성공(실험)  성공(이론)   실패(실험)  실패(이론)")
    rows = []
    for alpha, (hit, miss) in zip(ALPHAS, measured):
        hit_theory, miss_theory = chaining_theory(alpha)
        n = round(alpha * M)
        print(f"{alpha:6.2f}  {n:7d}  {hit:10.3f}  {hit_theory:10.3f}  {miss:11.3f}  {miss_theory:10.3f}")
        rows.append((alpha, n, f"{hit:.4f}", f"{hit_theory:.4f}", f"{miss:.4f}", f"{miss_theory:.4f}"))

    with open(os.path.join(HERE, "results.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("alpha", "n", "hit_measured", "hit_theory", "miss_measured", "miss_theory"))
        writer.writerows(rows)

    line_chart(
        os.path.join(HERE, "results.svg"),
        f"개별 체이닝: 적재율과 탐색 비용 (M = {M})",
        "적재율 α = N / M", "비교한 노드 수 (평균)",
        [
            ("성공 · 이론 1 + α/2", "#2563eb", "line", [(a, chaining_theory(a)[0]) for a in (0, 4)]),
            ("성공 · 실험", "#2563eb", "dot", [(a, hit) for a, (hit, _) in zip(ALPHAS, measured)]),
            ("실패 · 이론 α", "#dc2626", "dash", [(a, chaining_theory(a)[1]) for a in (0, 4)]),
            ("실패 · 실험", "#dc2626", "ring", [(a, miss) for a, (_, miss) in zip(ALPHAS, measured)]),
        ],
        x_range=(0, 4), y_range=(0, 4.5),
        note=f"무작위 URL, {TRIALS}번 평균\n실패 탐색은 없는 키 {MISSES}개\n호너 해시 R = 31",
    )
    print("저장: experiments/results.csv, experiments/results.svg")


if __name__ == "__main__":
    main()
