import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import BallEvent
from app.services.moderator import moderate_message
from app.services.thread_gen import should_generate_thread
from app.services.chatbot import get_stats_context

def test_moderation_layer():
    print("Testing Moderation Layer (Tier 1 - Regex)...")
    # Clean text should pass
    clean_msg = "CSK is going to win this match easily!"
    res1 = moderate_message(clean_msg)
    assert not res1.is_toxic, "Failed: Clean message flagged as toxic!"
    print("OK: Clean message passed.")
    
    # Severe profanity should block
    bad_msg = "You are a complete chutiya and a loser."
    res2 = moderate_message(bad_msg)
    assert res2.is_toxic, "Failed: Profane message was not blocked!"
    print("OK: Profane message successfully blocked.")
    print("Reason:", res2.reason)

def test_thread_generator():
    print("\nTesting Thread Generator logic...")
    # Normal dot ball should not trigger a thread
    normal_event = BallEvent(over="14.1", batsman="Dhoni", bowler="Bumrah", runs=0, event_type="normal", description="Defensive stroke.")
    assert not should_generate_thread(normal_event), "Failed: Normal event triggered a thread!"
    print("OK: Normal dot ball did not trigger thread.")
    
    # Wicket should trigger a thread
    wicket_event = BallEvent(over="14.2", batsman="Dhoni", bowler="Bumrah", runs=0, event_type="wicket", description="Clean bowled!")
    assert should_generate_thread(wicket_event), "Failed: Wicket did not trigger a thread!"
    print("OK: Wicket event successfully triggered thread.")
    
    # Six runs should trigger a thread
    six_event = BallEvent(over="14.3", batsman="Dhoni", bowler="Bumrah", runs=6, event_type="boundary", description="Hit for six!")
    assert should_generate_thread(six_event), "Failed: Six did not trigger a thread!"
    print("OK: Boundary (six) successfully triggered thread.")

def test_chatbot_stats_db():
    print("\nTesting Chatbot local database context...")
    # Check stats parsing
    context = get_stats_context("tell me about Virat Kohli record")
    assert "Virat Kohli" in context, "Failed: Kohli record not found in stats context!"
    print("OK: Virat Kohli stats successfully loaded.")
    
    # Check stats vs Bumrah
    context_vs = get_stats_context("what is kohli vs bumrah?")
    assert "vs_bumrah" in context_vs or "Vs Bumrah" in context_vs, "Failed: Matchup stats not found!"
    print("OK: Matchup record successfully loaded.")

if __name__ == "__main__":
    print("=== RUNNING DUGOUT BACKEND TESTS ===")
    try:
        test_moderation_layer()
        test_thread_generator()
        test_chatbot_stats_db()
        print("\nALL BACKEND UNIT TESTS PASSED SUCCESSFULLY! (OK)")
    except AssertionError as e:
        print("\nTEST FAILURE:", e)
        sys.exit(1)
