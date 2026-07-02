import json
import httpx
import asyncio
from google import genai
from google.genai import types
from app.config import (
    GEMINI_API_KEY, USE_LOCAL_LLM, LOCAL_LLM_URL, LOCAL_LLM_MODEL,
    USE_HF_LLM, HF_API_KEY, HF_LLM_MODEL,
    USE_PINECONE, PINECONE_API_KEY, PINECONE_INDEX_NAME,
    USE_WEB_SEARCH, TAVILY_API_KEY
)
try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None

# Local Cricket Stats Database
STATS_DB = {
    "virat kohli": {
        "runs": "12,215",
        "average": "48.69",
        "strike_rate": "138.2",
        "half_centuries": "92",
        "centuries": "8",
        "vs_bumrah": "92 balls faced, 124 runs, 4 dismissals, SR 134.8"
    },
    "rohit sharma": {
        "runs": "11,532",
        "average": "31.59",
        "strike_rate": "140.8",
        "half_centuries": "78",
        "centuries": "5",
        "vs_starc": "64 balls faced, 88 runs, 2 dismissals, SR 137.5"
    },
    "ms dhoni": {
        "runs": "7,270",
        "average": "38.26",
        "strike_rate": "135.6",
        "death_strike_rate": "175.4",
        "trophies": "5 IPL Titles",
        "vs_spin": "Average 42.1, Strike Rate 118.9"
    },
    "jasprit bumrah": {
        "wickets": "264",
        "economy_rate": "6.42",
        "average": "18.52",
        "best_bowling": "5/10",
        "death_economy": "5.45"
    },
    "hardik pandya": {
        "runs": "4,420",
        "average": "28.35",
        "strike_rate": "139.5",
        "wickets": "152",
        "economy_rate": "8.12"
    }
}

def get_stats_context(query: str) -> str:
    """Simple parser to query local stats and avoid LLM hallucinations."""
    q = query.lower()
    found_stats = []
    
    for player, stats in STATS_DB.items():
        if player in q or (len(player.split()) > 1 and player.split()[1] in q):
            stat_str = f"**{player.title()} Career Stats:**\n"
            for k, v in stats.items():
                stat_str += f"- {k.replace('_', ' ').title()}: {v}\n"
            found_stats.append(stat_str)
            
    return "\n".join(found_stats) if found_stats else "No matching historical player stats found in database."

def is_off_topic(query: str) -> bool:
    """
    Checks if a user query is off-topic (not about cricket, stats, match, or players).
    Returns True if off-topic, False if on-topic.
    """
    q = query.lower().strip()
    
    # List of keywords that are explicitly off-topic
    off_topic_keywords = [
        "python", "code", "programming", "javascript", "html", "css", "java", "c++",
        "geography", "capital of", "president of", "prime minister of", "weather",
        "math", "calculus", "algebra", "history", "science", "biology", "physics", "chemistry",
        "movie", "song", "recipe", "cooking", "write a story", "write an essay", "developer", "software"
    ]
    if any(keyword in q for keyword in off_topic_keywords):
        return True
        
    # List of keywords that are cricket-related. If any is found, it's on-topic
    cricket_keywords = [
        "cricket", "match", "score", "run", "wicket", "over", "ball", "batsman", "bowler",
        "ipl", "t20", "odi", "test match", "csk", "mi", "rcb", "dhoni", "kohli", "rohit",
        "bumrah", "pandya", "starc", "gaikwad", "dube", "jadeja", "six", "four", "boundary",
        "strike rate", "average", "stats", "stadium", "pitch", "umpire", "drs", "century", "half-century",
        "trophy", "dismissal", "record", "spinner", "pacer", "target"
    ]
    if any(keyword in q for keyword in cricket_keywords):
        return False
        
    # Standard greeting and general questions to assistant are on-topic
    conversational = ["hi", "hello", "hey", "who are you", "what is your name", "help", "greet", "how are you", "what do you do", "yo"]
    if any(q.startswith(w) for w in conversational) or q in conversational:
        return False
        
    return False

def get_greeting_response(query: str) -> str:
    """Returns a cricket-themed response if the query is a simple greeting or identity question."""
    q = query.lower().strip()
    # Normalize ending punctuation
    q = q.rstrip("?.! ")
    
    greetings = ["hi", "hello", "hey", "yo", "greet"]
    if any(q == g or q.startswith(g + " ") for g in greetings):
        return "Hey there! 🏏 I'm Duggy, your cricket stats sidekick. Ask me about the live match, stats, or players! 📈"
    
    identity = ["who are you", "what is your name", "what do you do", "help"]
    if any(i in q for i in identity):
        return "I am Duggy, your cricket-obsessed AI Stats Companion! 🏏 Ask me about the live match, player stats, or matchups! 📈"
        
    return ""

def query_tavily_search(query_text: str) -> str:
    """Queries Tavily Search API for real-time web results (Sync)."""
    if not USE_WEB_SEARCH or not TAVILY_API_KEY:
        return ""
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query_text,
            "search_depth": "basic",
            "include_answer": False
        }
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                snippets = []
                for res in results[:3]:
                    title = res.get("title", "News")
                    content = res.get("content", "")
                    url_link = res.get("url", "")
                    snippets.append(f"- **{title}** ({url_link}): {content}")
                return "\n".join(snippets) if snippets else "No web results found."
            else:
                print(f"Tavily search API error (status {r.status_code}): {r.text}")
    except Exception as e:
        print(f"Tavily search exception: {e}")
    return ""

def get_huggingface_embeddings_sync(text: str) -> list:
    """Generates 384-dimensional text embeddings using HF API (Sync)."""
    if not HF_API_KEY:
        return []
    try:
        url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": [text]}
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                res = r.json()
                if isinstance(res, list) and len(res) > 0:
                    return res[0]
            print(f"HF embeddings error (status {r.status_code}): {r.text}")
    except Exception as e:
        print(f"HF embeddings exception: {e}")
    return []

def query_pinecone_vectors(query_text: str) -> str:
    """Queries Pinecone Vector DB for relevant social context (Sync)."""
    if not USE_PINECONE or not PINECONE_API_KEY or not Pinecone:
        return ""
    try:
        embedding = get_huggingface_embeddings_sync(query_text)
        if not embedding:
            return ""
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(PINECONE_INDEX_NAME)
        res = index.query(vector=embedding, top_k=3, include_metadata=True)
        matches = res.get("matches", [])
        snippets = []
        for match in matches:
            metadata = match.get("metadata", {})
            text = metadata.get("text", "")
            if text:
                snippets.append(f"- (Score: {match.get('score'):.2f}): {text}")
        return "\n".join(snippets) if snippets else "No vector match found."
    except Exception as e:
        print(f"Pinecone query exception: {e}")
    return ""

async def query_tavily_search_async(query_text: str) -> str:
    """Queries Tavily Search API asynchronously for real-time web results."""
    if not USE_WEB_SEARCH or not TAVILY_API_KEY:
        return ""
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query_text,
            "search_depth": "basic",
            "include_answer": False
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                snippets = []
                for res in results[:3]:
                    title = res.get("title", "News")
                    content = res.get("content", "")
                    url_link = res.get("url", "")
                    snippets.append(f"- **{title}** ({url_link}): {content}")
                return "\n".join(snippets) if snippets else "No web results found."
            else:
                print(f"Tavily search API error (status {r.status_code}): {r.text}")
    except Exception as e:
        print(f"Tavily search exception: {e}")
    return ""

async def get_huggingface_embeddings_async(text: str) -> list:
    """Generates 384-dimensional text embeddings using HF API asynchronously."""
    if not HF_API_KEY:
        return []
    try:
        url = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": [text]}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                res = r.json()
                if isinstance(res, list) and len(res) > 0:
                    return res[0]
            print(f"HF embeddings error (status {r.status_code}): {r.text}")
    except Exception as e:
        print(f"HF embeddings exception: {e}")
    return []

async def query_pinecone_vectors_async(query_text: str) -> str:
    """Queries Pinecone Vector DB for relevant social context (Async)."""
    if not USE_PINECONE or not PINECONE_API_KEY or not Pinecone:
        return ""
    try:
        embedding = await get_huggingface_embeddings_async(query_text)
        if not embedding:
            return ""
        def run_pinecone():
            pc = Pinecone(api_key=PINECONE_API_KEY)
            index = pc.Index(PINECONE_INDEX_NAME)
            return index.query(vector=embedding, top_k=3, include_metadata=True)
            
        res = await asyncio.to_thread(run_pinecone)
        matches = res.get("matches", [])
        snippets = []
        for match in matches:
            metadata = match.get("metadata", {})
            text = metadata.get("text", "")
            if text:
                snippets.append(f"- (Score: {match.get('score'):.2f}): {text}")
        return "\n".join(snippets) if snippets else "No vector match found."
    except Exception as e:
        print(f"Pinecone query exception: {e}")
    return ""

def build_prompt_context(query: str, stats_context: str, vector_context: str, web_context: str, match_score: dict) -> str:
    # Determine if live scorecard context is relevant to the query
    q = query.lower()
    include_live_context = True
    
    # If the user specifically mentions other major teams, players, or tournaments,
    # we exclude the live simulator match context (CSK vs MI) to avoid anchoring bias.
    other_topics = [
        "world cup", "wc", "india", "ireland", "pakistan", "australia", "england", 
        "sri lanka", "south africa", "west indies", "nz", "new zealand", "bangladesh", 
        "afghanistan", "rcb", "srh", "kkr", "dc", "pbks", "lsg", "gt", "rr"
    ]
    if any(topic in q for topic in other_topics):
        include_live_context = False
        
    prompt = ""
    if include_live_context:
        prompt += (
            f"Live Match Context:\n"
            f"- Match: {match_score.get('batting_team')} vs {match_score.get('bowling_team')}\n"
            f"- Current Score: {match_score.get('runs')}/{match_score.get('wickets')} in {match_score.get('overs')} overs\n"
            f"- Target: {match_score.get('target', 'N/A')}\n"
            f"- Current Striker: {match_score.get('batsman_striker', 'Unknown')}\n"
            f"- Current Bowler: {match_score.get('bowler_active', 'Unknown')}\n"
            f"- Recent Balls: {', '.join(match_score.get('recent_balls', []))}\n\n"
        )
    
    if stats_context and stats_context != "No matching historical player stats found in database.":
        prompt += f"Database Stats Context:\n{stats_context}\n\n"
        
    if vector_context:
        prompt += f"Pinecone Vector Context (Social/News):\n{vector_context}\n\n"
    if web_context:
        prompt += f"Real-Time Web Search Context:\n{web_context}\n\n"
        
    prompt += f"User Query: \"{query}\""
    return prompt

def ask_duggy_ai(query: str, match_score: dict) -> str:
    # Check domain guardrail first
    if is_off_topic(query):
        return "I am a cricket specialist! Ask me about the live match, stats, or players."

    # Check greeting interceptor
    greeting = get_greeting_response(query)
    if greeting:
        return greeting

    # Query stats database first
    stats_context = get_stats_context(query)
    
    # Retrieve Pinecone Vector DB context
    vector_context = query_pinecone_vectors(query)
    
    # Retrieve Tavily Web Search context
    web_context = query_tavily_search(query)
    
    # Build prompt dynamically using context builder
    prompt = build_prompt_context(query, stats_context, vector_context, web_context, match_score)
    
    # Check if local LLM is enabled
    if USE_LOCAL_LLM:
        try:
            system_instruction = (
                "You are 'Duggy', the witty, cricket-obsessed AI Stats Companion on the DugOut platform. "
                "Your tone is energetic, filled with cricket emojis, and highly engaging. "
                "CRITICAL: Base your answer STRICTLY on the provided Real-Time Web Search Context or Database Stats Context. "
                "Do NOT use your pre-trained knowledge if it contradicts the provided contexts. "
                "Keep responses under 3 sentences. Always format with markdown."
            )
            
            payload = {
                "model": LOCAL_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7
                }
            }
            
            with httpx.Client(timeout=60.0) as client:
                r = client.post(f"{LOCAL_LLM_URL}/api/chat", json=payload)
                if r.status_code == 200:
                    data = r.json()
                    content = data.get("message", {}).get("content", "").strip()
                    if content:
                        return content
                print(f"Local LLM API error (status {r.status_code}), falling back...")
        except Exception as e:
            print(f"Local LLM error: {e}, falling back...")

    # Try Hugging Face Inference API next
    if USE_HF_LLM and HF_API_KEY:
        try:
            system_instruction = (
                "You are 'Duggy', the witty, cricket-obsessed AI Stats Companion on the DugOut platform. "
                "Your tone is energetic, filled with cricket emojis, and highly engaging—like a T20 fan who knows every stat. "
                "Keep cricket-related responses under 4 sentences. Always format with markdown."
            )
            
            url = f"https://api-inference.huggingface.co/models/{HF_LLM_MODEL}/v1/chat/completions"
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}
            payload = {
                "model": HF_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            with httpx.Client(timeout=30.0) as client:
                r = client.post(url, headers=headers, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if content:
                        return content
                print(f"Hugging Face Inference API error (status {r.status_code}): {r.text}, falling back...")
        except Exception as e:
            print(f"Hugging Face Inference API error: {e}, falling back...")

    # If local/HF LLM disabled/failed, fall back to Gemini API
    if GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            system_instruction = (
                "You are 'Duggy', the witty, cricket-obsessed AI Stats Companion on the DugOut platform. "
                "Your tone is energetic, filled with cricket emojis, and highly engaging—like a T20 fan who knows every stat. "
                "Keep cricket-related responses under 4 sentences. Always format with markdown."
            )
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            
            return response.text.strip()
        except Exception as e:
            print(f"Chatbot AI Error: {e}")
            
    return ask_duggy_mock(query, stats_context, match_score)

async def stream_duggy_ai(query: str, match_score: dict):
    # Check domain guardrail first
    if is_off_topic(query):
        yield "I am a cricket specialist! Ask me about the live match, stats, or players."
        return

    # Check greeting interceptor
    greeting = get_greeting_response(query)
    if greeting:
        yield greeting
        return

    stats_context = get_stats_context(query)
    
    # Retrieve Pinecone Vector DB context (Async)
    vector_context = await query_pinecone_vectors_async(query)
    
    # Retrieve Tavily Web Search context (Async)
    web_context = await query_tavily_search_async(query)
    
    # Build prompt dynamically using context builder
    prompt = build_prompt_context(query, stats_context, vector_context, web_context, match_score)
    
    # Try local LLM streaming first
    if USE_LOCAL_LLM:
        try:
            system_instruction = (
                "You are 'Duggy', the witty, cricket-obsessed AI Stats Companion on the DugOut platform. "
                "Your tone is energetic, filled with cricket emojis, and highly engaging. "
                "CRITICAL: Base your answer STRICTLY on the provided Real-Time Web Search Context or Database Stats Context. "
                "Do NOT use your pre-trained knowledge if it contradicts the provided contexts. "
                "Keep responses under 3 sentences. Always format with markdown."
            )
            
            payload = {
                "model": LOCAL_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "stream": True,
                "options": {
                    "temperature": 0.7
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", f"{LOCAL_LLM_URL}/api/chat", json=payload) as r:
                    if r.status_code == 200:
                        async for line in r.aiter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    content = chunk.get("message", {}).get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    pass
                        return # Exit function on success
                    else:
                        print(f"Local LLM API streaming error (status {r.status_code}), falling back...")
        except Exception as e:
            print(f"Local LLM streaming error: {e}, falling back...")

    # Try Hugging Face Inference API next
    if USE_HF_LLM and HF_API_KEY:
        try:
            system_instruction = (
                "You are 'Duggy', the witty, cricket-obsessed AI Stats Companion on the DugOut platform. "
                "Your tone is energetic, filled with cricket emojis, and highly engaging—like a T20 fan who knows every stat. "
                "Keep cricket-related responses under 4 sentences. Always format with markdown."
            )
            
            url = f"https://api-inference.huggingface.co/models/{HF_LLM_MODEL}/v1/chat/completions"
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}
            payload = {
                "model": HF_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as r:
                    if r.status_code == 200:
                        async for line in r.aiter_lines():
                            if line:
                                line_str = line.strip()
                                if line_str.startswith("data:"):
                                    data_content = line_str[5:].strip()
                                    if data_content == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(data_content)
                                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                        if content:
                                            yield content
                                    except json.JSONDecodeError:
                                        pass
                        return # Exit function on success
                    else:
                        print(f"Hugging Face Inference API streaming error (status {r.status_code}), falling back...")
        except Exception as e:
            print(f"Hugging Face Inference API streaming error: {e}, falling back...")

    # Fall back to Gemini API streaming if local/HF LLM fails or is disabled
    if GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            system_instruction = (
                "You are 'Duggy', the witty, cricket-obsessed AI Stats Companion on the DugOut platform. "
                "Your tone is energetic, filled with cricket emojis, and highly engaging—like a T20 fan who knows every stat. "
                "Keep cricket-related responses under 4 sentences. Always format with markdown."
            )
            
            response_stream = client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            
            for chunk in response_stream:
                if chunk.text:
                    await asyncio.sleep(0.02)
                    yield chunk.text
            return
        except Exception as e:
            print(f"Chatbot AI Streaming Error: {e}")

    # Fall back to simulated mock streaming
    mock_response = ask_duggy_mock(query, stats_context, match_score)
    for word in mock_response.split(' '):
        await asyncio.sleep(0.05)
        yield word + ' '


def ask_duggy_mock(query: str, stats_context: str, match_score: dict) -> str:
    """Mock responder for Duggy when Gemini is unavailable."""
    q = query.lower()
    
    # Simple rule-based match
    if "score" in q or "match" in q or "today" in q:
        return (
            f"🤖 *Duggy Live Stats Bot:*\n\n"
            f"Tonight's match is intense! 🏏 **{match_score.get('batting_team')}** is currently at "
            f"**{match_score.get('runs')}/{match_score.get('wickets')}** after **{match_score.get('overs')}** overs. "
            f"Target: **{match_score.get('target')}**. "
            f"Recent action: `[ {', '.join(match_score.get('recent_balls', []))} ]`. "
            f"Join the Stand to chat with other fans! 🔥"
        )
    elif any(player in q for player in ["kohli", "rohit", "dhoni", "bumrah", "pandya"]):
        return (
            f"🤖 *Duggy Live Stats Bot (Demo Mode):*\n\n"
            f"Here is what I found in our database context: 📊\n\n"
            f"{stats_context}\n"
            f"*Note: Gemini API key is missing or rate limits exceeded. Serving response directly from DugOut's local database!*"
        )
    else:
        return (
            f"🤖 *Duggy Live Stats Bot (Demo Mode):*\n\n"
            f"Hey there! I'm **Duggy**, your cricket stats sidekick. "
            f"Ask me about player stats (e.g. *Kohli*, *Bumrah*, *Dhoni*) or type 'score' to check the live match state! 📈\n\n"
            f"*(Tip: Ensure your `GEMINI_API_KEY` is configured in the `.env` file and has active quota to unlock dynamic AI analytics!)*"
        )
