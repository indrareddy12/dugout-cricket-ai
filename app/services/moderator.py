import re
import json
from google import genai
from google.genai import types
from app.config import GEMINI_API_KEY

class ModerationResult:
    def __init__(self, is_toxic: bool, reason: str = ""):
        self.is_toxic = is_toxic
        self.reason = reason

# Tier 1 Regex: Fast local block for common profanities & spam
BLOCKED_KEYWORDS = [
    r"\bbastard\b", r"\bbitch\b", r"\basshole\b", r"\bfuck\b", r"\bshit\b", r"\bcrap\b",
    r"\bchutiya\b", r"\bsala\b", r"\bgandu\b", r"\bhrami\b", r"\bbkl\b", r"\bmc\b", r"\bbc\b",
    r"\bspam\b", r"\bfree money\b", r"\bclick here\b", r"\bbuy now\b", r"\bwin cash\b"
]

def check_tier1_regex(text: str) -> ModerationResult:
    cleaned = text.lower().strip()
    for pattern in BLOCKED_KEYWORDS:
        if re.search(pattern, cleaned):
            return ModerationResult(is_toxic=True, reason="Flagged by local word-filter (Tier 1)")
    return ModerationResult(is_toxic=False)

def check_tier2_ai(text: str) -> ModerationResult:
    # If API key is not set, run in fallback/mock mode
    if not GEMINI_API_KEY:
        cleaned = text.lower()
        # Mock detection for demonstration purposes
        mock_triggers = ["hate", "kill", "die", "stupid", "idiot", "loser", "cheat", "scam"]
        for trigger in mock_triggers:
            if trigger in cleaned:
                return ModerationResult(is_toxic=True, reason=f"Flagged by Mock AI: contains '{trigger}' (Demo Mode)")
        return ModerationResult(is_toxic=False)
    
    try:
        # Initialize GenAI client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        system_instruction = (
            "You are a strict auto-moderator for a sports social network ('DugOut'). "
            "Analyze the message for toxicity, abuse, hate speech, racism, severe cyberbullying, or commercial spam. "
            "We allow friendly rivalry and banter between teams (e.g., 'CSK will crush MI', 'Rohit is overrated today'), "
            "but we strictly block abuse, personal threats, racism, and profanity. "
            "The message can be in English, Hindi, Hinglish (Hindi written in Roman characters), or other regional Indian slang. "
            "Respond ONLY with a JSON object containing: "
            "'is_toxic' (boolean) and 'reason' (string explaining why it is toxic, in 5 words or less)."
        )
        
        prompt = f"Analyze this message: \"{text}\""
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        
        # Parse JSON response
        data = json.loads(response.text.strip())
        is_toxic = data.get("is_toxic", False)
        reason = data.get("reason", "Flagged by AI safety check (Tier 2)")
        
        return ModerationResult(is_toxic=is_toxic, reason=reason if is_toxic else "")
    except Exception as e:
        print(f"Moderation AI Error: {e}")
        # Fallback to safe pass if AI errors out, or flag if local fallback triggers
        return ModerationResult(is_toxic=False)

def moderate_message(text: str) -> ModerationResult:
    # 1. Run local keyword check (Fast, 0ms)
    t1_res = check_tier1_regex(text)
    if t1_res.is_toxic:
        return t1_res
    
    # 2. Run LLM check (Multilingual, checks context & slang)
    t2_res = check_tier2_ai(text)
    return t2_res
