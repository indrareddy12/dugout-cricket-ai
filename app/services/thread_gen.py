import json
import uuid
from datetime import datetime
from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY
from app.models import BallEvent, MomentThread

def should_generate_thread(event: BallEvent) -> bool:
    """
    Decides if a ball event is significant enough to warrant its own discussion thread.
    Wickets, boundaries, DRS reviews, or large scoring events trigger threads.
    """
    if event.event_type in ["wicket", "drs"]:
        return True
    if event.event_type == "boundary" and event.runs >= 4:
        return True
    if "six" in event.description.lower() or "wicket" in event.description.lower():
        return True
    return False

def generate_thread_ai(event: BallEvent) -> MomentThread:
    thread_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%I:%M %p")
    
    # If no API Key is provided, use mock generation
    if not GEMINI_API_KEY:
        return generate_thread_mock(event, thread_id, timestamp)
        
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        system_instruction = (
            "You are a copywriter for a sports social network ('DugOut'). "
            "Given a live match ball event, draft a highly engaging thread title and description "
            "to pin to the match timeline and generate fan discussion. "
            "Use emojis, keep the title punchy and under 8 words, and write a description under 2 sentences. "
            "Highlight the dramatic context and ask a question to prompt fan responses. "
            "Respond strictly in JSON format with: "
            "'title' (string) and 'description' (string)."
        )
        
        prompt = (
            f"Event details:\n"
            f"- Over: {event.over}\n"
            f"- Batsman: {event.batsman}\n"
            f"- Bowler: {event.bowler}\n"
            f"- Runs: {event.runs}\n"
            f"- Event Type: {event.event_type}\n"
            f"- Play Description: {event.description}"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        data = json.loads(response.text.strip())
        title = data.get("title", f"Over {event.over}: {event.batsman} vs {event.bowler}")
        description = data.get("description", event.description)
        
        return MomentThread(
            id=thread_id,
            title=title,
            description=description,
            over=event.over,
            event_type=event.event_type,
            timestamp=timestamp,
            replies=[]
        )
    except Exception as e:
        print(f"Thread Generator AI Error: {e}")
        return generate_thread_mock(event, thread_id, timestamp)

def generate_thread_mock(event: BallEvent, thread_id: str, timestamp: str) -> MomentThread:
    """Fallback generator when API keys are not available."""
    if event.event_type == "wicket":
        title = f"💥 WICKET! {event.batsman} Out!"
        description = f"Over {event.over}: {event.bowler} clean bowls {event.batsman}! Huge blow for the batting side. Fans, is this the game-changer?"
    elif event.event_type == "drs":
        title = f"🔍 DRS APPEAL: LBW Check!"
        description = f"Over {event.over}: Big shout for LBW on {event.batsman} by {event.bowler}. The umpire says not out, but they are reviewing! OUT or NOT OUT?"
    elif event.event_type == "boundary":
        emoji = "🚀 SIX!" if event.runs == 6 else "⚡ FOUR!"
        title = f"{emoji} {event.batsman} strikes!"
        description = f"Over {event.over}: {event.batsman} hammers {event.bowler} for {event.runs} runs! What a clean shot. Can the bowler bounce back?"
    else:
        title = f"🏏 Big Moment in Over {event.over}"
        description = f"{event.batsman} faces {event.bowler}. Runs scored: {event.runs}. {event.description}"
        
    return MomentThread(
        id=thread_id,
        title=title,
        description=description,
        over=event.over,
        event_type=event.event_type,
        timestamp=timestamp,
        replies=[]
    )
