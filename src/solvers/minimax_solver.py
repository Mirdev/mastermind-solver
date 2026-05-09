# src/solvers/minimax_solver.py
import numpy as np
from src.solvers.base_solver import BaseMastermindSolver

class MinimaxSolver(BaseMastermindSolver):
    """Donald Knuth의 Minimax 전략 기반의 솔버."""
    
    def get_best_guess(self, turn):
        best_guess = None
        eval_list = []

        if len(self.candidates) == 1:
            best_guess = self.candidates[0]

        if turn == 1:
            if self.engine.allow_duplicates:
                pattern = [self.start_digits[i // 2] for i in range(self.digits)]
                best_guess = tuple(int(d) for d in pattern)
            else:
                best_guess = tuple(int(d) for d in self.start_digits[:self.digits])

        if best_guess is None:
            S_list = self.candidates 
            if not S_list:
                return None

            full_guesses = getattr(self.engine, 'all_candidates', self.all_guesses)

            if turn == 2:
                if hasattr(self.engine, 'history') and self.engine.history:
                    first_guess = self.engine.history[0][0]
                else:
                    if self.engine.allow_duplicates:
                        pattern = [self.start_digits[i // 2] for i in range(self.digits)]
                        first_guess = tuple(int(d) for d in pattern)
                    else:
                        first_guess = tuple(int(d) for d in self.start_digits[:self.digits])
                G_list = self._get_turn2_templates(first_guess, full_guesses)
            else:
                G_list = full_guesses

            if not G_list:
                return None

            N, M = len(S_list), len(G_list)

            if self.engine.__class__.__name__ == "MastermindLUTEngine":
                G_idx = np.array([c[0]*1000 + c[1]*100 + c[2]*10 + c[3] for c in G_list], dtype=np.int32)
                S_idx = np.array([c[0]*1000 + c[1]*100 + c[2]*10 + c[3] for c in S_list], dtype=np.int32)
                grid = self.engine.lut_matrix[np.ix_(S_idx, G_idx)]
            else:
                G = np.array(G_list, dtype=np.int8)
                S = np.array(S_list, dtype=np.int8)
                strikes = (S[:, None, :] == G[None, :, :]).sum(axis=2)
                H_S = (S[..., None] == np.arange(10)).sum(axis=1)
                H_G = (G[..., None] == np.arange(10)).sum(axis=1)
                balls = np.minimum(H_S[:, None, :], H_G[None, :, :]).sum(axis=2) - strikes
                grid = (strikes << 4) | balls

            for j in range(M):
                _, counts = np.unique(grid[:, j], return_counts=True)
                p = counts / N
                entropy = -np.sum(p * np.log2(p))
                worst_case = int(np.max(counts))
                eval_list.append((G_list[j], worst_case, float(entropy)))

            S_set = set(S_list)
            eval_list.sort(key=lambda x: (x[1], -round(x[2], 6), x[0] not in S_set))
            best_guess = eval_list[0][0]

        expected_splits = []
        worst_split_comparison = {}
        if eval_list:
            best_eval = eval_list[0]
            worst_eval = eval_list[-1]
            expected_splits = [["Worst-case", best_eval[1]]]
            worst_split_comparison = {
                "guess": list(worst_eval[0]),
                "splits": [["Worst-case", worst_eval[1]]]
            }

        evaluation_payload = {
            "metric_name": "Knuth Minimax (Worst-case) + Entropy Tie-breaker",
            "top_guesses": [{"guess": list(g), "score": w} for g, w, _ in eval_list],
            "expected_splits": expected_splits,
            "worst_split_comparison": worst_split_comparison
        }

        payload = self._extract_dashboard_data(turn, best_guess, "processing", evaluation_payload)
        if self.observer_callback:
            self.observer_callback(payload)
            
        return best_guess