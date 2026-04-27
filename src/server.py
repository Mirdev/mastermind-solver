# src/api/server.py
import sys
import os
import uuid
from typing import Dict, Tuple, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 프로젝트 루트 경로 주입
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(src_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lut_engine import MastermindLUTEngine
from src.game_engine import MastermindEngine
from src.solvers.fast_entropy_solver import FastEntropySolver

app = FastAPI(
    title="Mastermind AI Solver API",
    description="고성능 LUT 및 NumPy 벡터라이제이션이 적용된 숫자야구 AI API입니다.",
    version="1.0.0"
)

# 인메모리 세션 저장소 (실제 프로덕션 환경에서는 Redis 등 사용 권장)
active_sessions: Dict[str, dict] = {}

# --- [Data Models (Pydantic)] ---
class GameConfig(BaseModel):
    digits: int = 4
    allow_duplicates: bool = False
    allow_leading_zero: bool = False
    use_lut: bool = True

class FeedbackInput(BaseModel):
    strike: int
    ball: int

class TurnResponse(BaseModel):
    session_id: str
    turn: int
    guess: Tuple[int, ...]
    remaining_candidates: int
    message: str = "success"

# --- [API Endpoints] ---
@app.post("/game/start", response_model=TurnResponse)
def start_game(config: GameConfig):
    """새로운 게임 세션을 초기화하고 AI의 첫 번째 추측을 반환합니다."""
    
    # 1. 엔진 세팅
    if config.use_lut and config.digits == 4:
        engine = MastermindLUTEngine(
            digits=config.digits,
            allow_duplicates=config.allow_duplicates,
            allow_leading_zero=config.allow_leading_zero
        )
    else:
        engine = MastermindEngine(
            digits=config.digits,
            allow_duplicates=config.allow_duplicates,
            allow_leading_zero=config.allow_leading_zero
        )

    # 2. 솔버 세팅 (초고속 엔트로피 솔버 고정)
    solver = FastEntropySolver(engine)
    
    # 3. 1턴 연산
    turn = 1
    best_guess = solver.get_best_guess(turn)
    
    # 4. 세션 발급 및 상태 저장
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        "solver": solver,
        "turn": turn,
        "last_guess": best_guess,
        "digits": config.digits
    }
    
    return TurnResponse(
        session_id=session_id,
        turn=turn,
        guess=best_guess,
        remaining_candidates=len(solver.candidates),
        message="Game started successfully."
    )

@app.post("/game/{session_id}/feedback", response_model=TurnResponse)
def submit_feedback(session_id: str, feedback: FeedbackInput):
    """이전 추측에 대한 사용자의 피드백을 받아, 다음 최적의 추측을 반환합니다."""
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="유효하지 않거나 만료된 세션입니다.")
        
    session = active_sessions[session_id]
    solver = session["solver"]
    
    # 1. 정답 처리 (세션 파기)
    if feedback.strike == session["digits"] and feedback.ball == 0:
        turn = session["turn"]
        del active_sessions[session_id]
        return TurnResponse(
            session_id=session_id,
            turn=turn,
            guess=session["last_guess"],
            remaining_candidates=1,
            message=f"Game Over. {turn}턴 만에 정답을 맞혔습니다!"
        )
        
    # 2. 피드백 기반 후보군 축소
    solver.update_candidates(session["last_guess"], (feedback.strike, feedback.ball))
    
    if not solver.candidates:
        del active_sessions[session_id]
        raise HTTPException(status_code=400, detail="모순된 피드백입니다. 가능한 정답 후보군이 소멸했습니다.")
        
    # 3. 다음 턴 연산
    session["turn"] += 1
    next_guess = solver.get_best_guess(session["turn"])
    session["last_guess"] = next_guess
    
    return TurnResponse(
        session_id=session_id,
        turn=session["turn"],
        guess=next_guess,
        remaining_candidates=len(solver.candidates)
    )

@app.delete("/game/{session_id}")
def end_game(session_id: str):
    """진행 중인 게임 세션을 강제로 종료합니다."""
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": "Session deleted successfully."}
    raise HTTPException(status_code=404, detail="Session not found.")