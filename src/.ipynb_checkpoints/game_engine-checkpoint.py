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
        """S/B 판정 로직 (중복 허용 시에도 작동하도록 설계)"""
        strikes = sum(1 for s, g in zip(secret, guess) if s == g)
        
        # 중복 허용 시 볼 판정은 조금 더 복잡함
        s_list = list(secret)
        g_list = list(guess)
        
        # 스트라이크 제거 후 남은 숫자들로 볼 계산
        for i in range(len(g_list)-1, -1, -1):
            if g_list[i] == s_list[i]:
                s_list.pop(i)
                g_list.pop(i)
        
        balls = 0
        for g in g_list:
            if g in s_list:
                balls += 1
                s_list.remove(g)
                
        return strikes, balls