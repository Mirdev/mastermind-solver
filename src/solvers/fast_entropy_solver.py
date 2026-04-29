# src/solvers/fast_entropy_solver.py
import math
import numpy as np
import json
import os
from datetime import datetime
from itertools import permutations, product
import random

class FastEntropySolver:
    """
    NumPy Vectorization 기반의 초고속 Shannon Entropy 솔버.
    파이썬 반복문을 배제하고 3차원 브로드캐스팅 및 행렬 교차 연산을 사용하여 연산 속도를 극대화합니다.
    """
    _candidates_cache = {}
    
    def __init__(self, engine, observer_callback=None):
        self.engine = engine
        self.observer_callback = observer_callback
        self.digits = engine.digits
        
        base_digits = '0123456789'
        if not self.engine.allow_leading_zero:
            self.start_digits = base_digits[1:] + base_digits[0]
        else:
            self.start_digits = base_digits
            
        self.candidates = self._generate_all_candidates()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        self.log_dir = os.path.join(project_root, "logs")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"sim_log_{timestamp}.jsonl")
        self._log_initial_state()

    def _log_initial_state(self):
        total = len(self.candidates)
        probs = [[0.0] * 10 for _ in range(self.digits)]
        
        if total > 0:
            for cand in self.candidates:
                for i, digit in enumerate(cand):
                    probs[i][digit] += 1 / total

        payload = {
            "turn": 0,
            "solver_name": self.__class__.__name__,
            "best_guess": [],  
            "status": "standby",
            "dashboard_1_heatmap": {"probabilities": probs},
            "dashboard_2_trend": {"remaining_count": total},
            "dashboard_3_evaluation": {
                "metric_name": "초기화 완료 (Fast Mode)",
                "top_guesses": [],
                "expected_splits": [],
                "worst_split_comparison": {}
            }
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
        if self.observer_callback:
            self.observer_callback(payload)

    def _generate_all_candidates(self):
        cache_key = (self.engine.digits, self.engine.allow_duplicates, self.engine.allow_leading_zero)
        
        if cache_key in FastEntropySolver._candidates_cache:
            return FastEntropySolver._candidates_cache[cache_key][:]

        if self.engine.allow_duplicates:
            all_cands = list(product(range(10), repeat=self.engine.digits))
        else:
            all_cands = list(permutations(range(10), self.engine.digits))

        if not self.engine.allow_leading_zero:
            all_cands = [c for c in all_cands if c[0] != 0]
        
        FastEntropySolver._candidates_cache[cache_key] = all_cands
        return all_cands[:]

    def update_candidates(self, guess, feedback):
        self.candidates = [
            c for c in self.candidates 
            if self.engine.get_feedback(c, guess) == feedback
        ]

    def _extract_dashboard_data(self, turn, best_guess, evaluation_list, status):
        total = len(self.candidates)
        probs = [[0.0]*10 for _ in range(self.digits)]
        for cand in self.candidates:
            for i, digit in enumerate(cand):
                probs[i][digit] += 1 / total

        expected_splits = {}
        if best_guess:
            for cand in self.candidates:
                fb = self.engine.get_feedback(cand, best_guess)
                expected_splits[fb] = expected_splits.get(fb, 0) + 1
        sorted_splits = sorted(expected_splits.items(), key=lambda x: x[1], reverse=True)
        
        worst_splits = []
        worst_guess = None
        if evaluation_list and len(evaluation_list) > 1:
            worst_guess = evaluation_list[-1][0] 
            w_splits_dict = {}
            for cand in self.candidates:
                fb = self.engine.get_feedback(cand, worst_guess)
                w_splits_dict[fb] = w_splits_dict.get(fb, 0) + 1
            worst_splits = sorted(w_splits_dict.items(), key=lambda x: x[1], reverse=True)
        
        payload = {
            "turn": turn,
            "solver_name": "FastEntropySolver",
            "best_guess": list(best_guess) if best_guess else [],
            "status": status, 
            "dashboard_1_heatmap": {"probabilities": probs},
            "dashboard_2_trend": {"remaining_count": total},
            "dashboard_3_evaluation": {
                "metric_name": "Shannon Entropy (bits)",
                "top_guesses": [{"guess": list(g), "score": s} for g, s, _ in evaluation_list],
                "expected_splits": sorted_splits,
                "worst_split_comparison": { 
                    "guess": list(worst_guess) if worst_guess else [],
                    "splits": worst_splits
                }
            }
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
        return payload

    def log_state_after_feedback(self, turn, guess):
        print(f"\n[AI Thinking] 다음 공격(Turn {turn+1})을 위한 최적 경로 분석 중...")
        return self.get_best_guess(turn + 1) 
    
    def get_best_guess(self, turn):
        eval_list = []
        best_guess = None

        is_lut = self.engine.__class__.__name__ == "MastermindLUTEngine"

        # 1. 1턴 하드코딩 (수학적 상수 반환)
        if not is_lut and turn == 1:
            if self.engine.allow_duplicates:
                # 자릿수(self.digits)에 맞춰 동적으로 최적 패턴(AAB, AABB, AABBC 등) 자동 생성
                pattern = [self.start_digits[i // 2] for i in range(self.digits)]
                best_guess = tuple(int(d) for d in pattern)
            else:
                best_guess = tuple(int(d) for d in self.start_digits[:self.digits])

        # 2. 전수조사 연산 (분기문 없는 깔끔한 로직)
        if best_guess is None:
            if is_lut:
                # LUT 전용 슬라이싱 연산
                cand_idx = np.array([c[0]*1000 + c[1]*100 + c[2]*10 + c[3] for c in self.candidates], dtype=np.int32)
                N = len(cand_idx)
                grid = self.engine.lut_matrix[np.ix_(cand_idx, cand_idx)]
                
                for j in range(N):
                    _, counts = np.unique(grid[:, j], return_counts=True)
                    p = counts / N
                    entropy = -np.sum(p * np.log2(p))

                    # [추가] NumPy를 활용하여 최악의 경우(가장 큰 덩어리) 도출
                    worst_case = int(np.max(counts))
                    eval_list.append((self.candidates[j], float(entropy), worst_case))
                    
            else:
                # N자리 범용 브로드캐스팅 연산
                C = np.array(self.candidates, dtype=np.int8)
                N = len(C)
                
                strikes = (C[:, None, :] == C[None, :, :]).sum(axis=2)
                H = (C[..., None] == np.arange(10)).sum(axis=1)
                matches = np.minimum(H[:, None, :], H[None, :, :]).sum(axis=2)
                balls = matches - strikes
                
                grid = (strikes << 4) | balls
                
                for j in range(N):
                    _, counts = np.unique(grid[:, j], return_counts=True)
                    p = counts / N
                    entropy = -np.sum(p * np.log2(p))
                    
                    # [추가] NumPy를 활용하여 최악의 경우(가장 큰 덩어리) 도출
                    worst_case = int(np.max(counts))
                    eval_list.append((self.candidates[j], float(entropy), worst_case))

            eval_list.sort(key=lambda x: (round(x[1], 6), -x[2]), reverse=True)
            best_guess = eval_list[0][0]

        payload = self._extract_dashboard_data(turn, best_guess, eval_list, "processing")
        
        if self.observer_callback:
            self.observer_callback(payload)
            
        return best_guess

    def log_game_over(self, turn, guess, status):
        self._extract_dashboard_data(turn, guess, [], status=status)
    
    def solve(self, secret):
        turns = 0
        while True:
            turns += 1
            guess = self.get_best_guess(turns)
            feedback = self.engine.get_feedback(secret, guess)
            
            if feedback == (self.engine.digits, 0):
                return turns
                
            self.update_candidates(guess, feedback)