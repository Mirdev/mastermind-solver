from collections import Counter

class PositionalFrequencySolver:
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
        from itertools import permutations
        return list(permutations(range(10), self.digits))

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