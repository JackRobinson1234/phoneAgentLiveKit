"""
Test script for Twilio timeout functionality
"""

import os
import requests
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client

# Twilio credentials
account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')

# Your server URL
base_url = os.environ.get('BASE_URL', 'http://localhost:5000')

def test_timeout_handler():
    """Test the timeout handler functionality"""
    print("Testing timeout handler...")
    
    # Simulate a timeout request to the timeout handler
    url = f"{base_url}/webhook/voice/timeout"
    payload = {
        'From': '+12345678901',
        'CallSid': 'TEST_CALL_SID_123'
    }
    
    try:
        print(f"Sending request to {url}")
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

def test_twilio_client():
    """Test the Twilio client connection"""
    print("Testing Twilio client connection...")
    
    try:
        client = Client(account_sid, auth_token)
        calls = client.calls.list(limit=1)
        print(f"✅ Successfully connected to Twilio API. Found {len(calls)} recent calls.")
    except Exception as e:
        print(f"❌ Failed to connect to Twilio API: {str(e)}")

if __name__ == "__main__":
    print("Starting Twilio timeout tests...")
    
    # Test Twilio client connection
    if account_sid and auth_token:
        test_twilio_client()
    else:
        print("⚠️ Twilio credentials not found in environment variables. Skipping client test.")
    
    # Test timeout handler
    test_timeout_handler()
