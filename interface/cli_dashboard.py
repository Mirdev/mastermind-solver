import json
import os
from datetime import datetime

class CLIDashboard:
    """
    솔버로부터 데이터를 받아 시각화 및 로깅을 수행하는 컨트롤러
    - Dash 1: 10x4 전치 히트맵 (자릿수가 열, 숫자가 행)
    - Dash 2: 후보군 현황
    - Dash 3: 상위 추천 목록
    - Dash 4: 솔버별 결정 근거 (Decision Tree vs Score Breakdown)
    """
    def __init__(self, log_dir="logs"):
        self.history = []
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 실행 시마다 고유한 파일명 생성 (예: log_20260425_090000.jsonl)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"sim_log_{timestamp}.jsonl")

    def receive_data(self, payload):
        """솔버의 콜백을 통해 데이터를 수신하는 입구"""
        # 트랙 1: 메모리에 저장 (실시간 분석용)
        self.history.append(payload)
        
        # 트랙 2: 파일(JSONL)에 영구 저장 (나중에 D3.js 연동용)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
        # 도스 기반 실시간 렌더링
        self._render_console(payload)

    def _render_console(self, data):
        turn = data['turn']
        solver = data['solver_name']
        remains = data['dashboard_2_trend']['remaining_count']
        metric_name = data['dashboard_3_evaluation']['metric_name']
        eval_data = data['dashboard_3_evaluation']
        best_guess = data['best_guess']
        probs = data['dashboard_1_heatmap']['probabilities']
        num_pos = len(probs)
        
        print(f"\n" + "="*62)
        print(f"[{solver}] Turn {turn} 시각화 분석 리포트")
        print(f"="*62)
        
        # [Dash 2] 후보군 현황
        print(f"▶ [Dash 2] 남은 정답 후보군: {remains}개")
        
        # [Dash 3] 상위 추천 목록 (솔버 공통)
        print(f"▶ [Dash 3] {metric_name} 상위 추천:")
        top_picks = eval_data.get('top_guesses', [])
        if not top_picks:
            print("   (초반 턴 속도 최적화를 위해 탐색 스킵)")
        else:
            for i, pick in enumerate(top_picks[:3]):
                print(f"   {i+1}. {pick['guess']} (점수: {pick['score']:.4f})")

        # [Dash 4] 솔버별 결정적 근거 (Why this guess?)
        print(f"▶ [Dash 4] AI의 결정적 근거 (Why {best_guess}?):")
        if solver == "EntropySolver" and 'expected_splits' in eval_data:
            splits = eval_data['expected_splits']
            worst_comp = eval_data.get('worst_split_comparison', {})
            if not splits:
                print("   (탐색 스킵)")
            else:
                print(f"   [채택] {best_guess}를 찔렀을 때 (엔트로피 최고점):")
                print(f"     ├─ 가장 운이 나쁜 [{splits[0][0][0]}S {splits[0][0][1]}B] 판정 시에도 ➔ {splits[0][1]}개만 남음!")
                
                if worst_comp and worst_comp.get('splits'):
                    w_guess = worst_comp['guess']
                    w_splits = worst_comp['splits']
                    print(f"   [비교] 만약 최악의 수 {w_guess}를 찔렀다면?")
                    print(f"     └─ 가장 운이 나쁜 [{w_splits[0][0][0]}S {w_splits[0][0][1]}B] 판정 시 ➔ 무려 {w_splits[0][1]}개나 남음.")
                    
        elif solver == "HeuristicSolver":
            # 휴리스틱: 가중치 합산(Score Breakdown) 표기
            if remains <= 1:
                print("   (후보군이 1개이므로 연산 스킵)")
            else:
                breakdown_strs = []
                total_score = 0
                for pos, (p_list, chosen_digit) in enumerate(zip(probs, best_guess)):
                    # 확률 * 남은 개수 = 해당 자리의 실제 출현 빈도수
                    score = p_list[chosen_digit] * remains 
                    total_score += score
                    breakdown_strs.append(f"{pos+1}번[{chosen_digit}]:{score:.1f}점")
                
                formula = " + ".join(breakdown_strs)
                print(f"   └─ 빈도합산: {formula} = 총 {total_score:.1f}점 (가성비 1위)")
        else:
            print("   (선택 근거 데이터 없음)")

       # [Dash 1] 10x4 전치(Transposed) 확률 히트맵
        print(f"▶ [Dash 1] 자릿수별 확률 히트맵 (%) - [*]는 AI 선택")
        
        # 헤더 생성 (자릿수가 열)
        header = f" Digit  |  " + " | ".join([f" Pos {i+1:^1} " for i in range(num_pos)]) + " |"
        sep = "-" * len(header)
        print(f"   {sep}\n   {header}\n   {sep}")
        
        # 0부터 9까지 행(Row)으로 출력
        for d in range(10):
            row_str = f"   {d:^5}   | "
            for pos in range(num_pos):
                prob = probs[pos][d]
                val_str = f"{prob*100:5.1f}" if prob > 0 else "  -  "
                
                # AI가 이번 턴에 선택한 숫자면 대괄호[*] 표시
                if best_guess[pos] == d:
                    row_str += f"[{val_str:^7}]|"
                else:
                    row_str += f" {val_str:^7} |"
            print(row_str)
        print(f"   {sep}")
        print("="*62)