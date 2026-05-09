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
            
        # [수정된 부분] 전체 추측 공간(G)과 정답 후보군(S)을 명확히 분리하여 저장
        self.all_guesses = self._generate_all_candidates()
        self.candidates = self.all_guesses[:]

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
        if self.is_benchmark or not self.log_file:
            return {}
            
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

    def _get_turn2_templates(self, first_guess, all_possible_guesses):
        """1턴 추측을 기준으로 2턴의 대칭성 파괴 대표 템플릿 추출 (타입 안정성 및 중복 처리 강화)"""
        # [수정] 들어온 값이 문자열이든 튜플이든 무조건 정수형(int) 집합으로 강제 변환
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
                        # 미사용 숫자가 처음 등장할 때, 지정된 순서(std_unused)대로 등장하는지 검증
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

        # 2. 전수조사 연산 (리던던시가 완벽히 소거된 클린 코드)
        if best_guess is None:
            S_list = self.candidates 
            # [수정된 부분] 엔진에 전체 후보군이 없더라도, 솔버가 자체 보존 중인 전체 공간(all_guesses)을 사용
            full_guesses = getattr(self.engine, 'all_candidates', self._generate_all_candidates())

            # [핵심] 2턴일 경우 템플릿을 추출하여 탐색 공간(G)을 극단적으로 압축
            if turn == 2:
                if hasattr(self.engine, 'history') and self.engine.history:
                    first_guess = self.engine.history[0][0]
                else:
                    # [수정] 문자열이 아닌 명확한 정수형 튜플로 first_guess 생성
                    if self.engine.allow_duplicates:
                        pattern = [self.start_digits[i // 2] for i in range(self.digits)]
                        first_guess = tuple(int(d) for d in pattern)
                    else:
                        first_guess = tuple(int(d) for d in self.start_digits[:self.digits])
                        
                G_list = self._get_turn2_templates(first_guess, full_guesses)
            else:
                G_list = full_guesses

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

            # --- [단일화된 평가 루프] 튜플 구조: (guess, entropy, worst_case) ---
            for j in range(M):
                _, counts = np.unique(grid[:, j], return_counts=True)
                p = counts / N
                entropy = -np.sum(p * np.log2(p))
                worst_case = int(np.max(counts))
                eval_list.append((G_list[j], float(entropy), worst_case))

            # --- [FastEntropy 정렬 전략] ---
            # 1순위: 엔트로피 최대화 (내림차순, reverse=True)
            # 2순위: 최악의 경우 최소화 (-x[2]를 통해 오름차순 효과)
            eval_list.sort(key=lambda x: (round(x[1], 6), -x[2]), reverse=True)
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
            feedback = self.engine.get_feedback(secret, guess)
            
            if feedback == (self.engine.digits, 0):
                return turns
                
            self.update_candidates(guess, feedback)