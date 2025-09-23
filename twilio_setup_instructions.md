# Configuring Twilio with Your Railway Deployment

This guide will walk you through the steps to connect your Twilio phone number (+1 539-309-1337) with your Animal Control API deployed on Railway.

## Prerequisites

- Your Animal Control API deployed on Railway
- Twilio account with the phone number (+1 539-309-1337)
- Twilio Account SID and Auth Token

## Step 1: Update Environment Variables on Railway

1. Go to your Railway project dashboard
2. Navigate to the "Variables" tab
3. Add the following environment variables:
   - `TWILIO_ACCOUNT_SID`: Your Twilio Account SID (found in your Twilio Console)
   - `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token (found in your Twilio Console)
   - `TWILIO_PHONE_NUMBER`: +15393091337

## Step 2: Configure Twilio Webhooks

1. Log in to your [Twilio Console](https://www.twilio.com/console)
2. Navigate to "Phone Numbers" > "Manage" > "Active Numbers"
3. Click on your phone number (+1 539-309-1337)
4. Scroll down to the "Voice & Fax" section:
   - For "A CALL COMES IN", select "Webhook" and enter:
     - URL: `https://phoneagent-production.up.railway.app/webhook/voice`
     - Method: HTTP POST
5. Scroll down to the "Messaging" section:
   - For "A MESSAGE COMES IN", select "Webhook" and enter:
     - URL: `https://phoneagent-production.up.railway.app/webhook/sms`
     - Method: HTTP POST
6. Click "Save" at the bottom of the page

## Step 3: Test Your Integration

### Testing Voice Capabilities

1. Call your Twilio number (+1 539-309-1337) from any phone
2. You should hear the Animal Control greeting
3. Speak to interact with the Animal Control agent
4. The agent will respond using Twilio's text-to-speech capabilities

### Testing SMS Capabilities

1. Send a text message to your Twilio number (+1 539-309-1337)
2. The Animal Control agent should respond to your message
3. Continue the conversation via SMS

## Troubleshooting

### Voice Call Issues

- **No response when calling**: Check your Railway logs for errors. Make sure the `/webhook/voice` endpoint is working correctly.
- **Call connects but no greeting**: Verify that your LLMAnimalControlAgent is properly initialized in the voice handler.
- **Poor speech recognition**: Try speaking clearly and in a quiet environment.

### SMS Issues

- **No response to SMS**: Check your Railway logs for errors. Make sure the `/webhook/sms` endpoint is working correctly.
- **Delayed responses**: This could be due to high latency in the LLM API calls. Consider optimizing your agent's response time.

## Advanced Configuration

### Customizing Voice

You can customize the voice used for text-to-speech in the `twilio_handlers.py` file:

```python
# In the voice_webhook function
gather = Gather(
    input='speech dtmf',
    action='/webhook/voice',
    method='POST',
    speech_timeout='auto',
    enhanced='true',
    language='en-US',
    voice='Polly.Joanna'  # Change this to a different voice
)
```

Available voices include:
- `Polly.Joanna` (female, US English)
- `Polly.Matthew` (male, US English)
- `alice` (female, US English)
- `man` (male, US English)
- `woman` (female, US English)

### Setting Up Fallback URLs

For improved reliability, you can set up fallback URLs in your Twilio configuration:

1. In your Twilio phone number configuration
2. Add fallback URLs for both Voice and Messaging
3. These URLs will be called if your primary webhook fails

## Monitoring and Logs

- Monitor your Railway logs for any errors in handling Twilio requests
- Check your Twilio Console's "Debugger" section for any Twilio-specific issues
- Consider setting up error notifications in both Railway and Twilio

## Security Considerations

- Ensure your Auth Token is kept secure and not exposed in your code
- Consider implementing signature validation for Twilio webhooks
- Regularly rotate your Auth Token for enhanced security
