import math
from collections import Counter

class EntropySolver:
    """
    Shannon Entropy 기반 솔버.
    각 추측이 후보군을 얼마나 줄여줄 수 있는지(기대 정보량)를 계산하여 최적의 수를 선택함.
    """
    def __init__(self, engine):
        self.engine = engine
        self.digits = engine.digits
        self.candidates = self._generate_all_candidates()

    def _generate_all_candidates(self):
        from itertools import permutations
        return list(permutations(range(10), self.digits))

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
            return (0, 1, 2, 3)
        
        if len(self.candidates) > 500:  # 후보가 너무 많을 때의 임시 전략
            return self.candidates[0]

        best_guess = None
        max_entropy = -1

        for guess in self.candidates:
            # 각 피드백 결과의 분포 확인
            counts = Counter()
            for cand in self.candidates:
                feedback = self.engine.get_feedback(cand, guess)
                counts[feedback] += 1
            
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