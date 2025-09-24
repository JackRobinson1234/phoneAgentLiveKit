from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import os
import logging
import datetime
from agents.llm_animal_control_agent import LLMAnimalControlAgent
import json
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

app = Flask(__name__)

# Store conversation state for each caller
# In production, use a database instead of in-memory storage
caller_sessions = {}

@app.route("/answer", methods=['POST'])
def answer_call():
    """Handle incoming calls"""
    # Get the caller's phone number
    caller_id = request.values.get('From', '')
    call_sid = request.values.get('CallSid', '')
    
    debug_print("INCOMING CALL", f"Caller: {caller_id}, Call SID: {call_sid}")
    
    # Create a new TwiML response
    resp = VoiceResponse()
    
    # Check if this is a new caller
    if caller_id not in caller_sessions:
        debug_print("NEW CALLER", f"Caller: {caller_id}")
        # Initialize a new session with the agent
        debug_print("INITIALIZING AGENT", f"For caller: {caller_id}")
        agent = LLMAnimalControlAgent()
        debug_print("GETTING GREETING", f"For caller: {caller_id}")
        initial_greeting = agent.get_initial_greeting()
        
        debug_print("STORING SESSION", f"For caller: {caller_id}")
        caller_sessions[caller_id] = {
            'agent': agent,
            'context': {'conversation_started': True, 'turn_count': 0},
            'call_sid': call_sid
        }
        
        debug_print("SENDING GREETING", f"To caller: {caller_id}, Message: '{initial_greeting[:50]}...'")
        # Add a greeting and wait for user input
        gather = Gather(input='speech', action='/process_speech', timeout_url='/timeout_handler', language='en-US', **DEFAULT_GATHER_PARAMS)
        gather.say(initial_greeting)
        resp.append(gather)
        
        # If no input is received, prompt again
        resp.redirect('/answer')
    else:
        debug_print("CONTINUING CONVERSATION", f"With caller: {caller_id}")
        # Continue existing conversation
        gather = Gather(input='speech', action='/process_speech', timeout_url='/timeout_handler', language='en-US', **DEFAULT_GATHER_PARAMS)
        gather.say("Please continue with your animal control request.")
        resp.append(gather)
    
    return str(resp)

@app.route("/process_speech", methods=['POST'])
def process_speech():
    """Process speech input from the caller"""
    # Get the caller's phone number and speech input
    caller_id = request.values.get('From', '')
    speech_result = request.values.get('SpeechResult', '')
    call_sid = request.values.get('CallSid', '')
    
    debug_print("SPEECH INPUT RECEIVED", f"Caller: {caller_id}, Input: '{speech_result}'")
    
    # Create a new TwiML response
    resp = VoiceResponse()
    
    # Check if we have a session for this caller
    if caller_id in caller_sessions:
        debug_print("SESSION FOUND", f"For caller: {caller_id}")
        session = caller_sessions[caller_id]
        agent = session['agent']
        context = session['context']
        
        # Update turn count
        context['turn_count'] += 1
        debug_print("TURN COUNT UPDATED", f"Caller: {caller_id}, Turn: {context['turn_count']}")
        
        # Check for call ending phrases
        if speech_result.lower() in ['goodbye', 'bye', 'end call', 'hang up']:
            debug_print("CALL ENDING PHRASE DETECTED", f"Caller: {caller_id}, Phrase: '{speech_result}'")
            resp.say("Thank you for contacting Animal Control Services. Goodbye!")
            debug_print("HANGING UP", f"Caller: {caller_id}")
            resp.hangup()
            # Clean up the session
            debug_print("CLEANING UP SESSION", f"For caller: {caller_id}")
            del caller_sessions[caller_id]
            return str(resp)
        
        debug_print("PROCESSING INPUT", f"Caller: {caller_id}, Input length: {len(speech_result)} chars")
        # Process the input through the agent
        result, next_state, updated_context = agent.process_input(speech_result, context)
        debug_print("INPUT PROCESSED", f"Caller: {caller_id}, Next state: {next_state}")
        
        debug_print("UPDATING CONTEXT", f"Caller: {caller_id}")
        # Update the session context
        caller_sessions[caller_id]['context'] = updated_context
        
        # Get the response message
        response_message = updated_context.get('message', "I'm processing your request.")
        debug_print("RESPONSE GENERATED", f"Caller: {caller_id}, Response length: {len(response_message)} chars")
        
        debug_print("SENDING RESPONSE", f"To caller: {caller_id}")
        # Respond to the caller and wait for more input
        gather = Gather(input='speech', action='/process_speech', timeout_url='/timeout_handler', language='en-US', **DEFAULT_GATHER_PARAMS)
        gather.say(response_message)
        resp.append(gather)
        
        # If no input is received, prompt again
        resp.redirect('/process_speech')
    else:
        debug_print("SESSION NOT FOUND", f"For caller: {caller_id}")
        # Session expired or not found
        resp.say("I'm sorry, but your session has expired. Please call back.")
        debug_print("HANGING UP - NO SESSION", f"Caller: {caller_id}")
        resp.hangup()
    
    return str(resp)

@app.route("/timeout_handler", methods=['POST'])
def timeout_handler():
    """Handle timeouts when user doesn't respond"""
    # Get the caller's phone number
    caller_id = request.values.get('From', '')
    call_sid = request.values.get('CallSid', '')
    
    debug_print("TIMEOUT DETECTED", f"Caller: {caller_id}, Call SID: {call_sid}")
    
    # Create a new TwiML response
    resp = VoiceResponse()
    
    # Check if this is the first timeout or a repeated one
    session = caller_sessions.get(caller_id, {})
    timeout_count = session.get('timeout_count', 0)
    
    # Update timeout count
    if caller_id in caller_sessions:
        caller_sessions[caller_id]['timeout_count'] = timeout_count + 1
    else:
        caller_sessions[caller_id] = {'timeout_count': 1}
    
    # If this is the first or second timeout, check if they're still there
    if timeout_count < 2:
        debug_print("CHECKING USER PRESENCE", f"Timeout count: {timeout_count + 1}")
        
        # Ask if they're still there and gather input
        gather = Gather(
            input='speech', 
            action='/process_speech',
            timeout_url='/timeout_handler',
            language='en-US',
            **DEFAULT_GATHER_PARAMS
        )
        
        # Use a different message based on timeout count
        if timeout_count == 0:
            gather.say("Are you still there? I didn't hear anything.")
        else:
            gather.say("I still don't hear a response. Please say something if you're still on the line.")
        
        resp.append(gather)
    else:
        # After multiple timeouts, assume user is gone and hang up
        debug_print("MULTIPLE TIMEOUTS", f"Hanging up after {timeout_count + 1} timeouts")
        resp.say("I haven't heard from you for a while. Please call back when you're ready to continue. Goodbye.")
        resp.hangup()
        
        # Clean up the session
        if caller_id in caller_sessions:
            del caller_sessions[caller_id]
    
    return str(resp)

@app.route("/status_callback", methods=['POST'])
def status_callback():
    """Handle call status callbacks"""
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    
    debug_print("CALL STATUS UPDATE", f"Call SID: {call_sid}, Status: {call_status}")
    
    # If the call ended, clean up the session
    if call_status in ['completed', 'busy', 'failed', 'no-answer', 'canceled']:
        debug_print("CALL ENDED", f"Call SID: {call_sid}, Status: {call_status}")
        for caller_id, session in list(caller_sessions.items()):
            if session.get('call_sid') == call_sid:
                debug_print("CLEANING UP SESSION", f"For caller: {caller_id}, Call SID: {call_sid}")
                del caller_sessions[caller_id]
                debug_print("SESSION REMOVED", f"For caller: {caller_id}")
                break
    
    return '', 204  # Return empty response with 204 No Content status

if __name__ == "__main__":
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
