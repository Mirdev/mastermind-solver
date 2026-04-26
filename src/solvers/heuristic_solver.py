from collections import Counter
from itertools import permutations, product
import json
import os
from datetime import datetime

class HeuristicSolver:
    """
    [Naive Bayesian 구조의 변형]
    각 위치(Position)별 숫자의 독립 출현 확률을 계산하는 대신, 
    연산 효율을 위해 빈도수(Frequency)의 합을 최대화하는 방향으로 추측함.
    """
    # [핵심] 모든 인스턴스가 공유하는 클래스 레벨 캐시
    _candidates_cache = {}
    
    def __init__(self, engine, observer_callback=None):
        self.engine = engine
        self.observer_callback = observer_callback
        self.digits = engine.digits
        # 생성 시점에 캐시를 확인하여 후보군 할당
        self.candidates = self._generate_all_candidates()

        # 솔버가 생성될 때 딱 한 번 로그 파일을 준비합니다.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        self.log_dir = os.path.join(project_root, "logs")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"sim_log_{timestamp}.jsonl")
        self._log_initial_state()

    def _log_initial_state(self):
        """프로그램 시작 직후 관제 센터를 활성화하기 위한 0턴(초기) 상태를 기록합니다."""
        total = len(self.candidates)
        probs = [[0.0] * 10 for _ in range(self.digits)]
        
        if total > 0:
            for cand in self.candidates:
                for i, digit in enumerate(cand):
                    probs[i][digit] += 1 / total

        payload = {
            "turn": 0,
            "solver_name": self.__class__.__name__,
            "best_guess": [],  
            "status": "standby",
            "dashboard_1_heatmap": {"probabilities": probs},
            "dashboard_2_trend": {"remaining_count": total},
            "dashboard_3_evaluation": {
                "metric_name": "프로그램 초기화 완료 (대기 중)",
                "top_guesses": [],
                "expected_splits": [],
                "worst_split_comparison": {}
            }
        }
        
        # 파일에 기록하여 웹 대시보드 트리거
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
        # CLI 대시보드 트리거
        if self.observer_callback:
            self.observer_callback(payload)

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

    def _extract_dashboard_data(self, turn, best_guess, evaluation_list, status):
        """대시보드용 공용 데이터 구조 생성"""
        # 1번 대시보드용 확률 행렬 계산
        total = len(self.candidates)
        probs = [[0.0]*10 for _ in range(self.digits)]
        for cand in self.candidates:
            for i, digit in enumerate(cand):
                probs[i][digit] += 1 / total
        
        payload = {
            "turn": turn,
            "solver_name": "HeuristicSolver",
            "best_guess": list(best_guess) if best_guess else [],
            "status": status,  # 진행 중: "processing", 승리: "win", 패배: "lose",
            "dashboard_1_heatmap": {"probabilities": probs},
            "dashboard_2_trend": {"remaining_count": total},
            "dashboard_3_evaluation": {
                "metric_name": "Positional Frequency Score(NB)",
		# 빈 리스트가 넘어오더라도 에러가 나지 않도록 처리
                "top_guesses": [{"guess": list(g), "score": s} for g, s in evaluation_list[:5]]
            }
        }
        
        # [핵심 고정] 페이로드가 만들어지는 즉시 파일에 강제 기록! (UI 존재 여부와 무관)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
        return payload

    def get_best_guess(self, turn):
        """
        위치별 빈도 가중치 합산(Positional Weight Sum) 로직
        """
        eval_list = []
        best_guess = None

        if len(self.candidates) == 1:
            best_guess = self.candidates[0]
        elif self.engine.allow_duplicates == True and turn == 1:
            best_guess = tuple((i % 10) for i in range(1, self.engine.digits + 1))
        elif self.engine.allow_duplicates == True and turn == 2:
            best_guess = tuple(((i + self.engine.digits) % 10) for i in range(1, self.engine.digits + 1))
        else:
            # 위치별 숫자의 빈도 측정
            position_counts = [{} for _ in range(self.engine.digits)]
            for cand in self.candidates:
                for i, digit in enumerate(cand):
                    position_counts[i][digit] = position_counts[i].get(digit, 0) + 1
    
            for cand in self.candidates:
                # 확률의 곱(Bayesian) 대신 빈도의 합(Heuristic)을 선택하여 성능 최적화
                score = sum(position_counts[i][val] for i, val in enumerate(cand))
                eval_list.append((cand, score))

            eval_list.sort(key=lambda x: x[1], reverse=True)
            best_guess = eval_list[0][0]

    	# [핵심 고정] 조건문 밖으로 탈출: 무조건 페이로드를 생성하고 내부에서 로깅까지 완료!
        payload = self._extract_dashboard_data(turn, best_guess, eval_list, "processing")
        
        # UI 콜백(대시보드)이 켜져 있을 때만 화면에 그리라고 데이터를 던져줌
        if self.observer_callback:
            self.observer_callback(payload)
            
        return best_guess

    def log_state_after_feedback(self, turn, guess):
        """피드백 직후, 다음 턴에 사용할 최적수를 미리 계산하여 대시보드에 띄웁니다."""
        # 1. 다음 턴을 위한 준비 (후보군 기반 확률 재계산 등은 get_best_guess 내부에서 수행됨)
        # 2. 다음 턴(turn + 1)의 최적수를 미리 계산
        # 이 호출이 자동으로 _extract_dashboard_data를 수행하여 로그를 남기고 대시보드를 갱신합니다.
        print(f"\n[AI Thinking] 다음 공격(Turn {turn+1})을 위한 최적 경로 분석 중...")
        
        # 상태를 'processing'으로 하여 다음 수를 계산하고 리포트를 생성합니다.
        # 이 메서드 안에서 이미 self.observer_callback(payload)이 호출됩니다.
        next_best = self.get_best_guess(turn + 1) 
        
        return next_best

    def log_game_over(self, turn, guess, status):
        """게임 종료 시 최종 상태(win/lose)를 강제로 한 번 더 로깅하여 대시보드에 알림"""
        # 더 이상 계산할 필요 없으므로 eval_list는 빈 배열 전달
        self._extract_dashboard_data(turn, guess, [], status=status)
    
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