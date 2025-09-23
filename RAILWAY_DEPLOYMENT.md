# Railway Deployment Guide for Animal Control API

This guide explains how to deploy the Animal Control API to Railway for use with Twilio integration.

## Prerequisites

1. A [Railway](https://railway.app/) account
2. [Git](https://git-scm.com/) installed on your machine
3. An [OpenRouter](https://openrouter.ai/) API key
4. A [Twilio](https://www.twilio.com/) account with phone number

## Deployment Steps

### 1. Prepare Your Repository

Ensure your repository includes these files (already created):
- `Procfile` - Tells Railway how to run your app
- `runtime.txt` - Specifies Python version
- `requirements.txt` - Lists all dependencies
- `.env.example` - Template for environment variables

### 2. Deploy to Railway

#### Option 1: Deploy from GitHub

1. Push your code to GitHub
2. Log in to [Railway](https://railway.app/)
3. Click "New Project" → "Deploy from GitHub"
4. Select your repository
5. Railway will automatically detect the Python project

#### Option 2: Deploy with Railway CLI

1. Install the Railway CLI:
   ```bash
   npm i -g @railway/cli
   ```

2. Login to Railway:
   ```bash
   railway login
   ```

3. Initialize a new project:
   ```bash
   railway init
   ```

4. Deploy your app:
   ```bash
   railway up
   ```

### 3. Configure Environment Variables

In the Railway dashboard:

1. Go to your project
2. Click on "Variables"
3. Add the following variables:
   - `OPENROUTER_API_KEY` - Your OpenRouter API key
   - `TWILIO_ACCOUNT_SID` - Your Twilio Account SID
   - `TWILIO_AUTH_TOKEN` - Your Twilio Auth Token
   - `TWILIO_PHONE_NUMBER` - Your Twilio phone number
   - `DEBUG` - Set to "False" for production

### 4. Configure Twilio Webhook

1. Get your Railway deployment URL from the Railway dashboard
2. Go to your Twilio account
3. Navigate to "Phone Numbers" → Select your number
4. Under "Messaging":
   - Set the webhook URL to: `https://your-railway-url.up.railway.app/webhook/sms`
   - Set the method to "HTTP POST"
5. Under "Voice":
   - Set the webhook URL to: `https://your-railway-url.up.railway.app/webhook/voice`
   - Set the method to "HTTP POST"

### 5. Test Your Deployment

1. Send an SMS to your Twilio phone number
2. The message should be processed by your API on Railway
3. You should receive a response from the Animal Control Agent

## Troubleshooting

### API Not Responding
- Check Railway logs for errors
- Verify environment variables are set correctly
- Ensure the Procfile is configured properly

### Twilio Integration Issues
- Verify webhook URLs are correct
- Check Twilio logs for request/response details
- Ensure your Twilio number has SMS and voice capabilities enabled

## Monitoring and Maintenance

- Railway provides logs and metrics for your deployment
- Set up notifications for deployment failures
- Consider setting up a staging environment for testing changes

## Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Twilio SMS Quickstart](https://www.twilio.com/docs/sms/quickstart)
- [Twilio Voice Quickstart](https://www.twilio.com/docs/voice/quickstart)
