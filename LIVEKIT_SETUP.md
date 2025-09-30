# LiveKit Voice Agent Setup Guide

This guide walks you through setting up the LiveKit voice agent for Animal Control Services.

## Prerequisites

1. **Python >= 3.9** (you have Python 3.13)
2. **LiveKit Cloud Account** - Sign up at https://cloud.livekit.io (free tier available)
3. **AI Provider API Keys**:
   - **Deepgram** (Speech-to-Text): https://deepgram.com
   - **OpenAI** (LLM): https://openai.com
   - **Cartesia** (Text-to-Speech): https://cartesia.ai

## Step 1: Install LiveKit CLI

Install the LiveKit CLI with Homebrew:

```bash
brew install livekit-cli
```

## Step 2: Link Your LiveKit Cloud Project

Authenticate and link your LiveKit Cloud project:

```bash
lk cloud auth
```

This opens a browser window to authenticate. Follow the prompts.

## Step 3: Get Your API Keys

### LiveKit API Keys

Run this command to automatically populate `.env.local` with your LiveKit credentials:

```bash
lk app env -w
```

This creates a `.env.local` file with:
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `LIVEKIT_URL`

### AI Provider Keys

You need to sign up for these services and get API keys:

1. **Deepgram** (STT): https://console.deepgram.com/signup
   - Free tier: 45,000 minutes/year
   - Get your API key from the dashboard

2. **OpenAI** (LLM): https://platform.openai.com/signup
   - You may already have this
   - Get your API key from API Keys section

3. **Cartesia** (TTS): https://cartesia.ai
   - Sign up for an account
   - Get your API key from the dashboard

## Step 4: Configure Environment Variables

Edit `.env.local` (or `.env`) and add your AI provider keys:

```bash
# LiveKit Configuration (auto-populated by lk app env -w)
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# AI Provider Keys
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
CARTESIA_API_KEY=your_cartesia_api_key
```

## Step 5: Install Python Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

Or if using uv (recommended):

```bash
uv pip install -r requirements.txt
```

## Step 6: Download Model Files

Download the required model files for turn detection, VAD, and noise cancellation:

```bash
python agent.py download-files
```

## Step 7: Test in Console Mode (Python Only)

Test your agent locally in your terminal:

```bash
python agent.py console
```

This lets you speak to the agent directly in your terminal using your microphone.

## Step 8: Run in Development Mode

Start your agent in development mode to connect it to LiveKit Cloud:

```bash
python agent.py dev
```

This makes your agent available from anywhere. You can test it using the **LiveKit Agents Playground**:
https://agents-playground.livekit.io

## Step 9: Deploy to LiveKit Cloud

When ready for production, deploy your agent:

```bash
lk agent create
```

This command:
- Creates a `Dockerfile` and `.dockerignore`
- Creates a `livekit.toml` configuration file
- Registers your agent with LiveKit Cloud
- Deploys it automatically

## Agent CLI Modes

### Console Mode (Python only)
```bash
python agent.py console
```
- Runs locally in your terminal
- Uses your microphone and speakers
- Great for testing

### Dev Mode
```bash
python agent.py dev
```
- Connects to LiveKit Cloud
- Available from anywhere via playground
- Hot-reloads on code changes

### Start Mode (Production)
```bash
python agent.py start
```
- Production mode
- No auto-reload
- Optimized for performance

## Telephony Integration

To receive phone calls, you need to set up LiveKit's SIP integration:

1. Go to your LiveKit Cloud project settings
2. Navigate to **SIP** section
3. Follow the instructions to:
   - Get a phone number (via Twilio, Telnyx, or other SIP provider)
   - Configure SIP trunk
   - Route calls to your agent

For telephony, update the noise cancellation in `agent.py`:

```python
room_input_options=RoomInputOptions(
    noise_cancellation=noise_cancellation.BVCTelephony(),  # Use BVCTelephony for phone calls
)
```

## Testing Your Agent

### In Playground
1. Run `python agent.py dev`
2. Open https://agents-playground.livekit.io
3. Connect to your room
4. Start speaking!

### Via Phone (after SIP setup)
1. Deploy your agent: `lk agent create`
2. Configure SIP routing
3. Call your phone number
4. Speak with your agent!

## Customization

### Change Voice
Edit `agent.py` and update the TTS voice ID:

```python
tts=cartesia.TTS(
    model="sonic-2",
    voice="your-voice-id-here"  # Browse voices at cartesia.ai
)
```

### Change LLM Model
```python
llm=openai.LLM(
    model="gpt-4o"  # or "gpt-4", "gpt-3.5-turbo", etc.
)
```

### Adjust Instructions
Modify the `AnimalControlVoiceAssistant.__init__()` method to change the agent's behavior.

## Troubleshooting

### "No module named 'livekit'"
Run: `pip install -r requirements.txt`

### "Model files not found"
Run: `python agent.py download-files`

### "Connection refused"
Make sure you've run `lk cloud auth` and have valid credentials in `.env.local`

### Agent not responding
Check that all API keys are valid and have sufficient credits

## Cost Estimates

Based on typical usage:

- **LiveKit**: Free tier includes 10,000 participant minutes/month
- **Deepgram**: Free tier includes 45,000 minutes/year (~$0.0043/min after)
- **OpenAI GPT-4o-mini**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **Cartesia**: Pricing varies, check their website

A typical 5-minute call costs approximately:
- LiveKit: Free (within tier)
- Deepgram: ~$0.02
- OpenAI: ~$0.01-0.05
- Cartesia: ~$0.05-0.10
- **Total: ~$0.08-0.17 per 5-minute call**

## Next Steps

1. **Test locally**: `python agent.py console`
2. **Test in playground**: `python agent.py dev`
3. **Set up telephony**: Configure SIP integration
4. **Deploy to production**: `lk agent create`
5. **Monitor usage**: Check LiveKit Cloud dashboard

## Resources

- LiveKit Docs: https://docs.livekit.io
- LiveKit Agents: https://docs.livekit.io/agents/
- Telephony Guide: https://docs.livekit.io/guides/telephony/
- Example Projects: https://github.com/livekit-examples

## Support

- LiveKit Discord: https://livekit.io/discord
- GitHub Issues: https://github.com/livekit/agents
