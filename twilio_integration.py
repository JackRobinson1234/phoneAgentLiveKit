from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import os
from agents.llm_animal_control_agent import LLMAnimalControlAgent
import json

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
    
    # Create a new TwiML response
    resp = VoiceResponse()
    
    # Check if this is a new caller
    if caller_id not in caller_sessions:
        # Initialize a new session with the agent
        agent = LLMAnimalControlAgent()
        initial_greeting = agent.get_initial_greeting()
        
        caller_sessions[caller_id] = {
            'agent': agent,
            'context': {'conversation_started': True, 'turn_count': 0},
            'call_sid': call_sid
        }
        
        # Add a greeting and wait for user input
        gather = Gather(input='speech', action='/process_speech', timeout=5,
                        speech_timeout='auto', language='en-US')
        gather.say(initial_greeting)
        resp.append(gather)
        
        # If no input is received, prompt again
        resp.redirect('/answer')
    else:
        # Continue existing conversation
        gather = Gather(input='speech', action='/process_speech', timeout=5,
                       speech_timeout='auto', language='en-US')
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
    
    # Create a new TwiML response
    resp = VoiceResponse()
    
    # Check if we have a session for this caller
    if caller_id in caller_sessions:
        session = caller_sessions[caller_id]
        agent = session['agent']
        context = session['context']
        
        # Update turn count
        context['turn_count'] += 1
        
        # Check for call ending phrases
        if speech_result.lower() in ['goodbye', 'bye', 'end call', 'hang up']:
            resp.say("Thank you for contacting Animal Control Services. Goodbye!")
            resp.hangup()
            # Clean up the session
            del caller_sessions[caller_id]
            return str(resp)
        
        # Process the input through the agent
        result, next_state, updated_context = agent.process_input(speech_result, context)
        
        # Update the session context
        caller_sessions[caller_id]['context'] = updated_context
        
        # Get the response message
        response_message = updated_context.get('message', "I'm processing your request.")
        
        # Respond to the caller and wait for more input
        gather = Gather(input='speech', action='/process_speech', timeout=5,
                       speech_timeout='auto', language='en-US')
        gather.say(response_message)
        resp.append(gather)
        
        # If no input is received, prompt again
        resp.redirect('/process_speech')
    else:
        # Session expired or not found
        resp.say("I'm sorry, but your session has expired. Please call back.")
        resp.hangup()
    
    return str(resp)

@app.route("/status_callback", methods=['POST'])
def status_callback():
    """Handle call status callbacks"""
    call_sid = request.values.get('CallSid')
    call_status = request.values.get('CallStatus')
    
    # If the call ended, clean up the session
    if call_status in ['completed', 'busy', 'failed', 'no-answer', 'canceled']:
        for caller_id, session in list(caller_sessions.items()):
            if session.get('call_sid') == call_sid:
                del caller_sessions[caller_id]
                break
    
    return '', 204  # Return empty response with 204 No Content status

if __name__ == "__main__":
    # Get port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
