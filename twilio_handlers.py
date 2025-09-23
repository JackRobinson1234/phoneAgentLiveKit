"""
Twilio webhook handlers for Animal Control API
Handles both voice and SMS interactions
"""

import os
import logging
from flask import request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

from agents.llm_animal_control_agent import LLMAnimalControlAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Twilio client
try:
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    twilio_phone_number = os.environ.get('TWILIO_PHONE_NUMBER')
    twilio_client = Client(account_sid, auth_token) if account_sid and auth_token else None
except Exception as e:
    logger.error(f"Error initializing Twilio client: {str(e)}")
    twilio_client = None

# Store active conversations by phone number
active_conversations = {}

def register_twilio_routes(app):
    """Register Twilio webhook routes with the Flask app"""
    
    @app.route('/webhook/voice', methods=['POST'])
    def voice_webhook():
        """Handle incoming voice calls"""
        try:
            # Get caller phone number
            caller_number = request.values.get('From', '')
            
            # Create TwiML response
            response = VoiceResponse()
            
            # Check if this is a new call or continuation
            if 'SpeechResult' in request.values:
                # This is a continuation with speech input
                user_input = request.values.get('SpeechResult', '')
                logger.info(f"Received speech input: {user_input}")
                
                # Process the input with our agent
                agent_response = process_voice_input(caller_number, user_input)
                
                # Speak the response and gather more input
                gather = Gather(
                    input='speech dtmf',
                    action='/webhook/voice',
                    method='POST',
                    speech_timeout='auto',
                    enhanced='true',
                    language='en-US'
                )
                gather.say(agent_response)
                response.append(gather)
                
                # If no input is received, end the call
                response.say("I didn't hear anything. Thank you for calling Animal Control Services. Goodbye!")
                response.hangup()
            else:
                # This is a new call
                logger.info(f"New call from {caller_number}")
                
                # Start a new conversation
                greeting = start_voice_conversation(caller_number)
                
                # Speak greeting and gather input
                gather = Gather(
                    input='speech dtmf',
                    action='/webhook/voice',
                    method='POST',
                    speech_timeout='auto',
                    enhanced='true',
                    language='en-US'
                )
                gather.say(greeting)
                response.append(gather)
                
                # If no input is received, end the call
                response.say("I didn't hear anything. Thank you for calling Animal Control Services. Goodbye!")
                response.hangup()
            
            return str(response)
        
        except Exception as e:
            logger.error(f"Error in voice webhook: {str(e)}")
            response = VoiceResponse()
            response.say("I'm sorry, there was an error processing your request. Please try again later.")
            response.hangup()
            return str(response)
    
    @app.route('/webhook/sms', methods=['POST'])
    def sms_webhook():
        """Handle incoming SMS messages"""
        try:
            # Get sender phone number and message body
            sender_number = request.values.get('From', '')
            message_body = request.values.get('Body', '').strip()
            
            logger.info(f"Received SMS from {sender_number}: {message_body}")
            
            # Process the message with our agent
            agent_response = process_sms_input(sender_number, message_body)
            
            # Create TwiML response
            response = MessagingResponse()
            response.message(agent_response)
            
            return str(response)
        
        except Exception as e:
            logger.error(f"Error in SMS webhook: {str(e)}")
            response = MessagingResponse()
            response.message("I'm sorry, there was an error processing your message. Please try again later.")
            return str(response)
    
    logger.info("Twilio webhook routes registered")

def start_voice_conversation(phone_number):
    """Start a new conversation for voice call"""
    try:
        # Create a new agent instance
        agent = LLMAnimalControlAgent()
        
        # Get initial greeting
        greeting = agent.start_conversation()
        
        # Store the agent instance
        active_conversations[phone_number] = agent
        
        return greeting
    except Exception as e:
        logger.error(f"Error starting voice conversation: {str(e)}")
        return "Hello! I'm the Animal Control Services assistant. How can I help you today?"

def process_voice_input(phone_number, user_input):
    """Process voice input and get response"""
    try:
        # Get the agent instance for this phone number
        agent = active_conversations.get(phone_number)
        
        # If no agent exists, create a new one
        if not agent:
            agent = LLMAnimalControlAgent()
            active_conversations[phone_number] = agent
            agent.start_conversation()
        
        # Process the message
        response = agent.process_message(user_input)
        
        return response
    except Exception as e:
        logger.error(f"Error processing voice input: {str(e)}")
        return "I'm sorry, I couldn't process that. Could you please try again?"

def process_sms_input(phone_number, message_body):
    """Process SMS input and get response"""
    try:
        # Get the agent instance for this phone number
        agent = active_conversations.get(phone_number)
        
        # If no agent exists, create a new one
        if not agent:
            agent = LLMAnimalControlAgent()
            active_conversations[phone_number] = agent
            agent.start_conversation()
        
        # Process the message
        response = agent.process_message(message_body)
        
        return response
    except Exception as e:
        logger.error(f"Error processing SMS input: {str(e)}")
        return "I'm sorry, I couldn't process that. Could you please try again?"

def end_conversation(phone_number):
    """End a conversation and clean up"""
    if phone_number in active_conversations:
        del active_conversations[phone_number]
