#!/usr/bin/env python3
"""
Voice interface for Animal Control Agent using API
Uses API for conversation management and gTTS for voice output
"""

import os
import time
import argparse
import tempfile
import requests
import json
from gtts import gTTS
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
RAILWAY_URL = os.environ.get('RAILWAY_URL', '')
API_BASE_URL = RAILWAY_URL if RAILWAY_URL else "http://localhost:5001"

class APIVoiceInterface:
    def __init__(self, use_voice_output=True):
        self.conversation_id = None
        self.use_voice_output = use_voice_output
        
    def text_to_speech(self, text):
        """Convert text to speech and play it"""
        # Handle empty or None text
        if not text or not text.strip():
            print("Agent: [No response]")
            return
            
        print(f"Agent: {text}")
        
        if not self.use_voice_output:
            return
        
        try:
            # Generate speech using gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                temp_filename = fp.name
                tts.save(temp_filename)
            
            # Play the audio using the default player on macOS
            if os.name == 'posix':  # macOS or Linux
                subprocess.call(['afplay' if 'darwin' in os.uname().sysname.lower() else 'mpg123', temp_filename])
            elif os.name == 'nt':  # Windows
                os.system(f'start {temp_filename}')
            
            # Clean up the temporary file
            os.unlink(temp_filename)
        except Exception as e:
            print(f"Error playing speech: {e}")
    
    def start_conversation(self):
        """Start a conversation with the agent via API"""
        try:
            # Call API to start conversation
            response = requests.post(f"{API_BASE_URL}/conversations")
            data = response.json()
            
            # Store conversation ID
            self.conversation_id = data['conversation_id']
            
            # Get initial greeting
            initial_greeting = data.get('message', '')
            
            # If the initial greeting is empty, use a default greeting
            if not initial_greeting or not initial_greeting.strip():
                initial_greeting = "Hello! I'm the Animal Control Services assistant. How can I help you today?"
                print("Warning: Received empty greeting from API, using default greeting instead.")
                
            self.text_to_speech(initial_greeting)
            
            # Main conversation loop
            while True:
                # Get user input via text
                user_input = input("You: ")
                
                # Check for exit commands
                if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye', 'end']:
                    self._end_conversation()
                    break
                
                # Skip empty inputs
                if not user_input.strip():
                    continue
                
                # Send message to API
                agent_response = self._send_message(user_input)
                
                # Convert to speech
                self.text_to_speech(agent_response)
        
        except Exception as e:
            print(f"Error in conversation: {e}")
            if self.conversation_id:
                self._end_conversation()
    
    def _send_message(self, message):
        """Send a message to the API and get response"""
        try:
            # Call API to send message
            response = requests.post(
                f"{API_BASE_URL}/conversations/{self.conversation_id}/messages",
                json={'message': message}
            )
            data = response.json()
            
            # Get the agent's response
            agent_response = data.get('message', '')
            
            # Handle empty responses
            if not agent_response or not agent_response.strip():
                print("Warning: Received empty response from API")
                return "I'm sorry, I didn't understand that. Could you please rephrase or ask another question?"
            
            return agent_response
        
        except Exception as e:
            print(f"Error sending message: {e}")
            return "I'm sorry, but I encountered an error processing your request."
    
    def _end_conversation(self):
        """End the conversation via API"""
        try:
            # Call API to end conversation
            response = requests.delete(f"{API_BASE_URL}/conversations/{self.conversation_id}")
            data = response.json()
            
            # Get end message
            end_message = data.get('message', '')
            
            # Use default message if empty
            if not end_message or not end_message.strip():
                end_message = "Thank you for contacting Animal Control Services. Goodbye!"
            
            # Speak end message
            self.text_to_speech(end_message)
        
        except Exception as e:
            print(f"Error ending conversation: {e}")
            self.text_to_speech("Thank you for contacting Animal Control Services. Goodbye!")

def main():
    parser = argparse.ArgumentParser(description='Animal Control Voice Agent (API Version)')
    parser.add_argument('--no-voice', action='store_true', help='Run without voice output')
    args = parser.parse_args()
    
    # Create the voice interface
    voice_interface = APIVoiceInterface(use_voice_output=not args.no_voice)
    
    # Start the conversation
    voice_interface.start_conversation()

if __name__ == "__main__":
    main()
