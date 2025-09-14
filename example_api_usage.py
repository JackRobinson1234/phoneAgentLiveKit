#!/usr/bin/env python3
"""
Example usage of the Health Agent API
Shows how to interact with the API endpoints
"""

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:5000"

def example_conversation():
    """Example of a complete conversation flow"""
    
    print("🏥 Health Agent API Example")
    print("=" * 40)
    
    # 1. Start a new conversation
    print("\n1. Starting new conversation...")
    response = requests.post(f"{BASE_URL}/conversations")
    
    if response.status_code == 201:
        data = response.json()
        conversation_id = data['conversation_id']
        print(f"✅ Conversation started: {conversation_id}")
        print(f"🤖 {data['message']}")
    else:
        print(f"❌ Failed to start conversation: {response.text}")
        return
    
    # 2. Send messages
    messages = [
        "hello",
        "I need an eye doctor",
        "My name is John Smith", 
        "john.smith@email.com",
        "next friday at 2pm"
    ]
    
    for i, message in enumerate(messages, 2):
        print(f"\n{i}. Sending message: '{message}'")
        
        response = requests.post(
            f"{BASE_URL}/conversations/{conversation_id}/messages",
            json={"message": message}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"🤖 {data['message']}")
            print(f"📍 Current state: {data['current_state']}")
            
            # Show context if available
            context = data.get('context', {})
            if context.get('patient_name'):
                print(f"👤 Patient: {context['patient_name']}")
            if context.get('specialty'):
                print(f"🏥 Specialty: {context['specialty']}")
        else:
            print(f"❌ Failed to send message: {response.text}")
            break
        
        time.sleep(1)  # Brief pause between messages
    
    # 3. Get conversation status
    print(f"\n{len(messages) + 2}. Getting conversation status...")
    response = requests.get(f"{BASE_URL}/conversations/{conversation_id}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📊 Status: {data['current_state']}")
        print(f"🔄 Complete: {data['is_complete']}")
        print(f"📝 Context: {json.dumps(data['context'], indent=2)}")
    
    # 4. End conversation
    print(f"\n{len(messages) + 3}. Ending conversation...")
    response = requests.delete(f"{BASE_URL}/conversations/{conversation_id}")
    
    if response.status_code == 200:
        print("✅ Conversation ended successfully")
    else:
        print(f"❌ Failed to end conversation: {response.text}")

def test_health_check():
    """Test the health check endpoint"""
    print("\n🔍 Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API is healthy: {data['status']}")
        print(f"🕐 Timestamp: {data['timestamp']}")
    else:
        print(f"❌ Health check failed: {response.text}")

if __name__ == "__main__":
    try:
        # Test health check first
        test_health_check()
        
        # Run example conversation
        example_conversation()
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server.")
        print("Make sure the server is running with: python api.py")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
