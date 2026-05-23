# src/solvers/heuristic_solver.py
from src.solvers.base_solver import BaseMastermindSolver

class HeuristicSolver(BaseMastermindSolver):
    """위치별 숫자의 빈도수 합을 극대화하는 경량화 솔버."""
    
    def get_best_guess(self, turn):
        eval_list = []
        best_guess = None

        if len(self.candidates) == 1:
            best_guess = self.candidates[0]
        elif turn == 1:
            best_guess = self.get_random_first_guess()
        else:
            position_counts = [{} for _ in range(self.engine.digits)]
            for cand in self.candidates:
                for i, digit in enumerate(cand):
                    position_counts[i][digit] = position_counts[i].get(digit, 0) + 1
    
            for cand in self.candidates:
                score = sum(position_counts[i][val] for i, val in enumerate(cand))
                eval_list.append((cand, score))

            eval_list.sort(key=lambda x: x[1], reverse=True)
            best_guess = eval_list[0][0]

        evaluation_payload = {
            "metric_name": "Positional Frequency Score(NB)",
            "top_guesses": [{"guess": list(g), "score": s} for g, s in eval_list],
            "expected_splits": [],
            "worst_split_comparison": {}
        }
        
        payload = self._extract_dashboard_data(turn, best_guess, "processing", evaluation_payload)
        if self.observer_callback:
            self.observer_callback(payload)
            
        return best_guess