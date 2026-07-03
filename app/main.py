import os
import uuid
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, List, Set

from app.models import BallEvent, ChatMessage, MomentThread, DRSState, VoteRequest
from app.services.moderator import moderate_message
from app.services.thread_gen import should_generate_thread, generate_thread_ai
from app.services.chatbot import ask_duggy_ai
from app.services.state_manager import state_manager
from app.config import USE_REDIS

app = FastAPI(title="DugOut Live Platform", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    # If Redis is enabled, connect to the server and start listener
    if USE_REDIS:
        await state_manager.initialize()

# Mount static directory
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

from app.routers.ai_chat import router as ai_chat_router
app.include_router(ai_chat_router)

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

# 1. Chat & WebSocket Gateway
@app.websocket("/ws/chat/{stand_id}")
async def websocket_chat_endpoint(websocket: WebSocket, stand_id: str):
    if stand_id not in ["csk", "mi", "neutral"]:
        await websocket.close(code=4000, reason="Invalid Stand ID")
        return
        
    await websocket.accept()
    await state_manager.register_socket(stand_id, websocket)
    
    # Send current state to newly joined user
    try:
        scorecard = await state_manager.get_scorecard()
        threads = await state_manager.get_threads()
        drs_state = await state_manager.get_drs()
        moderator_logs = await state_manager.get_moderator_logs()
        fan_counts = await state_manager.get_fan_counts()
        
        fantasy_teams = await state_manager.get_fantasy_teams()
        debate_state = await state_manager.get_active_debate()
        await websocket.send_text(json.dumps({
            "type": "init",
            "scorecard": scorecard,
            "threads": [t.model_dump() for t in threads],
            "drs": drs_state.model_dump(),
            "moderator_logs": moderator_logs,
            "fan_counts": fan_counts,
            "fantasy_teams": fantasy_teams,
            "debate": debate_state
        }))
        
        while True:
            data = await websocket.receive_text()
            message_payload = json.loads(data)
            
            if message_payload.get("type") == "submit_debate_argument":
                argument = message_payload.get("argument", "").strip()
                team_val = message_payload.get("team", "neutral")
                if team_val in ["csk", "mi"]:
                    await state_manager.submit_debate_statement(team_val, argument)
                continue

            if message_payload.get("type") == "reset_debate":
                await state_manager.reset_debate()
                continue

            if message_payload.get("type") == "share_fantasy_card":
                card_type = message_payload.get("card_type", "brag")
                team_name = message_payload.get("team_name", "Indra's Dream Team")
                captain = message_payload.get("captain", "Ruturaj Gaikwad")
                total_points = message_payload.get("total_points", 102)
                sender = message_payload.get("sender", "Anonymous")
                team = message_payload.get("team", "neutral")
                
                if card_type == "brag":
                    msg_text = f"🚀 [Fantasy Brag] {sender}'s Captain {captain} is firing! {team_name} total is now {total_points} pts! 🏆"
                else:
                    msg_text = f"😭 [Fantasy Cry] Pressure! {sender}'s Captain {captain} is bleeding points. {team_name} is down to {total_points} pts! 📉"
                
                message_id = str(uuid.uuid4())
                timestamp = datetime.now().strftime("%I:%M %p")
                
                msg_obj = ChatMessage(
                    id=message_id,
                    stand_id=stand_id,
                    sender="Fantasy Bot",
                    message=msg_text,
                    timestamp=timestamp,
                    team=team,
                    is_blocked=False
                )
                await state_manager.broadcast_to_stand(stand_id, {
                    "type": "message",
                    "message": msg_obj.model_dump()
                })
                continue
            
            sender = message_payload.get("sender", "Anonymous")
            raw_text = message_payload.get("message", "").strip()
            team = message_payload.get("team", "neutral")
            
            if not raw_text:
                continue
                
            # --- Chat Moderation Layer (System E) ---
            mod_result = moderate_message(raw_text)
            
            message_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%I:%M %p")
            
            msg_obj = ChatMessage(
                id=message_id,
                stand_id=stand_id,
                sender=sender,
                message=raw_text if not mod_result.is_toxic else f"🚫 [Message blocked for toxicity: {mod_result.reason}]",
                timestamp=timestamp,
                team=team,
                is_blocked=mod_result.is_toxic,
                block_reason=mod_result.reason
            )
            
            # Save toxic messages to admin moderator logs
            if mod_result.is_toxic:
                log_entry = {
                    "id": message_id,
                    "sender": sender,
                    "original_message": raw_text,
                    "reason": mod_result.reason,
                    "timestamp": timestamp,
                    "stand_id": stand_id
                }
                await state_manager.add_moderator_log(log_entry)
                # Broadcast the updated logs to all users for demo purposes
                await state_manager.broadcast_to_all({
                    "type": "moderator_log",
                    "log": log_entry
                })
            
            # Broadcast message to stand channel
            await state_manager.broadcast_to_stand(stand_id, {
                "type": "message",
                "message": msg_obj.model_dump()
            })
            
    except WebSocketDisconnect:
        await state_manager.unregister_socket(stand_id, websocket)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        await state_manager.unregister_socket(stand_id, websocket)

# 2. AI Thread Generator (System F) + Score Update
@app.post("/api/match/ball")
async def register_ball_event(event: BallEvent):
    scorecard = await state_manager.get_scorecard()
    
    # 1. Update live scorecard
    scorecard["overs"] = event.over
    
    # Calculate scores based on event
    if event.event_type == "wicket":
        scorecard["wickets"] = min(10, scorecard["wickets"] + 1)
        scorecard["recent_balls"].append("W")
        scorecard["recent_balls"] = scorecard["recent_balls"][-6:]
        # shift excitement levels
        scorecard["excitement_csk"] = max(10, scorecard["excitement_csk"] - 15)
        scorecard["excitement_mi"] = min(90, scorecard["excitement_mi"] + 15)
    else:
        scorecard["runs"] += event.runs
        if event.runs == 4:
            scorecard["recent_balls"].append("4")
        elif event.runs == 6:
            scorecard["recent_balls"].append("6")
            scorecard["excitement_csk"] = min(90, scorecard["excitement_csk"] + 10)
            scorecard["excitement_mi"] = max(10, scorecard["excitement_mi"] - 10)
        elif event.runs == 0:
            scorecard["recent_balls"].append("0")
        else:
            scorecard["recent_balls"].append(str(event.runs))
        scorecard["recent_balls"] = scorecard["recent_balls"][-6:]

    # Update Striker/Bowler labels
    scorecard["batsman_striker"] = f"{event.batsman}: {34 + scorecard['runs'] % 30}*({18 + int(float(event.over)*6) % 20})"
    scorecard["bowler_active"] = f"{event.bowler}: 3.{int(float(event.over)*10)%6}-0-{scorecard['runs'] % 25 + 15}-{scorecard['wickets']}"

    # Save to state manager
    updated_scorecard = await state_manager.update_scorecard(scorecard)

    # Update fantasy points
    await state_manager.update_fantasy_points(event.batsman, event.bowler, event.runs, event.event_type)

    # Broadcast updated scorecard
    await state_manager.broadcast_to_all({
        "type": "scorecard",
        "scorecard": updated_scorecard
    })
    
    # 2. Check if event triggers a new Moment Thread (System F)
    if should_generate_thread(event):
        new_thread = generate_thread_ai(event)
        await state_manager.add_thread(new_thread)
        
        # Broadcast thread creation
        await state_manager.broadcast_to_all({
            "type": "new_thread",
            "thread": new_thread.model_dump()
        })
        
    # 3. Handle DRS Trigger Special View
    drs_active = False
    if event.event_type == "drs":
        drs_state = await state_manager.start_drs(event.batsman, event.bowler, event.over)
        drs_active = drs_state.is_active
        
        # Broadcast DRS Trigger
        await state_manager.broadcast_to_all({
            "type": "drs_trigger",
            "drs": drs_state.model_dump()
        })
        
        # Start a background task for DRS countdown
        asyncio.create_task(run_drs_countdown())
        
    return {"status": "success", "scorecard": updated_scorecard, "drs_active": drs_active}

# DRS Countdown Worker
async def run_drs_countdown():
    drs_state = await state_manager.get_drs()
    while drs_state.is_active and drs_state.time_remaining > 0:
        await asyncio.sleep(1)
        drs_state = await state_manager.tick_drs()
        
        # Broadcast countdown tick
        await state_manager.broadcast_to_all({
            "type": "drs_tick",
            "time_remaining": drs_state.time_remaining
        })
        
    if drs_state.is_active:
        # Determine verdict based on votes or default if empty
        total_votes = drs_state.votes_out + drs_state.votes_not_out
        if total_votes > 0:
            crowd_verdict = "OUT" if drs_state.votes_out > drs_state.votes_not_out else "NOT_OUT"
        else:
            crowd_verdict = "OUT"
            
        # The official verdict will mimic a 3rd umpire random call for drama
        official_verdict = "OUT" if (drs_state.votes_out % 2 == 0) else "NOT_OUT"
        
        drs_state = await state_manager.resolve_drs(official_verdict)
        
        # Create thread for DRS result
        verdict_str = "OUT 🔴" if official_verdict == "OUT" else "NOT OUT 🟢"
        crowd_str = "OUT 🔴" if crowd_verdict == "OUT" else "NOT OUT 🟢"
        
        new_thread = MomentThread(
            id=str(uuid.uuid4()),
            title=f"📺 DRS Verdict: {verdict_str}!",
            description=(
                f"Umpire review resolved: Rohit is ruled {verdict_str}. "
                f"Crowd verdict was {crowd_str} ({int(drs_state.votes_out / max(1, total_votes) * 100)}% OUT). "
                f"Discuss the decision!"
            ),
            over=drs_state.over,
            event_type="drs_result",
            timestamp=datetime.now().strftime("%I:%M %p"),
            replies=[]
        )
        
        await state_manager.add_thread(new_thread)
        
        # Broadcast DRS complete
        await state_manager.broadcast_to_all({
            "type": "drs_resolved",
            "drs": drs_state.model_dump(),
            "thread": new_thread.model_dump()
        })

# 3. DRS Voting API
@app.post("/api/drs/vote")
async def cast_drs_vote(vote_req: VoteRequest):
    drs_state = await state_manager.get_drs()
    if not drs_state.is_active:
        raise HTTPException(status_code=400, detail="No active DRS review to vote on.")
        
    if vote_req.vote not in ["OUT", "NOT_OUT"]:
        raise HTTPException(status_code=400, detail="Invalid vote. Must be 'OUT' or 'NOT_OUT'")
        
    updated_drs = await state_manager.cast_drs_vote(vote_req.vote)
        
    # Broadcast updated vote counts
    await state_manager.broadcast_to_all({
        "type": "drs_vote_update",
        "votes_out": updated_drs.votes_out,
        "votes_not_out": updated_drs.votes_not_out
    })
    
    return {"status": "success"}
