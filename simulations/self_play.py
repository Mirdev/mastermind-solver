import sys
import os
import time
import random
import argparse

# [Path Hack] 프로젝트 루트 경로 주입
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.game_engine import MastermindEngine
from src.solvers.entropy_solver import EntropySolver
from src.solvers.heuristic_solver import HeuristicSolver
from src.solvers.fast_entropy_solver import FastEntropySolver
from interface.cli_dashboard import CLIDashboard  # 대시보드 모듈

def get_user_choice(prompt, default_val):
    choice = input(f"{prompt} (y: 예, n: 아니오, r: 랜덤, 기본 {default_val}): ").lower()
    if choice == 'r':
        return random.choice([True, False])
    elif choice == 'y':
        return True
    elif choice == 'n':
        return False
    return default_val == 'y'

def run_self_play(use_dashboard=False):
    print("==========================================")
    print("   🤖 AI vs AI: Dynamic Validation 🤖    ")
    print("==========================================")

    # 대시보드 객체 초기화
    dashboard = CLIDashboard() if use_dashboard else None
    if use_dashboard:
        print("[System] 대시보드 및 로그 기록 모드가 활성화되었습니다.\n")

    # 1. 시뮬레이션 환경 동적 설정 (자릿수 N자리 확장 대응)
    try:
        digits_input = input("0) 자릿수 (기본 4): ")
        digits = int(digits_input) if digits_input else 4
    except ValueError:
        digits = 4

    allow_dup = get_user_choice("1) 중복 허용?", "n")
    allow_zero = get_user_choice("2) 리딩 제로 허용?", "n")
    # 대규모 연산이므로 LUT 사용을 기본값(y)으로 추천
    use_lut = get_user_choice("3) 초고속 LUT 가속 엔진 사용?", "y")
    
    print("\n[솔버 선택] 1: Entropy | 2: Heuristic | 3: Fast-Entropy | r: Random")
    solver_choice = input("선택 (기본 1): ").lower()
    if solver_choice == 'r':
        solver_choice = random.choice(["1", "2"])
    
    # [핵심 로직] 4자리 제한 판정 및 엔진 분기
    if use_lut and digits != 4:
        print("\n[!] 경고: LUT 가속 엔진은 4자리(Digits=4) 환경에서만 동작합니다.")
        print("[!] 안전을 위해 기존 일반 엔진(MastermindEngine)으로 자동 전환합니다.")
        use_lut = False

    if use_lut:
        from src.lut_engine import MastermindLUTEngine
        # 파일 부재 시 엔진 내부에서 자체적으로 제네레이터를 호출하여 투명하게 세팅
        engine = MastermindLUTEngine(digits=digits, allow_duplicates=allow_dup, allow_leading_zero=allow_zero)
        print("\n[System] LUT 가속 엔진이 성공적으로 로드되었습니다.")
    else:
        engine = MastermindEngine(digits=digits, allow_duplicates=allow_dup, allow_leading_zero=allow_zero)

    callback = dashboard.receive_data if dashboard else None
    if solver_choice == "2":
        solver = HeuristicSolver(engine, observer_callback=callback)
    elif solver_choice == "1":
        solver = EntropySolver(engine, observer_callback=callback)
    else:
        solver = FastEntropySolver(engine, observer_callback=callback)

    # 2. 정답 생성 (설정된 규칙에 맞는 후보군 중 랜덤 선택)
    secret_str = random.choice(solver.candidates)
    secret_answer = tuple(int(d) for d in secret_str)
    
    print("\n" + "="*40)
    print(f"📡 [설정 완료]")
    print(f" - 규칙: {digits}자리 / 중복:{allow_dup} / 리딩제로:{allow_zero}")
    print(f" - 엔진: {engine.__class__.__name__}")
    print(f" - 솔버: {solver.__class__.__name__}")
    print(f" - 정답: [ {secret_str} ] (AI 수비수만 알고 있음)")
    print("="*40 + "\n")

    turn = 1
    total_start = time.time()

    while True:
        print(f"--- [Turn {turn}] 남은 후보: {len(solver.candidates)} ---")
        
        # A. 공격수 추측
        step_start = time.time()
        guess = solver.get_best_guess(turn)
        step_time = time.time() - step_start
        
        # B. 수비수 판정
        guess_tuple = tuple(int(d) for d in guess)
        strike, ball = engine.get_feedback(secret_answer, guess_tuple)
        
        print(f"▶ 공격수: \"{guess}\" (계산: {step_time:.4f}s)")
        print(f"◁ 수비수: \"{strike}S {ball}B\"")

        # 시각적 흐름을 위한 딜레이 (가속 엔진 테스트를 위해 시간을 줄임)
        time.sleep(1) 

        # C. 종료 및 업데이트
        if (strike, ball) == (digits, 0):
            print(f"\n🎉 검증 성공! {turn}턴 만에 정답을 찾았습니다.")
            if hasattr(solver, 'log_game_over'):
                solver.log_game_over(turn, guess, "win")
            break

        if turn >= 9:  # 9회 제한 초과 시
            if hasattr(solver, 'log_game_over'):
                solver.log_game_over(turn, guess, "lose")
            print("💀 9턴 제한 도달! (LOSE)")
            break
            
        solver.update_candidates(guess, (strike, ball))
        
        if not solver.candidates:
            print("\n❌ 검증 실패: 로직에 모순이 발생하여 후보군이 소멸했습니다.")
            if hasattr(solver, 'log_game_over'):
                solver.log_game_over(turn, guess, "lose")
            break
            
        turn += 1

    print(f"\n⏱️ 전체 시뮬레이션 소요 시간: {time.time() - total_start:.4f}초")

if __name__ == "__main__":
    # argparse를 통한 명령줄 인자 파싱 처리
    parser = argparse.ArgumentParser(description="Mastermind Interactive Calculator")
    parser.add_argument('-d', '--dashboard', action='store_true', help="대시보드 모드를 활성화합니다.")
    args = parser.parse_args()
    
    run_self_play(use_dashboard=args.dashboard)