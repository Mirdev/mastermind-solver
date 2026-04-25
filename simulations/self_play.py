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
from interface.cli_dashboard import CLIDashboard  # 대시보드 모듈 추가됨

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

    # 1. 시뮬레이션 환경 동적 설정
    digits = 4
    allow_dup = get_user_choice("1) 중복 허용?", "n")
    allow_zero = get_user_choice("2) 리딩 제로 허용?", "n")
    
    print("\n[솔버 선택] 1: Entropy | 2: Heuristic | r: Random")
    solver_choice = input("선택 (기본 1): ").lower()
    if solver_choice == 'r':
        solver_choice = random.choice(["1", "2"])
    
    # 엔진 및 솔버 초기화
    engine = MastermindEngine(digits=digits, allow_duplicates=allow_dup, allow_leading_zero=allow_zero)

    callback = dashboard.receive_data if dashboard else None
    if solver_choice == "2":
        solver = HeuristicSolver(engine, observer_callback=callback)
    else:
        solver = EntropySolver(engine, observer_callback=callback)

    # 2. 정답 생성 (설정된 규칙에 맞는 후보군 중 랜덤 선택)
    secret_str = random.choice(solver.candidates)
    secret_answer = tuple(int(d) for d in secret_str)
    
    print("\n" + "="*40)
    print(f"📡 [설정 완료]")
    print(f" - 규칙: {digits}자리 / 중복:{allow_dup} / 리딩제로:{allow_zero}")
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
        strike, ball = engine.get_feedback(guess_tuple, secret_answer)
        
        print(f"▶ 공격수: \"{guess}\" (계산: {step_time:.4f}s)")
        print(f"◁ 수비수: \"{strike}S {ball}B\"")

        # C. 종료 및 업데이트
        if (strike, ball) == (digits, 0):
            print(f"\n🎉 검증 성공! {turn}턴 만에 정답을 찾았습니다.")
            break
            
        solver.update_candidates(guess, (strike, ball))
        
        if not solver.candidates:
            print("\n❌ 검증 실패: 로직에 모순이 발생하여 후보군이 소멸했습니다.")
            break
            
        turn += 1
        time.sleep(0.2) # 흐름 확인용 딜레이

    print(f"\n⏱️ 전체 시뮬레이션 소요 시간: {time.time() - total_start:.2f}초")

if __name__ == "__main__":
    # argparse를 통한 명령줄 인자 파싱 처리
    parser = argparse.ArgumentParser(description="Mastermind Interactive Calculator")
    parser.add_argument('-d', '--dashboard', action='store_true', help="대시보드 모드를 활성화합니다.")
    args = parser.parse_args()
    
    run_self_play(use_dashboard=args.dashboard)