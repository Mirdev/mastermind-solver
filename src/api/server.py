import uuid
import json
import datetime
from pathlib import Path
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse
import requests

from src.game_engine import MastermindEngine
from src.lut_engine import MastermindLUTEngine
from src.solvers.entropy_solver import EntropySolver
from src.solvers.heuristic_solver import HeuristicSolver
from src.solvers.fast_entropy_solver import FastEntropySolver
from src.solvers.minimax_solver import MinimaxSolver

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
    elif config.solver_type == "minimax":
        solver = MinimaxSolver(engine)
    elif config.solver_type == "fast_entropy":
        solver = FastEntropySolver(engine)
    else:
        # 조용히 기본값으로 넘어가는 대신 에러를 반환하여 안전성 확보
        raise HTTPException(status_code=400, detail=f"Unsupported solver_type: {config.solver_type}")

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"sim_log_{timestamp}_{session_id}.jsonl"
    log_path = log_dir / log_filename
    solver.log_file = str(log_path)
    
    with open(log_path, "a", encoding="utf-8") as f:
        pass
        
    guess = solver.get_best_guess(1)
    
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
            
    secret = tuple(int(d) for d in config.my_secret) if config.my_secret else engine.generate_secret()

    session_data = {
        "engine": engine,
        "solver": solver,
        "config": config,
        "turn": 1,
        "current_guess": guess,
        "secret": secret,
        "history": []
    }
    
    SESSIONS[session_id] = session_data
    
    return {
        "session_id": session_id,
        "log_file": log_filename,
        "message": "Engine Initialized.",
        "turn": 1,
        "state": "standby",
        "ai_guess": guess,
        "secret": "".join(map(str, secret)) # [핵심 추가] 생성된 비밀 숫자를 프론트엔드로 전달
    }

# [신규 추가] 자가 대결 턴을 자동으로 넘기는 오토 파일럿 라우터
@app.post("/game/{session_id}/auto_step")
def auto_step_phase(session_id: str):
    session = get_session(session_id)
    solver = session["solver"]
    engine = session["engine"]
    turn = session["turn"]
    guess = session.get("current_guess")
    secret = session["secret"]
    
    if not guess:
        raise HTTPException(status_code=400, detail="AI guess missing.")
        
    s, b = engine.get_feedback(guess, secret)
    solver.update_candidates(guess, (s, b))
    
    if s == session["config"].digits:
        final_log = {
            "turn": turn, "best_guess": guess, "status": "win",
            "solver_name": solver.__class__.__name__,
            "dashboard_2_trend": {"remaining_count": 1}
        }
        with open(solver.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(final_log) + "\n")
        return {"state": "game_over", "result": "win", "turn": turn}
        
    if not solver.candidates:
        return {"state": "error", "message": "모순 발생! 후보군이 없습니다."}
        
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
        "state": "auto_turn",
        "turn": next_turn,
        "guess": next_guess,
        "feedback": {"strike": s, "ball": b}
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
@app.get("/logs/")
def list_logs():
    log_dir = Path("logs")
    if not log_dir.exists():
        return {"files": []}
    files = sorted(log_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"files": [f.name for f in files]}

@app.get("/api/kasi/")
def get_kasi_proxy(yyyy: int):
    """
    브라우저 대신 서버가 천문연 API를 호출하여 CORS를 우회합니다.
    """
    url = f"https://astro.kasi.re.kr/life/lunc?yyyy={yyyy}&mm=01&dd=01"
    try:
        response = requests.get(url, timeout=5)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy Error: {str(e)}")