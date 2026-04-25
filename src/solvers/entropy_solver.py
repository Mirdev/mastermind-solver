import math
import random
from collections import Counter
from itertools import permutations, product

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

    def _extract_dashboard_data(self, turn, best_guess, evaluation_list):
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
        
        return {
            "turn": turn,
            "solver_name": "EntropySolver",
            "best_guess": list(best_guess) if best_guess else [],
            "dashboard_1_heatmap": {"probabilities": probs},
            "dashboard_2_trend": {"remaining_count": total},
            "dashboard_3_evaluation": {
                "metric_name": "Shannon Entropy (bits)",
                "top_guesses": [{"guess": list(g), "score": s} for g, s in evaluation_list[:5]],
                "expected_splits": sorted_splits,
                "worst_split_comparison": { # 비교 데이터 전송
                    "guess": list(worst_guess) if worst_guess else [],
                    "splits": worst_splits
                }
            }
        }

    def get_best_guess(self, turn):
        """
        [Engineering Note]
        초반(1~2턴)에는 전체 후보군에 대한 엔트로피 계산량이 지수적으로 많으므로,
        실시간 응답성을 위해 미리 계산된 최적의 수(Heuristic Seed)를 사용함.
        """
        eval_list = []
        best_guess = None

        # 하드코딩된 초반 전략 (성능 최적화를 위한 의도적 설계)
        if turn == 1:
            best_guess = tuple(int(d) for d in self.start_digits[:4])
        elif turn == 2:
            best_guess = tuple(int(d) for d in self.start_digits[4:8])
        else:
            # sampling code
            if len(self.candidates) > 500:
                best_guess = self.candidates[0]
            else:
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

                eval_list.sort(key=lambda x: x[1], reverse=True)
                best_guess = eval_list[0][0]

	# 데이터 발송
        if self.observer_callback:
            payload = self._extract_dashboard_data(turn, best_guess, eval_list)
            self.observer_callback(payload)
            
        return best_guess
        
    def solve(self, secret):
        turns = 0
        while True:
            turns += 1
            
            guess = self.get_best_guess(turns)
                
            feedback = self.engine.get_feedback(secret, guess)
            
            # 정답 판정 (엔진의 digits 설정 사용)
            if feedback == (self.engine.digits, 0):
                return turns
                
            self.update_candidates(guess, feedback)