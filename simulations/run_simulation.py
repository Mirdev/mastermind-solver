import sys
import os
import time

# 프로젝트 루트 경로 추가 (패키지 임포트용)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_engine import MastermindEngine
from src.solvers.heuristic_solver import HeuristicSolver
from src.solvers.fast_entropy_solver import FastEntropySolver
from src.solvers.minimax_solver import MinimaxSolver

# LUT 엔진 로드 (안전성 검증)
try:
    from src.lut_engine import MastermindLUTEngine
    HAS_LUT = True
except ImportError:
    HAS_LUT = False

def benchmark(solver_class, engine_class, config, iterations):
    total_turns = 0
    max_turns = 0
    start_time = time.time()
    
    # 진행률 갱신 간격 (최소 1회마다 갱신되도록 보정)
    update_interval = max(1, iterations // 10)

    sys.stdout.write(f"\r      연산준비중...")
    sys.stdout.flush()

    for i in range(iterations):
        # [핵심] 매 게임마다 무결성 상태의 새 엔진 인스턴스 생성
        engine = engine_class(**config)
        secret = engine.generate_secret()
        
        # is_benchmark=True를 주입하여 솔버의 디스크 쓰기를 차단
        solver = solver_class(engine, is_benchmark=True)
        turns = solver.solve(secret)
        
        total_turns += turns
        if turns > max_turns:
            max_turns = turns
            
        # 동적 프로그레스 바 출력 (동일한 줄 덮어쓰기)
        if (i + 1) % update_interval == 0 or (i + 1) == iterations:
            ratio = (i + 1) / iterations
            filled_blocks = int(ratio * 10)
            bar = "■" * filled_blocks + "□" * (10 - filled_blocks)
            sys.stdout.write(f"\r   ... 실행중... [{bar}] {i+1}/{iterations}회")
            sys.stdout.flush()

    # 진행률 출력 완료 후 줄바꿈
    print()

    end_time = time.time()
    total_duration = end_time - start_time
    avg_turns = total_turns / iterations
    time_per_iter = total_duration / iterations
    
    return avg_turns, max_turns, time_per_iter, total_duration

def run_grid_search():
    # 축 1: 16가지 게임 엔진 환경 설정
    grid_environments = [
        {"desc": "3자리 표준 (LUT 미적용)", "digits": 3, "use_lut": False, "dup": False, "zero": False, "iters": 1000},
        {"desc": "3자리 리딩제로 (LUT 미적용)", "digits": 3, "use_lut": False, "dup": False, "zero": True, "iters": 1000},
        {"desc": "3자리 중복 (LUT 미적용)", "digits": 3, "use_lut": False, "dup": True, "zero": False, "iters": 1000},
        {"desc": "3자리 하드코어 (LUT 미적용)", "digits": 3, "use_lut": False, "dup": True, "zero": True, "iters": 1000},
        {"desc": "4자리 표준 (LUT 미적용)", "digits": 4, "use_lut": False, "dup": False, "zero": False, "iters": 1000},
        {"desc": "4자리 표준 (LUT 적용)",   "digits": 4, "use_lut": True,  "dup": False, "zero": False, "iters": 1000},
        {"desc": "4자리 리딩제로 (LUT 미적용)", "digits": 4, "use_lut": False, "dup": False, "zero": True, "iters": 1000},
        {"desc": "4자리 리딩제로 (LUT 적용)",   "digits": 4, "use_lut": True,  "dup": False, "zero": True, "iters": 1000},
        {"desc": "4자리 중복 (LUT 미적용)", "digits": 4, "use_lut": False, "dup": True, "zero": False, "iters": 1000},
        {"desc": "4자리 중복 (LUT 적용)",   "digits": 4, "use_lut": True,  "dup": True, "zero": False, "iters": 1000},
        {"desc": "4자리 하드코어 (LUT 미적용)","digits": 4, "use_lut": False,  "dup": True,  "zero": True,  "iters": 1000},
        {"desc": "4자리 하드코어 (LUT 적용)","digits": 4, "use_lut": True,  "dup": True,  "zero": True,  "iters": 1000},
        {"desc": "5자리 표준 (LUT 미적용)", "digits": 5, "use_lut": False, "dup": False, "zero": False, "iters": 1000},
        {"desc": "5자리 리딩제로 (LUT 미적용)", "digits": 5, "use_lut": False, "dup": False, "zero": True, "iters": 1000},
        {"desc": "5자리 중복 (LUT 미적용)", "digits": 5, "use_lut": False, "dup": True, "zero": False, "iters": 1000},
        {"desc": "5자리 하드코어 (LUT 미적용)","digits": 5, "use_lut": False,  "dup": True,  "zero": True,  "iters": 1000},
    ]

    # 축 2: 3가지 솔버 (오리지널 섀넌 엔트로피 배제)
    solvers = [
        ("Heuristic (Freq)", HeuristicSolver),
        ("Fast Shannon (Vectorized)", FastEntropySolver),
        ("Minimax (Knuth)", MinimaxSolver)
    ]

    print("=" * 70)
    print("▶ 4x4x3 마스터마인드 벤치마크 그리드 서치 시작")
    print("=" * 70)

    for env in grid_environments:
        print(f"\n[Environment] {env['desc']} | 시뮬레이션: {env['iters']}회")
        
        # 엔진 클래스 동적 할당
        if env['use_lut'] and HAS_LUT:
            engine_class = MastermindLUTEngine
        else:
            engine_class = MastermindEngine
            
        config = {
            "digits": env['digits'],
            "allow_duplicates": env['dup'],
            "allow_leading_zero": env['zero']
        }

        for solver_name, solver_ptr in solvers:
            print(f" [*] {solver_name}")
            
            # 벤치마크 실행
            avg_turns, max_turns, time_per_iter, total_dt = benchmark(
                solver_class=solver_ptr, 
                engine_class=engine_class, 
                config=config, 
                iterations=env['iters']
            )
            
            # 결과 출력
            print(f"     => 평균: {avg_turns:.3f}턴 | 최악: {max_turns}턴 | 회당: {time_per_iter * 1000:.1f}ms | 총합: {total_dt:.2f}s")

if __name__ == "__main__":
    run_grid_search()