# In 100,000 simulations (no repetitive candidates), the entropy version required on average approximately 0.01 fewer turns than the naive Bayesian (light) version.
# In smaller simulations (1,000–10,000 trials), the maximum observed difference was 2 turns, with an average gap of about 0.6 turns.
# Adding heuristics(like fixed approximation for 3 turns) makes entropy-based solver faster
# 0.x secs difference between two versions in this version(originally, the time difference was much larger)(in no repetitive candidates)
# Therefore, the faster (or light) version is effectively a legacy version, but it has been deliberately retained for its probabilistic approach, which allows it to reach results more quickly (naive Bayesian).
# it takes about half the time of the entropy-based version, but requires one turn more on average.(in repetitive candidates)
# In the end, the performance of the two versions is almost similar.

"""
Overall, while the entropy-based solver can be considered the more principled and theoretically optimal approach, 
large-scale validation (100,000 trials) shows that its advantage over the naive Bayesian (light) solver is practically negligible (≈0.01 turns on average).
In contrast, the Bayesian solver consistently runs faster, often by a factor of two, and thus remains a valid and efficient alternative.
In short, the entropy version represents methodological refinement, whereas the Bayesian version represents pragmatic efficiency; both remain competitive depending on whether accuracy or speed is prioritized.
"""

import random
import time
import math
from collections import Counter
from itertools import permutations

def feedback(guess, answer):
    strikes = sum(g == a for g, a in zip(guess, answer))
    balls = sum(min(guess.count(d), answer.count(d)) for d in set(guess)) - strikes
    return strikes, balls

def update_distribution(candidates):
    position_counts = [Counter() for _ in range(4)]
    for c in candidates:
        for i, digit in enumerate(c):
            position_counts[i][digit] += 1
    return position_counts

def score_by_position_counts(candidate, position_counts):
    score = 0
    for i, d in enumerate(candidate):
        score += position_counts[i][d]
    return score

def entropy_of_guess(guess, candidates):
    dist = Counter()
    for theta in candidates:
        sb = feedback(guess, theta)
        dist[sb] += 1
        
    total = len(candidates)
    entropy = 0
    
    for count in dist.values():
        p = count / total
        entropy -= p * math.log2(p)
        
    worst_case = max(dist.values())
    
    return entropy, worst_case

def choose_guess(candidates):
    best_guess, best_entropy, best_worst_case = None, -1, 10001
    
    for guess in candidates:
        entropy, worst_case = entropy_of_guess(guess, candidates)
        if entropy > best_entropy or (entropy == best_entropy and worst_case < best_worst_case):
            best_entropy, best_worst_case, best_guess = entropy, worst_case, guess
    return best_guess

M = input("Debug mode?(y/n)")
D = input("Duplicates(y) or No duplicates(n)?")
L = 'y'
if D == 'n':
    L = input("Permit Leading zero?(y/n)")
    MM = input("Faster or more accurate?(f/a)")

digits = '0123456789'

if D == 'y':
    start_digits = digits
    candidates = [f'{c:04d}' for c in range(10000)]
elif L == 'y':
    start_digits = digits
    candidates = [''.join(p) for p in permutations(digits, 4)]
else:
    start_digits = digits[1:]+digits[0]
    candidates = [''.join(p) for p in permutations(digits, 4) if p[0] != '0']

if M == 'y':
    real_answer = random.choice(candidates)
    print("Answer(for debug):", real_answer)
    
turn = 1
while candidates:
    start = time.time()
    if D == 'n' and MM == 'f':
        position_counts = update_distribution(candidates)
        guess = max(candidates, key=lambda c: score_by_position_counts(c, position_counts))
    else:
        if turn == 1:
            guess = start_digits[:4]
        elif turn == 2:
            guess = start_digits[4:8]
        elif turn == 3:
            guess = start_digits[8:]+''.join(random.sample(start_digits[:2]+start_digits[4:6],2))
        else:
            guess = choose_guess(candidates)

    if M == 'y':
        observed_feedback = feedback(guess, real_answer)
        print(f"Turn {turn}: guess={guess}, candidates={len(candidates)}, feedback={observed_feedback}, execution_time={time.time()-start:.5f}s")
    else:
        print(f"Turn {turn}: guess={guess}, candidates={len(candidates)}, execution_time={time.time()-start:.5f}s")
        user_input = input("Enter the number of strikes and balls without spaces (e.g., 11): ")
        observed_feedback = tuple(int(c) for c in user_input)

    if observed_feedback == (4,0):
        print(f"Correct answer ({guess}) found!")
        break
    elif turn > 8:
        print("Game over!")
        break

    candidates = [c for c in candidates if feedback(guess, c) == observed_feedback]
    turn += 1
if not candidates:
    print("Cannot find the number!")