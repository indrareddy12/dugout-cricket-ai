import sys
import os
import asyncio

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.chatbot import is_off_topic, ask_duggy_ai, stream_duggy_ai

def test_domain_guardrail():
    print("Testing Domain Guardrails (On-topic vs Off-topic)...")
    # On-topic
    assert not is_off_topic("What is Virat Kohli's average against spin?"), "Failed: On-topic query marked as off-topic"
    assert not is_off_topic("score CSK"), "Failed: On-topic query marked as off-topic"
    assert not is_off_topic("tell me about Rohit vs Starc matchup"), "Failed: On-topic query marked as off-topic"
    assert not is_off_topic("hi duggy"), "Failed: On-topic query marked as off-topic"
    print("OK: On-topic queries passed.")

    # Off-topic
    assert is_off_topic("Write a Python script to add two numbers"), "Failed: Off-topic query marked as on-topic"
    assert is_off_topic("What is the capital of France?"), "Failed: Off-topic query marked as on-topic"
    assert is_off_topic("who is the president of the United States?"), "Failed: Off-topic query marked as on-topic"
    print("OK: Off-topic queries successfully flagged.")

def test_chatbot_off_topic_reply():
    print("\nTesting Chatbot off-topic response...")
    match_score = {
        "batting_team": "CSK",
        "bowling_team": "MI",
        "runs": 164,
        "wickets": 4,
        "overs": "17.2",
        "target": 192,
        "recent_balls": ["4", "0", "6", "W", "1", "2"]
    }
    
    reply = ask_duggy_ai("Write a python script", match_score)
    assert reply == "I am a cricket specialist! Ask me about the live match, stats, or players.", f"Failed: Unexpected reply for off-topic query: {reply}"
    print("OK: Chatbot returned off-topic banner response.")

async def async_test_stream_duggy():
    print("\nTesting async chatbot stream...")
    match_score = {
        "batting_team": "CSK",
        "bowling_team": "MI",
        "runs": 164,
        "wickets": 4,
        "overs": "17.2",
        "target": 192,
        "recent_balls": ["4", "0", "6", "W", "1", "2"]
    }
    
    # Test streaming on-topic (we can just verify it returns some content)
    chunks = []
    async for chunk in stream_duggy_ai("what is kohli stats?", match_score):
        chunks.append(chunk)
    
    full_response = "".join(chunks)
    assert len(full_response) > 0, "Failed: Stream returned empty response!"
    print("OK: Chatbot streaming works.")

    # Test streaming off-topic
    chunks_off = []
    async for chunk in stream_duggy_ai("write python code", match_score):
        chunks_off.append(chunk)
    full_response_off = "".join(chunks_off)
    assert full_response_off == "I am a cricket specialist! Ask me about the live match, stats, or players.", f"Failed: Unexpected stream reply for off-topic query: {full_response_off}"
    print("OK: Chatbot stream blocked off-topic queries.")

def test_huggingface_config():
    print("\nTesting Hugging Face Config integration...")
    from app.config import USE_HF_LLM, HF_LLM_MODEL
    # Should load settings safely
    assert USE_HF_LLM is False or USE_HF_LLM is True, "USE_HF_LLM is not loaded as boolean"
    assert HF_LLM_MODEL == "meta-llama/Meta-Llama-3-8B-Instruct", f"Unexpected default HF model: {HF_LLM_MODEL}"
    print("OK: Hugging Face configurations loaded successfully.")

def test_search_fallbacks():
    print("\nTesting Pinecone and Tavily Search fallback config...")
    from unittest.mock import patch
    from app.services.chatbot import query_tavily_search, query_pinecone_vectors
    
    # Force search to be disabled to test the fallback path
    with patch("app.services.chatbot.USE_WEB_SEARCH", False):
        with patch("app.services.chatbot.USE_PINECONE", False):
            assert query_tavily_search("kohli") == "", "Tavily search did not fall back to empty string when disabled"
            assert query_pinecone_vectors("kohli") == "", "Pinecone search did not fall back to empty string when disabled"
            
    # Force search to be enabled but with empty keys
    with patch("app.services.chatbot.USE_WEB_SEARCH", True):
        with patch("app.services.chatbot.TAVILY_API_KEY", ""):
            assert query_tavily_search("kohli") == "", "Tavily search did not fall back to empty string when key is empty"
            
    with patch("app.services.chatbot.USE_PINECONE", True):
        with patch("app.services.chatbot.PINECONE_API_KEY", ""):
            assert query_pinecone_vectors("kohli") == "", "Pinecone search did not fall back to empty string when key is empty"
            
    print("OK: Pinecone and Tavily search fallback configuration validated.")
def test_search_context_injection():
    print("\nTesting search context injection into prompt...")
    from unittest.mock import patch, MagicMock
    # Mock search functions to return test data
    with patch("app.services.chatbot.query_pinecone_vectors", return_value="[MOCK PINECONE MATCH]"):
        with patch("app.services.chatbot.query_tavily_search", return_value="[MOCK TAVILY MATCH]"):
            # Mock the Gemini client to capture the prompt
            with patch("app.services.chatbot.genai.Client") as MockClient:
                mock_instance = MagicMock()
                MockClient.return_value = mock_instance
                
                # Mock config flags to force Gemini path
                with patch("app.services.chatbot.USE_LOCAL_LLM", False):
                    with patch("app.services.chatbot.USE_HF_LLM", False):
                        with patch("app.services.chatbot.GEMINI_API_KEY", "mock-gemini-key"):
                            from app.services.chatbot import ask_duggy_ai
                            
                            match_score = {"batting_team": "CSK", "bowling_team": "MI", "runs": 100, "wickets": 2, "overs": "10"}
                            ask_duggy_ai("Virat Kohli stats?", match_score)
                            
                            # Check what prompt was sent to generate_content
                            args, kwargs = mock_instance.models.generate_content.call_args
                            contents = kwargs.get("contents") or args[0]
                            
                            assert "[MOCK PINECONE MATCH]" in contents, "Pinecone context not found in prompt!"
                            assert "[MOCK TAVILY MATCH]" in contents, "Tavily context not found in prompt!"
    print("OK: Pinecone and Tavily contexts successfully injected into prompt.")

if __name__ == "__main__":
    print("=== RUNNING DUGOUT CHATBOT TESTS ===")
    test_domain_guardrail()
    test_chatbot_off_topic_reply()
    test_huggingface_config()
    test_search_fallbacks()
    test_search_context_injection()
    asyncio.run(async_test_stream_duggy())
    print("\nALL DUGOUT CHATBOT TESTS PASSED SUCCESSFULLY! (OK)")


