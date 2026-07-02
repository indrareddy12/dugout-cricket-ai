# 🏏 DugOut: Spatial Social Hub for Cricket Fans with Real-Time AI

DugOut is an interactive, real-time social platform designed for cricket fans. It features a bird's eye spatial stadium map, crowd-sourced Decision Review System (DRS) polls, dynamic live game simulators, and a wit-filled local AI Stats Companion named **Duggy** (powered by local open-source LLMs).

---

## 🚀 Key Features

### 1. 🤖 System A: AI Stats Companion ("Duggy")
*   **Local Open-Source AI**: Queries a local **Ollama** instance running `llava:latest` to generate energetic, emoji-rich cricket analytics.
*   **Real-time RAG Pipeline**: Leverages **Tavily Web Search** and **Pinecone Vector Database** to merge live cricket news, match thread banter, and local database statistics.
*   **Bypassed Anchoring Bias**: Implements dynamic context separation to prevent the local model from being confused by mock simulator scores when asked about general global cricket tournaments.

### 2. 🎮 System B: Match Simulator Deck
*   An interactive event control deck allows developers/presenters to post real-time ball occurrences (Dot Balls, Singles, 4s, 6s, Wickets, DRS Appeals).
*   Events instantly update the scoreboard, run rate, ball timeline, and audience Fan Pulse excitation levels in real-time.

### 3. ⚖️ System C: Interactive Crowd DRS Voting
*   Triggering a DRS review locks the stands into a synchronous **15-second crowd voting poll**.
*   Fans vote `OUT` or `NOT OUT` with visual progress meters, resolving cleanly with official simulated umpire verdicts.

### 4. 🏟️ System D: Spatial Social Stands & Vector Map
*   **Interactive SVG Stadium**: A beautiful visual vector map of the ground displays active spectator counts per section.
*   **One-Click Transitions**: Hovering over sectors lights up the CSK, MI, or Neutral stands in team colors. Clicking a sector transitions the user to that stand's dedicated chatroom socket.

### 5. 🛡️ System E: Moderation Shield
*   An active regex-based toxicity filter scans all fan chatter on both the frontend and backend.
*   Toxic comments are immediately censored with placeholders (e.g. `[Message blocked for toxicity]`) and logged to an admin Moderation Shield board.

### 6. 💬 System F: Moment-Based AI Thread Generator
*   Match milestones (wickets or boundaries) automatically prompt the AI thread engine to compile and inject an active discussion card into the social feeds.

---

## 🛠️ Technology Stack
*   **Backend Framework**: FastAPI (Uvicorn web server, Python 3.12+)
*   **Real-time Comms**: WebSockets (Asyncio-driven multi-room connection loops)
*   **State Management**: Unified abstract state manager supporting local InMemory fallback and production-ready **Redis Clustered Pub/Sub**.
*   **Frontend**: Vanilla HTML5, CSS3, JavaScript (responsive layouts, glassmorphism UI, vector SVG path transitions).
*   **AI Engine**: Ollama (`llava:latest`), Hugging Face Inference API, Google Gemini Pro.
*   **Search/Retrieval**: Tavily API, Pinecone Client.

---

## ⚙️ Setup & Installation

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/indrareddy12/dugout-cricket-ai.git
cd dugout-cricket-ai
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```ini
# Server Mode
USE_REDIS=false
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=

# Local LLM Config (Ollama)
USE_LOCAL_LLM=true
LOCAL_LLM_URL=http://localhost:11434
LOCAL_LLM_MODEL=llava:latest

# Hugging Face Config (Fallback)
USE_HF_LLM=false
HF_API_KEY=
HF_LLM_MODEL=meta-llama/Meta-Llama-3-8B-Instruct

# Gemini Config (Fallback)
GEMINI_API_KEY=

# Pinecone Config
USE_PINECONE=false
PINECONE_API_KEY=
PINECONE_INDEX_NAME=dugout-index

# Tavily Web Search API
USE_WEB_SEARCH=true
TAVILY_API_KEY=your_tavily_api_key_here
```

### 3. Run the Local LLM (Ollama)
Make sure Ollama is installed and running on your system, then pull the model:
```bash
ollama pull llava:latest
```

### 4. Start the Application Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000/`** in your browser.

---

## 🧪 Testing

The codebase includes full unit tests validating state manager thread safety, chatbot retrieving patterns, and backend moderation layers.

Run all tests:
```bash
python tests/test_services.py
python tests/test_chatbot.py
python tests/test_state_manager.py
```
