#!/usr/bin/env python3
"""
Twilio SIP Bridge - Routes Twilio calls to LiveKit
Minimal webhook to bridge Twilio PSTN to LiveKit SIP
"""

from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Dial
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Your LiveKit SIP endpoint
LIVEKIT_SIP_ENDPOINT = os.getenv('LIVEKIT_SIP_ENDPOINT', 'sip:animal-control@sip.livekit.cloud')

@app.route("/twilio-bridge", methods=['POST'])
def twilio_bridge():
    """
    Webhook endpoint for Twilio to forward calls to LiveKit via SIP
    
    Configure in Twilio:
    Voice Configuration → A call comes in → Webhook → https://your-domain.com/twilio-bridge
    """
    # Get caller information
    caller = request.values.get('From', 'Unknown')
    call_sid = request.values.get('CallSid', '')
    
    print(f"Incoming call from {caller}, Call SID: {call_sid}")
    
    # Create TwiML response to forward to LiveKit
    response = VoiceResponse()
    dial = Dial()
    
    # Forward the call to LiveKit SIP endpoint
    dial.sip(LIVEKIT_SIP_ENDPOINT)
    response.append(dial)
    
    return str(response)

@app.route("/health", methods=['GET'])
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "twilio-livekit-bridge"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
