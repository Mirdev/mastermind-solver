# Mastermind(숫자야구) AI Solver

**Information Theory와 Naive Bayesian 접근법을 결합한 고성능 숫자 야구(Mastermind) 솔버입니다.**

단순한 무차별 대입(Brute-force)이 아니라, 기대 정보량(Shannon Entropy, $$H(X) = -\sum p(x) \log_2 p(x)$$)을 극대화하고 빈도 분석(Heuristic)을 통해 최적의 해를 찾아냅니다. 9회 제한이 있는 실전 야구 게임 규칙에서도 압도적인 승률을 보장합니다.

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
* **Explainable AI (XAI) Dashboard**: 블랙박스 형태를 탈피하고, AI의 의사결정 과정을 투명하게 시각화하는 4단계 분석 리포트를 제공합니다.
    * **Dash 2 (Trend)**: 남은 정답 후보군의 실시간 생존 현황 추적.
    * **Dash 3 (Evaluation)**: 알고리즘 목적 함수(Entropy/Freq)에 따른 상위 추천 공격수 목록.
    * **Dash 4 (Rationale)**: AI의 결정적 근거 증명. (Entropy: 최악의 수(Max) 방어력을 대조하는 Minimax 스플릿 비교 / Heuristic: 위치별 빈도수 가중치 산식 해체)
    * **Dash 1 (Heatmap)**: 자릿수별 확률 분포와 AI의 실제 선택을 한눈에 파악할 수 있는 10x4 전치(Transposed) 히트맵.
* **Simulation Logging**: 추후 웹/D3.js 시각화 확장을 대비한 JSONL 형식의 턴별 로그 파일 자동 생성 기능.
* **D3.js Dashboard** *(new)*: 간단한 streamlit 대시보드에서 화려한 애니메이션이 적용되는 D3.js 대시보드 기능 제공

---

## Web-based Real-time Control Center

단순한 CLI를 넘어, Streamlit 기반의 실시간 관제 센터를 통해 AI의 추론 과정을 물리적으로 시각화합니다.

* **Live Monitoring Mode**: `self-play.py` 실행 시 실시간으로 생성되는 JSONL 로그를 감시하여, AI가 현재 어떤 데이터를 기반으로 다음 수를 결정하는지 초단위로 렌더링합니다.
* **Historical Replay Engine**: 과거에 수행된 시뮬레이션 로그 목록을 사이드바에서 선택하여 턴별로 복기할 수 있는 VOD 기능을 제공합니다.
* **Ghosting Zero UX**: `st.session_state` 기반의 Double Rerun 메커니즘을 적용하여, 라이브 모드 전환 시 이전 차트의 잔상이 남지 않는 깨끗한 화면 세척 로직을 구현했습니다.

### 4-Layer Analysis Report
1.  **Dash 1 (Heatmap)**: 자릿수별 숫자 출현 확률 분포를 10x4 매트릭스로 시각화. AI가 선택한 숫자는 강조 표시됩니다.
2.  **Dash 2 (Trend)**: 턴이 경과함에 따라 정답 후보군이 얼마나 급격하게 소거되는지 선형 그래프로 추적합니다.
3.  **Dash 3 (Evaluation)**: 현재 알고리즘(Entropy/Heuristic)이 평가한 공격 후보군 리스트와 각각의 점수를 표 형태로 제공합니다.
4.  **Dash 4 (Rationale)**: 
    * **Entropy**: Minimax 기반 스플릿 비교 (최악의 판정 시에도 남는 후보수 최소화 증명).
    * **Heuristic**: 나이브 베이지안 빈도 가중치 합산 산식 노출.

---

## Neural Dashboard UI/UX (The Eyes) (New)

단순한 CLI와 streamlit 출력을 넘어, **고도로 정제된 D3.js 애니메이션 인터페이스**를 구현했습니다. AI의 추론 과정을 물리적이고 직관적으로 시각화합니다.

### 4-Layer Real-time Analysis Report
1. **Dash 1 [확률장 4-Chamber] (Heatmap)**: 
    * **True Sync Masking Engine**: 레이더 스캐너가 내려가는 좌표에 맞춰 과거와 현재의 확률 데이터가 실시간으로 단절 및 덧씌워지는 **ECG(심전도)** 연출.
    * 스캔이 지나간 자리는 **Cool-down Glow(Fade-out)** 효과가 적용되어 시각적 깊이감을 제공합니다.
2. **Dash 2 [후보군 붕괴] (Trend)**: 
    * **Gravity Shatter Engine**: 턴이 경과하여 정답 후보군이 소거될 때마다, 파편들이 물리 엔진 기반의 포물선 궤적을 그리며 컨테이너 바닥으로 쏟아져 내립니다(Bounce).
3. **Dash 3 [전술 평가] (Evaluation)**: 
    * **Matrix Scramble**: 알고리즘 목적 함수(Entropy/Freq)에 따른 상위 추천 공격숫자를 띄울 때, 데이터가 0.1초 단위로 디코딩되는 매트릭스 텍스트 효과를 적용했습니다.
4. **Dash 4 [판단 근거] (Rationale)**: 
    * **Neural Split & Cross Counter**: AI의 결정적 근거를 증명합니다. 최악의 방어력(Max)을 대조하는 Minimax 스플릿 결과를 좌우에서 중앙으로 꽂히는 슬라이드 임팩트로 연출합니다. 

> **Ghosting Zero UX**: `st.session_state` 및 JS 상태 관리 제어를 통해 라이브 모드 전환 시 이전 차트의 잔상이 남거나 꿀렁이는 현상을 완벽히 차단한 Soft-Update 로직이 적용되어 있습니다.

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

## Dashboard example

### EntropySolver

```text
==============================================================
[EntropySolver] Turn 4 시각화 분석 리포트
==============================================================
▶ [Dash 2] 남은 정답 후보군: 22개
▶ [Dash 3] Shannon Entropy (bits) 상위 추천:
   1. [5, 2, 6, 3] (점수: 3.4474)
   2. [5, 2, 1, 6] (점수: 3.3176)
   3. [2, 6, 3, 5] (점수: 3.3176)
▶ [Dash 4] AI의 결정적 근거 (Why [5, 2, 6, 3]?):
   [채택] [5, 2, 6, 3]를 찔렀을 때 (엔트로피 최고점):
     ├─ 가장 운이 나쁜 [1S 2B] 판정 시에도 ➔ 3개만 남음!
   [비교] 만약 최악의 수 [5, 8, 2, 4]를 찔렀다면?
     └─ 가장 운이 나쁜 [1S 1B] 판정 시 ➔ 무려 11개나 남음.
▶ [Dash 1] 자릿수별 확률 히트맵 (%) - [*]는 AI 선택
   --------------------------------------------------
    Digit  |   Pos 1  |  Pos 2  |  Pos 3  |  Pos 4  |
   --------------------------------------------------
     0     |     -    |    -    |    -    |    -    |
     1     |     -    |    9.1  |   18.2  |   13.6  |
     2     |     4.5  |[  31.8 ]|    4.5  |    9.1  |
     3     |    18.2  |    -    |   31.8  |[   9.1 ]|
     4     |     4.5  |    9.1  |    -    |   36.4  |
     5     | [  45.5 ]|    4.5  |    -    |   13.6  |
     6     |     -    |   27.3  |[  13.6 ]|    9.1  |
     7     |     4.5  |    9.1  |   27.3  |    9.1  |
     8     |    22.7  |    9.1  |    4.5  |    -    |
     9     |     -    |    -    |    -    |    -    |
   --------------------------------------------------
```

### HeuristicSolver(Positional Frequency Score(NB))

```text
==============================================================
[HeuristicSolver] Turn 5 시각화 분석 리포트
==============================================================
▶ [Dash 2] 남은 정답 후보군: 3개
▶ [Dash 3] Positional Frequency Score(NB) 상위 추천:
   1. [7, 3, 9, 0] (점수: 8.0000)
   2. [7, 6, 1, 0] (점수: 7.0000)
   3. [9, 3, 7, 0] (점수: 7.0000)
▶ [Dash 4] AI의 결정적 근거 (Why [7, 3, 9, 0]?):
   └─ 빈도합산: 1번[7]:2.0점 + 2번[3]:2.0점 + 3번[9]:1.0점 + 4번[0]:3.0점 = 총 8.0점 (가성비 1위)
▶ [Dash 1] 자릿수별 확률 히트맵 (%) - [*]는 AI 선택
   --------------------------------------------------
    Digit  |   Pos 1  |  Pos 2  |  Pos 3  |  Pos 4  |
   --------------------------------------------------
     0     |     -    |    -    |    -    |[ 100.0 ]|
     1     |     -    |    -    |   33.3  |    -    |
     2     |     -    |    -    |    -    |    -    |
     3     |     -    |[  66.7 ]|    -    |    -    |
     4     |     -    |    -    |    -    |    -    |
     5     |     -    |    -    |    -    |    -    |
     6     |     -    |   33.3  |    -    |    -    |
     7     | [  66.7 ]|    -    |   33.3  |    -    |
     8     |     -    |    -    |    -    |    -    |
     9     |    33.3  |    -    |[  33.3 ]|    -    |
   --------------------------------------------------
```

---

## GUI Dashboard example
<img width="1467" height="862" alt="1" src="https://github.com/user-attachments/assets/cf1b2e5a-1a0f-4b3e-a9ae-ff76474660e5" />
<img width="1430" height="822" alt="Image" src="https://github.com/user-attachments/assets/ab7bc134-18ea-42d7-8ba9-a32baf57fd63" />

---

## D3.js Dashboard example
<img width="1900" height="758" alt="스크린샷 2026-04-26 172342" src="https://github.com/user-attachments/assets/b4ed7e69-2769-4378-8465-0d3a85162c1a" />

---

## Engineering Note (Fine-tuning)

실용적인 성능 향상을 위해 다음과 같은 로직을 반영하였습니다.

1. **Heuristic '1234' Strategy**: 중복 허용 시 정보량이 적은 패턴(예: 0000)을 피하기 위해 첫 턴을 '1234'로 고정하여 초기 후보군 소거 영역을 확보합니다.
2. **Entropy 2-Turn Seed**: 연산량과 턴 수의 Trade-off를 고려하여, 연산 부하가 큰 초반 2턴은 고정 시드를 사용하고 이후 전수조사에 진입합니다.
3. **Strict Candidate Integrity**: 휴리스틱 연산 시 반드시 남은 후보군 내에서 최적해를 선택하도록 설계하여 논리적 모순 및 무한 루프를 방지합니다.
4. **Input Validation Loop**: 인터랙티브 환경에서 사용자의 피드백 오류(S/B 합계 오류 등)를 실시간으로 검증합니다.
5. **Data Decoupling**: 솔버의 핵심 연산 로직과 CLI 렌더링 로직을 완벽히 분리하여 연산 병목현상을 방지합니다.
6. **State-aware UI Synchronization**: Streamlit의 단방향 렌더링 특성으로 인한 차트 잔상 문제를 해결하기 위해, `session_state`를 이용한 델타 모니터링 및 조건부 리셋 로직을 설계하여 UI 동기화 무결성을 확보했습니다.
7. **Multi-process Data Streaming (JSONL)**: 연산 엔진과 시각화 툴 사이의 병목을 없애기 위해 무거운 데이터베이스 대신 JSONL(JSON Lines) 형식을 채택했습니다. 이는 스트리밍 방식의 쓰기가 가능하여 대규모 시뮬레이션 중에도 시각화 로그를 실시간으로 안전하게 Flush 할 수 있는 구조적 이점을 제공합니다.
8. **Dual Clip-path Sync Masking (ECG Architecture)**: 대시보드 1의 심전도(ECG) 효과를 위해 D3.js의 듀얼 클립 패스(Dual Clip-path) 기술을 도입했습니다. 스캐너의 Y좌표와 마스크의 높이를 1ms 오차 없이 동기화하여, 데이터가 '바뀌는 것'이 아니라 선을 경계로 '물리적으로 덧씌워지는' 고정밀 시각화를 구현했습니다.
9. **Recursive Animation Kill-switch**: 비동기적으로 실행되는 JS 애니메이션 루프와 실시간 데이터 수신 턴 사이의 충돌을 방지하기 위해 글로벌 킬 스위치(Global Kill-switch) 로직을 설계했습니다. 'TARGET HIT' 또는 'GAME OVER' 상태 감지 즉시 모든 재귀 호출을 중단하고 최종 상태로 UI를 고정하여 리소스 낭비와 시각적 노이즈를 차단합니다.
10. **Physics-based Entropy Visualization**: 단순한 수치 변동을 넘어, 정보 엔트로피가 해소되는 과정을 **D3 물리 엔진(Gravity & Scatter)**으로 형상화했습니다. 후보군이 파괴되어 쏟아지는 연출은 솔버가 불확실성을 제거하는 물리적 과정을 사용자에게 직관적으로 전달합니다.

---

## Installation
```bash
git clone https://github.com/Mirdev/mastermind-solver.git
cd mastermind-solver
pip install -r requirements.txt
```

---

## How to Run

명령어 뒤에 -d 또는 --dashboard 플래그를 추가하면 심층 시각화 대시보드가 함께 활성화됩니다.

### 1. 실전 대결 및 계산기 (Interactive Tool)
9회 제한 룰이 적용된 실전 대결 모드입니다.
```bash
python interface/interface_tool.py [-d]
```
### 2. AI 자가 대결 시뮬레이션 (Self-Play)
```bash
python simulations/self_play.py [-d]
```
### 3. 벤치마크 테스트
```bash
python simulations/run_simulation.py
```
### 4. Web Dashboard 실행 (실시간 관제)

**1) 먼저 터미널 A에서 웹 대시보드 가동**

```bash
streamlit run interface/web_dashboard.py
```

**2) 터미널 B에서 시뮬레이션 실행**

```bash
python interface/interface_tool.py [-d]
```
혹은
```bash
python simulations/self_play.py [-d]
```

### 5. D3.js Dashboard 실행 (실시간 관제)
**1) 먼저 터미널 A에서 웹 서버 가동**

```bash
python -m http.server 8000
```

**2) 웹 브라우저에서 웹 서버 접속**

```text
http://localhost:8000/interface/d3_dashboard.html
```

**3) 터미널 B에서 시뮬레이션 실행**

```bash
python interface/interface_tool.py [-d]
```
혹은
```bash
python simulations/self_play.py [-d]
```


---

## Directory Structure
```text
.
├── src/
│   ├── game_engine/    # 핵심 게임 로직 및 피드백 엔진
│   └── solvers/        # Entropy 및 Heuristic 알고리즘 구현체
├── interface/          # CLI, GUI 및 D3.js 기반 대시보드 렌더러 및 인터랙티브 툴(상대방과 대결시 사용 툴)
├── simulations/        # 벤치마크 및 AI 자가 대결 스크립트
├── logs/               # JSONL 시뮬레이션 로그 기록 폴더
└── README.md
```

## License

This project is licensed under the **GNU GPL v3.0** - see the [LICENSE](LICENSE.txt) file for details.
