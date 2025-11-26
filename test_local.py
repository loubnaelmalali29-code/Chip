"""Simple script to test Chip locally with various message types and misspellings."""

import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8000"
WEBHOOK_ENDPOINT = f"{BASE_URL}/api/v1/webhooks/loop"


def send_test_message(text: str, message_id: str = None, recipient: str = "+15551234567") -> Dict[str, Any]:
    """Send a test message to the local Chip server."""
    if message_id is None:
        import time
        message_id = f"test_{int(time.time() * 1000)}"
    
    payload = {
        "alert_type": "message_inbound",
        "text": text,
        "recipient": recipient,
        "message_id": message_id,
    }
    
    print(f"\n{'='*60}")
    print(f"Testing message: {text!r}")
    print(f"Message ID: {message_id}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            WEBHOOK_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        try:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return result
        except:
            print(f"Response Text: {response.text}")
            return {"status": response.status_code, "text": response.text}
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to server!")
        print("   Make sure the server is running:")
        print("   hypercorn main:app --reload --log-level debug")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None


def main():
    """Run a series of tests."""
    print("🧪 Testing Chip Locally")
    print("=" * 60)
    print("Make sure the server is running:")
    print("  hypercorn main:app --reload --log-level debug")
    print("=" * 60)
    
    # Test cases
    tests = [
        # Normal messages
        ("What challenges are available?", "normal_message"),
        
        # Misspellings - should be corrected
        ("challege", "misspelling_challenge"),
        ("comunity", "misspelling_community"),
        ("submited", "misspelling_submitted"),
        ("challege comunity", "multiple_misspellings"),
        ("What challeges are in the comunity?", "misspelling_in_sentence"),
        
        # Empty/whitespace
        ("", "empty_message"),
        ("   ", "whitespace_only"),
        
        # Normal variations
        ("Hi Chip!", "greeting"),
        ("Tell me about opportunities", "opportunities_query"),
    ]
    
    results = []
    for text, test_name in tests:
        result = send_test_message(text, message_id=test_name)
        results.append((test_name, result))
        
        # Small delay between requests
        import time
        time.sleep(0.5)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    for test_name, result in results:
        status = "✓" if result and result.get("ok") else "✗"
        print(f"{status} {test_name}")
    
    print(f"\n{'='*60}")
    print("✅ Testing complete!")
    print("Check the server logs to see spelling corrections in action.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

