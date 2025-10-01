# Animal Control Voice Agent

A LiveKit-powered voice AI agent for handling animal control services via phone calls.

## 🎯 Features

- **Real-time voice conversations** using LiveKit Agents
- **Natural language understanding** with OpenAI GPT-4
- **High-quality speech** with Deepgram STT and Cartesia TTS
- **Phone integration** via Twilio SIP trunk
- **State machine logic** for structured conversations
- **Multi-service support**: Emergency cases, found animals, lost pets, surrenders

## 📁 Project Structure

```
phoneAgent/
├── src/                    # Source code
│   ├── agents/            # LLM agent logic
│   ├── state_machine/     # Conversation state machine
│   ├── models/            # Data models
│   ├── utils/             # Utility functions
│   ├── config.py          # Configuration
│   └── settings.py        # Settings
├── docs/                  # Documentation
│   ├── LIVEKIT_SETUP.md
│   ├── LIVEKIT_QUICKSTART.md
│   ├── PHONE_NUMBER_SETUP.md
│   └── TWILIO_VS_LIVEKIT.md
├── scripts/               # Utility scripts
│   └── setup_sip_trunk.py
├── agent.py              # Main LiveKit agent entrypoint
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── Dockerfile           # Docker configuration
└── livekit.toml         # LiveKit configuration
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# LiveKit
LIVEKIT_API_KEY=your_key
LIVEKIT_API_SECRET=your_secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# AI Providers
DEEPGRAM_API_KEY=your_key
OPENAI_API_KEY=your_key
CARTESIA_API_KEY=your_key
OPENROUTER_API_KEY=your_key

# Twilio (for phone integration)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=your_number
```

### 3. Download Model Files

```bash
python agent.py download-files
```

### 4. Test Locally

```bash
# Test in terminal (Python only)
python agent.py console

# Test in browser
python agent.py dev
```

Then visit: https://agents-playground.livekit.io

### 5. Deploy to LiveKit Cloud

```bash
lk agent create
```

## 📞 Phone Integration

### Set Up SIP Trunk

Run the setup script:

```bash
python scripts/setup_sip_trunk.py
```

Or manually create dispatch rule:

```bash
lk sip dispatch create \
  --name "Animal Control" \
  --trunks ST_YOUR_TRUNK_ID \
  --individual "animal-control-"
```

### Configure Twilio

1. Go to Twilio Console → Phone Numbers
2. Select your number
3. **Voice Configuration** → **A call comes in** → Select **Trunk**
4. Choose **LiveKit Trunk**
5. Save

## 🧪 Testing

### Test in Playground

```bash
python agent.py dev
```

Visit https://agents-playground.livekit.io and start speaking!

### Test via Phone

Call your Twilio number and speak with the agent.

### Monitor Logs

```bash
lk agent logs
```

## 📚 Documentation

- **[Quick Start Guide](docs/LIVEKIT_QUICKSTART.md)** - Get running in < 10 minutes
- **[Full Setup Guide](docs/LIVEKIT_SETUP.md)** - Detailed setup instructions
- **[Phone Setup](docs/PHONE_NUMBER_SETUP.md)** - Configure phone integration
- **[Migration Guide](docs/TWILIO_VS_LIVEKIT.md)** - Twilio vs LiveKit comparison

## 🏗️ Architecture

### Voice Pipeline

```
Phone → Twilio → LiveKit SIP → LiveKit Room → Agent
                                                ↓
                                    Deepgram (STT)
                                                ↓
                                    OpenAI (LLM)
                                                ↓
                                    Cartesia (TTS)
                                                ↓
                                    LiveKit → Caller
```

### Agent Logic

The agent uses a state machine to handle different conversation flows:

1. **Greeting** - Initial welcome
2. **Service Determination** - Identify user's need
3. **Information Gathering** - Collect details
4. **Confirmation** - Verify information
5. **Completion** - Finalize and summarize

## 🔧 Development

### Project Dependencies

- **LiveKit Agents** - Voice agent framework
- **OpenAI** - LLM for conversation
- **Deepgram** - Speech-to-text
- **Cartesia** - Text-to-speech
- **Twilio** - Phone infrastructure (optional)

### Adding New Features

1. Update state machine in `src/state_machine/`
2. Add new states in `src/state_machine/animal_control_states.py`
3. Update agent logic in `src/agents/llm_animal_control_agent.py`
4. Test locally with `python agent.py dev`
5. Deploy with `lk agent create`

## 📊 Monitoring

### View Agent Status

```bash
lk agent list
```

### View Logs

```bash
lk agent logs
```

### View SIP Configuration

```bash
lk sip inbound list
lk sip dispatch-rule list
```

## 💰 Cost Estimates

Typical 5-minute call:

- LiveKit: Free (within 10k min/month tier)
- Deepgram STT: ~$0.02
- OpenAI GPT-4o-mini: ~$0.01-0.05
- Cartesia TTS: ~$0.05-0.10
- **Total: ~$0.08-0.17 per call**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

[Your License Here]

## 🆘 Support

- LiveKit Discord: https://livekit.io/discord
- Documentation: https://docs.livekit.io
- Issues: [GitHub Issues](your-repo-url)

## 🙏 Acknowledgments

- LiveKit team for the amazing voice agent framework
- OpenAI for GPT models
- Deepgram for speech recognition
- Cartesia for text-to-speech
