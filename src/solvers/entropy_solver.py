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
    
    def __init__(self, engine):
        self.engine = engine
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

    def get_best_guess(self, turn):
        """
        [Engineering Note]
        초반(1~2턴)에는 전체 후보군에 대한 엔트로피 계산량이 지수적으로 많으므로,
        실시간 응답성을 위해 미리 계산된 최적의 수(Heuristic Seed)를 사용함.
        """
        # 하드코딩된 초반 전략 (성능 최적화를 위한 의도적 설계)
        if turn == 1:
            res = self.start_digits[:4]
        elif turn == 2:
            res = self.start_digits[4:8]
        else:
            # sampling code
            if len(self.candidates) > 500:
                return self.candidates[0]
    
            best_guess = None
            max_entropy = -1
    
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
                
                if entropy > max_entropy:
                    max_entropy = entropy
                    best_guess = guess
            
            return best_guess
        return tuple(int(d) for d in res)
        
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