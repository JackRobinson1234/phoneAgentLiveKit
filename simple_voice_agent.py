#!/usr/bin/env python3
"""
Simplified voice interface for Animal Control Agent
Uses only gTTS for text-to-speech and defaults to text input
"""

import os
import time
import argparse
import tempfile
from gtts import gTTS
import subprocess
from agents.llm_animal_control_agent import LLMAnimalControlAgent

class SimpleVoiceInterface:
    def __init__(self, use_voice_output=True):
        self.agent = LLMAnimalControlAgent()
        self.context = {'conversation_started': True, 'turn_count': 0}
        self.use_voice_output = use_voice_output
        
    def text_to_speech(self, text):
        """Convert text to speech and play it"""
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
        """Start a conversation with the agent"""
        # Get initial greeting
        initial_greeting = self.agent.start_conversation()
        self.text_to_speech(initial_greeting)
        
        # Main conversation loop
        while True:
            # Get user input via text
            user_input = input("You: ")
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye', 'end']:
                self.text_to_speech("Thank you for contacting Animal Control Services. Goodbye!")
                break
            
            # Process through the agent
            response = self.agent.process_message(user_input)
            
            # Get conversation status
            self.context = self.agent.state_machine.context
            
            # The response is already set from process_message
            
            # Convert to speech
            self.text_to_speech(response)

def main():
    parser = argparse.ArgumentParser(description='Animal Control Voice Agent')
    parser.add_argument('--no-voice', action='store_true', help='Run without voice output')
    args = parser.parse_args()
    
    # Create the voice interface
    voice_interface = SimpleVoiceInterface(use_voice_output=not args.no_voice)
    
    # Start the conversation
    voice_interface.start_conversation()

if __name__ == "__main__":
    main()
