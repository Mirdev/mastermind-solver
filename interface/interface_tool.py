import sys
import os
import time
import argparse

# 경로 주입
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.game_engine import MastermindEngine
from src.solvers.entropy_solver import EntropySolver
from src.solvers.heuristic_solver import HeuristicSolver
from src.solvers.fast_entropy_solver import FastEntropySolver
from src.solvers.minimax_solver import MinimaxSolver
from interface.cli_dashboard import CLIDashboard  # 대시보드 모듈 추가됨



def do_attack(solver, turn, digits):
    """AI가 공격하고 사용자의 피드백을 받는 함수"""
    start_time = time.time()

    guess = solver.get_best_guess(turn)
    print(f"▶ AI 추천 공격: **{guess}** (계산: {time.time() - start_time:.4f}s)")
    
    while True:
        fb_input = input(f"   피드백 입력 (예: 1 1 / 정답 {digits} 0 / 스킵 s): ").lower().strip()
        if fb_input == 's': return False
        
        s, b = -1, -1
        # 1. 띄어쓰기 입력 처리 (예: "1 1")
        parts = fb_input.split()
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            s, b = int(parts[0]), int(parts[1])
        # 2. 붙여쓰기 입력 처리 (예: "11")
        elif len(fb_input) == 2 and fb_input.isdigit():
            s, b = int(fb_input[0]), int(fb_input[1])
            
        # 통합된 판정 로직
        if s >= 0 and b >= 0 and (s + b) <= digits:
            if (s, b) == (digits, 0):
                print(f"\n🎉 승리! {turn}회 만에 정답을 맞혔습니다.")
                if hasattr(solver, 'log_game_over'):
                    solver.log_game_over(turn, guess, "win")
                return True
            solver.update_candidates(guess, (s, b))
            if hasattr(solver, 'log_state_after_feedback'):
                solver.log_state_after_feedback(turn, guess)
            return False
            
        print(f"   [!] 잘못된 입력입니다. {digits}자리 이하의 숫자로 '1 1' 또는 '11'처럼 입력하세요.")

def do_defense(engine, solver, my_secret, digits, turn):
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
                guess = solver.get_best_guess(turn)
                if hasattr(solver, 'log_game_over'):
                    solver.log_game_over(turn, guess, "lose")
                return True
            break
        print(f"   [!] {digits}자리 숫자를 입력해 주세요.")
    return False

def run_calculator(use_dashboard=False):
    print("==========================================")
    print("   ⚾ Mastermind Baseball Console ⚾    ")
    print("==========================================")

    # 대시보드 객체 초기화
    dashboard = CLIDashboard() if use_dashboard else None
    if use_dashboard:
        print("[System] 대시보드 및 로그 기록 모드가 활성화되었습니다.\n")

    # 설정부 (자릿수, 중복여부 등)
    try:
        digits = int(input("1) 자릿수 (기본 4): ") or 4)
        allow_dup = input("2) 중복 허용? (y/n): ").lower() == 'y'
        allow_zero = input("3) 0으로 시작 허용? (y/n): ").lower() == 'y'
        use_lut = input("4) 초고속 LUT 가속 엔진 사용? (y/n): ").lower() == 'y'
        solver_choice = input("\n[솔버] 1: Entropy | 2: Heuristic | 3: Fast-Entropy | 4: Minimax (기본 1): ") or "1"
    except ValueError:
        digits, allow_dup, allow_zero, use_lut, solver_choice = 4, False, False, False, "1"

    # [핵심 로직] 4자리 제한 판정 및 엔진 분기
    if use_lut and digits != 4:
        print("\n[!] 경고: LUT 가속 엔진은 4자리(Digits=4) 환경에서만 동작합니다.")
        print("[!] 안전을 위해 기존 일반 엔진(MastermindEngine)으로 자동 전환합니다.")
        use_lut = False

    if use_lut:
        from src.lut_engine import MastermindLUTEngine
        # 파일 부재 시 엔진 내부에서 자체적으로 제네레이터를 호출하여 투명하게 세팅을 마칩니다.
        engine = MastermindLUTEngine(digits=digits, allow_duplicates=allow_dup, allow_leading_zero=allow_zero)
        print("\n[System] LUT 가속 엔진이 성공적으로 로드되었습니다.")
    else:
        engine = MastermindEngine(digits=digits, allow_duplicates=allow_dup, allow_leading_zero=allow_zero)

    # 솔버 생성 시 대시보드 콜백 전달
    callback = dashboard.receive_data if dashboard else None
    if solver_choice == "1":
        solver = EntropySolver(engine, observer_callback=callback)
    elif solver_choice == "2":
        solver = HeuristicSolver(engine, observer_callback=callback)
    elif solver_choice == "3":
        solver = FastEntropySolver(engine, observer_callback=callback)
    else:
        solver = MinimaxSolver(engine, observer_callback=callback)

    while True:
        my_secret_str = input(f"\n상대방이 맞춰야 할 '당신의 숫자'({digits}자리)를 입력하세요: ").replace(" ", "")
        if len(my_secret_str) == digits and my_secret_str.isdigit():
            my_secret = tuple(int(d) for d in my_secret_str)
            break
        print(f"   [!] {digits}자리의 숫자로만 입력해주세요.")
    is_atk_first = input("당신이 먼저 공격하시겠습니까? (y/n): ").lower() == 'y'

    # 9회 제한 루프
    for turn in range(1, 10):
        print(f"\n--- [{turn}회] 남은 후보군: {len(solver.candidates)} ---")

        if is_atk_first:
            if do_attack(solver, turn, digits): return
            print("-" * 20)
            if do_defense(engine, solver, my_secret, digits, turn): return
        else:
            if do_defense(engine, solver, my_secret, digits, turn): return
            print("-" * 20)
            if do_attack(solver, turn, digits): return

        # 타임라인 검증 1: 피드백 모순으로 인한 후보군 소멸 시 대시보드 정상 종료 처리
        if not solver.candidates:
            print("\n❌ 오류: 피드백 모순! 후보군이 소멸했습니다.")
            if hasattr(solver, 'log_game_over'):
                guess = solver.get_best_guess(turn-1) if turn > 1 else ()
                solver.log_game_over(turn, guess, "lose")
            return

    # 타임라인 검증 2: 9회 오버 시 대시보드 정상 종료 처리
    print(f"\n💀 [GAME OVER] 9회가 종료되었습니다!")
    if hasattr(solver, 'log_game_over'):
        guess = solver.get_best_guess(turn)
        solver.log_game_over(turn, guess, "lose")

if __name__ == "__main__":
    # argparse를 통한 명령줄 인자 파싱 처리
    parser = argparse.ArgumentParser(description="Mastermind Interactive Calculator")
    parser.add_argument('-d', '--dashboard', action='store_true', help="대시보드 모드를 활성화합니다.")
    args = parser.parse_args()
    
    run_calculator(use_dashboard=args.dashboard)