# Test Curl Commands for Railway Deployment

Use these curl commands to test your Animal Control API deployed on Railway. Replace `phoneagent-production.up.railway.app` with your actual Railway domain if it's different.

## Health Check Endpoint

Test if your API is up and running:

```bash
curl https://phoneagent-production.up.railway.app/health
```

Expected response:
```json
{
  "service": "animal-control-api",
  "status": "healthy",
  "timestamp": "2025-09-23T18:32:52.000Z"
}
```

## Conversation Endpoints

### Start a new conversation

```bash
curl -X POST https://phoneagent-production.up.railway.app/conversations
```

Expected response:
```json
{
  "conversation_id": "some-uuid-here",
  "message": "Hello! I'm here to help with animal control services. How can I assist you today?",
  "timestamp": "2025-09-23T18:32:52.000Z"
}
```

### Send a message in a conversation

Replace `{conversation_id}` with the ID received from the previous command:

```bash
curl -X POST \
  https://phoneagent-production.up.railway.app/conversations/{conversation_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "I need to report a stray dog in my neighborhood"}'
```

Expected response:
```json
{
  "message": "I'm sorry to hear about the stray dog. I'd be happy to help you report this. Could you please provide the location where you saw the dog?",
  "timestamp": "2025-09-23T18:33:10.000Z"
}
```

### End a conversation

```bash
curl -X DELETE https://phoneagent-production.up.railway.app/conversations/{conversation_id}
```

Expected response:
```json
{
  "message": "Thank you for using Animal Control Services. Goodbye!",
  "timestamp": "2025-09-23T18:34:05.000Z"
}
```

## Test Twilio Webhook Endpoints

### Test Voice Webhook

This simulates a Twilio voice call webhook:

```bash
curl -X POST \
  https://phoneagent-production.up.railway.app/webhook/voice \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=%2B15551234567"
```

Expected response: TwiML response with voice instructions

### Test SMS Webhook

This simulates a Twilio SMS webhook:

```bash
curl -X POST \
  https://phoneagent-production.up.railway.app/webhook/sms \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "From=%2B15551234567&Body=Help%20with%20animal%20control"
```

Expected response: TwiML response with SMS message

## Test with More Complex Scenarios

### Report a stray animal (full conversation flow)

```bash
# Start conversation
CONV_ID=$(curl -s -X POST https://phoneagent-production.up.railway.app/conversations | jq -r '.conversation_id')

# Send initial report
curl -X POST \
  https://phoneagent-production.up.railway.app/conversations/$CONV_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "I need to report a stray dog in my neighborhood"}'

# Provide location
curl -X POST \
  https://phoneagent-production.up.railway.app/conversations/$CONV_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "Near 123 Main Street, behind the grocery store"}'

# Provide description
curl -X POST \
  https://phoneagent-production.up.railway.app/conversations/$CONV_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "It's a medium-sized brown dog, looks like a labrador mix"}'

# End conversation
curl -X DELETE https://phoneagent-production.up.railway.app/conversations/$CONV_ID
```

## Troubleshooting

If you receive errors:

1. Check that your Railway app is deployed and running
2. Verify the correct port is being used (Railway uses port 8080)
3. Check Railway logs for any errors
4. Ensure your environment variables are set correctly in Railway

## Notes

- For the Twilio webhook tests, these will only return proper TwiML responses but won't actually process through the LLM since they're just simulating the webhook call
- The `%2B` in the phone numbers is the URL-encoded version of the plus sign
- For the complex scenario, you'll need `jq` installed to parse the JSON response
