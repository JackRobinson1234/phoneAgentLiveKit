# Setting Up Your Animal Control Phone Agent with Twilio

This guide will walk you through setting up a phone number for your Animal Control Agent using Twilio.

## 1. Create a Twilio Account

1. Go to [Twilio's website](https://www.twilio.com/) and sign up for an account
2. Complete the verification process

## 2. Purchase a Phone Number

1. In your Twilio dashboard, navigate to "Phone Numbers" → "Manage" → "Buy a Number"
2. Search for a number with voice capabilities
3. Purchase the number (typically costs ~$1/month plus usage fees)

## 3. Configure Your Webhook URLs

1. Go to your purchased number's configuration page
2. Under "Voice & Fax" section, set the following:
   - When a call comes in: Webhook, with URL: `https://your-server.com/answer` (HTTP POST)
   - Status Callback URL: `https://your-server.com/status_callback` (HTTP POST)

## 4. Deploy Your Flask Application

### Option 1: Deploy to Heroku

1. Create a `Procfile` with the content:
   ```
   web: gunicorn twilio_integration:app
   ```

2. Create a new Heroku app:
   ```
   heroku create animal-control-phone-agent
   git push heroku main
   ```

3. Set your environment variables:
   ```
   heroku config:set OPENAI_API_KEY=your_openai_api_key
   ```

### Option 2: Deploy to Ngrok (for testing)

1. Install ngrok: `pip install pyngrok`
2. Run your Flask app: `python twilio_integration.py`
3. In another terminal, run: `ngrok http 5000`
4. Copy the HTTPS URL provided by ngrok
5. Update your Twilio webhook URLs with this temporary URL

## 5. Test Your Phone Agent

1. Call your Twilio phone number
2. Speak to your Animal Control Agent
3. Check the logs in your deployment platform for any issues

## 6. Optimize for Production

For a production deployment, consider:
- Using a database to store session data instead of in-memory storage
- Implementing authentication for your webhook endpoints
- Setting up monitoring and logging
- Adding error handling and fallback responses

## Troubleshooting

- **No response when calling**: Check your webhook URLs in the Twilio dashboard
- **Error responses**: Check your application logs
- **Poor speech recognition**: Try speaking clearly and in a quiet environment
- **Call disconnects**: Ensure your server is responding within Twilio's timeout limits
