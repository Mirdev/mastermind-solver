import random

class MastermindEngine:
    def __init__(self, digits=4, allow_duplicates=False, allow_leading_zero=True):
        self.digits = digits
        self.allow_duplicates = allow_duplicates
        self.allow_leading_zero = allow_leading_zero

    def generate_secret(self):
        """설정된 규칙에 맞는 정답 생성"""
        numbers = list(range(10))
        
        while True:
            if self.allow_duplicates:
                secret = tuple(random.choices(numbers, k=self.digits))
            else:
                secret = tuple(random.sample(numbers, self.digits))
            
            # 0으로 시작하면 안 되는 경우 체크
            if not self.allow_leading_zero and secret[0] == 0:
                continue
            return secret

    def get_feedback(self, secret, guess):
        """
        [고속 최적화 버전]
        동적 메모리 할당(list, pop, remove)과 내장 함수 호출을 배제하여 
        LUT가 없는 3자리, 5자리 환경에서의 연산 속도를 극대화한 로직
        """
        strikes = 0
        s_counts = [0] * 10
        g_counts = [0] * 10
        
        # 1. 단일 루프로 스트라이크 판정 및 볼(Ball) 판정을 위한 숫자 빈도 수집
        for s, g in zip(secret, guess):
            if s == g:
                strikes += 1
            else:
                # 스트라이크가 아닌 숫자들만 카운팅
                s_counts[s] += 1
                g_counts[g] += 1
                
        # 2. 내장 함수를 배제하고 순수 조건문으로 볼(Ball) 개수 합산
        balls = 0
        for i in range(10):
            # 양쪽 모두에 존재하는 숫자(볼 조건 충족)인 경우
            if g_counts[i] > 0 and s_counts[i] > 0:
                # min() 함수 호출 대신 삼항 연산자(조건문) 활용하여 최솟값 가산
                balls += s_counts[i] if s_counts[i] < g_counts[i] else g_counts[i]
                
        return strikes, balls