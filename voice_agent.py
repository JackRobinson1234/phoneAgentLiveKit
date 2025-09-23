#!/usr/bin/env python3
"""
Voice interface for Animal Control Agent
Handles text-to-speech and speech-to-text locally
"""

import os
import time
import threading
import argparse
import queue
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
from gtts import gTTS
from io import BytesIO
import pygame
import speech_recognition as sr
from agents.llm_animal_control_agent import LLMAnimalControlAgent

class VoiceInterface:
    def __init__(self):
        self.agent = LLMAnimalControlAgent()
        self.context = {'conversation_started': True, 'turn_count': 0}
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.audio_queue = queue.Queue()
        pygame.mixer.init()
        
    def text_to_speech(self, text):
        """Convert text to speech and play it"""
        print(f"Agent: {text}")
        
        # Generate speech using gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Save to a BytesIO object
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        # Play the audio
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    
    def speech_to_text(self):
        """Convert speech to text using microphone input"""
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("Processing speech...")
                try:
                    text = self.recognizer.recognize_google(audio)
                    print(f"You: {text}")
                    return text
                except sr.UnknownValueError:
                    print("Could not understand audio")
                    return ""
                except sr.RequestError as e:
                    print(f"Error with speech recognition service: {e}")
                    return ""
            except sr.WaitTimeoutError:
                print("No speech detected")
                return ""
    
    def start_conversation(self):
        """Start a voice conversation with the agent"""
        # Get initial greeting
        initial_greeting = self.agent.get_initial_greeting()
        self.text_to_speech(initial_greeting)
        
        # Main conversation loop
        while True:
            # Get user input via speech
            user_input = self.speech_to_text()
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye', 'end']:
                self.text_to_speech("Thank you for contacting Animal Control Services. Goodbye!")
                break
            
            # Skip empty inputs
            if not user_input:
                self.text_to_speech("I didn't catch that. Could you please repeat?")
                continue
            
            # Process through the agent
            result, next_state, updated_context = self.agent.process_input(user_input, self.context)
            
            # Update context
            self.context = updated_context
            
            # Get the response message
            response = updated_context.get('message', "I'm processing your request.")
            
            # Convert to speech
            self.text_to_speech(response)

def main():
    parser = argparse.ArgumentParser(description='Animal Control Voice Agent')
    parser.add_argument('--no-voice', action='store_true', help='Run in text-only mode')
    args = parser.parse_args()
    
    if args.no_voice:
        # Text-only mode
        agent = LLMAnimalControlAgent()
        context = {'conversation_started': True, 'turn_count': 0}
        
        # Get initial greeting
        initial_greeting = agent.get_initial_greeting()
        print(f"Agent: {initial_greeting}")
        
        # Main conversation loop
        while True:
            # Get user input via text
            user_input = input("You: ")
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye', 'end']:
                print("Agent: Thank you for contacting Animal Control Services. Goodbye!")
                break
            
            # Process through the agent
            result, next_state, updated_context = agent.process_input(user_input, context)
            
            # Update context
            context = updated_context
            
            # Get the response message
            response = context.get('message', "I'm processing your request.")
            
            # Print response
            print(f"Agent: {response}")
    else:
        # Voice mode
        voice_interface = VoiceInterface()
        voice_interface.start_conversation()

if __name__ == "__main__":
    main()
