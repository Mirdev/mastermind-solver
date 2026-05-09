# src/solvers/base_solver.py
import os
import json
import numpy as np
from datetime import datetime
from itertools import permutations, product
from abc import ABC, abstractmethod

class BaseMastermindSolver(ABC):
    """
    모든 마스터마인드 솔버의 상태 통제 및 게임 루프를 담당하는 추상 기반 클래스.
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
        if cache_key in BaseMastermindSolver._candidates_cache:
            return BaseMastermindSolver._candidates_cache[cache_key][:]

        if self.engine.allow_duplicates:
            all_cands = list(product(range(10), repeat=self.engine.digits))
        else:
            all_cands = list(permutations(range(10), self.engine.digits))

        if not self.engine.allow_leading_zero:
            all_cands = [c for c in all_cands if c[0] != 0]
        
        BaseMastermindSolver._candidates_cache[cache_key] = all_cands
        return all_cands[:]

    def update_candidates(self, guess, feedback):
        self.candidates = [
            c for c in self.candidates 
            if self.engine.get_feedback(c, guess) == feedback
        ]

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

    def _extract_dashboard_data(self, turn, best_guess, status, evaluation_payload):
        if self.is_benchmark or not self.log_file:
            return {}
            
        total = len(self.candidates)
        probs = [[0.0]*10 for _ in range(self.digits)]
        for cand in self.candidates:
            for i, digit in enumerate(cand):
                probs[i][digit] += 1 / total
        
        payload = {
            "turn": turn,
            "solver_name": self.__class__.__name__,
            "best_guess": list(best_guess) if best_guess else [],
            "status": status, 
            "dashboard_1_heatmap": {"probabilities": probs},
            "dashboard_2_trend": {"remaining_count": total},
            "dashboard_3_evaluation": evaluation_payload
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
        return payload

    def log_state_after_feedback(self, turn, guess):
        print(f"\n[AI Thinking] 다음 공격(Turn {turn+1})을 위한 최적 경로 분석 중...")
        return self.get_best_guess(turn + 1)

    def log_game_over(self, turn, guess, status):
        self._extract_dashboard_data(turn, guess, status, {
            "metric_name": "게임 종료",
            "top_guesses": [],
            "expected_splits": [],
            "worst_split_comparison": {}
        })
    
    def solve(self, secret):
        turns = 0
        while True:
            turns += 1
            guess = self.get_best_guess(turns)
            if guess is None:
                return turns
            feedback = self.engine.get_feedback(secret, guess)
            if feedback == (self.engine.digits, 0):
                return turns
            self.update_candidates(guess, feedback)

    @abstractmethod
    def get_best_guess(self, turn):
        """각 솔버가 구현해야 하는 핵심 알고리즘"""
        pass