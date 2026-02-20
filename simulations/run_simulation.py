import sys
import os
import time

# 프로젝트 루트 경로 추가 (패키지 임포트용)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_engine import MastermindEngine
from src.solvers.heuristic_solver import HeuristicSolver
from src.solvers.entropy_solver import EntropySolver

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
            "iters": 100
        },
        {
            "desc": "확장 규칙 (중복X, 0시작O)",
            "config": {"digits": 4, "allow_duplicates": False, "allow_leading_zero": True},
            "iters": 100
        },
        {
            "desc": "중복 규칙 (중복O, 0시작X)",
            "config": {"digits": 4, "allow_duplicates": True, "allow_leading_zero": False},
            "iters": 100  # 중복 허용 시 연산량이 늘어나므로 횟수 조정
        },
        {
            "desc": "하드코어 규칙 (중복O, 0시작O)",
            "config": {"digits": 4, "allow_duplicates": True, "allow_leading_zero": True},
            "iters": 100  # 중복 허용 시 연산량이 늘어나므로 횟수 조정
        }
    ]

    for scenario in test_scenarios:
        print(f"\n{'='*50}")
        print(f"▶ 테스트 시나리오: {scenario['desc']}")
        print(f"▶ 설정: {scenario['config']}")
        print(f"{'='*50}")

        # 공통 엔진 생성
        engine = MastermindEngine(**scenario['config'])

        # 각 솔버별 벤치마크 실행
        solvers = [
            ("Heuristic (Freq)", HeuristicSolver),
            ("Shannon Entropy", EntropySolver)
        ]

        for name, solver_ptr in solvers:
            print(f"[*] {name} 테스트 시작 ({scenario['iters']}회)...")
            avg, dt = benchmark(solver_ptr, engine, scenario['iters'])
            print(f"[-] 결과: 평균 {avg:.2f}회 | 총 소요시간: {dt:.2f}초")

if __name__ == "__main__":
    # 모든 경우의 수를 전부 탐색하므로 1000번만 수행
    run_all_benchmarks()