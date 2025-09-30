# Connecting Your Twilio Phone Number to LiveKit

This guide shows you how to connect your Twilio phone number `(539) 309-1337` to your LiveKit voice agent.

## Overview

You have 3 options:

1. **SIP Bridge** (Recommended) - Keep Twilio number, forward to LiveKit via SIP
2. **Direct TwiML** - Simple webhook that forwards calls
3. **Port to LiveKit** - Move number entirely to LiveKit (advanced)

---

## Option 1: SIP Bridge (Recommended)

This keeps your Twilio number but routes calls to LiveKit for processing.

### Step 1: Get LiveKit SIP Endpoint

1. Go to https://cloud.livekit.io
2. Navigate to your project → **Settings** → **SIP**
3. Enable SIP integration
4. Copy your SIP endpoint (e.g., `sip:your-project@sip.livekit.cloud`)

### Step 2: Add to Environment Variables

Add to `.env`:
```bash
LIVEKIT_SIP_ENDPOINT=sip:your-project@sip.livekit.cloud
```

### Step 3: Deploy the Bridge

You have two options:

#### Option A: Use TwiML Bin (No Code Deploy)

1. In Twilio Console, go to **TwiML Bins**
2. Create new TwiML Bin
3. Add this TwiML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Sip>sip:your-project@sip.livekit.cloud</Sip>
    </Dial>
</Response>
```

4. Save and copy the URL

#### Option B: Deploy Bridge Webhook (More Control)

Deploy `twilio_sip_bridge.py`:

```bash
# Install twilio if needed
pip install twilio

# Run locally for testing
python twilio_sip_bridge.py

# Or deploy to Railway/Heroku/etc
```

### Step 4: Configure Twilio Number

1. Go to Twilio Console → **Phone Numbers** → **Manage** → **Active Numbers**
2. Click on `(539) 309-1337`
3. Under **Voice Configuration**:
   - **A call comes in**: Select **TwiML Bin** (Option A) or **Webhook** (Option B)
   - **URL**: Enter your TwiML Bin URL or webhook URL
   - **HTTP Method**: POST
4. Click **Save**

### Step 5: Configure LiveKit SIP Routing

In LiveKit Cloud dashboard:

1. Go to **SIP** → **Inbound Rules**
2. Add rule to route calls to your agent
3. Configure room name pattern (e.g., `animal-control-{callId}`)

### Step 6: Deploy Your Agent

```bash
# Deploy to LiveKit Cloud
lk agent create

# Or run in dev mode for testing
python agent.py dev
```

### Step 7: Test!

Call `(539) 309-1337` and you should be connected to your LiveKit agent!

---

## Option 2: Direct TwiML (Simplest)

If LiveKit SIP isn't available yet, use direct TwiML forwarding:

### In Twilio Console:

1. Go to your phone number `(539) 309-1337`
2. **Voice Configuration** → **A call comes in** → **TwiML Bin**
3. Create TwiML Bin with:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Connecting you to Animal Control Services.</Say>
    <Dial>
        <Sip>sip:animal-control@sip.livekit.cloud</Sip>
    </Dial>
</Response>
```

---

## Option 3: Port Number to LiveKit (Advanced)

Move your number entirely from Twilio to LiveKit:

### Requirements:
- LiveKit Enterprise plan (SIP trunking)
- Or use a SIP provider like Telnyx, Bandwidth

### Steps:

1. **Choose SIP Provider**:
   - Telnyx: https://telnyx.com
   - Bandwidth: https://www.bandwidth.com
   - Twilio Elastic SIP Trunking (keep Twilio, different setup)

2. **Port Your Number**:
   - Request port from Twilio to new provider
   - Takes 7-14 days typically
   - Requires account info and authorization

3. **Configure SIP Trunk**:
   - Point SIP trunk to LiveKit
   - Configure inbound/outbound routing

4. **Update LiveKit**:
   - Configure SIP integration
   - Set up routing rules

---

## Troubleshooting

### Call doesn't connect
- ✅ Check LiveKit SIP endpoint is correct
- ✅ Verify agent is deployed: `lk agent create`
- ✅ Check LiveKit dashboard for SIP logs
- ✅ Ensure Twilio webhook is saved

### Poor audio quality
- ✅ Verify `BVCTelephony()` is used in `agent.py` (already updated)
- ✅ Check network connectivity
- ✅ Review LiveKit audio logs

### Agent doesn't respond
- ✅ Check agent logs: `lk agent logs`
- ✅ Verify API keys are valid (Deepgram, OpenAI, Cartesia)
- ✅ Test agent in playground first

### Twilio shows error
- ✅ Check webhook URL is publicly accessible
- ✅ Verify TwiML syntax is correct
- ✅ Review Twilio debugger logs

---

## Cost Comparison

### Current Setup (Twilio + LiveKit):
- Twilio: $0.013/min (inbound) + $0.001/min (SIP)
- LiveKit: ~$0.009/min (STT + LLM + TTS)
- **Total: ~$0.023/min**

### After Porting to SIP Provider:
- Telnyx: $0.004/min (inbound)
- LiveKit: ~$0.009/min
- **Total: ~$0.013/min (43% cheaper)**

---

## Testing Checklist

- [ ] LiveKit agent deployed and running
- [ ] SIP endpoint configured in LiveKit Cloud
- [ ] Twilio number configured with TwiML/webhook
- [ ] Test call connects successfully
- [ ] Audio quality is clear
- [ ] Agent responds appropriately
- [ ] Call can be ended gracefully

---

## Next Steps

1. **Test in dev mode first**: `python agent.py dev`
2. **Deploy to production**: `lk agent create`
3. **Configure Twilio webhook** with your LiveKit SIP endpoint
4. **Make test call** to verify everything works
5. **Monitor logs** in LiveKit dashboard

---

## Support

- **LiveKit SIP Docs**: https://docs.livekit.io/guides/sip/
- **LiveKit Discord**: https://livekit.io/discord
- **Twilio SIP Docs**: https://www.twilio.com/docs/voice/sip

---

## Quick Reference

**Your Twilio Number**: (539) 309-1337

**LiveKit Project**: phone-agent-hwjoo4vr.livekit.cloud

**Agent File**: `agent.py`

**Bridge File**: `twilio_sip_bridge.py` (if using Option 1B)

**Deploy Command**: `lk agent create`

**Test Command**: `python agent.py dev`
