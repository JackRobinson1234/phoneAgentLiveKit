#!/usr/bin/env python3
"""
Animal Control API System Launcher
Kills any existing API server processes and starts the API server with a console chat interface
"""

import os
import sys
import signal
import subprocess
import time
import socket
import threading
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_PORT = int(os.environ.get("PORT", 5001))
API_SCRIPT = "animal_control_api.py"
API_HOST = '0.0.0.0'
DEBUG_MODE = os.environ.get("DEBUG", "False").lower() == "true"
API_BASE_URL = f"http://localhost:{API_PORT}"

class ConsoleChatClient:
    """Console-based chat client for interacting with the Animal Control API"""
    
    def __init__(self):
        self.conversation_id = None
        self.running = False
    
    def start_conversation(self):
        """Start a new conversation with the API"""
        try:
            response = requests.post(f"{API_BASE_URL}/conversations")
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"\nError: API returned status code {response.status_code}")
                print(f"Response: {response.text}\n")
                return False
                
            # Parse the JSON response
            try:
                data = response.json()
            except Exception as json_error:
                print(f"\nError parsing JSON response: {json_error}")
                print(f"Raw response: {response.text}\n")
                return False
            
            # Check if conversation_id is in the response
            if 'conversation_id' not in data:
                print("\nError: API response missing conversation_id")
                print(f"Response data: {data}\n")
                return False
                
            # Store conversation ID
            self.conversation_id = data['conversation_id']
            
            # Display initial greeting
            initial_greeting = data.get('message', '')
            if initial_greeting:
                print(f"\nAgent: {initial_greeting}\n")
            else:
                print("\nAgent: Hello! I'm here to help with animal control services. How can I assist you today?\n")
                
            return True
        except requests.exceptions.ConnectionError:
            print("\nError: Could not connect to the API server")
            print(f"Make sure the API server is running at {API_BASE_URL}\n")
            return False
        except Exception as e:
            print(f"\nError starting conversation: {e}")
            print("Make sure the API server is running.\n")
            return False
    
    def send_message(self, message):
        """Send a message to the API and get response"""
        if not self.conversation_id:
            print("No active conversation. Please start a new conversation first.")
            return False
            
        try:
            # Send the message to the API
            response = requests.post(
                f"{API_BASE_URL}/conversations/{self.conversation_id}/messages",
                json={'message': message}
            )
            
            # Check if the request was successful
            if response.status_code != 200:
                print(f"\nError: API returned status code {response.status_code}")
                print(f"Response: {response.text}\n")
                
                # If the conversation doesn't exist anymore, reset the conversation ID
                if response.status_code == 404:
                    print("Conversation not found. Starting a new conversation...")
                    self.conversation_id = None
                    return self.start_conversation()
                    
                return False
                
            # Parse the JSON response
            try:
                data = response.json()
            except Exception as json_error:
                print(f"\nError parsing JSON response: {json_error}")
                print(f"Raw response: {response.text}\n")
                return False
            
            # Display agent's response
            agent_response = data.get('message', '')
            if agent_response:
                print(f"\nAgent: {agent_response}\n")
            else:
                print("\nAgent: I'm sorry, I didn't understand that. Could you please rephrase?\n")
                
            return True
            
        except requests.exceptions.ConnectionError:
            print("\nError: Could not connect to the API server")
            print(f"Make sure the API server is running at {API_BASE_URL}\n")
            return False
        except Exception as e:
            print(f"\nError sending message: {e}")
            return False
    
    def end_conversation(self):
        """End the conversation"""
        if not self.conversation_id:
            print("\nNo active conversation to end.\n")
            return True
            
        try:
            # Send the delete request to end the conversation
            response = requests.delete(f"{API_BASE_URL}/conversations/{self.conversation_id}")
            
            # Check if the request was successful
            if response.status_code != 200:
                # If 404, the conversation doesn't exist anymore, which is fine
                if response.status_code == 404:
                    print("\nConversation already ended or not found.\n")
                    self.conversation_id = None
                    return True
                    
                print(f"\nError: API returned status code {response.status_code}")
                print(f"Response: {response.text}\n")
                return False
                
            # Parse the JSON response
            try:
                data = response.json()
            except Exception as json_error:
                print(f"\nError parsing JSON response: {json_error}")
                print(f"Raw response: {response.text}\n")
                # Still consider the conversation ended
                self.conversation_id = None
                return True
            
            # Display end message
            end_message = data.get('message', 'Thank you for using Animal Control Services. Goodbye!')
            print(f"\nAgent: {end_message}\n")
            
            self.conversation_id = None
            return True
            
        except requests.exceptions.ConnectionError:
            print("\nError: Could not connect to the API server")
            print(f"Make sure the API server is running at {API_BASE_URL}\n")
            # Still consider the conversation ended locally
            self.conversation_id = None
            return True
        except Exception as e:
            print(f"\nError ending conversation: {e}")
            # Still consider the conversation ended locally
            self.conversation_id = None
            return True
    
    def run_chat_loop(self):
        """Run the main chat loop"""
        print("\n=== Animal Control Chat Interface ===")
        print("Type 'exit', 'quit', or 'bye' to end the conversation")
        print("Starting conversation...")
        
        # Try to start a conversation
        start_attempts = 0
        max_attempts = 3
        
        while start_attempts < max_attempts:
            if self.start_conversation():
                break
            
            start_attempts += 1
            if start_attempts < max_attempts:
                print(f"Retrying... (Attempt {start_attempts + 1}/{max_attempts})")
                time.sleep(2)  # Wait before retrying
        
        # If we couldn't start a conversation after max attempts, ask if user wants to continue
        if start_attempts >= max_attempts:
            print("\nCould not start a conversation after multiple attempts.")
            response = input("Do you want to continue without a conversation? (y/n): ").lower()
            if response != 'y' and response != 'yes':
                return
        
        self.running = True
        
        while self.running:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                # Check for exit commands
                if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    self.end_conversation()
                    self.running = False
                    break
                
                # Check for restart command
                if user_input.lower() in ['restart', 'reset']:
                    print("Restarting conversation...")
                    self.end_conversation()
                    if not self.start_conversation():
                        print("Failed to restart conversation. Please try again.")
                    continue
                
                # Skip empty inputs
                if not user_input:
                    continue
                
                # Send message to API
                if not self.send_message(user_input):
                    # If sending failed and we don't have a conversation ID, try to start a new one
                    if not self.conversation_id:
                        print("Trying to start a new conversation...")
                        self.start_conversation()
                
            except KeyboardInterrupt:
                print("\nInterrupted by user. Ending conversation...")
                self.end_conversation()
                self.running = False
                break
            except Exception as e:
                print(f"\nError in chat loop: {e}")
                print("Trying to recover...")
                # Don't exit, just try to continue
                if not self.conversation_id:
                    print("Trying to start a new conversation...")
                    self.start_conversation()

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_and_kill_process_on_port(port):
    """Find and kill the process using the specified port"""
    if not is_port_in_use(port):
        print(f"No process found using port {port}")
        return False
    
    # Find the process ID using the port
    if sys.platform.startswith('darwin'):  # macOS
        cmd = f"lsof -i tcp:{port} | grep LISTEN | awk '{{print $2}}'"
    elif sys.platform.startswith('linux'):  # Linux
        cmd = f"netstat -tulpn | grep :{port} | awk '{{print $7}}' | cut -d/ -f1"
    else:
        print(f"Unsupported platform: {sys.platform}")
        return False
    
    try:
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        if output:
            pid = int(output.split('\n')[0])
            print(f"Killing process {pid} using port {port}")
            os.kill(pid, signal.SIGTERM)
            
            # Wait for the port to be released
            for _ in range(5):  # Try 5 times
                time.sleep(1)
                if not is_port_in_use(port):
                    print(f"Port {port} released")
                    return True
            
            # Force kill if needed
            print(f"Force killing process {pid}")
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
            return not is_port_in_use(port)
        else:
            print(f"No process ID found for port {port}")
            return False
    except subprocess.CalledProcessError:
        print(f"Error finding process using port {port}")
        return False
    except Exception as e:
        print(f"Error killing process: {e}")
        return False

def start_api_server():
    """Start the API server"""
    print("Starting API server...")
    
    # Use Popen to start the server in the background
    process = subprocess.Popen(
        [sys.executable, API_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Wait for the server to start (look for the "Running on" message)
    server_started = False
    for line in process.stdout:
        print(line, end='')
        if "Running on" in line:
            print("API server started successfully!")
            server_started = True
            break
    
    return process

def wait_for_api_ready(timeout=30):
    """Wait for the API server to be ready"""
    print("Waiting for API server to be ready...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                print("API server is ready!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    print("Timed out waiting for API server to be ready")
    return False

def main():
    """Main function"""
    print("=== Animal Control API System Launcher ===")
    
    # Kill any existing process using the API port
    if is_port_in_use(API_PORT):
        print(f"Port {API_PORT} is in use. Attempting to kill the process...")
        if not find_and_kill_process_on_port(API_PORT):
            print(f"Failed to kill process using port {API_PORT}")
            print(f"Please manually kill the process and try again")
            sys.exit(1)
    
    # Start the API server
    api_process = start_api_server()
    
    print(f"\nAPI server starting on http://{API_HOST}:{API_PORT}")
    
    # Wait for API server to be ready
    if not wait_for_api_ready():
        print("API server failed to start properly. Exiting.")
        api_process.terminate()
        sys.exit(1)
    
    # Create and start chat client
    chat_client = ConsoleChatClient()
    
    try:
        # Run the chat loop in the main thread
        chat_client.run_chat_loop()
        
        # After chat loop ends, ask if user wants to stop the server
        response = input("\nDo you want to stop the API server too? (y/n): ").lower()
        if response == 'y' or response == 'yes':
            print("Stopping API server...")
            api_process.terminate()
            try:
                api_process.wait(timeout=3)
                print("API server stopped.")
            except subprocess.TimeoutExpired:
                print("Force killing API server...")
                api_process.kill()
                print("API server stopped.")
        else:
            print("API server continues to run in the background.")
            print(f"API is available at http://{API_HOST}:{API_PORT}")
    
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Shutting down...")
        
        # Stop the API server
        print("Stopping API server...")
        api_process.terminate()
        
        try:
            api_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            print("Force killing API server...")
            api_process.kill()
        
        print("API server stopped.")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
