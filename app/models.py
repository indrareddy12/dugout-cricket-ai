from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class BallEvent(BaseModel):
    over: str = Field(..., description="The over number (e.g., '14.2')")
    batsman: str = Field(..., description="Batsman name")
    bowler: str = Field(..., description="Bowler name")
    runs: int = Field(0, description="Runs scored on this ball")
    event_type: str = Field("normal", description="Type of event: 'boundary', 'wicket', 'drs', 'dot', 'normal'")
    description: str = Field("", description="A description of the action")

class ChatMessage(BaseModel):
    id: str
    stand_id: str = Field(..., description="csk, mi, or neutral")
    sender: str
    message: str
    timestamp: str
    team: str = Field(..., description="csk, mi, or neutral")
    is_blocked: bool = False
    block_reason: str = ""

class MomentThread(BaseModel):
    id: str
    title: str
    description: str
    over: str
    event_type: str
    timestamp: str
    replies: List[ChatMessage] = []

class DRSState(BaseModel):
    match_id: str = "live_match_1"
    batsman: str = ""
    bowler: str = ""
    over: str = ""
    is_active: bool = False
    votes_out: int = 0
    votes_not_out: int = 0
    time_remaining: int = 15
    official_verdict: Optional[str] = None  # "OUT" or "NOT_OUT"

class VoteRequest(BaseModel):
    vote: str = Field(..., description="OUT or NOT_OUT")
