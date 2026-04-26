# src/lut_generator.py
import numpy as np
import os
import sys
from itertools import product

# 경로 주입 (단독 실행을 위함)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.game_engine import MastermindEngine

def generate_lut_4_digits():
    print("==========================================")
    print("  🚀 4자리 전용 LUT 데이터 생성기 시작  ")
    print("==========================================")
    print("[System] 10,000 x 10,000 행렬을 계산합니다. (메모리 약 100MB 할당)")
    
    # 0000 ~ 9999 까지의 인덱스를 담을 10000x10000 int8 배열
    lut_matrix = np.zeros((10000, 10000), dtype=np.int8)
    
    # 생성기용 임시 엔진 (모든 경우의 수를 만들기 위해 제약 해제)
    engine = MastermindEngine(digits=4, allow_duplicates=True, allow_leading_zero=True)
    all_cands = list(product(range(10), repeat=4))
    total_steps = len(all_cands)
    
    for i, secret in enumerate(all_cands):
        # 튜플 (1, 2, 3, 4) -> 정수 인덱스 1234 변환
        idx_secret = secret[0]*1000 + secret[1]*100 + secret[2]*10 + secret[3]
        
        for guess in all_cands:
            idx_guess = guess[0]*1000 + guess[1]*100 + guess[2]*10 + guess[3]
            s, b = engine.get_feedback(secret, guess)
            
            # 비트 마스킹 (상위 4비트: Strike, 하위 4비트: Ball)
            lut_matrix[idx_secret, idx_guess] = (s << 4) | b
            
        if (i + 1) % 1000 == 0:
            print(f" -> 진행률: {i + 1} / {total_steps} 완료")

    # 저장 경로 확보 (프로젝트 루트의 data 폴더)
    data_dir = os.path.join(root_dir, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    save_path = os.path.join(data_dir, "feedback_lut_4.npy")
    np.save(save_path, lut_matrix)
    print(f"\n✅ [성공] LUT 파일 생성이 완료되었습니다.\n경로: {save_path}")

if __name__ == "__main__":
    generate_lut_4_digits()