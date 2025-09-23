#!/usr/bin/env python3
"""
Animal Control Voice System Launcher
Kills any existing API server processes and starts both the API server and voice agent
Supports both local and Railway deployments
"""

import os
import sys
import signal
import subprocess
import time
import socket

# Import dotenv for environment variables
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_PORT = int(os.environ.get("PORT", 5001))
API_SCRIPT = "animal_control_api.py"
VOICE_SCRIPT = "api_voice_agent.py"
API_STARTUP_WAIT = 3  # seconds to wait for API to fully initialize
RAILWAY_URL = os.environ.get('RAILWAY_URL', '')
USE_REMOTE_API = os.environ.get('USE_REMOTE_API', 'False').lower() == 'true'

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
    
    # Additional wait to ensure the server is fully initialized
    if server_started:
        print(f"Waiting {API_STARTUP_WAIT} seconds for API server to fully initialize...")
        time.sleep(API_STARTUP_WAIT)
    
    return process

def start_voice_agent():
    """Start the voice agent"""
    print("\nStarting voice agent...")
    
    # Use Popen to start the voice agent in the foreground
    process = subprocess.Popen(
        [sys.executable, VOICE_SCRIPT],
        # No stdout/stderr redirection so user can interact directly
    )
    
    print("Voice agent started. You can now interact with it.")
    return process

def main():
    """Main function"""
    print("=== Animal Control Voice System Launcher ===")
    
    api_process = None
    
    # Check if we should use a remote API (Railway deployment)
    if USE_REMOTE_API and RAILWAY_URL:
        print(f"Using remote API at: {RAILWAY_URL}")
    else:
        # Kill any existing process using the API port
        if is_port_in_use(API_PORT):
            print(f"Port {API_PORT} is in use. Attempting to kill the process...")
            if not find_and_kill_process_on_port(API_PORT):
                print(f"Failed to kill process using port {API_PORT}")
                print(f"Please manually kill the process and try again")
                sys.exit(1)
        
        # Start the local API server
        api_process = start_api_server()
    
    # Start the voice agent
    voice_process = start_voice_agent()
    
    if api_process:
        print("\nBoth API server and voice agent are now running.")
        print("You can interact with the voice agent in this terminal.")
        print("The API server is running in the background.")
    else:
        print("\nVoice agent is now running, connected to the remote API.")
        print("You can interact with the voice agent in this terminal.")
    
    try:
        # Wait for the voice agent to exit
        voice_process.wait()
        
        print("\nVoice agent has exited.")
        
        # Only ask about stopping API if we started a local one
        if api_process:
            # Ask if user wants to kill the API server too
            response = input("Do you want to stop the API server too? (y/n): ").lower()
            if response == 'y' or response == 'yes':
                print("Stopping API server...")
                api_process.terminate()
                api_process.wait(timeout=5)
                print("API server stopped.")
            else:
                print("API server continues to run in the background.")
            
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Shutting down...")
        
        # Stop the voice agent
        print("Stopping voice agent...")
        voice_process.terminate()
        
        # Only stop the API if we started a local one
        if api_process:
            print("Stopping API server...")
            api_process.terminate()
            
            try:
                voice_process.wait(timeout=3)
                api_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print("Force killing processes...")
                voice_process.kill()
                api_process.kill()
            
            print("All processes stopped.")
        else:
            try:
                voice_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print("Force killing voice agent...")
                voice_process.kill()
            
            print("Voice agent stopped.")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
