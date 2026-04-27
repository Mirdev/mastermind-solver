import uuid
import json
import datetime
from pathlib import Path
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse

from src.game_engine import MastermindEngine
from src.lut_engine import MastermindLUTEngine
from src.solvers.entropy_solver import EntropySolver
from src.solvers.heuristic_solver import HeuristicSolver
from src.solvers.fast_entropy_solver import FastEntropySolver

app = FastAPI(title="Mastermind AI Tactical API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GameConfig(BaseModel):
    mode: str = "interactive"
    digits: int = 4
    allow_dup: bool = False
    allow_zero: bool = False
    use_lut: bool = True
    solver_type: str = "fast_entropy"
    is_atk_first: bool = True
    my_secret: Optional[str] = None

class FeedbackInput(BaseModel):
    strike: int
    ball: int

class OpponentGuessInput(BaseModel):
    guess: str

SESSIONS: Dict[str, dict] = {}

def get_session(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return SESSIONS[session_id]

@app.post("/game/start")
def start_game(config: GameConfig):
    session_id = str(uuid.uuid4())
    
    if config.use_lut and config.digits == 4:
        engine = MastermindLUTEngine(config.digits, config.allow_dup, config.allow_zero)
    else:
        engine = MastermindEngine(config.digits, config.allow_dup, config.allow_zero)
        
    if config.solver_type == "heuristic":
        solver = HeuristicSolver(engine)
    else:
        solver = FastEntropySolver(engine)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"sim_log_{timestamp}_{session_id}.jsonl"
    log_path = log_dir / log_filename
    solver.log_file = str(log_path)
    
    with open(log_path, "a", encoding="utf-8") as f:
        pass
        
    # 무조건 1턴 타겟 연산 (시작 즉시 대시보드 렌더링 보장)
    guess = solver.get_best_guess(1)
    
    # 방어막: 만약 get_best_guess가 로그를 쓰지 않았다면 강제 뼈대 기록
    if not log_path.exists() or log_path.stat().st_size == 0:
        init_log = {
            "turn": 1,
            "best_guess": guess,
            "status": "processing",
            "solver_name": solver.__class__.__name__,
            "dashboard_2_trend": {"remaining_count": len(solver.candidates)}
        }
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(init_log) + "\n")
            
    session_data = {
        "engine": engine,
        "solver": solver,
        "config": config,
        "turn": 1,
        "current_guess": guess,
        "history": []
    }
    
    SESSIONS[session_id] = session_data
    
    return {
        "session_id": session_id,
        "log_file": log_filename,
        "message": "Engine Initialized.",
        "turn": 1,
        "state": "standby",
        "ai_guess": guess
    }

@app.post("/game/{session_id}/attack")
def ai_attack_phase(session_id: str, feedback: FeedbackInput):
    session = get_session(session_id)
    solver = session["solver"]
    turn = session["turn"]
    guess = session.get("current_guess")
    
    if not guess:
        raise HTTPException(status_code=400, detail="AI has not made a guess yet.")
        
    solver.update_candidates(guess, (feedback.strike, feedback.ball))
    
    # [내 공격 성공] 내가 4S를 맞췄을 때
    if feedback.strike == session["config"].digits:
        final_log = {
            "turn": turn, "best_guess": guess, "status": "win",
            "solver_name": solver.__class__.__name__,
            "dashboard_2_trend": {"remaining_count": 1}
        }
        with open(solver.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(final_log) + "\n")
        return {"state": "game_over", "result": "win", "turn": turn}
        
    if not solver.candidates:
        return {"state": "error", "message": "피드백 모순! 남은 후보군이 0개입니다. Strike/Ball 입력을 확인하세요."}
        
    if turn >= 9:
        final_log = {
            "turn": turn, "best_guess": guess, "status": "lose",
            "solver_name": solver.__class__.__name__,
            "dashboard_2_trend": {"remaining_count": len(solver.candidates)}
        }
        with open(solver.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(final_log) + "\n")
        return {"state": "game_over", "result": "lose", "turn": turn}

    session["turn"] += 1
    next_turn = session["turn"]
    next_guess = solver.get_best_guess(next_turn)
    session["current_guess"] = next_guess

    return {
        "state": "ai_attack_turn",
        "turn": next_turn,
        "ai_guess": next_guess,
        "remaining_candidates": len(solver.candidates)
    }

@app.post("/game/{session_id}/defense")
def user_defense_phase(session_id: str, opp: OpponentGuessInput):
    session = get_session(session_id)
    engine = session["engine"]
    config = session["config"]
    
    if not config.my_secret:
        raise HTTPException(status_code=400, detail="No secret set.")
        
    opp_guess = tuple(int(d) for d in opp.guess)
    my_secret = tuple(int(d) for d in config.my_secret)
    s, b = engine.get_feedback(opp_guess, my_secret)
    
    # [내 방어 실패] 상대방이 내 숫자를 맞췄을 때
    if s == config.digits:
        final_log = {
            "turn": session["turn"], "best_guess": opp_guess, "status": "lose",
            "solver_name": session["solver"].__class__.__name__,
            "dashboard_2_trend": {"remaining_count": 0}
        }
        with open(session["solver"].log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(final_log) + "\n")
            
    return {
        "state": "defense_turn",
        "opponent_guess": opp.guess,
        "feedback": {"strike": s, "ball": b}
    }

@app.get("/logs/{file_name}")
def get_session_log(file_name: str):
    file_path = Path("logs") / file_name
    if not file_path.exists():
        return {"status": "waiting"}
    return FileResponse(str(file_path), media_type="text/plain")

@app.get("/api/logs")
def list_logs():
    log_dir = Path("logs")
    if not log_dir.exists():
        return {"files": []}
    files = sorted(log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"files": [f.name for f in files]}