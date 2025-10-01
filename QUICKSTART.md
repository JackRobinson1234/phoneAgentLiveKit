# Quick Start Guide

Get your call logging system up and running in 10 minutes!

## 🚀 Quick Setup (10 minutes)

### 1. Run SQL Schema (3 min)

1. Open [Supabase Dashboard](https://supabase.com/dashboard)
2. Go to **SQL Editor**
3. Copy all content from `database/schema.sql`
4. Paste and click **Run**
5. ✅ You should see "Success. No rows returned"

### 2. Configure Environment (2 min)

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your credentials:
SUPABASE_URL=https://aupkbdhnljgoqwkjyxlg.supabase.co
SUPABASE_KEY=your_anon_key_here
```

Your Supabase key is in: Dashboard → Settings → API → anon public key

### 3. Install Dependencies (2 min)

```bash
pip install --upgrade supabase websockets
```

### 4. Test Setup (3 min)

```bash
python test_logging.py
```

You should see:
```
✅ Logger initialized successfully!
✅ Call started: <uuid>
✅ Transition 1 logged
✅ Transition 2 logged
✅ Call ended
✅ All Tests Passed!
```

### 5. Verify in Supabase (1 min)

1. Go to Supabase Dashboard
2. Click **Table Editor**
3. Select `calls` table
4. You should see your test call!

## ✅ You're Done!

Your agent will now automatically log all calls. Every conversation will be tracked with:
- Full state transition history
- User inputs and agent responses
- Context updates
- LLM usage and performance metrics

## 📊 View Your Data

### In Supabase Dashboard
- **Table Editor** → Browse `calls` and `state_transitions`
- **SQL Editor** → Run custom queries

### Using Python
```bash
# Run analytics dashboard
python database/example_queries.py
```

This shows:
- Recent calls
- Completion rates
- Performance metrics
- Top state transitions
- Mermaid flow diagrams

### Generate Flow Diagram
```python
from src.logging import CallLogger

logger = CallLogger()
mermaid = logger.generate_mermaid_flow(call_id='your-call-id')
print(mermaid)
```

Paste output into [Mermaid Live](https://mermaid.live/) to visualize!

## 🎯 What Gets Logged

Every call logs:
- ✅ Session ID and timestamps
- ✅ Duration and completion status
- ✅ All state transitions
- ✅ User inputs and agent responses
- ✅ Context snapshots (what data was collected)
- ✅ LLM usage (model, tokens, response time)
- ✅ Optimization type (single vs double LLM call)

## 📈 Key Metrics

### Check Optimization Effectiveness
```sql
SELECT 
    transition_type,
    COUNT(*) as count,
    AVG(processing_time_ms) as avg_time
FROM state_transitions
WHERE from_state != to_state
GROUP BY transition_type;
```

**Expected:** `optimized` transitions ~50% faster than `fallback`

### Check Completion Rate
```sql
SELECT 
    completion_status,
    COUNT(*) as count
FROM calls
GROUP BY completion_status;
```

### Most Common Paths
```sql
SELECT 
    from_state || ' → ' || to_state as transition,
    COUNT(*) as frequency
FROM state_transitions
WHERE from_state != to_state
GROUP BY from_state, to_state
ORDER BY frequency DESC
LIMIT 10;
```

## 🐛 Troubleshooting

### "Logger initialization failed"

**Check environment variables:**
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('SUPABASE_URL')); print(os.getenv('SUPABASE_KEY'))"
```

Should print your URL and key. If not:
- Make sure `.env` file exists
- Check that values are set correctly
- No quotes needed around values

### "No data appearing"

**Check if logger is enabled:**
Look for this when starting your agent:
```
✅ Call logger initialized successfully
```

If you see:
```
⚠️ Call logger disabled - Supabase credentials not found
```

Then your `.env` file isn't being loaded.

### "Connection refused"

**Verify Supabase project is active:**
1. Go to Supabase Dashboard
2. Check project status
3. Try running a query in SQL Editor

## 📚 Documentation

- **`SETUP_LOGGING.md`** - Detailed setup guide
- **`IMPLEMENTATION_SUMMARY.md`** - What was built and why
- **`database/README.md`** - Database schema documentation
- **`database/example_queries.py`** - Query examples

## 🎉 Next Steps

### Immediate
1. ✅ Make some test calls
2. ✅ Check data in Supabase
3. ✅ Run `example_queries.py`
4. ✅ Generate Mermaid diagrams

### Soon
1. Build a dashboard to visualize flows
2. Set up alerts for errors
3. Track metrics over time
4. A/B test different prompts

### Later
1. Export data for BI tools
2. ML-based flow optimization
3. Predictive analytics
4. Multi-language tracking

## 💡 Pro Tips

### Performance
- Indexes are already created for fast queries
- Use date ranges for large datasets
- JSONB queries work great for context searches

### Security
- Anon key is safe for client use (with RLS)
- Service key for admin operations only
- Enable RLS policies for production

### Cost
- Free tier: 500MB database, 2GB bandwidth
- Typical usage: ~1KB per transition
- 1000 calls/day ≈ 5MB/day ≈ 150MB/month

## 🎯 Success Checklist

- [ ] SQL schema executed successfully
- [ ] Environment variables configured
- [ ] Dependencies installed
- [ ] Test script passes all tests
- [ ] Test call visible in Supabase
- [ ] Can generate Mermaid diagrams
- [ ] Analytics queries work

## 🆘 Need Help?

1. **Check logs** - Look for "📊 LOGGER:" messages
2. **Run test script** - `python test_logging.py`
3. **Check Supabase** - Dashboard → Logs → Postgres Logs
4. **Verify schema** - Table Editor should show `calls` and `state_transitions`

---

**Ready to go!** Your agent is now logging all calls for analytics and debugging. 🎉
