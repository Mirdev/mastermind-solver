import sys
import os
import time

# 프로젝트 루트 경로 추가 (패키지 임포트용)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_engine import MastermindEngine
from src.solvers.heuristic_solver import HeuristicSolver
from src.solvers.entropy_solver import EntropySolver
from src.solvers.fast_entropy_solver import FastEntropySolver
from src.solvers.minimax_solver import MinimaxSolver

# LUT 엔진은 4자리 전용이므로 안전하게 임포트합니다.
try:
    from src.lut_engine import MastermindLUTEngine
    HAS_LUT = True
except ImportError:
    HAS_LUT = False

def benchmark(solver_class, engine, iterations=1000):
    total_turns = 0
    max_turns = 0  # 최악의 턴 수를 기록할 변수
    start_time = time.time()
    
    # [핵심 해결 1] 솔버는 건드리지 않고, 시뮬레이션 단에서 누락된 all_candidates를 강제 주입하여 IndexError 방지
    if not hasattr(engine, 'all_candidates'):
        dummy = solver_class(engine)
        if hasattr(dummy, '_generate_all_candidates'):
            engine.all_candidates = dummy._generate_all_candidates()
            
    for i in range(iterations):
        # [핵심 해결 2] 매 게임마다 엔진의 이전 기록(history)을 완벽하게 초기화하여 무한루프 원천 차단
        if hasattr(engine, 'history'):
            engine.history = []
            
        secret = engine.generate_secret()
        solver = solver_class(engine)
        turns = solver.solve(secret)
        total_turns += turns
        
        # 현재 턴 수가 기존 최악의 턴 수보다 크면 갱신
        if turns > max_turns:
            max_turns = turns
            
        # [핵심 해결 3] 시뮬레이션이 멈춘 것인지 연산 중인지 파악할 수 있도록 100회 단위로 진행률 표시
        if (i + 1) % 100 == 0:
            print(f"   ... 연산 중: {i + 1}/{iterations} 회 완료")

    end_time = time.time()
    avg_turns = total_turns / iterations
    duration = end_time - start_time
    
    return avg_turns, duration, max_turns

def run_all_benchmarks():
    # 1. 테스트하고 싶은 다양한 게임 규칙 설정
    test_scenarios = [
        {
            "desc": "표준 규칙 (중복X, 0시작X)",
            "config": {"digits": 4, "allow_duplicates": False, "allow_leading_zero": False},
            "iters": 1000
        },
        {
            "desc": "확장 규칙 (중복X, 0시작O)",
            "config": {"digits": 4, "allow_duplicates": False, "allow_leading_zero": True},
            "iters": 1000
        },
        {
            "desc": "중복 규칙 (중복O, 0시작X)",
            "config": {"digits": 4, "allow_duplicates": True, "allow_leading_zero": False},
            "iters": 1000
        },
        {
            "desc": "하드코어 규칙 (중복O, 0시작O)",
            "config": {"digits": 4, "allow_duplicates": True, "allow_leading_zero": True},
            "iters": 1000
        }
    ]

    for scenario in test_scenarios:
        print(f"\n{'='*60}")
        print(f"▶ 테스트 시나리오: {scenario['desc']}")
        print(f"▶ 설정: {scenario['config']}")

        # 4자리 환경일 경우 LUT 가속 엔진을 우선적으로 로드하여 성능을 극대화합니다.
        if HAS_LUT and scenario['config'].get('digits', 4) == 4:
            engine = MastermindLUTEngine(**scenario['config'])
            engine_name = "MastermindLUTEngine (O(1) 캐시 가속)"
            actual_iters = scenario['iters']
        else:
            engine = MastermindEngine(**scenario['config'])
            engine_name = "MastermindEngine (일반)"
            # [핵심 해결 4] LUT 미적용 시 1000번은 몇 시간 넘게 걸려 '멈춘 것'으로 착각하게 되므로 횟수 조절
            actual_iters = min(100, scenario['iters'])
            if actual_iters < scenario['iters']:
                print(f"▶ [경고] LUT 미적용 구간입니다. 멈춤(지연) 현상 방지를 위해 {actual_iters}회로 축소 진행합니다.")

        print(f"▶ 사용 엔진: {engine_name}")
        print(f"{'='*60}")

        solvers = [
            ("Heuristic (Freq)", HeuristicSolver),
            ("Shannon Entropy (Standard)", EntropySolver),
            ("Fast Shannon Entropy (Vectorized)", FastEntropySolver),
            ("Minimax (Knuth)", MinimaxSolver)
        ]

        for name, solver_ptr in solvers:
            print(f"[*] {name} 테스트 시작 ({actual_iters}회)...")
            avg, dt, max_turns = benchmark(solver_ptr, engine, actual_iters)
            print(f"[-] 결과: 평균 {avg:.2f}회 | 최악 {max_turns}회 | 총 소요시간: {dt:.2f}초")

if __name__ == "__main__":
    run_all_benchmarks()