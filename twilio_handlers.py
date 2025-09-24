"""
Twilio webhook handlers for Animal Control API
Handles both voice and SMS interactions
"""

import os
import logging
import datetime
from flask import request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

from agents.llm_animal_control_agent import LLMAnimalControlAgent
from twilio_config import DEFAULT_GATHER_PARAMS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Debug function to print actions with timestamps
def debug_print(action, details=None):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    if details:
        logger.info(f"[{timestamp}] {action}: {details}")
    else:
        logger.info(f"[{timestamp}] {action}")

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
    
    # Define the base URL for webhooks
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    webhook_base = f"{base_url}/webhook"
    
    @app.route('/webhook/voice/timeout', methods=['POST', 'GET'])
    def voice_timeout_handler():
        """Handle timeouts when user doesn't respond"""
        try:
            # Get caller phone number
            caller_number = request.values.get('From', '')
            call_sid = request.values.get('CallSid', '')
            
            debug_print("TIMEOUT DETECTED", f"Caller: {caller_number}, Call SID: {call_sid}")
            
            # Create TwiML response
            response = VoiceResponse()
            
            # Check if this is the first timeout or a repeated one
            timeout_count = active_conversations.get(caller_number, {}).get('timeout_count', 0)
            active_conversations.setdefault(caller_number, {})['timeout_count'] = timeout_count + 1
            
            # If this is the first or second timeout, check if they're still there
            if timeout_count < 2:
                debug_print("CHECKING USER PRESENCE", f"Timeout count: {timeout_count + 1}")
                
                # Ask if they're still there and gather input
                gather = Gather(
                    input='speech dtmf',
                    action='/webhook/voice',
                    method='POST',
                    language='en-US',
                    # Note: timeout_url is not supported by Twilio Gather
                    **DEFAULT_GATHER_PARAMS
                )
                
                # Use a different message based on timeout count
                if timeout_count == 0:
                    gather.say("<speak><prosody rate='fast'>Are you still there? I didn't hear anything.</prosody></speak>", voice='Polly.Matthew')
                else:
                    gather.say("<speak><prosody rate='fast'>I still don't hear a response. Please say something if you're still on the line.</prosody></speak>", voice='Polly.Matthew')
                
                response.append(gather)
            else:
                # After multiple timeouts, assume user is gone and hang up
                debug_print("MULTIPLE TIMEOUTS", f"Hanging up after {timeout_count + 1} timeouts")
                response.say("<speak><prosody rate='fast'>I haven't heard from you for a while. Please call back when you're ready to continue. Goodbye.</prosody></speak>", voice='Polly.Matthew')
                response.hangup()
                
                # Clean up the session
                if caller_number in active_conversations:
                    del active_conversations[caller_number]
            
            return str(response)
            
        except Exception as e:
            logger.error(f"Error in timeout handler: {str(e)}")
            response = VoiceResponse()
            response.say("<speak><prosody rate='fast'>I'm sorry, there was an error. Please call back later.</prosody></speak>", voice='Polly.Matthew')
            response.hangup()
            return str(response)
    
    @app.route('/webhook/voice', methods=['POST'])
    def voice_webhook():
        """Handle incoming voice calls"""
        try:
            # Get caller phone number
            caller_number = request.values.get('From', '')
            call_sid = request.values.get('CallSid', '')
            
            debug_print("VOICE WEBHOOK", f"Call SID: {call_sid}, Caller: {caller_number}")
            
            # Create TwiML response
            response = VoiceResponse()
            
            # Check if this is a new call or continuation
            if 'SpeechResult' in request.values:
                # This is a continuation with speech input
                user_input = request.values.get('SpeechResult', '')
                debug_print("SPEECH INPUT", f"Caller: {caller_number}, Input: '{user_input}'")
                
                # Check for empty or very short input that might indicate recognition failure
                if not user_input or len(user_input.strip()) < 2:
                    debug_print("SPEECH RECOGNITION FAILURE", f"Caller: {caller_number}")
                    # Handle speech recognition failure
                    response.say("<speak><prosody rate='fast'>I didn't quite catch that. Could you please repeat?</prosody></speak>", voice='Polly.Matthew')
                    
                    # Add a new Gather to try again
                    gather = Gather(
                        input='speech dtmf',
                        action='/webhook/voice',
                        method='POST',
                        language='en-US',
                        # Note: timeout_url is not supported by Twilio Gather
                        hints='stray dog, stray cat, animal control, wildlife, raccoon, skunk, possum, coyote, report, emergency, surrender pet, adoption',
                        **DEFAULT_GATHER_PARAMS
                    )
                    gather.say("<speak><prosody rate='fast'>Please tell me how I can help you with animal control services.</prosody></speak>", voice='Polly.Matthew')
                    response.append(gather)
                    return str(response)
                
                debug_print("PROCESSING VOICE INPUT", f"Caller: {caller_number}")
                # Process the input with our agent
                agent_response = process_voice_input(caller_number, user_input)
                debug_print("AGENT RESPONSE", f"Length: {len(agent_response)} chars")
                
                # Speak the response and gather more input
                gather = Gather(
                    input='speech dtmf',
                    action='/webhook/voice',
                    method='POST',
                    language='en-US',
                    # Note: timeout_url is not supported by Twilio Gather
                    hints='stray dog, stray cat, animal control, wildlife, raccoon, skunk, possum, coyote, report, emergency, surrender pet, adoption',
                    **DEFAULT_GATHER_PARAMS
                )
                # Add voice speed control with SSML
                gather.say(f"<speak><prosody rate='fast'>{agent_response}</prosody></speak>", voice='Polly.Matthew')
                response.append(gather)
                
                # Only if Gather times out (user doesn't say anything), this will execute
                # The timeout parameter above ensures we wait 10 seconds for input
            else:
                # This is a new call
                debug_print("NEW CALL", f"Caller: {caller_number}, Call SID: {call_sid}")
                
                debug_print("STARTING CONVERSATION", f"Caller: {caller_number}")
                # Start a new conversation
                greeting = start_voice_conversation(caller_number)
                debug_print("GREETING GENERATED", f"Length: {len(greeting)} chars")
                
                # Speak greeting and gather input
                gather = Gather(
                    input='speech dtmf',
                    action='/webhook/voice',
                    method='POST',
                    language='en-US',
                    # Note: timeout_url is not supported by Twilio Gather
                    hints='stray dog, stray cat, animal control, wildlife, raccoon, skunk, possum, coyote, report, emergency, surrender pet, adoption',
                    **DEFAULT_GATHER_PARAMS
                )
                # Add voice speed control with SSML
                gather.say(f"<speak><prosody rate='fast'>{greeting}</prosody></speak>", voice='Polly.Matthew')
                response.append(gather)
                
                # Only if Gather times out (user doesn't say anything), this will execute
                # The timeout parameter above ensures we wait 10 seconds for input
            
            return str(response)
        
        except Exception as e:
            logger.error(f"Error in voice webhook: {str(e)}")
            response = VoiceResponse()
            
            # Create a more helpful error message with SSML for better voice quality
            error_message = "<speak><prosody rate='fast'>I'm having trouble understanding that. Could you please try again or call back later if the problem continues?</prosody></speak>"
            
            # Add a Gather to allow the user to try again immediately
            gather = Gather(
                input='speech dtmf',
                action='/webhook/voice',
                method='POST',
                language='en-US',
                # Note: timeout_url is not supported by Twilio Gather
                **DEFAULT_GATHER_PARAMS
            )
            gather.say(error_message, voice='Polly.Matthew')
            response.append(gather)
            
            # Only hang up if the user doesn't respond to the gather
            return str(response)
    
    @app.route('/webhook/sms', methods=['POST'])
    def sms_webhook():
        """Handle incoming SMS messages"""
        try:
            # Get sender phone number and message body
            sender_number = request.values.get('From', '')
            message_body = request.values.get('Body', '').strip()
            
            debug_print("SMS RECEIVED", f"From: {sender_number}, Message: '{message_body}'")
            
            debug_print("PROCESSING SMS", f"From: {sender_number}")
            # Process the message with our agent
            agent_response = process_sms_input(sender_number, message_body)
            debug_print("SMS RESPONSE GENERATED", f"Length: {len(agent_response)} chars")
            
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
        debug_print("CREATING AGENT", f"For caller: {phone_number}")
        # Create a new agent instance
        agent = LLMAnimalControlAgent()
        
        debug_print("STARTING AGENT CONVERSATION", f"For caller: {phone_number}")
        # Get initial greeting
        greeting = agent.start_conversation()
        
        debug_print("STORING AGENT", f"For caller: {phone_number}")
        # Store the agent instance
        active_conversations[phone_number] = agent
        
        return greeting
    except Exception as e:
        logger.error(f"Error starting voice conversation: {str(e)}")
        return "Hello! I'm the Animal Control Services assistant. How can I help you today?"

def process_voice_input(phone_number, user_input):
    """Process voice input and get response"""
    try:
        debug_print("RETRIEVING AGENT", f"For caller: {phone_number}")
        # Get the agent instance for this phone number
        agent = active_conversations.get(phone_number)
        
        # If no agent exists, create a new one
        if not agent:
            debug_print("NO AGENT FOUND", f"Creating new agent for caller: {phone_number}")
            agent = LLMAnimalControlAgent()
            active_conversations[phone_number] = agent
            agent.start_conversation()
        
        debug_print("AGENT PROCESSING MESSAGE", f"Input length: {len(user_input)} chars")
        # Process the message
        response = agent.process_message(user_input)
        debug_print("AGENT PROCESSED MESSAGE", f"Response length: {len(response)} chars")
        
        return response
    except Exception as e:
        logger.error(f"Error processing voice input: {str(e)}")
        return "I'm sorry, I couldn't process that. Could you please try again?"

def process_sms_input(phone_number, message_body):
    """Process SMS input and get response"""
    try:
        debug_print("RETRIEVING AGENT FOR SMS", f"From: {phone_number}")
        # Get the agent instance for this phone number
        agent = active_conversations.get(phone_number)
        
        # If no agent exists, create a new one
        if not agent:
            debug_print("NO SMS AGENT FOUND", f"Creating new agent for sender: {phone_number}")
            agent = LLMAnimalControlAgent()
            active_conversations[phone_number] = agent
            agent.start_conversation()
        
        debug_print("AGENT PROCESSING SMS", f"Message length: {len(message_body)} chars")
        # Process the message
        response = agent.process_message(message_body)
        debug_print("AGENT PROCESSED SMS", f"Response length: {len(response)} chars")
        
        return response
    except Exception as e:
        logger.error(f"Error processing SMS input: {str(e)}")
        return "I'm sorry, I couldn't process that. Could you please try again?"

def end_conversation(phone_number):
    """End a conversation and clean up"""
    if phone_number in active_conversations:
        debug_print("ENDING CONVERSATION", f"For: {phone_number}")
        del active_conversations[phone_number]
        debug_print("CONVERSATION ENDED", f"For: {phone_number}")
    else:
        debug_print("END CONVERSATION FAILED", f"No active conversation for: {phone_number}")
