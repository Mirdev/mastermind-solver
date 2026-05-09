# src/solvers/minimax_solver.py
import math
import numpy as np
import json
import os
from datetime import datetime
from itertools import permutations, product
import random

class MinimaxSolver:
    """
    Donald Knuth의 Minimax 전략을 최우선으로 하는 솔버.
    가장 큰 후보군 덩어리(Worst-case)를 최소화(Minimize)하는 것을 1순위로,
    동률 시 섀넌 엔트로피를 2순위로, 후보군 소속 여부를 3순위로 사용하여 최적의 수를 결정합니다.
    """
    _candidates_cache = {}
    
    def __init__(self, engine, observer_callback=None, is_benchmark=False):
        self.engine = engine
        self.observer_callback = observer_callback
        self.is_benchmark = is_benchmark
        self.digits = engine.digits

        self.log_file = None
        
        base_digits = '0123456789'
        if not self.engine.allow_leading_zero:
            self.start_digits = base_digits[1:] + base_digits[0]
        else:
            self.start_digits = base_digits
            
        self.candidates = self._generate_all_candidates()

        if not self.is_benchmark:
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
                "metric_name": "초기화 완료",
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
        
        if cache_key in MinimaxSolver._candidates_cache:
            return MinimaxSolver._candidates_cache[cache_key][:]

        if self.engine.allow_duplicates:
            all_cands = list(product(range(10), repeat=self.engine.digits))
        else:
            all_cands = list(permutations(range(10), self.engine.digits))

        if not self.engine.allow_leading_zero:
            all_cands = [c for c in all_cands if c[0] != 0]
        
        MinimaxSolver._candidates_cache[cache_key] = all_cands
        return all_cands[:]

    def update_candidates(self, guess, feedback):
        self.candidates = [
            c for c in self.candidates 
            if self.engine.get_feedback(c, guess) == feedback
        ]

    def _extract_dashboard_data(self, turn, best_guess, evaluation_list, status):
        if self.is_benchmark or not self.log_file:
            return {}
            
        total = len(self.candidates)
        probs = [[0.0]*10 for _ in range(self.digits)]
        for cand in self.candidates:
            for i, digit in enumerate(cand):
                probs[i][digit] += 1 / total

        expected_splits = []
        worst_split_comparison = {}

        if evaluation_list:
            # evaluation_list는 (guess, worst_case, entropy) 형태이며 오름차순 정렬되어 있음
            best_eval = evaluation_list[0]
            worst_eval = evaluation_list[-1]

            expected_splits = [["Worst-case", best_eval[1]]]
            worst_split_comparison = {
                "guess": list(worst_eval[0]),
                "splits": [["Worst-case", worst_eval[1]]]
            }

        payload = {
            "turn": turn,
            "solver_name": "MinimaxSolver",
            "best_guess": list(best_guess) if best_guess else [],
            "status": status, 
            "dashboard_1_heatmap": {"probabilities": probs},
            "dashboard_2_trend": {"remaining_count": total},
            "dashboard_3_evaluation": {
                "metric_name": "Knuth Minimax (Worst-case) + Entropy Tie-breaker",
                "top_guesses": [{"guess": list(g), "score": w} for g, w, _ in evaluation_list],
                "expected_splits": expected_splits,
                "worst_split_comparison": worst_split_comparison
            }
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
        return payload

    def log_state_after_feedback(self, turn, guess):
        print(f"\n[AI Thinking] 다음 공격(Turn {turn+1})을 위한 최적 경로 분석 중...")
        return self.get_best_guess(turn + 1)

    def _get_turn2_templates(self, first_guess, all_possible_guesses):
        used = set(int(d) for d in first_guess) 
        std_unused = [d for d in range(10) if d not in used]
        
        templates = []
        for guess in all_possible_guesses:
            mapping = {}
            next_idx = 0
            is_canonical = True
            
            for d in guess:
                if d not in used:
                    if d not in mapping:
                        if d != std_unused[next_idx]:
                            is_canonical = False
                            break
                        mapping[d] = std_unused[next_idx]
                        next_idx += 1
                        
            if is_canonical:
                templates.append(guess)
                
        return templates
    
    def get_best_guess(self, turn):
        best_guess = None
        eval_list = []

        if len(self.candidates) == 1:
            best_guess = self.candidates[0]

        # 1. 1턴 하드코딩 (수학적 상수 반환)
        if turn == 1:
            if self.engine.allow_duplicates:
                pattern = [self.start_digits[i // 2] for i in range(self.digits)]
                best_guess = tuple(int(d) for d in pattern)
            else:
                best_guess = tuple(int(d) for d in self.start_digits[:self.digits])

        # 2. 전수조사 연산
        if best_guess is None:
            S_list = self.candidates 
            
            # [수정 사항 3 방어 로직] S_list가 비어있을 경우 (ZeroDivisionError 및 IndexError 방지)
            if not S_list:
                return None

            full_guesses = getattr(self.engine, 'all_candidates', self._generate_all_candidates())

            if turn == 2:
                if hasattr(self.engine, 'history') and self.engine.history:
                    first_guess = self.engine.history[0][0]
                else:
                    if self.engine.allow_duplicates:
                        pattern = [self.start_digits[i // 2] for i in range(self.digits)]
                        first_guess = tuple(int(d) for d in pattern)
                    else:
                        first_guess = tuple(int(d) for d in self.start_digits[:self.digits])
                        
                G_list = self._get_turn2_templates(first_guess, full_guesses)
            else:
                G_list = full_guesses

            # [수정 사항 3 방어 로직] 탐색 공간(G_list)이 비어있을 경우
            if not G_list:
                return None

            N, M = len(S_list), len(G_list)

            # --- [Grid 생성 분기] ---
            if self.engine.__class__.__name__ == "MastermindLUTEngine":
                G_idx = np.array([c[0]*1000 + c[1]*100 + c[2]*10 + c[3] for c in G_list], dtype=np.int32)
                S_idx = np.array([c[0]*1000 + c[1]*100 + c[2]*10 + c[3] for c in S_list], dtype=np.int32)
                grid = self.engine.lut_matrix[np.ix_(S_idx, G_idx)]
            else:
                G = np.array(G_list, dtype=np.int8)
                S = np.array(S_list, dtype=np.int8)
                
                strikes = (S[:, None, :] == G[None, :, :]).sum(axis=2)
                H_S = (S[..., None] == np.arange(10)).sum(axis=1)
                H_G = (G[..., None] == np.arange(10)).sum(axis=1)
                balls = np.minimum(H_S[:, None, :], H_G[None, :, :]).sum(axis=2) - strikes
                grid = (strikes << 4) | balls

            # --- [단일화된 평가 루프] 튜플 구조: (guess, worst_case, entropy) ---
            for j in range(M):
                _, counts = np.unique(grid[:, j], return_counts=True)
                p = counts / N
                entropy = -np.sum(p * np.log2(p))
                worst_case = int(np.max(counts))
                # [수정 사항 1 적용] _extract_dashboard_data와 동일한 (guess, worst_case, entropy) 순서로 통일
                eval_list.append((G_list[j], worst_case, float(entropy)))

            # --- [Minimax 정렬 전략] ---
            # 1순위: 최악의 경우 최소화 (x[1], 오름차순)
            # 2순위: 엔트로피 최대화 (-round(x[2], 6)을 통해 내림차순 효과)
            # 3순위: [수정 사항 4 적용] 동률 시 남은 정답 후보군에 속한 경우 우선 (무한 루프 방지)
            S_set = set(S_list)
            eval_list.sort(key=lambda x: (x[1], -round(x[2], 6), x[0] not in S_set))
            best_guess = eval_list[0][0]

        # 대시보드 페이로드 전송
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
            
            # 방어 로직: 더 이상 추측할 수 없을 때 무한 루프 방지
            if guess is None:
                return turns
                
            feedback = self.engine.get_feedback(secret, guess)
            
            if feedback == (self.engine.digits, 0):
                return turns
                
            self.update_candidates(guess, feedback)