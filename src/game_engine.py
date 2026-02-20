import random

class MastermindEngine:
    """
    숫자야구의 핵심 규칙(정답 생성, 스트라이크/볼 판정)을 담당하는 엔진
    """
    def __init__(self, digits=4):
        self.digits = digits

    def generate_secret(self):
        """중복 없는 4자리 정답 생성 (수학적 무작위성 확보)"""
        nums = list(range(10))
        random.shuffle(nums)
        return tuple(nums[:self.digits])

    def get_feedback(self, secret, guess):
        """
        스트라이크와 볼 개수 반환
        중복 계산을 피하기 위해 set 연산을 활용한 최적화 로직 적용
        """
        strikes = sum(1 for s, g in zip(secret, guess) if s == g)
        common = len(set(secret) & set(guess))
        balls = common - strikes
        return strikes, balls