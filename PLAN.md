# 구현 계획

`SPEC.md`를 구현하는 순서다. 묶음마다 **테스트를 먼저** 쓰고, 실패하는 것을 본 뒤 구현한다.
`src/` 안에서는 `dict`, `set`, 내장 `hash()`를 쓰지 않는다 (SPEC 1절).

## 파일

| 파일 | 내용 | 의존 |
| --- | --- | --- |
| `src/base62.py` | `encode`, `decode` (1단계에서 끝남) | 없음 |
| `src/hash_table.py` | `horner`, `horner_steps`, `HashTable` | 없음 |
| `src/shortener.py` | `Shortener` | `base62`, `hash_table` |
| `src/server.py` | `http.server` 웹 서버 | `shortener`, `hash_table`, `linear_probing` |
| `experiments/probe_experiment.py` | 적재율 실험 | `hash_table`, `svgplot` |
| `src/linear_probing.py` | `LinearProbingHashTable` (과제) | `hash_table` |
| `experiments/compare_experiment.py` | 두 방식 비교 실험 (과제) | `probe_experiment`, `linear_probing`, `svgplot` |
| `experiments/svgplot.py` | SVG 그래프 그리기 | 없음 |

## 순서

### 1. 테스트 작성 (4단계 앞부분, 구현 없음)

1. `tests/test_hash_table.py`: SPEC 6절의 8~29번.
   - 충돌은 흉내 내지 않고 실제 키로 만든다. 한 글자 키의 해시는 `ord(c) mod M`이므로
     `M = 11`에서 `a`, `l`, `w`는 모두 9번 칸이다. `Aa`와 `BB`는 어떤 `M`에서도 충돌한다.
   - 호너 해시의 기댓값은 주제 08의 출력(`stop` 9, `pots` 79, …)과 다항식을 직접 계산한 값으로 적는다.
2. `tests/test_shortener.py`: SPEC 6절의 30~45번.
3. `make test`를 돌려 **실패하는 것을 확인**하고 커밋한다. 이때 실패는 정상이다.

### 2. 해시 테이블 (`src/hash_table.py`)

1. `horner(key, m)`과 `horner_steps(key, m)`. 문자열이 아니면 `TypeError`.
2. 노드: `key`, `value`, `next` 세 칸. `__slots__`로 고정한다.
3. `HashTable.__init__`: 인자 검사, 길이 `capacity`인 `list`에 `None`을 채운다.
4. `find(key)`: 칸을 계산하고 리스트를 따라가며 비교한 노드를 센다. `get`, `in`은 `find`를 쓴다.
5. `put(key, value)`: 같은 키가 있으면 값만 바꾸고, 없으면 맨 앞에 붙인 뒤 적재율을 본다.
6. 크기 조정: `2M + 1` 이상의 가장 작은 소수(31의 배수 제외)를 찾아 모든 노드를 다시 넣는다.
   소수 판정은 제곱근까지 나눠 보는 것으로 충분하다.
7. `buckets()`, `capacity`, `load_factor`, `__len__`.

### 3. 단축기 (`src/shortener.py`)

1. URL 검사 함수: 문자열인지 → 앞뒤 공백 자르기 → 공백·제어 문자·역슬래시 → 스킴 → 호스트
   → 한 모양으로 맞추기(스킴·호스트 소문자, 기본 포트, 빈 경로. 포트 검사 포함) → 길이.
2. `Shortener`: URL→코드, 코드→URL 두 `HashTable`과 다음 일련번호(1부터).
3. `shorten(url)`: 검사 → URL→코드 테이블에 있으면 그 코드 → 없으면 다음 번호를
   `base62.encode`로 바꿔 두 테이블에 넣는다. 예약 코드(`table`, `shorten`)는 건너뛴다.
   **코드는 URL의 해시값으로 만들지 않는다.**
4. `expand(code)`: 코드→URL 테이블의 `get`. 없으면 `None`.

### 4. 구현 확인 (4단계 뒷부분)

- `make test`가 모두 통과할 때까지 **코드만** 고친다. 테스트는 고치지 않는다.
- `grep -n "dict\|set(\|hash(" src/*.py`가 아무것도 찾지 않아야 한다.
  이 검사에 걸리지 않게 함수 이름도 `horner`로 짓는다 (`…hash(`로 끝나는 이름을 쓰지 않는다).

### 5. 규칙 파일과 검사 (5단계)

- `.github/copilot-instructions.md`에 저장소 규칙을 적는다.
- `tests/test_rules.py`: `src/*.py`를 `ast`로 읽어 `dict`·`set`·`hash` 이름, `{}` 리터럴,
  dict·set 컴프리헨션, `collections` 가져오기가 없는지 검사한다. grep보다 정확하고 `make test`에 들어간다.

### 6. 적재율 실험 (6단계)

- `experiments/probe_experiment.py`: 칸 4093개, `max_load=None`, 시드를 고정한 무작위 URL.
- 적재율 0.25~4에서 성공 탐색(넣은 키 전부)과 실패 탐색(없는 키 2000개)의 평균 비교 노드 수를 잰다.
- 이론값(성공 `1 + α/2`, 실패 `α`)과 나란히 표로 찍고 `results.csv`, SVG 그래프로 저장한다.
- 내장 `hash()`를 쓰지 않으므로 다시 돌려도 같은 숫자가 나와야 한다.

### 7. 웹 서버 (7단계)

- `tests/test_server.py`를 먼저 쓴다 (SPEC 6절의 46~56번). 빈 포트에 서버를 띄워 `http.client`로 요청한다.
- `src/server.py`: `GET /`, `POST /shorten`, `GET /<코드>`, `GET /table`.
- 짧은 링크의 주소는 `X-Forwarded-Host` → `Host` 순서로 정한다.
- 폼 본문은 `urllib.parse.parse_qsl`로 읽는다. `parse_qs`는 `dict`를 돌려주므로 쓰지 않는다.
- 화면에 넣는 값은 모두 `html.escape`를 거친다.

## 과제: 선형 탐지 (이슈 #8)

SPEC 7절. 수업과 같은 순서로 한다: 명세 → 테스트 → 구현 → 실험 → 화면.

1. **테스트 먼저**: `tests/test_linear_probing.py`
   - `HashTableContractTests`를 상속해 `table_class`만 바꾼다. 같은 테스트가 두 테이블에 돈다.
   - 선형 탐지만의 사례를 더한다: 끝 칸에서 0번 칸으로 넘어가기, 가득 찬 테이블, 들여다본 칸 수.
   - `ShortenerTests`, `ServerTests`도 상속해 선형 탐지로 한 번 더 돌린다.
2. **구현**: `src/linear_probing.py`
   - 탐지 한 곳(`_probe`)에서 칸과 들여다본 칸 수를 함께 구하고 `find`, `put`, 크기 조정이 모두 그것을 쓴다.
   - 탐지는 많아야 M번 돈다. 가득 찬 테이블에서도 끝난다.
   - 인자 검사와 다음 칸 수 계산은 `hash_table.py`의 것을 같이 쓴다.
3. **바꿔 끼우기**: `Shortener(table_class=...)`, `make_server(table=...)`, `--table`, `make serve TABLE=linear`.
4. **비교 실험**: `experiments/compare_experiment.py`. 6단계의 `run_trial`을 다시 쓴다.
   같은 시드로 두 테이블을 채우고, 실제로 같은 키가 들어갔는지 확인한 뒤 잰다.
5. **화면**: `/table`에서 테이블 종류에 따라 그리는 함수를 고른다.

## 하지 않는 것

- 삭제, 파일 저장, 로그인 (SPEC 8절)
- 선형 탐지의 삭제와 지워짐 표시
