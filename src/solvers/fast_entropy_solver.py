# src/solvers/fast_entropy_solver.py
import numpy as np
from src.solvers.base_solver import BaseMastermindSolver

class FastEntropySolver(BaseMastermindSolver):
    """NumPy Vectorization 기반의 초고속 Shannon Entropy 솔버."""
    
    def get_best_guess(self, turn):
        best_guess = None
        eval_list = []

        if len(self.candidates) == 1:
            best_guess = self.candidates[0]

        # 1턴 하드코딩
        if turn == 1:
            if self.engine.allow_duplicates:
                pattern = [self.start_digits[i // 2] for i in range(self.digits)]
                best_guess = tuple(int(d) for d in pattern)
            else:
                best_guess = tuple(int(d) for d in self.start_digits[:self.digits])

        # 2턴 이후 연산
        if best_guess is None:
            S_list = self.candidates 
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

            N, M = len(S_list), len(G_list)

            # 그리드 생성 (LUT 또는 동적 연산)
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

            # 엔트로피 평가 루프
            for j in range(M):
                _, counts = np.unique(grid[:, j], return_counts=True)
                p = counts / N
                entropy = -np.sum(p * np.log2(p))
                worst_case = int(np.max(counts))
                eval_list.append((G_list[j], float(entropy), worst_case))

            eval_list.sort(key=lambda x: (round(x[1], 6), -x[2]), reverse=True)
            best_guess = eval_list[0][0]

        # --- [Dashboard Data 정제] ---
        def get_detailed_splits(guess):
            if not guess: return []
            counts = {}
            for cand in self.candidates:
                fb = self.engine.get_feedback(cand, guess)
                counts[fb] = counts.get(fb, 0) + 1
            return sorted(counts.items(), key=lambda x: x[1], reverse=True)

        expected_splits = get_detailed_splits(best_guess)
        worst_guess = eval_list[-1][0] if eval_list and len(eval_list) > 1 else None
        worst_splits = get_detailed_splits(worst_guess)
            
        evaluation_payload = {
            "metric_name": "Shannon Entropy (bits)",
            "top_guesses": [{"guess": list(g), "score": s} for g, s, _ in eval_list[:10]],
            "expected_splits": expected_splits,
            "worst_split_comparison": { 
                "guess": list(worst_guess) if worst_guess else [],
                "splits": worst_splits
            }
        }
        
        payload = self._extract_dashboard_data(turn, best_guess, "processing", evaluation_payload)
        if self.observer_callback:
            self.observer_callback(payload)
            
        return best_guess