import sys
import os
import time

# 프로젝트 루트 경로 추가 (패키지 임포트용)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_engine import MastermindEngine
from src.solvers.heuristic_solver import PositionalFrequencySolver
from src.solvers.entropy_solver import EntropySolver

def benchmark(solver_class, name, iterations=1000):
    engine = MastermindEngine()
    total_turns = 0
    start_time = time.time()

    print(f"[*] {name} 테스트 시작 ({iterations}회)...")
    
    for _ in range(iterations):
        secret = engine.generate_secret()
        solver = solver_class(engine)
        turns = 0
        
        while True:
            turns += 1
            # 엔트로피 솔버의 경우 현재 턴 정보를 넘겨줌
            if isinstance(solver, EntropySolver):
                guess = solver.get_best_guess(turns)
            else:
                guess = solver.get_best_guess()
                
            feedback = engine.get_feedback(secret, guess)
            if feedback == (4, 0):
                break
            solver.update_candidates(guess, feedback)
        
        total_turns += turns

    end_time = time.time()
    avg_turns = total_turns / iterations
    duration = end_time - start_time
    
    print(f"[-] 결과: 평균 {avg_turns:.2f}회 | 총 소요시간: {duration:.2f}초")
    return avg_turns, duration

if __name__ == "__main__":
    # 10만 번은 시간이 너무 걸릴 수 있으니, 1차 검증용으로 1,000번만 수행
    benchmark(PositionalFrequencySolver, "Heuristic (Positional Frequency)", iterations=1000)
    benchmark(EntropySolver, "Shannon Entropy", iterations=100) # 엔트로피는 무거우므로 100회만