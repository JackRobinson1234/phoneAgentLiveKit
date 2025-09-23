# Setting Up Railway Environment Variables

To ensure your Railway deployment works correctly with Twilio, you need to set up the following environment variables in your Railway project.

## Required Environment Variables

1. **OPENROUTER_API_KEY**
   - Value: Your OpenRouter API key
   - Example: `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`

2. **TWILIO_ACCOUNT_SID**
   - Value: Your Twilio Account SID (found in your Twilio Console)
   - Example: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

3. **TWILIO_AUTH_TOKEN**
   - Value: Your Twilio Auth Token (found in your Twilio Console)
   - Example: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

4. **TWILIO_PHONE_NUMBER**
   - Value: Your Twilio phone number in E.164 format
   - Example: `+15393091337`

5. **PORT**
   - Value: `8080` (to match your Railway port configuration)
   - Note: Railway will automatically set this, but it's good to verify

## How to Set Environment Variables in Railway

1. Go to your Railway project dashboard
2. Click on the "Variables" tab
3. Click "New Variable" for each variable you want to add
4. Enter the variable name (e.g., `OPENROUTER_API_KEY`) and its value
5. Click "Add" to save each variable
6. After adding all variables, Railway will automatically redeploy your application

## Verifying Environment Variables

After setting up your environment variables, you can verify they're working correctly by:

1. Checking your Railway deployment logs for any environment-related errors
2. Testing your Twilio integration by sending an SMS or making a call to your Twilio number
3. Checking the Twilio console logs to see if webhook requests are being made successfully

## Important Notes

- Keep your Auth Token and API keys secure
- Never commit these values directly to your code
- If you need to rotate your credentials, update them in both Twilio and Railway
- The PORT variable should match the port you've configured in your Railway network settings (8080)
