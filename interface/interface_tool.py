import sys
import os
import time

# 경로 주입
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.game_engine import MastermindEngine
from src.solvers.entropy_solver import EntropySolver
from src.solvers.heuristic_solver import HeuristicSolver

# --- [정석: 함수를 밖으로 분리] ---

def do_attack(solver, turn, digits):
    """AI가 공격하고 사용자의 피드백을 받는 함수"""
    start_time = time.time()
    # 모든 솔버가 turn 인자를 받는다고 가정 (사용자 피드백 반영)
    guess = solver.get_best_guess(turn)
    print(f"▶ AI 추천 공격: **{guess}** (계산: {time.time() - start_time:.4f}s)")
    
    while True:
        fb_input = input("   피드백 입력 (예: 11 / 정답 40 / 스킵 s): ").lower().replace(" ", "")
        if fb_input == 's': return False
        
        if len(fb_input) == 2 and fb_input.isdigit():
            s, b = int(fb_input[0]), int(fb_input[1])
            if s + b <= digits:
                if (s, b) == (digits, 0):
                    print(f"\n🎉 승리! {turn}회 만에 정답을 맞혔습니다.")
                    return True
                solver.update_candidates(guess, (s, b))
                return False
        print(f"   [!] 잘못된 입력입니다. {digits}자리 이하의 숫자로 '11'처럼 입력하세요.")

def do_defense(engine, my_secret, digits, turn):
    """상대방의 공격에 대해 피드백을 주는 함수"""
    while True:
        opp_guess_str = input("▷ 상대방이 던진 숫자 입력: ").replace(" ", "")
        if not opp_guess_str: continue
        if len(opp_guess_str) == digits and opp_guess_str.isdigit():
            opp_guess = tuple(int(d) for d in opp_guess_str)
            s, b = engine.get_feedback(opp_guess, my_secret)
            print(f"   => 피드백: **{s} Strike, {b} Ball**")
            if (s, b) == (digits, 0):
                print(f"\n💀 패배... 상대방이 {turn}회 만에 정답을 맞혔습니다.")
                return True
            break
        print(f"   [!] {digits}자리 숫자를 입력해 주세요.")
    return False

def run_calculator():
    print("==========================================")
    print("   ⚾ Mastermind Baseball Console ⚾    ")
    print("==========================================")

    # 설정부 (자릿수, 중복여부 등)
    try:
        digits = int(input("1) 자릿수 (기본 4): ") or 4)
        allow_dup = input("2) 중복 허용? (y/n): ").lower() == 'y'
        allow_zero = input("3) 0으로 시작 허용? (y/n): ").lower() == 'y'
        solver_choice = input("\n[솔버] 1: Entropy | 2: Heuristic (기본 1): ") or "1"
    except ValueError:
        digits, allow_dup, allow_zero, solver_choice = 4, False, False, "1"

    engine = MastermindEngine(digits=digits, allow_duplicates=allow_dup, allow_leading_zero=allow_zero)
    solver = HeuristicSolver(engine) if solver_choice == "2" else EntropySolver(engine)

    my_secret_str = input(f"\n상대방이 맞춰야 할 '당신의 숫자'를 입력하세요: ")
    my_secret = tuple(int(d) for d in my_secret_str)
    is_atk_first = input("당신이 먼저 공격하시겠습니까? (y/n): ").lower() == 'y'

    # ⚾ 9회 제한 루프
    for turn in range(1, 10):
        print(f"\n--- [{turn}회] 남은 후보군: {len(solver.candidates)} ---")

        if is_atk_first:
            if do_attack(solver, turn, digits): return
            print("-" * 20)
            if do_defense(engine, my_secret, digits, turn): return
        else:
            if do_defense(engine, my_secret, digits, turn): return
            print("-" * 20)
            if do_attack(solver, turn, digits): return

        if not solver.candidates:
            print("\n❌ 오류: 피드백 모순! 후보군이 소멸했습니다.")
            return

    print(f"\n💀 [GAME OVER] 9회가 종료되었습니다!")

if __name__ == "__main__":
    run_calculator()