import sys
import os
import time

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_engine import MastermindEngine
from src.solvers.heuristic_solver import HeuristicSolver
from src.solvers.fast_entropy_solver import FastEntropySolver
from src.solvers.minimax_solver import MinimaxSolver

try:
    from src.lut_engine import MastermindLUTEngine
    HAS_LUT = True
except ImportError:
    HAS_LUT = False

def evaluate_target(target_str, iterations=100):
    target_secret = tuple(int(d) for d in target_str)
    digits = len(target_secret)
    allow_dup = 1 #len(set(target_secret)) != digits
    allow_zero = 1 #(target_secret[0] == 0)

    config = {
        "digits": digits,
        "allow_duplicates": allow_dup,
        "allow_leading_zero": allow_zero
    }

    if digits == 4 and HAS_LUT:
        engine_class = MastermindLUTEngine
    else:
        engine_class = MastermindEngine

    solvers = [
        ("Heuristic", HeuristicSolver),
        ("Entropy", FastEntropySolver),
        ("Minimax", MinimaxSolver)
    ]

    results = {}
    print(f"\n▶ 타겟 [{target_str}] 분석 중... (규칙: {digits}자리, 중복={'O' if allow_dup else 'X'}, 0시작={'O' if allow_zero else 'X'})")
    
    for solver_name, solver_class in solvers:
        total_turns = 0
        max_turns = 0
        
        sys.stdout.write(f"  [*] {solver_name} 연산 중...")
        sys.stdout.flush()

        start_time = time.time()  # 시간 측정 시작

        for _ in range(iterations):
            engine = engine_class(**config)
            solver = solver_class(engine, is_benchmark=True)
            turns = solver.solve(target_secret)
            
            total_turns += turns
            if turns > max_turns:
                max_turns = turns

        end_time = time.time()  # 시간 측정 종료
        total_duration = end_time - start_time
        time_per_iter = (total_duration / iterations) * 1000  # 밀리초(ms) 단위 변환

        avg_turns = total_turns / iterations
        results[solver_name] = {
            "avg": avg_turns, 
            "max": max_turns,
            "total_time": total_duration,
            "time_per_iter": time_per_iter
        }
        
        sys.stdout.write(f"\r  [*] {solver_name} -> 평균: {avg_turns:.3f}턴 | 최악: {max_turns}턴 | 총합: {total_duration:.2f}s | 회당: {time_per_iter:.1f}ms    \n")

    return results

def run_vs_mode(t1, t2, iters):
    print("=" * 60)
    print(f" ⚔️ VS MODE 대결: [{t1}] vs [{t2}] ({iters}회 시뮬레이션)")
    print("=" * 60)

    res1 = evaluate_target(t1, iters)
    res2 = evaluate_target(t2, iters)

    print("\n" + "=" * 60)
    print(" 📊 대결 결과 요약 (어떤 숫자가 더 맞추기 어려웠는가?)")
    print("=" * 60)
    
    for solver_name in res1.keys():
        avg1, avg2 = res1[solver_name]['avg'], res2[solver_name]['avg']
        diff = abs(avg1 - avg2)
        time1, time2 = res1[solver_name]['total_time'], res2[solver_name]['total_time']
        
        if avg1 > avg2:
            status = f"[{t1}] 승리 (더 어려움)"
        elif avg2 > avg1:
            status = f"[{t2}] 승리 (더 어려움)"
        else:
            status = "무승부 (동일한 난이도)"
            
        print(f"[{solver_name}] {status}")
        print(f"   - {t1}: {avg1:.3f}턴 (최악 {res1[solver_name]['max']}턴) | 소요시간: {time1:.2f}s")
        print(f"   - {t2}: {avg2:.3f}턴 (최악 {res2[solver_name]['max']}턴) | 소요시간: {time2:.2f}s")
        print(f"   - 턴 수 차이: {diff:.3f}턴\n")

if __name__ == "__main__":
    print("⚾ Tactical Target Benchmark System")
    target1 = input("첫 번째 타겟 숫자를 입력하십시오: ").strip()
    target2 = input("두 번째 타겟 숫자를 입력하십시오 (비교를 원치 않으시면 그냥 엔터를 누르세요): ").strip()
    
    iters_input = input("시뮬레이션 반복 횟수를 입력하십시오 (기본값 100): ").strip()
    iterations = int(iters_input) if iters_input.isdigit() else 100

    if not target1.isdigit():
        print("[오류] 타겟 숫자는 반드시 숫자로만 입력해야 합니다.")
        sys.exit(1)

    if target2:
        if not target2.isdigit():
            print("[오류] 두 번째 타겟 역시 숫자로만 입력해야 합니다.")
            sys.exit(1)
        if len(target1) != len(target2):
            print("[경고] 자릿수가 다르면 공정한 대결이 어렵지만, 연산은 진행합니다.")
        run_vs_mode(target1, target2, iterations)
    else:
        print("=" * 50)
        evaluate_target(target1, iterations)
        print("=" * 50)