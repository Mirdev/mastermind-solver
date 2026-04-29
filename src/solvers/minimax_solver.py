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
    동률 시 섀넌 엔트로피를 2순위로 사용하여 최적의 수를 결정합니다.
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
        total = len(self.candidates)
        probs = [[0.0]*10 for _ in range(self.digits)]
        for cand in self.candidates:
            for i, digit in enumerate(cand):
                probs[i][digit] += 1 / total

        expected_splits = []
        worst_split_comparison = {}

        if evaluation_list:
            # evaluation_list는 (guess, worst_case, entropy) 형태이며 오름차순(최적->최악) 정렬되어 있음
            best_eval = evaluation_list[0]
            worst_eval = evaluation_list[-1]

            # 피드백(스트라이크/볼) 문자열 대신, Minimax의 핵심인 worst_case 숫자 자체를 저장
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
                "expected_splits": expected_splits,            # 페이로드에 병합
                "worst_split_comparison": worst_split_comparison # 페이로드에 병합
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
        
        if turn == 1:
            # 중복 허용 시 0011 패턴이 엔트로피 효율이 높고, 중복 불가 시 0123 패턴이 높습니다.
            if self.engine.allow_duplicates:
                # 3자리(001), 4자리(0011), 5자리(00112) 등 자릿수에 맞춰 동적 생성
                pattern = [self.start_digits[i // 2] for i in range(self.digits)]
                best_guess = tuple(int(d) for d in pattern)
            else:
                best_guess = tuple(int(d) for d in self.start_digits[:self.digits])
        elif turn == 2:
            next_digits = (self.start_digits[self.digits:] + self.start_digits)[:self.digits]
            best_guess = tuple(int(d) for d in next_digits)

        # 2. 미니맥스 전수 조사
        if best_guess is None:
            C = np.array(self.candidates, dtype=np.int8)
            N = len(C)
            
            # 피드백 매트릭스 계산 (벡터화)
            strikes = (C[:, None, :] == C[None, :, :]).sum(axis=2)
            H = (C[..., None] == np.arange(10)).sum(axis=1)
            matches = np.minimum(H[:, None, :], H[None, :, :]).sum(axis=2)
            grid = (strikes << 4) | (matches - strikes)
            
            for j in range(N):
                _, counts = np.unique(grid[:, j], return_counts=True)
                
                # [핵심] Minimax 지표: 최악의 경우 남는 후보 수
                worst_case = int(np.max(counts))
                
                # [타이 브레이커] Entropy 지표
                p = counts / N
                entropy = -np.sum(p * np.log2(p))
                
                eval_list.append((self.candidates[j], worst_case, float(entropy)))

            # 정렬 전략: 1순위 워스트 케이스 최소화(오름차순), 2순위 엔트로피 최대화(내림차순)
            # worst_case는 작을수록 좋으므로 그대로(오름차순), entropy는 클수록 좋으므로 마이너스(-) 처리 후 정렬
            eval_list.sort(key=lambda x: (x[1], -round(x[2], 6)))
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