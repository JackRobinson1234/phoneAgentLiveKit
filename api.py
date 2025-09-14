#!/usr/bin/env python3
"""
REST API for the Health Agent
Provides HTTP endpoints for scheduling doctor appointments
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import logging
from typing import Dict, Any
from datetime import datetime

from agents.llm_health_agent import LLMHealthAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store active conversations in memory (in production, use Redis/database)
active_conversations: Dict[str, LLMHealthAgent] = {}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'health-agent-api',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/conversations', methods=['POST'])
def start_conversation():
    """
    Start a new conversation with the health agent
    
    Returns:
        JSON with conversation_id and initial message
    """
    try:
        # Create new conversation
        conversation_id = str(uuid.uuid4())
        agent = LLMHealthAgent()
        
        # Start the conversation
        initial_message = agent.start_conversation()
        
        # Store the agent instance
        active_conversations[conversation_id] = agent
        
        logger.info(f"Started new conversation: {conversation_id}")
        
        return jsonify({
            'conversation_id': conversation_id,
            'message': initial_message,
            'status': 'started'
        }), 201
        
    except Exception as e:
        logger.error(f"Error starting conversation: {str(e)}")
        return jsonify({
            'error': 'Failed to start conversation',
            'details': str(e)
        }), 500

@app.route('/conversations/<conversation_id>/messages', methods=['POST'])
def send_message(conversation_id: str):
    """
    Send a message to an existing conversation
    
    Request body:
        {
            "message": "user message text"
        }
    
    Returns:
        JSON with agent response
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Check if conversation exists
        if conversation_id not in active_conversations:
            return jsonify({'error': 'Conversation not found'}), 404
        
        agent = active_conversations[conversation_id]
        
        # Process the message
        response = agent.process_message(user_message)
        
        # Get current state for debugging
        current_state = agent.state_machine.get_current_state_name()
        context = agent.state_machine.get_context()
        
        logger.info(f"Processed message in conversation {conversation_id}, state: {current_state}")
        
        return jsonify({
            'conversation_id': conversation_id,
            'message': response,
            'current_state': current_state,
            'context': {
                'patient_name': context.get('patient_name'),
                'specialty': context.get('specialty'),
                'appointment_type': context.get('suggested_appointment_type'),
                'turn_count': context.get('turn_count', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing message in conversation {conversation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to process message',
            'details': str(e)
        }), 500

@app.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation_status(conversation_id: str):
    """
    Get the current status of a conversation
    
    Returns:
        JSON with conversation details
    """
    try:
        if conversation_id not in active_conversations:
            return jsonify({'error': 'Conversation not found'}), 404
        
        agent = active_conversations[conversation_id]
        current_state = agent.state_machine.get_current_state_name()
        context = agent.state_machine.get_context()
        
        return jsonify({
            'conversation_id': conversation_id,
            'current_state': current_state,
            'is_complete': agent.state_machine.is_complete,
            'context': {
                'patient_name': context.get('patient_name'),
                'patient_contact': context.get('patient_contact'),
                'specialty': context.get('specialty'),
                'appointment_type': context.get('suggested_appointment_type'),
                'suggested_doctor': context.get('suggested_doctor'),
                'turn_count': context.get('turn_count', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation status {conversation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to get conversation status',
            'details': str(e)
        }), 500

@app.route('/conversations/<conversation_id>', methods=['DELETE'])
def end_conversation(conversation_id: str):
    """
    End and cleanup a conversation
    
    Returns:
        JSON confirmation
    """
    try:
        if conversation_id not in active_conversations:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Remove the conversation
        del active_conversations[conversation_id]
        
        logger.info(f"Ended conversation: {conversation_id}")
        
        return jsonify({
            'conversation_id': conversation_id,
            'status': 'ended'
        })
        
    except Exception as e:
        logger.error(f"Error ending conversation {conversation_id}: {str(e)}")
        return jsonify({
            'error': 'Failed to end conversation',
            'details': str(e)
        }), 500

@app.route('/conversations', methods=['GET'])
def list_conversations():
    """
    List all active conversations
    
    Returns:
        JSON with list of conversation IDs and their states
    """
    try:
        conversations = []
        for conv_id, agent in active_conversations.items():
            conversations.append({
                'conversation_id': conv_id,
                'current_state': agent.state_machine.get_current_state_name(),
                'is_complete': agent.state_machine.is_complete,
                'turn_count': agent.state_machine.get_context().get('turn_count', 0)
            })
        
        return jsonify({
            'active_conversations': len(conversations),
            'conversations': conversations
        })
        
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        return jsonify({
            'error': 'Failed to list conversations',
            'details': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🏥 Health Agent API Server")
    print("=" * 50)
    print("Available endpoints:")
    print("  POST /conversations - Start new conversation")
    print("  POST /conversations/<id>/messages - Send message")
    print("  GET  /conversations/<id> - Get conversation status")
    print("  GET  /conversations - List all conversations")
    print("  DELETE /conversations/<id> - End conversation")
    print("  GET  /health - Health check")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
