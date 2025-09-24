"""
Test script for Twilio timeout functionality
"""

import requests
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse

def test_timeout_handler():
    """Test the timeout handler functionality"""
    print("Testing timeout handler...")
    
    # Simulate a timeout request to the timeout handler
    url = "http://localhost:5000/timeout_handler"
    payload = {
        'From': '+12345678901',
        'CallSid': 'TEST_CALL_SID_123'
    }
    
    try:
        response = requests.post(url, data=payload)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Check if the response contains the expected timeout message
        if "Are you still there?" in response.text:
            print("✅ Test passed: Timeout handler returned the expected message")
        else:
            print("❌ Test failed: Timeout handler did not return the expected message")
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")

if __name__ == "__main__":
    print("Starting timeout handler test...")
    test_timeout_handler()
