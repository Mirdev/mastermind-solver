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
    start_time = time.time()
    
    for _ in range(iterations):
        secret = engine.generate_secret()
        solver = solver_class(engine)
        turns = solver.solve(secret)
        total_turns += turns

    end_time = time.time()
    avg_turns = total_turns / iterations
    duration = end_time - start_time
    
    return avg_turns, duration

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
        else:
            engine = MastermindEngine(**scenario['config'])
            engine_name = "MastermindEngine (일반)"

        print(f"▶ 사용 엔진: {engine_name}")
        print(f"{'='*60}")

        solvers = [
            ("Heuristic (Freq)", HeuristicSolver),
            ("Shannon Entropy (Standard)", EntropySolver),
            ("Fast Shannon Entropy (Vectorized)", FastEntropySolver),
            ("Minimax (Knuth)", MinimaxSolver)
        ]

        for name, solver_ptr in solvers:
            print(f"[*] {name} 테스트 시작 ({scenario['iters']}회)...")
            avg, dt = benchmark(solver_ptr, engine, scenario['iters'])
            print(f"[-] 결과: 평균 {avg:.2f}회 | 총 소요시간: {dt:.2f}초")

if __name__ == "__main__":
    # 모든 경우의 수를 전부 탐색하므로 100번만 수행
    run_all_benchmarks()