from collections import Counter
from itertools import permutations, product

class HeuristicSolver:
    """
    [Naive Bayesian 구조의 변형]
    각 위치(Position)별 숫자의 독립 출현 확률을 계산하는 대신, 
    연산 효율을 위해 빈도수(Frequency)의 합을 최대화하는 방향으로 추측함.
    """
    def __init__(self, engine):
        self.engine = engine
        self.digits = engine.digits
        self.candidates = self._generate_all_candidates()

    def _generate_all_candidates(self):
        # 엔진의 allow_duplicates 설정에 따라 생성 방식 결정
        if self.engine.allow_duplicates:
            # 중복 허용: 0000 ~ 9999 (10^4개)
            all_cands = list(product(range(10), repeat=self.engine.digits))
        else:
            # 중복 비허용: nPr (10P4 = 5040개)
            all_cands = list(permutations(range(10), self.engine.digits))
    
        # 엔진의 allow_leading_zero 설정에 따라 필터링
        if not self.engine.allow_leading_zero:
            all_cands = [c for c in all_cands if c[0] != 0]
            
        return all_cands

    def update_candidates(self, guess, feedback):
        self.candidates = [
            c for c in self.candidates 
            if self.engine.get_feedback(c, guess) == feedback
        ]

    def get_best_guess(self):
        """
        위치별 빈도 가중치 합산(Positional Weight Sum) 로직
        """
        if len(self.candidates) == 1:
            return self.candidates[0]

        # 위치별 숫자의 빈도 측정
        position_counts = [Counter() for _ in range(self.digits)]
        for cand in self.candidates:
            for i, val in enumerate(cand):
                position_counts[i][val] += 1

        best_guess = None
        max_score = -1

        for cand in self.candidates:
            # 확률의 곱(Bayesian) 대신 빈도의 합(Heuristic)을 선택하여 성능 최적화
            score = sum(position_counts[i][val] for i, val in enumerate(cand))
            if score > max_score:
                max_score = score
                best_guess = cand

        return best_guess
        
    def solve(self, secret):
        turns = 0
        while True:
            turns += 1
            # 엔트로피 솔버는 turns가 필요하므로 가변 인자로 처리하거나 내부에서 판단
            if hasattr(self, 'get_best_guess') and self.__class__.__name__ == 'EntropySolver':
                guess = self.get_best_guess(turns)
            else:
                guess = self.get_best_guess()
                
            feedback = self.engine.get_feedback(secret, guess)
            
            # 정답 판정 (엔진의 digits 설정 사용)
            if feedback == (self.engine.digits, 0):
                return turns
                
            self.update_candidates(guess, feedback)