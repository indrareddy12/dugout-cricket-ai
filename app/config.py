import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Local LLM configuration
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:11434")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llava:latest")

# Hugging Face configuration
USE_HF_LLM = os.getenv("USE_HF_LLM", "false").lower() == "true"
HF_API_KEY = os.getenv("HF_API_KEY", "")
HF_LLM_MODEL = os.getenv("HF_LLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")

# Pinecone configuration
USE_PINECONE = os.getenv("USE_PINECONE", "false").lower() == "true"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "dugout-index")

# Tavily configuration
USE_WEB_SEARCH = os.getenv("USE_WEB_SEARCH", "false").lower() == "true"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# App Port & Host
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Redis configuration
USE_REDIS = os.getenv("USE_REDIS", "false").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Verify configuration status
if USE_REDIS:
    print(f"Redis Clustering is ENABLED (Host: {REDIS_HOST}:{REDIS_PORT})")
else:
    print("Redis Clustering is DISABLED (Using local in-memory fallback)")

if USE_LOCAL_LLM:
    print(f"Local LLM is enabled (Model: {LOCAL_LLM_MODEL}, URL: {LOCAL_LLM_URL})")
elif USE_HF_LLM:
    if not HF_API_KEY:
        print(f"WARNING: USE_HF_LLM is true, but HF_API_KEY is empty. Hugging Face features will fall back.")
    else:
        print(f"Hugging Face Inference API is enabled (Model: {HF_LLM_MODEL})")
else:
    if not GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY environment variable is not set and local/HF LLMs are disabled. AI features will operate in MOCK/FALLBACK mode.")
    else:
        print("Gemini API is configured successfully.")

if USE_PINECONE:
    if not PINECONE_API_KEY:
        print("WARNING: USE_PINECONE is true, but PINECONE_API_KEY is empty. Pinecone RAG is disabled.")
    else:
        print(f"Pinecone Vector Search is ENABLED (Index: {PINECONE_INDEX_NAME})")
else:
    print("Pinecone Vector Search is DISABLED")

if USE_WEB_SEARCH:
    if not TAVILY_API_KEY:
        print("WARNING: USE_WEB_SEARCH is true, but TAVILY_API_KEY is empty. Web Search is disabled.")
    else:
        print("Tavily Web Search is ENABLED")
else:
    print("Tavily Web Search is DISABLED")




