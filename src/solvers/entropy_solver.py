import math
import random
from collections import Counter
from itertools import permutations, product
import json
import os
from datetime import datetime
import numpy as np

class EntropySolver:
    """
    Shannon Entropy 기반 솔버.
    각 추측이 후보군을 얼마나 줄여줄 수 있는지(기대 정보량)를 계산하여 최적의 수를 선택함.
    """
    # [핵심] 모든 인스턴스가 공유하는 클래스 레벨 캐시
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
        # 생성 시점에 캐시를 확인하여 후보군 할당
        self.candidates = self._generate_all_candidates()

        # 솔버가 생성될 때 딱 한 번 로그 파일을 준비합니다.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        self.log_dir = os.path.join(project_root, "logs")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"sim_log_{timestamp}.jsonl")
        self._log_initial_state()

    def _log_initial_state(self):
        """프로그램 시작 직후 관제 센터를 활성화하기 위한 0턴(초기) 상태를 기록합니다."""
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
                "metric_name": "프로그램 초기화 완료 (대기 중)",
                "top_guesses": [],
                "expected_splits": [],
                "worst_split_comparison": {}
            }
        }
        
        # 파일에 기록하여 웹 대시보드 트리거
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
        # CLI 대시보드 트리거
        if self.observer_callback:
            self.observer_callback(payload)

    def _generate_all_candidates(self):
        # 자릿수, 중복여부, 0시작여부를 조합한 고유 키 생성
        cache_key = (self.engine.digits, self.engine.allow_duplicates, self.engine.allow_leading_zero)
        
        # [데이터 체크]
        if cache_key in EntropySolver._candidates_cache:
            return EntropySolver._candidates_cache[cache_key][:]

        if self.engine.allow_duplicates:
            all_cands = list(product(range(10), repeat=self.engine.digits))
        else:
            all_cands = list(permutations(range(10), self.engine.digits))

        if not self.engine.allow_leading_zero:
            all_cands = [c for c in all_cands if c[0] != 0]
        
        # [저장]
        EntropySolver._candidates_cache[cache_key] = all_cands
        return all_cands[:]

    def update_candidates(self, guess, feedback):
        self.candidates = [
            c for c in self.candidates 
            if self.engine.get_feedback(c, guess) == feedback
        ]

    def _extract_dashboard_data(self, turn, best_guess, evaluation_list, status):
        """대시보드용 공용 데이터 구조 생성"""
        # 1번 대시보드용 확률 행렬 계산
        total = len(self.candidates)
        probs = [[0.0]*10 for _ in range(self.digits)]
        for cand in self.candidates:
            for i, digit in enumerate(cand):
                probs[i][digit] += 1 / total

        # [Dash 4] 1등 숫자(최고의 수)를 찔렀을 때의 쪼개짐
        expected_splits = {}
        if best_guess:
            for cand in self.candidates:
                fb = self.engine.get_feedback(cand, best_guess)
                expected_splits[fb] = expected_splits.get(fb, 0) + 1
        sorted_splits = sorted(expected_splits.items(), key=lambda x: x[1], reverse=True)
        
        # [신설] 꼴등 숫자(최악의 수)를 찔렀을 때의 쪼개짐 (비교용)
        worst_splits = []
        worst_guess = None
        if evaluation_list and len(evaluation_list) > 1:
            worst_guess = evaluation_list[-1][0] # 엔트로피 점수 꼴등
            w_splits_dict = {}
            for cand in self.candidates:
                fb = self.engine.get_feedback(cand, worst_guess)
                w_splits_dict[fb] = w_splits_dict.get(fb, 0) + 1
            worst_splits = sorted(w_splits_dict.items(), key=lambda x: x[1], reverse=True)
        
        payload = {
            "turn": turn,
            "solver_name": "EntropySolver",
            "best_guess": list(best_guess) if best_guess else [],
            "status": status,  # 진행 중: "processing", 승리: "win", 패배: "lose",
            "dashboard_1_heatmap": {"probabilities": probs},
            "dashboard_2_trend": {"remaining_count": total},
            "dashboard_3_evaluation": {
                "metric_name": "Shannon Entropy (bits)",
                "top_guesses": [{"guess": list(g), "score": s} for g, s in evaluation_list],
                "expected_splits": sorted_splits,
                "worst_split_comparison": { 
                    "guess": list(worst_guess) if worst_guess else [],
                    "splits": worst_splits
                }
            }
        }
        
        # [핵심 고정] 페이로드가 만들어지는 즉시 파일에 강제 기록! (UI 존재 여부와 무관)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
        return payload

    def log_state_after_feedback(self, turn, guess):
        """피드백 직후, 다음 턴에 사용할 최적수를 미리 계산하여 대시보드에 띄웁니다."""
        print(f"\n[AI Thinking] 다음 공격(Turn {turn+1})을 위한 최적 경로 분석 중...")
        
        # 상태를 'processing'으로 하여 다음 수를 계산하고 리포트를 생성합니다.
        next_best = self.get_best_guess(turn + 1) 
        return next_best
    
    def get_best_guess(self, turn):
        eval_list = []
        best_guess = None

        # [핵심 로직] 현재 장착된 엔진이 초고속 LUT 엔진인지 판별
        is_lut = self.engine.__class__.__name__ == "MastermindLUTEngine"

        if turn == 1:
            # 중복 허용 시 0011 패턴이 엔트로피 효율이 높고, 중복 불가 시 0123 패턴이 높습니다.
            if self.engine.allow_duplicates:
                best_guess = tuple(int(d) for d in self.start_digits[:2] + self.start_digits[:2])
            else:
                best_guess = tuple(int(d) for d in self.start_digits[:self.digits])

        # 가속 엔진이 아닐 때만 기존 하드코딩과 성능 타협(샘플링) 로직을 적용합니다.
        if not is_lut:
            if turn == 2:
                next_digits = (self.start_digits[self.digits:] + self.start_digits)[:self.digits]
                best_guess = tuple(int(d) for d in next_digits)
            elif len(self.candidates) > 500:
                best_guess = self.candidates[0]

        # LUT 엔진이 사용 중이거나, 비-LUT 환경에서 후보군이 500개 이하로 줄어든 경우
        if best_guess is None:
            for guess in self.candidates:
                # 각 피드백 결과의 분포 확인
                counts = {}
                for cand in self.candidates:
                    feedback = self.engine.get_feedback(cand, guess)
                    counts[feedback] = counts.get(feedback, 0) + 1
                
                # 섀넌 엔트로피 계산: H(X) = -Σ P(x) log2 P(x)
                entropy = 0
                total = len(self.candidates)
                for count in counts.values():
                    p = count / total
                    entropy -= p * math.log2(p)

                eval_list.append((guess, entropy))
            
            eval_list.sort(key=lambda x: (round(x[1], 6), random.random()), reverse=True)
            best_guess = eval_list[0][0]

        # [핵심 고정] 페이로드를 생성하고 내부에서 로깅까지 완료!
        payload = self._extract_dashboard_data(turn, best_guess, eval_list, "processing")
        
        # UI 콜백(대시보드)이 켜져 있을 때만 데이터를 전송
        if self.observer_callback:
            self.observer_callback(payload)
            
        return best_guess

    def log_game_over(self, turn, guess, status):
        """게임 종료 시 최종 상태(win/lose)를 강제로 한 번 더 로깅하여 대시보드에 알림"""
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