"""Test script for conversation context and new features."""

import requests
import json
import time
from typing import Dict, Any


BASE_URL = "http://localhost:8000"
WEBHOOK_ENDPOINT = f"{BASE_URL}/api/v1/webhooks/loop"
TEST_RECIPIENT = "+15551234567"


def send_test_message(text: str, message_id: str = None) -> Dict[str, Any]:
    """Send a test message to the local Chip server."""
    if message_id is None:
        message_id = f"test_{int(time.time() * 1000)}"
    
    payload = {
        "alert_type": "message_inbound",
        "text": text,
        "recipient": TEST_RECIPIENT,
        "message_id": message_id,
    }
    
    print(f"\n{'='*60}")
    print(f"📤 Sending: {text!r}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            WEBHOOK_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        try:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return result
        except:
            print(f"Response: {response.text}")
            return {"status": response.status_code, "text": response.text}
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to server!")
        print("   Make sure the server is running:")
        print("   python -m hypercorn main:app --reload --log-level debug")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None


def test_conversation_flow():
    """Test the full conversation flow with context."""
    print("🧪 TESTING CONVERSATION CONTEXT & NEW FEATURES")
    print("=" * 60)
    print("Make sure the server is running first!")
    print("=" * 60)
    
    # Test 1: Ask for challenges
    print("\n\n📋 TEST 1: Ask for challenges")
    send_test_message("What challenges are available?", "test1")
    time.sleep(2)
    
    # Test 2: Select option 2 (should maintain context)
    print("\n\n📋 TEST 2: Select option 2 (context test)")
    send_test_message("I'm interested in option 2", "test2")
    time.sleep(2)
    
    # Test 3: Select "the second challenge" (different phrasing)
    print("\n\n📋 TEST 3: Select 'the second challenge'")
    send_test_message("Tell me more about the second challenge", "test3")
    time.sleep(2)
    
    # Test 4: Spelling test - "intership"
    print("\n\n📋 TEST 4: Spelling test - 'intership'")
    send_test_message("What interships are available?", "test4")
    time.sleep(2)
    
    # Test 5: Spelling test - "challege"
    print("\n\n📋 TEST 5: Spelling test - 'challege'")
    send_test_message("Show me challeges", "test5")
    time.sleep(2)
    
    # Test 6: General knowledge question
    print("\n\n📋 TEST 6: General knowledge - capital of France")
    send_test_message("What's the capital of France?", "test6")
    time.sleep(2)
    
    # Test 7: Follow-up after general question
    print("\n\n📋 TEST 7: Follow-up after general question")
    send_test_message("Now tell me about opportunities", "test7")
    time.sleep(2)
    
    # Test 8: Multiple misspellings
    print("\n\n📋 TEST 8: Multiple misspellings")
    send_test_message("I want to see interships and challeges", "test8")
    time.sleep(2)
    
    print("\n\n" + "=" * 60)
    print("✅ Testing complete!")
    print("=" * 60)
    print("\nCheck the server logs to see:")
    print("  - Conversation history being maintained")
    print("  - Spelling corrections")
    print("  - Context awareness")
    print("=" * 60)


if __name__ == "__main__":
    test_conversation_flow()



