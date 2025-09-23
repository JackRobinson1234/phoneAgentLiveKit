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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create a separate debug logger for detailed Twilio interactions
debug_logger = logging.getLogger('twilio_debug')
debug_logger.setLevel(logging.DEBUG)

# Create file handler for debug logs
debug_file_handler = logging.FileHandler('twilio_debug.log')
debug_file_handler.setLevel(logging.DEBUG)
debug_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
debug_logger.addHandler(debug_file_handler)

# Also add console handler for immediate visibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('🔍 TWILIO DEBUG: %(message)s'))
debug_logger.addHandler(console_handler)

def debug_log(message, category="INFO"):
    """Helper function to log debug messages with timestamps and categories"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    formatted_message = f"[{timestamp}] [{category}] {message}"
    debug_logger.debug(formatted_message)

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
            # Get caller phone number and call SID
            caller_number = request.values.get('From', '')
            call_sid = request.values.get('CallSid', '')
            
            # Log all request parameters for debugging
            debug_log(f"Voice webhook called with SID: {call_sid}", "CALL_START")
            debug_log(f"Caller: {caller_number}", "CALLER_INFO")
            debug_log(f"All request parameters: {dict(request.values)}", "REQUEST_PARAMS")
            
            # Create TwiML response
            response = VoiceResponse()
            
            # Check if this is a new call or continuation
            if 'SpeechResult' in request.values:
                # This is a continuation with speech input
                user_input = request.values.get('SpeechResult', '')
                confidence = request.values.get('Confidence', 'unknown')
                debug_log(f"USER SAID: '{user_input}' (confidence: {confidence})", "USER_INPUT")
                logger.info(f"Received speech input: {user_input}")
                
                # Check for empty or very short input that might indicate recognition failure
                if not user_input or len(user_input.strip()) < 2:
                    # Handle speech recognition failure
                    debug_log(f"Speech recognition failed or too short: '{user_input}'", "RECOGNITION_FAILURE")
                    response.say("<speak><prosody rate='fast'>I didn't quite catch that. Could you please repeat?</prosody></speak>", voice='Polly.Matthew')
                    
                    # Add a new Gather to try again
                    gather = Gather(
                        input='speech dtmf',
                        action='/webhook/voice',
                        method='POST',
                        speech_timeout='auto',
                        enhanced=True,
                        language='en-US',
                        timeout=10,
                        bargeIn=True,
                        speechModel='phone_call',
                        hints='stray dog, stray cat, animal control, wildlife, raccoon, skunk, possum, coyote, report, emergency, surrender pet, adoption'
                    )
                    gather.say("<speak><prosody rate='fast'>Please tell me how I can help you with animal control services.</prosody></speak>", voice='Polly.Matthew')
                    response.append(gather)
                    debug_log("Asking user to repeat due to recognition failure", "SYSTEM_ACTION")
                    return str(response)
                
                # Process the input with our agent
                debug_log(f"Processing voice input: '{user_input}'", "PROCESSING_START")
                start_time = datetime.datetime.now()
                agent_response = process_voice_input(caller_number, user_input)
                processing_time = (datetime.datetime.now() - start_time).total_seconds()
                debug_log(f"Processing completed in {processing_time:.2f} seconds", "PROCESSING_END")
                debug_log(f"SYSTEM RESPONSE: '{agent_response}'", "SYSTEM_RESPONSE")
                
                # Speak the response and gather more input
                gather = Gather(
                    input='speech dtmf',
                    action='/webhook/voice',
                    method='POST',
                    speech_timeout='auto',
                    enhanced=True,
                    language='en-US',
                    timeout=10,
                    bargeIn=True,  # Allow user to interrupt the voice
                    speechModel='phone_call',  # Optimized for phone conversations
                    profanityFilter=False,  # Allow natural speech including potential profanity
                    hints='stray dog, stray cat, animal control, wildlife, raccoon, skunk, possum, coyote, report, emergency, surrender pet, adoption'
                )
                # Add voice speed control with SSML
                gather.say(f"<speak><prosody rate='fast'>{agent_response}</prosody></speak>", voice='Polly.Matthew')
                response.append(gather)
                debug_log("Gathering next user input", "SYSTEM_ACTION")
                
                # Only if Gather times out (user doesn't say anything), this will execute
                # The timeout parameter above ensures we wait 10 seconds for input
            else:
                # This is a new call
                debug_log(f"New call initiated from {caller_number}", "NEW_CALL")
                logger.info(f"New call from {caller_number}")
                
                # Start a new conversation
                debug_log("Starting new conversation", "CONVERSATION_START")
                start_time = datetime.datetime.now()
                greeting = start_voice_conversation(caller_number)
                processing_time = (datetime.datetime.now() - start_time).total_seconds()
                debug_log(f"Conversation started in {processing_time:.2f} seconds", "PROCESSING_TIME")
                debug_log(f"Initial greeting: '{greeting}'", "SYSTEM_GREETING")
                
                # Speak greeting and gather input
                gather = Gather(
                    input='speech dtmf',
                    action='/webhook/voice',
                    method='POST',
                    speech_timeout='auto',
                    enhanced=True,
                    language='en-US',
                    timeout=10,
                    bargeIn=True,  # Allow user to interrupt the voice
                    speechModel='phone_call',  # Optimized for phone conversations
                    profanityFilter=False,  # Allow natural speech including potential profanity
                    hints='stray dog, stray cat, animal control, wildlife, raccoon, skunk, possum, coyote, report, emergency, surrender pet, adoption'
                )
                # Add voice speed control with SSML
                gather.say(f"<speak><prosody rate='fast'>{greeting}</prosody></speak>", voice='Polly.Matthew')
                response.append(gather)
                debug_log("Waiting for initial user input", "SYSTEM_ACTION")
                
                # Only if Gather times out (user doesn't say anything), this will execute
                # The timeout parameter above ensures we wait 10 seconds for input
            
            debug_log("Returning TwiML response", "RESPONSE_SENT")
            return str(response)
        
        except Exception as e:
            logger.error(f"Error in voice webhook: {str(e)}")
            debug_log(f"ERROR in voice webhook: {str(e)}", "ERROR")
            debug_log(f"Error traceback: {e.__traceback__}", "ERROR_DETAILS")
            response = VoiceResponse()
            
            # Create a more helpful error message with SSML for better voice quality
            error_message = "<speak><prosody rate='fast'>I'm having trouble understanding that. Could you please try again or call back later if the problem continues?</prosody></speak>"
            debug_log("Sending error message to user", "ERROR_RECOVERY")
            
            # Add a Gather to allow the user to try again immediately
            gather = Gather(
                input='speech dtmf',
                action='/webhook/voice',
                method='POST',
                speech_timeout='auto',
                enhanced=True,
                language='en-US',
                timeout=10,
                bargeIn=True,
                speechModel='phone_call'
            )
            gather.say(error_message, voice='Polly.Matthew')
            response.append(gather)
            debug_log("Attempting to recover from error", "ERROR_RECOVERY")
            
            # Only hang up if the user doesn't respond to the gather
            return str(response)
    
    @app.route('/webhook/sms', methods=['POST'])
    def sms_webhook():
        """Handle incoming SMS messages"""
        try:
            # Get sender phone number and message body
            sender_number = request.values.get('From', '')
            message_body = request.values.get('Body', '').strip()
            message_sid = request.values.get('MessageSid', '')
            
            # Log all request parameters for debugging
            debug_log(f"SMS webhook called with SID: {message_sid}", "SMS_RECEIVED")
            debug_log(f"Sender: {sender_number}", "SENDER_INFO")
            debug_log(f"All request parameters: {dict(request.values)}", "REQUEST_PARAMS")
            debug_log(f"USER SMS: '{message_body}'", "USER_MESSAGE")
            
            logger.info(f"Received SMS from {sender_number}: {message_body}")
            
            # Process the message with our agent
            debug_log(f"Processing SMS: '{message_body}'", "PROCESSING_START")
            start_time = datetime.datetime.now()
            agent_response = process_sms_input(sender_number, message_body)
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            debug_log(f"Processing completed in {processing_time:.2f} seconds", "PROCESSING_END")
            debug_log(f"SYSTEM RESPONSE: '{agent_response}'", "SYSTEM_RESPONSE")
            
            # Create TwiML response
            response = MessagingResponse()
            response.message(agent_response)
            debug_log("Sending SMS response", "RESPONSE_SENT")
            
            return str(response)
        
        except Exception as e:
            logger.error(f"Error in SMS webhook: {str(e)}")
            debug_log(f"ERROR in SMS webhook: {str(e)}", "ERROR")
            debug_log(f"Error traceback: {e.__traceback__}", "ERROR_DETAILS")
            response = MessagingResponse()
            response.message("I'm sorry, there was an error processing your message. Please try again later.")
            debug_log("Sending error message to user", "ERROR_RECOVERY")
            return str(response)
    
    logger.info("Twilio webhook routes registered")

def start_voice_conversation(phone_number):
    """Start a new conversation for voice call"""
    try:
        debug_log(f"Creating new agent for {phone_number}", "AGENT_CREATION")
        start_time = datetime.datetime.now()
        
        # Create a new agent instance
        agent = LLMAnimalControlAgent()
        
        # Get initial greeting
        debug_log("Getting initial greeting", "CONVERSATION_INIT")
        greeting = agent.start_conversation()
        
        # Store the agent instance
        active_conversations[phone_number] = agent
        debug_log(f"Agent created and stored for {phone_number}", "AGENT_READY")
        
        processing_time = (datetime.datetime.now() - start_time).total_seconds()
        debug_log(f"Conversation initialization took {processing_time:.2f} seconds", "TIMING")
        
        return greeting
    except Exception as e:
        logger.error(f"Error starting voice conversation: {str(e)}")
        debug_log(f"ERROR starting conversation: {str(e)}", "ERROR")
        debug_log(f"Error traceback: {e.__traceback__}", "ERROR_DETAILS")
        return "Hello! I'm the Animal Control Services assistant. How can I help you today?"

def process_voice_input(phone_number, user_input):
    """Process voice input and get response"""
    try:
        debug_log(f"Processing voice input for {phone_number}: '{user_input}'", "VOICE_PROCESSING")
        
        # Get the agent instance for this phone number
        agent = active_conversations.get(phone_number)
        
        # If no agent exists, create a new one
        if not agent:
            debug_log(f"No existing agent found for {phone_number}, creating new one", "AGENT_CREATION")
            agent = LLMAnimalControlAgent()
            active_conversations[phone_number] = agent
            agent.start_conversation()
            debug_log("New conversation started for existing call", "CONVERSATION_RESTART")
        else:
            debug_log("Using existing agent for conversation", "AGENT_REUSE")
        
        # Process the message
        debug_log("Sending input to agent for processing", "AGENT_PROCESSING")
        start_time = datetime.datetime.now()
        response = agent.process_message(user_input)
        processing_time = (datetime.datetime.now() - start_time).total_seconds()
        debug_log(f"Agent processing took {processing_time:.2f} seconds", "TIMING")
        debug_log(f"Agent response: '{response}'", "AGENT_RESPONSE")
        
        return response
    except Exception as e:
        logger.error(f"Error processing voice input: {str(e)}")
        debug_log(f"ERROR processing voice input: {str(e)}", "ERROR")
        debug_log(f"Error traceback: {e.__traceback__}", "ERROR_DETAILS")
        return "I'm sorry, I couldn't process that. Could you please try again?"

def process_sms_input(phone_number, message_body):
    """Process SMS input and get response"""
    try:
        debug_log(f"Processing SMS input for {phone_number}: '{message_body}'", "SMS_PROCESSING")
        
        # Get the agent instance for this phone number
        agent = active_conversations.get(phone_number)
        
        # If no agent exists, create a new one
        if not agent:
            debug_log(f"No existing agent found for {phone_number}, creating new one", "AGENT_CREATION")
            agent = LLMAnimalControlAgent()
            active_conversations[phone_number] = agent
            agent.start_conversation()
            debug_log("New conversation started for SMS", "CONVERSATION_START")
        else:
            debug_log("Using existing agent for SMS conversation", "AGENT_REUSE")
        
        # Process the message
        debug_log("Sending SMS to agent for processing", "AGENT_PROCESSING")
        start_time = datetime.datetime.now()
        response = agent.process_message(message_body)
        processing_time = (datetime.datetime.now() - start_time).total_seconds()
        debug_log(f"Agent processing took {processing_time:.2f} seconds", "TIMING")
        debug_log(f"Agent response: '{response}'", "AGENT_RESPONSE")
        
        return response
    except Exception as e:
        logger.error(f"Error processing SMS input: {str(e)}")
        debug_log(f"ERROR processing SMS input: {str(e)}", "ERROR")
        debug_log(f"Error traceback: {e.__traceback__}", "ERROR_DETAILS")
        return "I'm sorry, I couldn't process that. Could you please try again?"

def end_conversation(phone_number):
    """End a conversation and clean up"""
    if phone_number in active_conversations:
        debug_log(f"Ending conversation for {phone_number}", "CONVERSATION_END")
        # Log conversation stats if available
        agent = active_conversations.get(phone_number)
        if agent and hasattr(agent, 'state_machine') and hasattr(agent.state_machine, 'context'):
            context = agent.state_machine.context
            turn_count = context.get('turn_count', 0)
            current_state = agent.state_machine.current_state.name if agent.state_machine.current_state else 'UNKNOWN'
            debug_log(f"Conversation stats - Turns: {turn_count}, Final state: {current_state}", "CONVERSATION_STATS")
            
        # Clean up the conversation
        del active_conversations[phone_number]
        debug_log(f"Conversation resources released for {phone_number}", "CLEANUP")
    else:
        debug_log(f"No active conversation found for {phone_number}", "CLEANUP_SKIPPED")
