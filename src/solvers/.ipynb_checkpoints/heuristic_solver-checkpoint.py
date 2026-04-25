from collections import Counter
from itertools import permutations, product

class HeuristicSolver:
    """
    [Naive Bayesian 구조의 변형]
    각 위치(Position)별 숫자의 독립 출현 확률을 계산하는 대신, 
    연산 효율을 위해 빈도수(Frequency)의 합을 최대화하는 방향으로 추측함.
    """
    # [핵심] 모든 인스턴스가 공유하는 클래스 레벨 캐시
    _candidates_cache = {}
    
    def __init__(self, engine):
        self.engine = engine
        self.digits = engine.digits
        # 생성 시점에 캐시를 확인하여 후보군 할당
        self.candidates = self._generate_all_candidates()

    def _generate_all_candidates(self):
        # 자릿수, 중복여부, 0시작여부를 조합한 고유 키 생성
        cache_key = (self.engine.digits, self.engine.allow_duplicates, self.engine.allow_leading_zero)
        
        # [정말 중요한 체크] 이미 캐시에 있다면 즉시 반환
        if cache_key in HeuristicSolver._candidates_cache:
            return HeuristicSolver._candidates_cache[cache_key][:]

        # 캐시에 없을 때만 최초 1회 실행되는 무거운 연산
        if self.engine.allow_duplicates:
            all_cands = list(product(range(10), repeat=self.engine.digits))
        else:
            all_cands = list(permutations(range(10), self.engine.digits))

        if not self.engine.allow_leading_zero:
            all_cands = [c for c in all_cands if c[0] != 0]
        
        # 결과를 캐시에 저장
        HeuristicSolver._candidates_cache[cache_key] = all_cands
        return all_cands[:]


    def update_candidates(self, guess, feedback):
        self.candidates = [
            c for c in self.candidates 
            if self.engine.get_feedback(c, guess) == feedback
        ]

    def get_best_guess(self, turns):
        """
        위치별 빈도 가중치 합산(Positional Weight Sum) 로직
        """
        if len(self.candidates) == 1:
            return self.candidates[0]

        if self.engine.allow_duplicates == True and turns == 1:
            return (1, 2, 3, 4)
        if self.engine.allow_duplicates == True and turns == 2:
            return (5, 6, 7, 8)

        else:
            # 위치별 숫자의 빈도 측정
            position_counts = [{} for _ in range(self.engine.digits)]
            for cand in self.candidates:
                for i, digit in enumerate(cand):
                    position_counts[i][digit] = position_counts[i].get(digit, 0) + 1
    
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
            
            guess = self.get_best_guess(turns)
                
            feedback = self.engine.get_feedback(secret, guess)
            
            # 정답 판정 (엔진의 digits 설정 사용)
            if feedback == (self.engine.digits, 0):
                return turns
                
            self.update_candidates(guess, feedback)