"""
Example queries for analyzing call logs
Run this after you have some call data logged
"""

import os
from supabase import create_client
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    print("\nMake sure you have:")
    print("1. Created a .env file (copy from .env.example)")
    print("2. Added your Supabase credentials")
    exit(1)

supabase = create_client(supabase_url, supabase_key)


def get_recent_calls(limit=10):
    """Get most recent calls"""
    result = supabase.table('calls').select('*').order('start_time', desc=True).limit(limit).execute()
    return result.data


def get_call_details(call_id):
    """Get full details of a specific call"""
    # Get call info
    call = supabase.table('calls').select('*').eq('call_id', call_id).execute()
    
    # Get all transitions
    transitions = supabase.table('state_transitions').select('*').eq('call_id', call_id).order('sequence_number').execute()
    
    return {
        'call': call.data[0] if call.data else None,
        'transitions': transitions.data
    }


def get_state_transition_stats():
    """Get statistics on state transitions"""
    # This requires a custom query - Supabase Python client doesn't support GROUP BY directly
    # You'd need to use the REST API or create a view
    
    result = supabase.table('state_transitions').select('from_state, to_state').execute()
    
    # Count transitions manually
    transitions = {}
    for t in result.data:
        key = f"{t['from_state']} → {t['to_state']}"
        transitions[key] = transitions.get(key, 0) + 1
    
    # Sort by frequency
    sorted_transitions = sorted(transitions.items(), key=lambda x: x[1], reverse=True)
    return sorted_transitions


def get_optimization_stats():
    """Compare optimized vs fallback transitions"""
    result = supabase.table('state_transitions').select('transition_type, processing_time_ms').execute()
    
    stats = {}
    for t in result.data:
        t_type = t['transition_type']
        if t_type not in stats:
            stats[t_type] = {'count': 0, 'total_time': 0, 'times': []}
        
        stats[t_type]['count'] += 1
        if t['processing_time_ms']:
            stats[t_type]['total_time'] += t['processing_time_ms']
            stats[t_type]['times'].append(t['processing_time_ms'])
    
    # Calculate averages
    for t_type in stats:
        if stats[t_type]['times']:
            stats[t_type]['avg_time'] = stats[t_type]['total_time'] / len(stats[t_type]['times'])
        else:
            stats[t_type]['avg_time'] = 0
    
    return stats


def get_context_field_frequency():
    """Get frequency of context fields collected"""
    result = supabase.table('state_transitions').select('context_updates').execute()
    
    field_counts = {}
    for t in result.data:
        if t['context_updates']:
            for field in t['context_updates'].keys():
                field_counts[field] = field_counts.get(field, 0) + 1
    
    sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_fields


def get_calls_by_status():
    """Get count of calls by completion status"""
    result = supabase.table('calls').select('completion_status').execute()
    
    status_counts = {}
    for call in result.data:
        status = call['completion_status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return status_counts


def get_average_call_duration():
    """Get average call duration"""
    result = supabase.table('calls').select('duration_seconds').execute()
    
    durations = [c['duration_seconds'] for c in result.data if c['duration_seconds']]
    
    if durations:
        return {
            'average': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations),
            'total_calls': len(durations)
        }
    return None


def print_call_flow(call_id):
    """Print a visual representation of a call flow"""
    details = get_call_details(call_id)
    
    if not details['call']:
        print(f"Call {call_id} not found")
        return
    
    call = details['call']
    print(f"\n{'='*60}")
    print(f"Call ID: {call['call_id']}")
    print(f"Session: {call['session_id']}")
    print(f"Duration: {call['duration_seconds']}s")
    print(f"Status: {call['completion_status']}")
    print(f"States visited: {call['total_states_visited']}")
    print(f"LLM calls: {call['total_llm_calls']}")
    print(f"Tokens used: {call['total_tokens_used']}")
    print(f"{'='*60}\n")
    
    print("Flow:")
    for t in details['transitions']:
        arrow = "→" if t['from_state'] != t['to_state'] else "↻"
        updates = list(t['context_updates'].keys()) if t['context_updates'] else []
        updates_str = f" [{', '.join(updates)}]" if updates else ""
        
        print(f"  {t['sequence_number']:2d}. {t['from_state']:20s} {arrow} {t['to_state']:20s} {updates_str}")
        print(f"      User: {t['user_input'][:50]}...")
        print(f"      Agent: {t['agent_response'][:50]}...")
        print(f"      Type: {t['transition_type']}, Time: {t['processing_time_ms']}ms")
        print()


def generate_mermaid_diagram(call_id):
    """Generate Mermaid diagram for a call"""
    details = get_call_details(call_id)
    
    if not details['call']:
        return None
    
    mermaid = "graph TD\n"
    
    for t in details['transitions']:
        from_state = t['from_state'] or 'START'
        to_state = t['to_state']
        
        # Get context updates for label
        updates = t.get('context_updates', {})
        if updates:
            label = ', '.join(list(updates.keys())[:3])  # Limit to 3 fields
        else:
            label = t.get('transition_type', '')
        
        # Add edge
        mermaid += f"    {from_state}-->|{label}|{to_state}\n"
    
    return mermaid


if __name__ == '__main__':
    print("Call Analytics Dashboard")
    print("=" * 60)
    
    # Recent calls
    print("\n📞 Recent Calls:")
    recent = get_recent_calls(5)
    for call in recent:
        print(f"  {call['session_id']}: {call['completion_status']} ({call['duration_seconds']}s)")
    
    # Call status breakdown
    print("\n📊 Calls by Status:")
    statuses = get_calls_by_status()
    for status, count in statuses.items():
        print(f"  {status}: {count}")
    
    # Average duration
    print("\n⏱️  Call Duration Stats:")
    duration_stats = get_average_call_duration()
    if duration_stats:
        print(f"  Average: {duration_stats['average']:.1f}s")
        print(f"  Min: {duration_stats['min']}s")
        print(f"  Max: {duration_stats['max']}s")
    
    # Optimization stats
    print("\n⚡ Optimization Stats:")
    opt_stats = get_optimization_stats()
    for t_type, stats in opt_stats.items():
        print(f"  {t_type}: {stats['count']} transitions, avg {stats['avg_time']:.0f}ms")
    
    # Top state transitions
    print("\n🔄 Top State Transitions:")
    transitions = get_state_transition_stats()[:10]
    for transition, count in transitions:
        print(f"  {transition}: {count}")
    
    # Top context fields
    print("\n📝 Most Collected Fields:")
    fields = get_context_field_frequency()[:10]
    for field, count in fields:
        print(f"  {field}: {count}")
    
    # Example: Print detailed flow for most recent call
    if recent:
        print("\n" + "="*60)
        print("Detailed Flow for Most Recent Call:")
        print_call_flow(recent[0]['call_id'])
        
        print("\nMermaid Diagram:")
        print(generate_mermaid_diagram(recent[0]['call_id']))
