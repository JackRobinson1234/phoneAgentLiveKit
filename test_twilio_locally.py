#!/usr/bin/env python3
"""
Test script for simulating Twilio voice interactions locally
This allows you to test your animal control phone agent without making actual phone calls
"""

import requests
import json
from bs4 import BeautifulSoup
import re
import time
import os
import sys

# Configuration
FLASK_SERVER_URL = "http://localhost:5000"
CALLER_ID = "+15551234567"  # Simulated caller ID

def extract_speech_text(twiml_response):
    """Extract the speech text from TwiML response"""
    soup = BeautifulSoup(twiml_response, 'xml')
    say_tags = soup.find_all('Say')
    if say_tags:
        return say_tags[0].text
    return None

def extract_action_url(twiml_response):
    """Extract the action URL from TwiML response"""
    soup = BeautifulSoup(twiml_response, 'xml')
    gather_tags = soup.find_all('Gather')
    if gather_tags and 'action' in gather_tags[0].attrs:
        return gather_tags[0]['action']
    return None

def simulate_call():
    """Simulate a phone call to the Twilio webhook"""
    print("\n=== Starting simulated call to Animal Control ===\n")
    
    # Initial call
    response = requests.post(
        f"{FLASK_SERVER_URL}/answer",
        data={"From": CALLER_ID, "CallSid": "SIMULATED_CALL_1"}
    )
    
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        return
    
    # Extract the initial greeting
    initial_greeting = extract_speech_text(response.text)
    action_url = extract_action_url(response.text)
    
    if not initial_greeting:
        print("Error: Could not extract greeting from response")
        return
    
    if not action_url:
        print("Error: Could not extract action URL from response")
        return
    
    print(f"Agent: {initial_greeting}")
    
    # Start conversation loop
    while True:
        # Get user input
        user_input = input("\nYou: ")
        
        if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
            print("\n=== Ending simulated call ===\n")
            break
        
        # Send user input to the webhook
        full_url = f"{FLASK_SERVER_URL}{action_url}"
        response = requests.post(
            full_url,
            data={
                "From": CALLER_ID,
                "CallSid": "SIMULATED_CALL_1",
                "SpeechResult": user_input
            }
        )
        
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code}")
            break
        
        # Extract the agent's response
        agent_response = extract_speech_text(response.text)
        action_url = extract_action_url(response.text)
        
        if not agent_response:
            print("Error: Could not extract response from TwiML")
            break
            
        if not action_url:
            print("Error: Could not extract action URL from response")
            break
        
        print(f"\nAgent: {agent_response}")

if __name__ == "__main__":
    # Check if Flask server is running
    try:
        requests.get(FLASK_SERVER_URL)
    except requests.exceptions.ConnectionError:
        print(f"Error: Flask server not running at {FLASK_SERVER_URL}")
        print("Please start the Flask server first with: python twilio_integration.py")
        sys.exit(1)
        
    simulate_call()
