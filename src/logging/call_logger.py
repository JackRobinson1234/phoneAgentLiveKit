"""
Call Logger for tracking conversation flows and state transitions
Logs to Supabase for analytics and debugging
Uses threading to avoid blocking the conversation flow
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from supabase import create_client, Client
import os
import json
import threading
from queue import Queue


class CallLogger:
    """Logs call data and state transitions to Supabase"""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize the call logger with Supabase credentials
        
        Args:
            supabase_url: Supabase project URL (defaults to env var)
            supabase_key: Supabase API key (defaults to env var)
        """
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and Key must be provided or set in environment")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Current call tracking
        self.current_call_id: Optional[uuid.UUID] = None
        self.sequence_number: int = 0
        self.start_time: Optional[datetime] = None
        self.llm_call_count: int = 0
        
        # Async logging with background thread
        self._shutdown = False  # Must be set before starting thread
        self._log_queue = Queue()
        self._worker_thread = threading.Thread(target=self._log_worker, daemon=True)
        self._worker_thread.start()
    
    def _log_worker(self):
        """Background worker that processes log queue"""
        from queue import Empty
        
        while not self._shutdown:
            try:
                # Get log task from queue (blocks until available)
                task = self._log_queue.get(timeout=1)
                
                if task is None:  # Shutdown signal
                    break
                
                # Execute the logging task
                task_type, data = task
                
                if task_type == 'start_call':
                    self._execute_start_call(data)
                elif task_type == 'log_transition':
                    self._execute_log_transition(data)
                elif task_type == 'end_call':
                    self._execute_end_call(data)
                
            except Empty:
                # Timeout waiting for task - this is normal, just continue
                continue
            except Exception as e:
                # Don't let worker thread die on errors
                if not self._shutdown:
                    import traceback
                    print(f"⚠️ LOGGER: Background worker error - {str(e)}")
                    print(f"⚠️ LOGGER: {traceback.format_exc()}")
    
    def start_call(self, session_id: str, initial_state: str, user_phone: str = None) -> uuid.UUID:
        """
        Start tracking a new call
        
        Args:
            session_id: Unique session identifier
            initial_state: Starting state of the conversation
            user_phone: Optional user phone number
            
        Returns:
            UUID of the created call
        """
        self.current_call_id = uuid.uuid4()
        self.sequence_number = 0
        self.start_time = datetime.now()
        self.llm_call_count = 0
        
        # Queue the logging task (non-blocking)
        data = {
            'call_id': str(self.current_call_id),
            'session_id': session_id,
            'start_time': self.start_time.isoformat(),
            'initial_state': initial_state,
            'completion_status': 'in_progress',
            'user_phone': user_phone
        }
        self._log_queue.put(('start_call', data))
        print(f"📊 LOGGER: Queued start call {self.current_call_id}")
            
        return self.current_call_id
    
    def _execute_start_call(self, data: Dict[str, Any]):
        """Execute start_call in background thread"""
        try:
            result = self.supabase.table('calls').insert(data).execute()
            print(f"✅ LOGGER: Started call {data['call_id']}")
        except Exception as e:
            print(f"❌ LOGGER ERROR: Failed to start call - {str(e)}")
    
    def log_transition(
        self,
        from_state: Optional[str],
        to_state: str,
        user_input: str,
        agent_response: str,
        context: Dict[str, Any],
        context_updates: Dict[str, Any],
        transition_type: str = 'continue',
        llm_model: str = None,
        llm_tokens: int = None,
        processing_time_ms: int = None
    ):
        """
        Log a state transition
        
        Args:
            from_state: State transitioning from (None for initial)
            to_state: State transitioning to
            user_input: What the user said
            agent_response: What the agent responded
            context: Full context snapshot
            context_updates: What changed in this step
            transition_type: Type of transition (optimized, fallback, continue, error)
            llm_model: LLM model used
            llm_tokens: Tokens consumed
            processing_time_ms: Processing time in milliseconds
        """
        if not self.current_call_id:
            print("⚠️ LOGGER WARNING: No active call to log transition")
            return
        
        self.sequence_number += 1
        
        if llm_tokens:
            self.llm_call_count += 1
        
        # Clean context for JSON serialization
        clean_context = self._clean_for_json(context)
        clean_updates = self._clean_for_json(context_updates)
        
        # Queue the logging task (non-blocking)
        data = {
            'call_id': str(self.current_call_id),
            'timestamp': datetime.now().isoformat(),
            'sequence_number': self.sequence_number,
            'from_state': from_state,
            'to_state': to_state,
            'transition_type': transition_type,
            'user_input': user_input,
            'agent_response': agent_response,
            'context_snapshot': clean_context,
            'context_updates': clean_updates,
            'llm_model': llm_model,
            'llm_tokens_used': llm_tokens,
            'processing_time_ms': processing_time_ms
        }
        self._log_queue.put(('log_transition', data))
        print(f"📊 LOGGER: Queued transition {from_state} → {to_state} (seq: {self.sequence_number})")
    
    def _execute_log_transition(self, data: Dict[str, Any]):
        """Execute log_transition in background thread"""
        try:
            result = self.supabase.table('state_transitions').insert(data).execute()
            print(f"✅ LOGGER: Logged transition {data['from_state']} → {data['to_state']}")
        except Exception as e:
            print(f"❌ LOGGER ERROR: Failed to log transition - {str(e)}")
    
    def end_call(self, final_state: str, completion_status: str = 'completed'):
        """
        End the current call and update final statistics
        
        Args:
            final_state: Final state of the conversation
            completion_status: Status (completed, error, abandoned)
        """
        if not self.current_call_id:
            print("⚠️ LOGGER WARNING: No active call to end")
            return
        
        end_time = datetime.now()
        duration = int((end_time - self.start_time).total_seconds()) if self.start_time else 0
        
        # Queue the logging task (non-blocking)
        data = {
            'call_id': str(self.current_call_id),
            'end_time': end_time.isoformat(),
            'final_state': final_state,
            'completion_status': completion_status,
            'duration_seconds': duration
        }
        self._log_queue.put(('end_call', data))
        print(f"📊 LOGGER: Queued end call {self.current_call_id} - Status: {completion_status}, Duration: {duration}s")
        
        # Reset tracking
        self.current_call_id = None
        self.sequence_number = 0
        self.start_time = None
        self.llm_call_count = 0
    
    def _execute_end_call(self, data: Dict[str, Any]):
        """Execute end_call in background thread"""
        try:
            call_id = data.pop('call_id')
            result = self.supabase.table('calls').update(data).eq('call_id', call_id).execute()
            print(f"✅ LOGGER: Ended call {call_id}")
        except Exception as e:
            print(f"❌ LOGGER ERROR: Failed to end call - {str(e)}")
    
    def _clean_for_json(self, data: Any) -> Any:
        """
        Clean data for JSON serialization
        Only keeps relevant fields for reporting and analytics
        """
        if data is None:
            return None
        
        if isinstance(data, dict):
            # Only include fields relevant for reporting
            # Exclude: UI state, temporary messages, internal tracking
            exclude_keys = [
                'conversation_history',
                'last_llm_response',
                'last_response',
                'message',
                'turn_count',
                'conversation_started',
                'last_user_input',
                'error_message',
                'completion_message'
            ]
            
            cleaned = {}
            for key, value in data.items():
                if key not in exclude_keys:
                    try:
                        # Test if serializable
                        json.dumps(value)
                        cleaned[key] = value
                    except (TypeError, ValueError):
                        # Skip non-serializable values
                        cleaned[key] = str(value)[:100]  # Truncate to 100 chars
            return cleaned
        
        return data
    
    def get_call_flow(self, call_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get the flow diagram data for a call
        
        Args:
            call_id: Call ID to retrieve (defaults to current call)
            
        Returns:
            Dictionary with call info and transitions
        """
        target_call_id = call_id or str(self.current_call_id)
        
        if not target_call_id:
            return None
        
        try:
            # Get call info
            call_result = self.supabase.table('calls').select('*').eq('call_id', target_call_id).execute()
            
            # Get transitions
            transitions_result = self.supabase.table('state_transitions').select(
                'sequence_number, from_state, to_state, transition_type, context_updates, timestamp'
            ).eq('call_id', target_call_id).order('sequence_number').execute()
            
            if call_result.data and len(call_result.data) > 0:
                return {
                    'call': call_result.data[0],
                    'transitions': transitions_result.data
                }
            
        except Exception as e:
            print(f"❌ LOGGER ERROR: Failed to get call flow - {str(e)}")
        
        return None
    
    def generate_mermaid_flow(self, call_id: str = None) -> str:
        """
        Generate a Mermaid diagram for a call flow
        
        Args:
            call_id: Call ID to generate diagram for
            
        Returns:
            Mermaid diagram as string
        """
        flow_data = self.get_call_flow(call_id)
        
        if not flow_data:
            return "graph TD\n    Error[No data available]"
        
        mermaid = "graph TD\n"
        
        for transition in flow_data['transitions']:
            from_state = transition['from_state'] or 'START'
            to_state = transition['to_state']
            
            # Get context updates for label
            updates = transition.get('context_updates', {})
            if updates:
                label = ', '.join(updates.keys())[:30]  # Limit label length
            else:
                label = transition.get('transition_type', '')
            
            # Add edge
            mermaid += f"    {from_state}-->|{label}|{to_state}\n"
        
        return mermaid


# Global instance (optional - can be initialized per call)
_global_logger: Optional[CallLogger] = None


def get_call_logger() -> Optional[CallLogger]:
    """Get the global call logger instance"""
    return _global_logger


def initialize_call_logger(supabase_url: str = None, supabase_key: str = None) -> CallLogger:
    """Initialize and return the global call logger"""
    global _global_logger
    _global_logger = CallLogger(supabase_url, supabase_key)
    return _global_logger
