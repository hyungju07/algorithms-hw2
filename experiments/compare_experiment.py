"""개별 체이닝과 선형 탐지를 같은 조건에서 비교한다 (과제).

같은 키를 같은 크기(M = 4093, 크기 조정 없음)의 두 테이블에 넣고, 적재율 0.1부터 0.9까지
성공·실패 탐색 비용의 평균을 잰다. 체이닝은 비교한 노드 수, 선형 탐지는 들여다본 칸 수다.

    make compare      # 표를 찍고 compare.csv, compare.svg, compare_log.svg를 다시 만든다 (30초쯤)
"""
import csv
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from hash_table import HashTable
from linear_probing import LinearProbingHashTable
from probe_experiment import M, MISSES, SEED, average, chaining_theory, run_trial
from svgplot import line_chart

ALPHAS = [k / 20 for k in range(2, 19)]     # 0.10, 0.15, ..., 0.90
TRIALS = 50                                 # 선형 탐지는 시행마다 편차가 커서 체이닝보다 많이 돌린다


def probing_theory(alpha):
    """크누스의 근삿값. (성공, 실패). 테이블이 아주 클 때의 값이다."""
    return (1 + 1 / (1 - alpha)) / 2, (1 + 1 / (1 - alpha) ** 2) / 2


def probing_exact(m, n):
    """칸이 m개, 키가 n개일 때의 정확한 기댓값 (Knuth, TAOCP 6.4). (성공, 실패)

    성공 = (1 + Q0(m, n-1)) / 2, 실패 = (1 + Q1(m, n)) / 2
    Q0(m, n) = 1 + n/m + n(n-1)/m^2 + ...,  Q1(m, n) = 1 + 2n/m + 3n(n-1)/m^2 + ...
    """
    def q(weighted, n):
        total, term = 0.0, 1.0
        for k in range(n + 1):
            total += (k + 1 if weighted else 1) * term
            term *= (n - k) / m
        return total
    return (1 + q(False, n - 1)) / 2, (1 + q(True, n)) / 2


def main():
    chaining_trials, probing_trials = [], []
    for trial in range(TRIALS):
        # 같은 시드로 두 번 돌리면 두 테이블에 같은 키가 같은 순서로 들어간다
        chaining, keys = run_trial(lambda: HashTable(capacity=M, max_load=None),
                                   ALPHAS, random.Random(SEED + trial))
        probing, same_keys = run_trial(lambda: LinearProbingHashTable(capacity=M, max_load=None),
                                       ALPHAS, random.Random(SEED + trial))
        assert keys == same_keys, "두 테이블에 다른 키가 들어갔다"
        chaining_trials.append(chaining)
        probing_trials.append(probing)
    chaining, probing = average(chaining_trials), average(probing_trials)

    print(f"M = {M} · 같은 무작위 URL · {TRIALS}번 평균 · 실패 탐색 {MISSES}회 · seed {SEED}")
    print("체이닝은 비교한 노드 수, 선형 탐지는 들여다본 칸 수")
    print("괄호 안은 이론값. 선형 탐지 실패는 (크누스 근삿값 / 이 크기의 정확한 기댓값), ±는 평균의 표준오차")
    print("적재율   키 수 |   체이닝 성공      체이닝 실패 |   선형 탐지 성공            선형 탐지 실패")
    rows = []
    for i, alpha in enumerate(ALPHAS):
        (c_hit, c_miss), (p_hit, p_miss) = chaining[i], probing[i]
        c_hit_t, c_miss_t = chaining_theory(alpha)
        p_hit_t, p_miss_t = probing_theory(alpha)
        n = round(alpha * M)
        p_hit_x, p_miss_x = probing_exact(M, n)
        # 시행마다의 실패 탐색 평균이 얼마나 흩어지는지로 평균의 표준오차를 구한다
        p_miss_se = statistics.stdev(trial[i][1] for trial in probing_trials) / math.sqrt(TRIALS)
        print(f"{alpha:6.2f}  {n:6d} | {c_hit:6.3f} ({c_hit_t:5.3f})  {c_miss:6.3f} ({c_miss_t:5.3f}) |"
              f" {p_hit:6.3f} ({p_hit_t:5.3f})  {p_miss:7.3f} ±{p_miss_se:5.3f} ({p_miss_t:6.3f} / {p_miss_x:6.3f})")
        rows.append((f"{alpha:.2f}", n) + tuple(f"{v:.4f}" for v in (
            c_hit, c_hit_t, c_miss, c_miss_t,
            p_hit, p_hit_t, p_hit_x, p_miss, p_miss_t, p_miss_x, p_miss_se)))

    with open(os.path.join(HERE, "compare.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("alpha", "n",
                         "chaining_hit", "chaining_hit_theory", "chaining_miss", "chaining_miss_theory",
                         "probing_hit", "probing_hit_theory", "probing_hit_exact",
                         "probing_miss", "probing_miss_theory", "probing_miss_exact", "probing_miss_stderr"))
        writer.writerows(rows)

    curve = [k / 200 for k in range(1, 191)]    # 이론 곡선은 0.005부터 0.95까지 촘촘히
    blue, orange = "#2563eb", "#ea580c"
    series = [
        ("선형 탐지 성공 · 이론", orange, "line", [(a, probing_theory(a)[0]) for a in curve]),
        ("선형 탐지 성공 · 실험", orange, "dot", [(a, hit) for a, (hit, _) in zip(ALPHAS, probing)]),
        ("선형 탐지 실패 · 이론", orange, "dash", [(a, probing_theory(a)[1]) for a in curve]),
        ("선형 탐지 실패 · 실험", orange, "ring", [(a, miss) for a, (_, miss) in zip(ALPHAS, probing)]),
        ("체이닝 성공 · 이론", blue, "line", [(a, chaining_theory(a)[0]) for a in curve]),
        ("체이닝 성공 · 실험", blue, "dot", [(a, hit) for a, (hit, _) in zip(ALPHAS, chaining)]),
        ("체이닝 실패 · 이론", blue, "dash", [(a, chaining_theory(a)[1]) for a in curve]),
        ("체이닝 실패 · 실험", blue, "ring", [(a, miss) for a, (_, miss) in zip(ALPHAS, chaining)]),
    ]
    note = (f"M = {M}, 같은 무작위 URL\n{TRIALS}번 평균, 없는 키 {MISSES}개\n"
            "실선·채운 점: 성공\n점선·빈 점: 실패\n체이닝: 비교한 노드 수\n선형 탐지: 들여다본 칸 수")
    line_chart(os.path.join(HERE, "compare.svg"),
               "개별 체이닝과 선형 탐지: 적재율과 탐색 비용",
               "적재율 α = N / M", "탐색 비용 (평균)", series,
               x_range=(0, 1), y_range=(0, 55), note=note)
    line_chart(os.path.join(HERE, "compare_log.svg"),
               "개별 체이닝과 선형 탐지: 적재율과 탐색 비용 (로그 눈금)",
               "적재율 α = N / M", "탐색 비용 (평균, 로그 눈금)", series,
               x_range=(0, 1), y_range=(0.05, 200), log_y=True, note=note)
    print("저장: experiments/compare.csv, compare.svg, compare_log.svg")


if __name__ == "__main__":
    main()
