#!/usr/bin/env python3
"""
API for Animal Control Agent
Provides endpoints for conversation management
"""

import os
import uuid
import logging
import re
from datetime import datetime
from typing import Dict
from flask import Flask, request, jsonify
from flask_cors import CORS

from agents.llm_animal_control_agent import LLMAnimalControlAgent
from config import API_HOST, API_PORT, DEBUG_MODE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store active conversations in memory (in production, use Redis/database)
active_conversations: Dict[str, LLMAnimalControlAgent] = {}

def clean_agent_response(response: str) -> str:
    """Clean the agent response to remove system outputs and emojis"""
    # If empty response, return empty string
    if not response or not response.strip():
        return ""
    
    # Check for special patterns in the initial greeting
    if "ANIMAL CONTROL AGENT" in response and "Welcome!" in response:
        # Extract just the relevant part from the initial greeting
        match = re.search(r'\{\s*"tool":\s*"generate_response".*?"response":\s*"(.*?)"', response, re.DOTALL)
        if match:
            # Extract the actual response from the JSON
            extracted = match.group(1)
            # Unescape any escaped characters
            extracted = extracted.replace('\\n', '\n').replace('\\"', '"')
            return extracted.strip()
    
    # If the response contains the robot emoji, extract only the user-facing part
    if '🤖' in response:
        # Find the last occurrence of the robot emoji
        last_robot_index = response.rfind('🤖')
        if last_robot_index != -1:
            # Take everything after the last robot emoji
            response = response[last_robot_index + 1:].strip()
    
    # Remove any lines with system debug info
    debug_prefixes = ['🔧', '🔄', '👤']
    lines = []
    for line in response.split('\n'):
        # Skip lines that start with debug prefixes
        if any(line.strip().startswith(prefix) for prefix in debug_prefixes):
            continue
        # Skip lines that contain specific debug patterns
        if any(pattern in line for pattern in ['CONTEXT DEBUG', 'SYSTEM:', 'STATE TRANSITION']):
            continue
        lines.append(line)
    
    response = '\n'.join(lines)
    
    # Remove specific phrases
    phrases_to_remove = [
        '*Enhanced with AI-powered understanding*',
        'You are now in the GREETING state',
        'I\'ll generate an appropriate greeting',
        'Let me use generate_response',
        'Using analyze_request',
    ]
    for phrase in phrases_to_remove:
        response = response.replace(phrase, '')
    
    # Remove JSON-like content
    response = re.sub(r'\{\s*"tool".*?\}', '', response, flags=re.DOTALL)
    
    # Remove any other emojis
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F700-\U0001F77F"  # alchemical symbols
                               u"\U0001F780-\U0001F7FF"  # Geometric Shapes
                               u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                               u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                               u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                               u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                               u"\U00002702-\U000027B0"  # Dingbats
                               u"\U000024C2-\U0001F251" 
                               "]+", flags=re.UNICODE)
    response = emoji_pattern.sub(r'', response)
    
    # Clean up multiple newlines and spaces
    response = re.sub(r'\n\s*\n', '\n\n', response)
    response = re.sub(r' +', ' ', response)
    
    return response.strip()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'animal-control-api',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/conversations', methods=['POST'])
def start_conversation():
    """
    Start a new conversation with the animal control agent
    
    Returns:
        JSON with conversation_id and initial message
    """
    try:
        # Create new conversation
        conversation_id = str(uuid.uuid4())
        agent = LLMAnimalControlAgent()
        
        # Get initial greeting
        initial_message = agent.start_conversation()
        
        # Clean the response
        clean_message = clean_agent_response(initial_message)
        
        # Store the agent instance
        active_conversations[conversation_id] = agent
        
        # Return conversation details
        return jsonify({
            'conversation_id': conversation_id,
            'message': clean_message,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return jsonify({
            'error': 'Failed to start conversation',
            'details': str(e)
        }), 500

@app.route('/conversations/<conversation_id>/messages', methods=['POST'])
def send_message(conversation_id):
    """
    Send a message to an existing conversation
    
    Args:
        conversation_id: ID of the conversation
        
    Returns:
        JSON with agent's response
    """
    try:
        # Check if conversation exists
        if conversation_id not in active_conversations:
            return jsonify({
                'error': 'Conversation not found'
            }), 404
        
        # Get message from request
        data = request.json
        if not data or 'message' not in data:
            return jsonify({
                'error': 'No message provided'
            }), 400
        
        user_message = data['message']
        
        # Get agent instance
        agent = active_conversations[conversation_id]
        
        # Process message
        response = agent.process_message(user_message)
        
        # Clean the response
        clean_message = clean_agent_response(response)
        
        # Return response
        return jsonify({
            'conversation_id': conversation_id,
            'message': clean_message,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({
            'error': 'Failed to process message',
            'details': str(e)
        }), 500

@app.route('/conversations/<conversation_id>', methods=['DELETE'])
def end_conversation(conversation_id):
    """
    End a conversation
    
    Args:
        conversation_id: ID of the conversation
        
    Returns:
        JSON with success message
    """
    try:
        # Check if conversation exists
        if conversation_id not in active_conversations:
            return jsonify({
                'error': 'Conversation not found'
            }), 404
        
        # Get agent instance
        agent = active_conversations[conversation_id]
        
        # End conversation
        end_message = agent.end_conversation()
        
        # Clean the response
        clean_message = clean_agent_response(end_message)
        
        # Remove from active conversations
        del active_conversations[conversation_id]
        
        # Return success
        return jsonify({
            'conversation_id': conversation_id,
            'message': clean_message,
            'status': 'ended',
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error ending conversation: {str(e)}")
        return jsonify({
            'error': 'Failed to end conversation',
            'details': str(e)
        }), 500

@app.route('/conversations/<conversation_id>/status', methods=['GET'])
def get_conversation_status(conversation_id):
    """
    Get status of a conversation
    
    Args:
        conversation_id: ID of the conversation
        
    Returns:
        JSON with conversation status
    """
    try:
        # Check if conversation exists
        if conversation_id not in active_conversations:
            return jsonify({
                'error': 'Conversation not found'
            }), 404
        
        # Get agent instance
        agent = active_conversations[conversation_id]
        
        # Get status
        status = agent.get_conversation_status()
        
        # Return status
        return jsonify({
            'conversation_id': conversation_id,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting conversation status: {str(e)}")
        return jsonify({
            'error': 'Failed to get conversation status',
            'details': str(e)
        }), 500

if __name__ == '__main__':
    # Use configuration variables
    app.run(host=API_HOST, port=API_PORT, debug=DEBUG_MODE)
