# src/lut_engine.py
import numpy as np
import os
from src.game_engine import MastermindEngine
from src.lut_generator import generate_lut_4_digits  # 제네레이터 임포트 추가

class MastermindLUTEngine(MastermindEngine):
    """
    미리 연산된 LUT를 메모리에 띄워 O(1) 속도로 피드백을 반환하는 가속 엔진.
    제약: 4자리에서만 동작하며, LUT 파일 부재 시 최초 1회 자동 생성합니다.
    """
    def __init__(self, digits=4, allow_duplicates=False, allow_leading_zero=True):
        if digits != 4:
            raise ValueError("[Error] LUT 가속 엔진은 현재 4자리 모드에서만 동작하도록 설계되었습니다.")
        
        super().__init__(digits, allow_duplicates, allow_leading_zero)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(os.path.dirname(current_dir), "data")
        self.lut_file_path = os.path.join(data_dir, "feedback_lut_4.npy")
        
        # [핵심 수정] 파일이 없으면 에러를 내지 않고 엔진이 스스로 자동 생성
        if not os.path.exists(self.lut_file_path):
            print("\n[System] 가속을 위한 LUT 캐시 파일이 발견되지 않았습니다.")
            print("[System] 최초 1회 자동 구축을 시작합니다. 잠시만 기다려주세요...")
            generate_lut_4_digits()
        
        self.lut_matrix = np.load(self.lut_file_path, mmap_mode='r')

    def get_feedback(self, secret, guess):
        if len(secret) != 4 or len(guess) != 4:
            raise ValueError("[Error] 입력된 값이 4자리가 아닙니다.")
            
        idx_secret = secret[0]*1000 + secret[1]*100 + secret[2]*10 + secret[3]
        idx_guess = guess[0]*1000 + guess[1]*100 + guess[2]*10 + guess[3]
        
        feedback_val = self.lut_matrix[idx_secret, idx_guess]
        return int((feedback_val >> 4) & 0x0F), int(feedback_val & 0x0F)