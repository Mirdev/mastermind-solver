# Mastermind AI Solver

**Information Theory와 Naive Bayesian 접근법을 결합한 고성능 숫자 야구(Mastermind) 솔버입니다.**

단순한 무차별 대입(Brute-force)이 아니라, 기대 정보량(Shannon Entropy)을 극대화하고 빈도 분석(Heuristic)을 통해 최적의 해를 찾아냅니다. 9회 제한이 있는 실전 야구 게임 규칙에서도 압도적인 승률을 보장합니다.

---

## Key Features

* **Dual-Engine Architecture**:
    * **Entropy Solver**: Shannon Entropy 기반. 이론적 최적해를 지향하며 최소 턴 수를 보장합니다. (중복 허용 규칙에서 탁월)
    * **Heuristic Solver**: 위치별 빈도 분석 기반. 연산 비용이 매우 낮아 대규모 시뮬레이션 및 실시간 처리에 적합합니다.
* **Flexible Rule Support**: 자릿수 변경(Default 4), 중복 허용(Duplicates), 0으로 시작하는 숫자(Leading Zero) 등 하드코어 규칙 완벽 대응.
* **Performance Fine-tuning**:
    * **Class-level Caching**: 후보군 생성 오버헤드 최소화.
    * **Strategic Turn Skipping**: 초반 2~3턴 하드코딩 시드를 통한 연산 지연 최적화.
    * **Pragmatic Sampling**: 연산 효율을 위한 $N=200$ 샘플링 로직 적용.
* **Interactive Tactical Console**: 실전 대결 모드 및 AI 추천 공격 기능을 제공합니다.

---

## Performance Benchmark (1000 Iterations)

여러 규칙에 따른 솔버별 성능 지표입니다.
```text
==================================================
▶ 테스트 시나리오: 표준 규칙 (중복X, 0시작X)
▶ 설정: {'digits': 4, 'allow_duplicates': False, 'allow_leading_zero': False}
==================================================
[*] Heuristic (Freq) 테스트 시작 (1000회)...
[-] 결과: 평균 5.39회 | 총 소요시간: 27.88초
[*] Shannon Entropy 테스트 시작 (1000회)...
[-] 결과: 평균 5.37회 | 총 소요시간: 153.56초

==================================================
▶ 테스트 시나리오: 확장 규칙 (중복X, 0시작O)
▶ 설정: {'digits': 4, 'allow_duplicates': False, 'allow_leading_zero': True}
==================================================
[*] Heuristic (Freq) 테스트 시작 (1000회)...
[-] 결과: 평균 5.42회 | 총 소요시간: 36.68초
[*] Shannon Entropy 테스트 시작 (1000회)...
[-] 결과: 평균 5.42회 | 총 소요시간: 105.00초

==================================================
▶ 테스트 시나리오: 중복 규칙 (중복O, 0시작X)
▶ 설정: {'digits': 4, 'allow_duplicates': True, 'allow_leading_zero': False}
==================================================
[*] Heuristic (Freq) 테스트 시작 (1000회)...
[-] 결과: 평균 7.08회 | 총 소요시간: 16.40초
[*] Shannon Entropy 테스트 시작 (1000회)...
[-] 결과: 평균 5.73회 | 총 소요시간: 247.91초

==================================================
▶ 테스트 시나리오: 하드코어 규칙 (중복O, 0시작O)
▶ 설정: {'digits': 4, 'allow_duplicates': True, 'allow_leading_zero': True}
==================================================
[*] Heuristic (Freq) 테스트 시작 (1000회)...
[-] 결과: 평균 7.09회 | 총 소요시간: 46.77초
[*] Shannon Entropy 테스트 시작 (1000회)...
[-] 결과: 평균 5.79회 | 총 소요시간: 211.30초
```


> **Insight**: 비중복 규칙에서는 휴리스틱이 효율적이나, **중복 허용 규칙**에서는 엔트로피 솔버가 높은 정밀도를 유지하며 최적의 경로를 찾아냅니다.

---

## Engineering Note (Fine-tuning)

실용적인 성능 향상을 위해 다음과 같은 로직을 반영하였습니다.

1. **Heuristic '1234' Strategy**: 중복 허용 시 정보량이 적은 패턴(예: 0000)을 피하기 위해 첫 턴을 '1234'로 고정하여 초기 후보군 소거 영역을 확보합니다.
2. **Entropy 2-Turn Seed**: 연산량과 턴 수의 Trade-off를 고려하여, 연산 부하가 큰 초반 2턴은 고정 시드를 사용하고 이후 전수조사에 진입합니다.
3. **Strict Candidate Integrity**: 휴리스틱 연산 시 반드시 남은 후보군 내에서 최적해를 선택하도록 설계하여 논리적 모순 및 무한 루프를 방지합니다.
4. **Input Validation Loop**: 인터랙티브 환경에서 사용자의 피드백 오류(S/B 합계 오류 등)를 실시간으로 검증합니다.

---

## How to Run

### 1. 실전 대결 및 계산기 (Interactive Tool)
9회 제한 룰이 적용된 실전 대결 모드입니다.
```bash
python interface/interface_tool.py
```
### 2. AI 자가 대결 시뮬레이션 (Self-Play)
```bash
python simulations/self_play.py
```
### 3. 벤치마크 테스트
```bash
python simulations/run_simulation.py
```

---

## Directory Structure
```text
.
├── src/
│   ├── game_engine/    # 핵심 게임 로직 및 피드백 엔진
│   └── solvers/        # Entropy 및 Heuristic 알고리즘 구현체
├── interface/          # CLI 기반 인터랙티브 툴
├── simulations/        # 벤치마크 및 자가 대결 스크립트
└── README.md
```
