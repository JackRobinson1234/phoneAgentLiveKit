-- Supabase Schema for Call Logging
-- Run this in Supabase SQL Editor

-- Calls table - stores high-level call information
CREATE TABLE IF NOT EXISTS calls (
    call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    user_phone VARCHAR(50),
    initial_state VARCHAR(50) NOT NULL,
    final_state VARCHAR(50),
    completion_status VARCHAR(50), -- 'completed', 'error', 'abandoned', 'in_progress'
    total_states_visited INTEGER DEFAULT 0,
    total_llm_calls INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- State transitions table - stores each state change and context
CREATE TABLE IF NOT EXISTS state_transitions (
    id BIGSERIAL PRIMARY KEY,
    call_id UUID REFERENCES calls(call_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sequence_number INTEGER NOT NULL,
    from_state VARCHAR(50),
    to_state VARCHAR(50) NOT NULL,
    transition_type VARCHAR(50), -- 'optimized', 'fallback', 'error', 'continue'
    user_input TEXT,
    agent_response TEXT,
    context_snapshot JSONB, -- Full context at this moment
    context_updates JSONB, -- What changed in this step
    llm_model VARCHAR(100),
    llm_tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_calls_start_time ON calls(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_calls_session ON calls(session_id);
CREATE INDEX IF NOT EXISTS idx_calls_status ON calls(completion_status);
CREATE INDEX IF NOT EXISTS idx_transitions_call ON state_transitions(call_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_transitions_states ON state_transitions(from_state, to_state);
CREATE INDEX IF NOT EXISTS idx_transitions_timestamp ON state_transitions(timestamp DESC);

-- GIN index for JSONB queries (search within context)
CREATE INDEX IF NOT EXISTS idx_context_snapshot ON state_transitions USING GIN (context_snapshot);
CREATE INDEX IF NOT EXISTS idx_context_updates ON state_transitions USING GIN (context_updates);

-- Enable Row Level Security (RLS)
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE state_transitions ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for now - you can restrict later)
CREATE POLICY "Enable all access for authenticated users" ON calls
    FOR ALL USING (true);

CREATE POLICY "Enable all access for authenticated users" ON state_transitions
    FOR ALL USING (true);

-- Function to update call statistics
CREATE OR REPLACE FUNCTION update_call_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE calls
    SET 
        total_states_visited = (
            SELECT COUNT(DISTINCT to_state) 
            FROM state_transitions 
            WHERE call_id = NEW.call_id
        ),
        total_llm_calls = (
            SELECT COUNT(*) 
            FROM state_transitions 
            WHERE call_id = NEW.call_id AND llm_tokens_used > 0
        ),
        total_tokens_used = (
            SELECT COALESCE(SUM(llm_tokens_used), 0)
            FROM state_transitions 
            WHERE call_id = NEW.call_id
        )
    WHERE call_id = NEW.call_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update stats
CREATE TRIGGER update_call_stats_trigger
    AFTER INSERT ON state_transitions
    FOR EACH ROW
    EXECUTE FUNCTION update_call_stats();

-- View for easy flow visualization
CREATE OR REPLACE VIEW call_flows AS
SELECT 
    c.call_id,
    c.session_id,
    c.start_time,
    c.completion_status,
    json_agg(
        json_build_object(
            'sequence', st.sequence_number,
            'from_state', st.from_state,
            'to_state', st.to_state,
            'transition_type', st.transition_type,
            'context_updates', st.context_updates,
            'timestamp', st.timestamp
        ) ORDER BY st.sequence_number
    ) as transitions
FROM calls c
LEFT JOIN state_transitions st ON c.call_id = st.call_id
GROUP BY c.call_id, c.session_id, c.start_time, c.completion_status;
